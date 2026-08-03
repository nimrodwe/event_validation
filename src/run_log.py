"""Collect pytest step logs so the dashboard can show each run."""

import json
import logging
from datetime import datetime, timezone

from src.config import TEST_RUNS


def event_uuid(payload):
    if not isinstance(payload, dict):
        return None
    if "UUID" in payload:
        return payload.get("UUID")
    props = payload.get("properties")
    if isinstance(props, dict) and "UUID" in props:
        return props.get("UUID")
    return None


def allure_capture(level, message):
    """Mirror plain log lines into Allure as short steps.

    JSON bodies (full events, headers blobs, etc.) stay on the local dashboard
    step log only — Allure gets the pytest-style expect / POST / GET / findings
    lines for every test, without bulky payloads.
    """
    try:
        import allure
    except ImportError:
        return

    text = message if message is not None else ""
    stripped = text.strip()
    try:
        # Dashboard-only: do not create Allure steps for JSON dumps.
        if stripped.startswith("{") or stripped.startswith("["):
            return

        first = stripped.splitlines()[0] if stripped else ""
        with allure.step("[" + level + "] " + first[:240]):
            pass
    except Exception:
        pass


def parse_dashboard_group(nodeid):
    """
    Group test_negatives[new_keys-e1] / test_type_bad[e1] for the dashboard.

    Negatives: suite → rule folder (new keys) → event-1
    type_bad: suite → event-1 (one test per event; all bad fields in that log)
    """
    from helpers.dataset_negatives import RULE_TITLE_BY_ID

    short = (nodeid or "").split("::")[-1]
    suite = None
    if short.startswith("test_negatives["):
        suite = "test_negatives"
        suite_label = "test_negatives"
    elif short.startswith("test_type_bad["):
        suite = "test_type_bad"
        suite_label = "test_type_bad"
    else:
        return None
    open_b = short.find("[")
    close_b = short.rfind("]")
    if open_b < 0 or close_b <= open_b:
        return None
    inner = short[open_b + 1 : close_b]

    # Negatives: new_keys-e1 → folder "new keys", leaf event-1
    if suite == "test_negatives":
        for kind_id, title in RULE_TITLE_BY_ID.items():
            prefix = kind_id + "-e"
            if not inner.startswith(prefix):
                continue
            event_num = inner[len(prefix) :]
            if not event_num.isdigit():
                continue
            return {
                "group_suite": suite,
                "group_suite_label": suite_label,
                "group_event": kind_id,
                "group_event_label": title,
                "group_leaf": "event-" + event_num,
            }
        return None

    # type_bad: e1 → folder event-1, leaf "bad types" (all findings in one test)
    # Also accept legacy e1-datetime ids.
    if len(inner) < 2 or inner[0] != "e":
        return None
    dash = inner.find("-")
    if dash == -1:
        event_id = inner
        leaf = "bad types"
    else:
        if dash < 2:
            return None
        event_id = inner[:dash]
        leaf = inner[dash + 1 :] or "bad types"
    if not event_id[1:].isdigit():
        return None
    event_num = event_id[1:]
    return {
        "group_suite": suite,
        "group_suite_label": suite_label,
        "group_event": event_id,
        "group_event_label": "event-" + event_num,
        "group_leaf": leaf,
    }


def enrich_test_groups(run):
    """Fill group_* on each test (for older run files that lack them)."""
    for test in run.get("tests") or []:
        if test.get("group_suite") and test.get("group_event"):
            continue
        group = parse_dashboard_group(test.get("nodeid"))
        if group:
            test.update(group)
    return run


def load_runs(limit=20):
    """Newest pytest runs first, for the dashboard."""
    if not TEST_RUNS.exists():
        return []

    runs = []
    for path in TEST_RUNS.glob("*.json"):
        if path.name == "latest.json":
            continue
        try:
            runs.append(enrich_test_groups(json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, OSError):
            continue

    runs.sort(key=lambda r: r.get("started", ""), reverse=True)
    return runs[:limit]


def clear_runs():
    """Delete all saved pytest run logs."""
    if not TEST_RUNS.exists():
        return
    for path in TEST_RUNS.glob("*.json"):
        path.unlink()


def make_step_logger(name, steps):
    """Logger that writes both to the console and to the run store steps list."""
    from helpers.logger import LoggerHelper

    return LoggerHelper(name).add_handler(StepLogHandler(steps)).get()


class StepLogHandler(logging.Handler):
    """Send log records into the dashboard step list and into Allure."""

    def __init__(self, steps):
        super().__init__()
        self.steps = steps

    def emit(self, record):
        message = record.getMessage()
        self.steps.append(
            {
                "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "message": message,
            }
        )
        # extra={"allure": False} → dashboard only (full event dumps, etc.).
        if getattr(record, "allure", True):
            allure_capture(record.levelname, message)


class TestRunStore:
    """One pytest session → one JSON file under out/test_runs/."""

    def __init__(self):
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.started = datetime.now(timezone.utc).isoformat()
        self.tests = []
        self.path = None

    def start(self):
        TEST_RUNS.mkdir(parents=True, exist_ok=True)
        self.path = TEST_RUNS / (self.run_id + ".json")
        self.save()

    def begin_test(self, nodeid, negative=None):
        short = (nodeid or "").split("::")[-1]
        if negative is None:
            negative = short.startswith("test_negatives") or short.startswith(
                "test_type_bad"
            )
        current = {
            "nodeid": nodeid,
            "outcome": "running",
            "uuid": None,
            "negative": bool(negative),
            "steps": [],
        }
        group = parse_dashboard_group(nodeid)
        if group:
            current.update(group)
        self.tests.append(current)
        return current

    def set_uuid(self, nodeid, uuid):
        """Record the first sent UUID for a running test (dashboard label).

        Empty string is kept when that is what was sent.
        Returns True if this call stored the uuid, False if already set / not found.
        """
        for test in reversed(self.tests):
            if test["nodeid"] == nodeid and test["outcome"] == "running":
                if test.get("uuid") is not None:
                    return False
                test["uuid"] = "" if uuid is None else str(uuid)
                self.save()
                return True
        return False

    def end_test(self, nodeid, outcome):
        for test in self.tests:
            if test["nodeid"] == nodeid and test["outcome"] == "running":
                test["outcome"] = outcome
                # Failed tests: ERROR first so the dashboard shows it above POST/GET data.
                if outcome == "failed":
                    steps = test.get("steps") or []
                    errs = [s for s in steps if s.get("level") == "ERROR"]
                    other = [s for s in steps if s.get("level") != "ERROR"]
                    test["steps"] = errs + other
                break
        self.save()

    def finish(self):
        payload = {
            "run_id": self.run_id,
            "started": self.started,
            "finished": datetime.now(timezone.utc).isoformat(),
            "tests": self.tests,
        }
        if self.path is not None:
            self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        latest = TEST_RUNS / "latest.json"
        latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save(self):
        if self.path is None:
            return
        payload = {
            "run_id": self.run_id,
            "started": self.started,
            "finished": None,
            "tests": self.tests,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_runs(self, limit=20):
        return load_runs(limit=limit)

    def clear_runs(self):
        clear_runs()

    def make_step_logger(self, name, steps):
        return make_step_logger(name, steps)
