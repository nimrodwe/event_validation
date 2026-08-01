"""Collect pytest step logs so the dashboard can show each run."""

import json
import logging
from datetime import datetime, timezone

from src.config import TEST_RUNS


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
        self._allure_capture(record.levelname, message)

    @staticmethod
    def _allure_capture(level, message):
        try:
            import allure
            from allure_commons.types import AttachmentType
        except ImportError:
            return

        text = message if message is not None else ""
        stripped = text.strip()
        title = level + " log"
        try:
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    pretty = json.dumps(json.loads(stripped), indent=2)
                except (json.JSONDecodeError, TypeError):
                    pretty = stripped
                allure.attach(pretty, name=title, attachment_type=AttachmentType.JSON)
            else:
                with allure.step("[" + level + "] " + stripped[:240]):
                    if len(stripped) > 240:
                        allure.attach(stripped, name=title, attachment_type=AttachmentType.TEXT)
        except Exception:
            pass


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

    def begin_test(self, nodeid):
        current = {
            "nodeid": nodeid,
            "outcome": "running",
            "uuid": None,
            "steps": [],
        }
        self.tests.append(current)
        return current

    def set_uuid(self, nodeid, uuid):
        """Record the first UUID for a running test (the one sent at the start).

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

    @staticmethod
    def load_runs(limit=20):
        """Newest pytest runs first, for the dashboard."""
        if not TEST_RUNS.exists():
            return []

        runs = []
        for path in TEST_RUNS.glob("*.json"):
            if path.name == "latest.json":
                continue
            try:
                runs.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue

        runs.sort(key=lambda r: r.get("started", ""), reverse=True)
        return runs[:limit]

    @staticmethod
    def clear_runs():
        """Delete all saved pytest run logs."""
        if not TEST_RUNS.exists():
            return
        for path in TEST_RUNS.glob("*.json"):
            path.unlink()

    @staticmethod
    def make_step_logger(name, steps):
        """Logger that writes both to the console and to the run store steps list."""
        from helpers.logger import LoggerHelper

        return LoggerHelper(name).add_handler(StepLogHandler(steps)).get()
