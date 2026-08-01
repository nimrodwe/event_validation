"""Logger helper — create and format loggers for steps/tests."""

import logging


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
