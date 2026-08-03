"""Logger helper — create and format loggers for steps/tests."""

import json
import logging
from datetime import datetime


def quiet_logger(name="parametrize"):
    """Quiet logger for building parametrize cases (no console spam)."""
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def type_line(match):
    """Standard one-line field type message for tests/dashboard."""
    return (
        "field=" + match["field"]
        + " actual=" + repr(match["actual"])
        + " expected_type=" + match["expected_type"]
    )


def _parse_dataset_datetime(text):
    """Parse validation-dataset datetime strings into datetime when possible."""
    if not isinstance(text, str) or not text.strip():
        return None
    for fmt in (
        "%B %d, %Y, %H:%M:%S",  # July 14, 2026, 16:43:11
        "%B %d, %Y, %H:%M",  # July 14, 2026, 16:43
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def expected_value_example(expected_type, actual=None):
    """
    What a correct value should look like for this EventsSchema type.

    Prefer deriving from the bad actual when we can (e.g. prose date → datetime(...)).
    """
    text = str(expected_type or "").lower()
    if "datetime" in text:
        parsed = _parse_dataset_datetime(actual)
        if parsed is not None:
            return (
                "datetime("
                + ", ".join(
                    [
                        str(parsed.year),
                        str(parsed.month),
                        str(parsed.day),
                        str(parsed.hour),
                        str(parsed.minute),
                        str(parsed.second),
                    ]
                )
                + ")"
            )
        return "datetime(YYYY, M, D, h, m, s)"
    if "map(" in text:
        # Emphasize type: schema wants a dict, not a JSON string with the same text.
        return "dict / Map(String, String) — not a JSON string"
    if "bool" in text:
        return "True  (or False / \"true\" / \"false\")"
    if "int" in text:
        return "123"
    if "float" in text:
        return "1.23"
    if "string" in text:
        return '"some text"'
    return "<value of type " + str(expected_type) + ">"


def _short_got(actual, max_len=80):
    """Compact got= for logs (avoid huge JSON blobs hiding the expected type)."""
    text = repr(actual)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_type_bad_finding(match):
    """Short type_bad finding: field, got (type), what it needed to be, PASS."""
    actual = match.get("actual")
    expected_type = match.get("expected_type")
    expected_value = expected_value_example(expected_type, actual)
    return (
        str(match.get("field"))
        + " got="
        + _short_got(actual)
        + " ("
        + type(actual).__name__
        + ")"
        + " expected="
        + expected_value
        + " ["
        + str(expected_type)
        + "]"
        + " result=PASS"
    )


class LoggerHelper:
    FORMAT = "[%(levelname)s] %(message)s"

    def __init__(self, name="app", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.handlers.clear()
        self.logger.setLevel(level)
        self.logger.propagate = False
        self.add_console()

    def add_console(self):
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(self.FORMAT))
        self.logger.addHandler(console)
        return self

    def add_handler(self, handler):
        self.logger.addHandler(handler)
        return self

    def get(self):
        return self.logger

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

    def type_line(self, match):
        return type_line(match)

    def collect(self, name="parametrize"):
        return quiet_logger(name)
