"""Assertion wrappers with clear failure messages."""


class AssertError(AssertionError):
    """Raised by AssertHelper with a formatted message."""


class AssertHelper:
    @staticmethod
    def _fail(title, details):
        lines = [title]
        for key, value in details:
            lines.append("  " + key + ": " + str(value))
        raise AssertError("\n".join(lines))

    @classmethod
    def truthy(cls, value, message="Expected a truthy value"):
        if value:
            return value
        cls._fail(message, [("actual", repr(value))])

    @classmethod
    def equal(cls, actual, expected, message="Values are not equal"):
        if actual == expected:
            return actual
        cls._fail(
            message,
            [
                ("expected", repr(expected)),
                ("actual", repr(actual)),
            ],
        )

    @classmethod
    def not_equal(cls, actual, unexpected, message="Values should not be equal"):
        if actual != unexpected:
            return actual
        cls._fail(
            message,
            [
                ("unexpected", repr(unexpected)),
                ("actual", repr(actual)),
            ],
        )

    @classmethod
    def is_true(cls, value, message="Expected True"):
        if value is True:
            return value
        cls._fail(message, [("actual", repr(value))])

    @classmethod
    def is_false(cls, value, message="Expected False"):
        if value is False:
            return value
        cls._fail(message, [("actual", repr(value))])

    @classmethod
    def has_key(cls, mapping, key, message=None):
        if key in mapping and mapping.get(key):
            return mapping[key]
        if message is None:
            message = "Missing required key: " + str(key)
        cls._fail(
            message,
            [
                ("key", repr(key)),
                ("value", repr(mapping.get(key))),
                ("available_keys", sorted(str(k) for k in mapping.keys())),
            ],
        )

    @classmethod
    def status_code(cls, response, expected, message=None):
        actual = getattr(response, "status_code", None)
        if actual == expected:
            return actual
        body = getattr(response, "text", "")
        if message is None:
            message = "Unexpected HTTP status code"
        cls._fail(
            message,
            [
                ("expected", expected),
                ("actual", actual),
                ("body", body[:500] if body else "<empty>"),
            ],
        )

    @classmethod
    def fits_type(cls, steps, match, message=None):
        """Assert value matches expected schema type (positive case)."""
        field = match.get("field", "<unknown>")
        expected_type = match.get("expected_type", "<unknown>")
        actual = match.get("actual")
        ok = steps.fits_type(actual, expected_type)
        if ok:
            return True
        if message is None:
            message = "Type check failed for field '" + str(field) + "'"
        cls._fail(
            message,
            [
                ("field", field),
                ("expected_type", expected_type),
                ("actual_type", type(actual).__name__),
                ("value", repr(actual)),
            ],
        )

    @classmethod
    def type_mismatch(cls, steps, match, message=None):
        """Assert value does NOT match expected schema type (negative case)."""
        field = match.get("field", "<unknown>")
        expected_type = match.get("expected_type", "<unknown>")
        actual = match.get("actual")
        ok = steps.fits_type(actual, expected_type)
        if not ok:
            return True
        if message is None:
            message = "Expected a type mismatch for field '" + str(field) + "', but it fit"
        cls._fail(
            message,
            [
                ("field", field),
                ("expected_type", expected_type),
                ("actual_type", type(actual).__name__),
                ("value", repr(actual)),
            ],
        )
