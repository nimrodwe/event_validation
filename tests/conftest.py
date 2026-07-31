import os
import platform
import sys

import allure
import pytest

from src.config import OUT
from src.local_stack import ensure_running
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
    RUN_STORE.begin_test(item.nodeid)

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

    # Surface parametrize inputs (e.g. field match dicts) in the Allure test.
    callspec = getattr(item, "callspec", None)
    if callspec:
        for key, value in callspec.params.items():
            if isinstance(value, (dict, list)):
                import json

                allure.attach(
                    json.dumps(value, indent=2, default=str),
                    name="param-" + str(key),
                    attachment_type=allure.attachment_type.JSON,
                )
            else:
                allure.dynamic.parameter(str(key), str(value))


def pytest_runtest_logreport(report):
    """Record pass/fail on the dashboard run after the test body finishes."""
    if report.when == "call":
        RUN_STORE.end_test(report.nodeid, report.outcome)


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
    yield ensure_running(open_browser=open_browser)


@pytest.fixture
def initialize(localhost, step_log):
    """Give each test data + steps + the shared localhost receiver."""
    yield BaseClass(localhost, step_log)
