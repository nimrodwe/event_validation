import os
import platform
import sys

import allure
import pytest

from helpers.asserts import AssertHelper
from helpers.flows import FlowHelper
from src.config import OUT
from src.local_stack import LocalStack
from src.receiver import connect as connect_receiver
from src.run_log import TestRunStore, make_step_logger
from tests.base_class import BaseClass

ALLURE_RESULTS = OUT / "allure-results"
RUN_STORE = TestRunStore()


def pytest_sessionstart(session):
    """Start the dashboard test-run store for this pytest session."""
    RUN_STORE.start()


def pytest_sessionfinish(session, exitstatus):
    """
    Finish the run store, then write Allure environment metadata.

    Environment file is written here (not sessionstart) so --clean-alluredir
    cannot wipe it before generate/serve.
    """
    RUN_STORE.finish()

    ALLURE_RESULTS.mkdir(parents=True, exist_ok=True)
    env_file = ALLURE_RESULTS / "environment.properties"
    lines = [
        "Project=event-validation",
        "Python=" + sys.version.split()[0],
        "Platform=" + platform.platform(),
    ]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Begin a dashboard test entry and attach allure labels."""
    # Marker forces (N); otherwise begin_test auto-detects test_negatives / test_type_bad.
    marker_negative = item.get_closest_marker("negative") is not None
    RUN_STORE.begin_test(
        item.nodeid, negative=True if marker_negative else None
    )

    allure.dynamic.epic("Event Validation")
    path = str(item.fspath).replace("\\", "/")
    if "test_catalog" in path:
        allure.dynamic.feature("Generated catalog")
        allure.dynamic.story(item.name)
    elif "test_data_types" in path:
        allure.dynamic.feature("Data types")
        allure.dynamic.story(item.name)
    else:
        allure.dynamic.feature("Tests")
        allure.dynamic.story(item.name)

    # Allure description = what the test does (from the test docstring).
    doc = (getattr(item, "function", None) and item.function.__doc__) or ""
    doc = " ".join(str(doc).split())
    if doc:
        allure.dynamic.description(doc)


def _hide_allure_suite_parameters():
    """Drop Allure Parameters so Suites shows only the test name.

    pytest-allure stores the full parametrize value (often a huge case dict) under
    the test name. The pytest id is already in the title (e.g. time=-1, new_keys-e1).
    """
    try:
        from allure_commons import plugin_manager
    except ImportError:
        return
    for plugin in plugin_manager.get_plugins():
        logger = getattr(plugin, "allure_logger", None)
        if logger is None:
            continue
        try:
            test_result = logger.get_test(None)
        except Exception:
            continue
        if test_result is None:
            continue
        params = getattr(test_result, "parameters", None)
        if params is not None:
            del params[:]


def _attach_allure_test_log(nodeid):
    """Attach the full step log as test.log (same lines as the dashboard)."""
    steps = _steps_for(nodeid)
    if not steps:
        return
    lines = []
    for step in steps:
        level = step.get("level") or "INFO"
        message = step.get("message")
        if message is None:
            message = ""
        lines.append("[" + str(level) + "] " + str(message))
    try:
        allure.attach(
            "\n".join(lines) + "\n",
            name="test.log",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """After the test body: attach full log, drop bulky Allure parameters."""
    outcome = yield
    if call.when == "call":
        _attach_allure_test_log(item.nodeid)
        _hide_allure_suite_parameters()
    return outcome


def pytest_runtest_logreport(report):
    """Record pass/fail on the dashboard run after the test body finishes."""
    if report.when != "call":
        return
    if report.failed and report.longrepr:
        for test in reversed(RUN_STORE.tests):
            if test["nodeid"] == report.nodeid:
                # Avoid duplicating AssertHelper errors already logged via step_log.
                already = any(
                    s.get("level") == "ERROR" for s in (test.get("steps") or [])
                )
                if not already:
                    from datetime import datetime, timezone

                    test.setdefault("steps", []).append(
                        {
                            "time": datetime.now(timezone.utc).isoformat(),
                            "level": "ERROR",
                            "message": str(report.longrepr),
                        }
                    )
                break
    RUN_STORE.end_test(report.nodeid, report.outcome)


@pytest.hookimpl(tryfirst=True)
def pytest_exception_interact(node, call, report):
    """Attach non-AssertHelper failures to Allure (AssertHelper already attaches)."""
    if call.excinfo is None:
        return
    from helpers.asserts import AssertError

    exc = call.excinfo.value
    if isinstance(exc, AssertError):
        return
    text = str(exc)
    if not text:
        return
    try:
        allure.attach(
            text,
            name="Why it failed",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass


def _steps_for(nodeid):
    for test in reversed(RUN_STORE.tests):
        if test["nodeid"] == nodeid:
            return test["steps"]
    return []


@pytest.fixture
def step_log(request):
    """Logger that writes to the console and to the dashboard step list."""
    steps = _steps_for(request.node.nodeid)
    logger = make_step_logger(request.node.nodeid, steps)
    yield logger
    RUN_STORE.save()


@pytest.fixture(scope="session")
def localhost():
    """Point tests at the local stack; stack stays up after pytest exits."""
    open_browser = os.environ.get("CI", "").lower() not in ("1", "true", "yes")
    yield LocalStack().ensure_running(open_browser=open_browser)


@pytest.fixture
def initialize(localhost, step_log, request):
    """Give each test data + steps + the shared localhost receiver."""
    AssertHelper.log = step_log

    def record_uuid(uuid):
        """Persist the first sent UUID for this test (dashboard + step log / Allure)."""
        text = "" if uuid is None else str(uuid)
        if RUN_STORE.set_uuid(request.node.nodeid, text):
            step_log.info("UUID " + text)

    AssertHelper.record_uuid = record_uuid
    base = BaseClass(localhost, step_log)
    base.record_uuid = record_uuid
    try:
        yield base
    finally:
        AssertHelper.log = None
        AssertHelper.record_uuid = None


@pytest.fixture
def catalog_receiver(tmp_path):
    """Fresh receiver so catalog tests use current server code."""
    server = connect_receiver(tmp_path / "received")
    yield server
    server.disconnect()


@pytest.fixture(scope="module")
def negatives_receiver(tmp_path_factory):
    """
    One receiver for all negative rule tests so event-1 is POSTed once,
    then reused if the same event is checked again in the module.
    """
    FlowHelper._NEG_RECEIVE_CACHE = {}
    root = tmp_path_factory.mktemp("negatives-received")
    server = connect_receiver(root / "received")
    yield server
    server.disconnect()
    FlowHelper._NEG_RECEIVE_CACHE = {}


@pytest.fixture(scope="module")
def type_bad_receiver(tmp_path_factory):
    """One receiver for type_bad field tests (shared POST per event)."""
    FlowHelper._TYPE_BAD_RECEIVE_CACHE = {}
    root = tmp_path_factory.mktemp("type-bad-received")
    server = connect_receiver(root / "received")
    yield server
    server.disconnect()
    FlowHelper._TYPE_BAD_RECEIVE_CACHE = {}
