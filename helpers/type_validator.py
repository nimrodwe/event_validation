"""Type validator — schema type checks used by synthetic/dataset helpers."""

from datetime import date, datetime


class TypeValidator:
    def __init__(self, logger):
        self.log = logger

    def fits_type(self, value, expected_type):
        text = expected_type.lower()

        if value is None:
            return "nullable" in text
        if "bool" in text:
            if isinstance(value, bool):
                return True
            return isinstance(value, str) and value.lower() in ("true", "false")
        if "map(" in text:
            return isinstance(value, dict)
        if "string" in text:
            return isinstance(value, str)
        if "datetime" in text:
            return isinstance(value, (datetime, date))
        if "int" in text or "float" in text:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return True
