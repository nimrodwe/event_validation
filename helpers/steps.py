"""Base step — logger + type helper."""

from datetime import date, datetime

# Probe every value against these schema-style types (dashboard type matrix).
TYPE_PROBES = (
    "String",
    "Nullable(Bool)",
    "Int64",
    "Float64",
    "DateTime64(3)",
    "Map(String, String)",
)


def type_family(type_name):
    """Map a schema type string to a coarse family used by fits_type."""
    text = str(type_name).lower()
    if "bool" in text:
        return "bool"
    if "map(" in text:
        return "map"
    if "datetime" in text:
        return "datetime"
    if "string" in text:
        return "string"
    if "int" in text or "float" in text:
        return "number"
    return "other"


class Step:
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
