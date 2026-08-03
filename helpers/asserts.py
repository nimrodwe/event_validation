"""Assertion helpers with clear failure messages (interview-friendly)."""

import json


class AssertError(AssertionError):
    """Test failed — message explains why."""


class AssertHelper:
    """
    Assert-only helpers used from tests and flows.

    Example:
        AssertHelper.equal(findings, [])
        AssertHelper.truthy(positives)
        AssertHelper.fits_type(steps, match)
    """

    def __init__(self):
        self.log = None
        self.record_uuid = None

    def _info(self, message, allure=True):
        """Log a step to the dashboard and Allure (same content)."""
        if self.log is None:
            return
        if allure:
            self.log.info(message)
        else:
            self.log.info(message, extra={"allure": False})

    def _log_event_body(self, label, event):
        """Log a full event: pretty JSON on dashboard; short Allure step + attachment.

        Dashboard / test.log get the pretty body. Allure gets one step titled
        with the label (and UUID when present), JSON as event.json — not a
        giant one-line INFO step.
        """
        from src.run_log import event_uuid

        pretty = json.dumps(event, indent=2, default=str, ensure_ascii=False)
        self._info(str(label), allure=False)
        self._info(pretty, allure=False)

        try:
            import allure
        except Exception:
            return

        uuid = event_uuid(event)
        title = str(label) if uuid is None else str(label) + " · UUID " + str(uuid)
        try:
            with allure.step("[INFO] " + title):
                allure.attach(
                    pretty,
                    name="event.json",
                    attachment_type=allure.attachment_type.JSON,
                )
        except Exception:
            pass

    def _format(self, value):
        try:
            return json.dumps(value, indent=2, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            return repr(value)

    def _plain(self, value):
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            return repr(value)

    def _attach_allure_json(self, name, value):
        try:
            import allure
        except Exception:
            return
        try:
            body = json.dumps(value, indent=2, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            body = repr(value)
        allure.attach(body, name=name, attachment_type=allure.attachment_type.JSON)

    def _attach_allure_text(self, name, text):
        try:
            import allure
        except Exception:
            return
        allure.attach(str(text), name=name, attachment_type=allure.attachment_type.TEXT)

    def _attach_tested_values(self, check, match, result):
        field = match.get("field", "<unknown>")
        expected_type = match.get("expected_type", "<unknown>")
        actual = match.get("actual")
        self._attach_allure_json(
            "tested values (" + str(check) + " / " + str(result) + ")",
            {
                "check": check,
                "result": result,
                "field": field,
                "expected_type": expected_type,
                "actual": actual,
                "actual_type": type(actual).__name__,
            },
        )

    def _attach_to_allure(self, message, details, data):
        try:
            import allure
        except Exception:
            return
        blocks = [message, ""]
        for key, value in details or []:
            blocks.append(str(key) + ":")
            blocks.append(self._plain(value))
            blocks.append("")
        if data is not None:
            blocks.append("data:")
            blocks.append(self._format(data))
        allure.attach(
            "\n".join(blocks),
            name="assertion failure",
            attachment_type=allure.attachment_type.TEXT,
        )

    def _fail(self, title, details, data=None):
        lines = [str(title), ""]
        for key, value in details or []:
            if isinstance(value, str) and "\n" in value:
                lines.append(str(key) + ":")
                lines.append(value)
                lines.append("")
            else:
                lines.append(str(key) + ": " + str(value))
                lines.append("")
        message = "\n".join(lines).rstrip() + "\n"
        if self.log is not None:
            self.log.error(message)
        self._attach_to_allure(message, details, data)
        raise AssertError(message)

    def truthy(self, value, message="Expected a truthy value", data=None):
        """Pass if value is not empty / False / None."""
        if value:
            return value
        self._fail(
            message,
            [
                (
                    "what went wrong",
                    "Value was missing, empty, or false — the test needed a real value.",
                ),
                ("what we got (actual)", value),
                ("what we expected", "a non-empty / truthy value"),
            ],
            data=data,
        )

    def _short(self, value):
        if isinstance(value, (dict, list)):
            try:
                text = json.dumps(value, default=str, ensure_ascii=False)
            except (TypeError, ValueError):
                text = repr(value)
            if len(text) > 120:
                return text[:117] + "..."
            return text
        return repr(value)

    def _collect_diffs(self, actual, expected, path=""):
        diffs = []
        if isinstance(actual, dict) and isinstance(expected, dict):
            for key in sorted(set(actual) | set(expected), key=str):
                child = (path + "." + str(key)) if path else str(key)
                if key not in actual:
                    diffs.append((child, "<missing>", expected[key]))
                elif key not in expected:
                    diffs.append((child, actual[key], "<missing>"))
                elif actual[key] != expected[key]:
                    diffs.extend(self._collect_diffs(actual[key], expected[key], child))
            return diffs
        if isinstance(actual, list) and isinstance(expected, list):
            if len(actual) != len(expected):
                diffs.append(
                    (
                        path or "<list>",
                        "length " + str(len(actual)),
                        "length " + str(len(expected)),
                    )
                )
            for index in range(min(len(actual), len(expected))):
                if actual[index] != expected[index]:
                    child = (
                        (path + "[" + str(index) + "]") if path else "[" + str(index) + "]"
                    )
                    diffs.extend(
                        self._collect_diffs(actual[index], expected[index], child)
                    )
            return diffs
        if actual != expected:
            diffs.append((path or "<value>", actual, expected))
        return diffs

    def _leaf_key(self, path):
        text = str(path or "<value>")
        if "." in text:
            text = text.rsplit(".", 1)[-1]
        return text

    def _format_mismatches(self, diffs):
        blocks = []
        for path, got, expected in diffs:
            blocks.append(
                "key: "
                + self._leaf_key(path)
                + "\n"
                + "before: "
                + self._short(expected)
                + "\n"
                + "after: "
                + self._short(got)
            )
        return "\n\n".join(blocks)

    def equal(self, actual, expected, message="Values are not equal", data=None):
        """Pass if actual == expected."""
        if actual == expected:
            return actual
        diffs = self._collect_diffs(actual, expected)
        if diffs:
            details = [
                (
                    "what went wrong",
                    str(len(diffs))
                    + " field(s) did not match. Showing key with value before and after.",
                ),
                ("mismatched fields", self._format_mismatches(diffs)),
            ]
            slim = None
            if isinstance(data, dict):
                slim = {}
                if data.get("UUID") is not None:
                    slim["UUID"] = data["UUID"]
                if data.get("case_id") is not None:
                    slim["case_id"] = data["case_id"]
                if not slim:
                    slim = None
            self._fail(message, details, data=slim)
        self._fail(
            message,
            [
                (
                    "what went wrong",
                    "The value we got is different from the value we expected.",
                ),
                ("what we got (actual)", actual),
                ("what we expected", expected),
            ],
            data=data,
        )

    def not_equal(self, actual, unexpected, message="Values should not be equal", data=None):
        """Pass if actual is different from unexpected."""
        if actual != unexpected:
            return actual
        self._fail(
            message,
            [
                (
                    "what went wrong",
                    "The value we got matched a forbidden value (they must differ).",
                ),
                ("what we got (actual)", actual),
                ("must not equal", unexpected),
            ],
            data=data,
        )

    def has_key(self, mapping, key, message=None, data=None):
        """Pass if mapping has key and its value is not empty."""
        if key in mapping and mapping.get(key):
            return mapping[key]
        if message is None:
            message = "Missing required key: " + str(key)
        self._fail(
            message,
            [
                ("what went wrong", "Required key is missing or empty."),
                ("key", key),
                (
                    "what we got (actual)",
                    mapping.get(key) if isinstance(mapping, dict) else None,
                ),
                ("what we expected", "a non-empty value for that key"),
            ],
            data=data if data is not None else mapping,
        )

    def status_code(self, response, expected, message=None, data=None):
        """Pass if HTTP response status matches expected (e.g. 200)."""
        actual = getattr(response, "status_code", None)
        if actual == expected:
            return actual
        body = getattr(response, "text", "")
        if message is None:
            message = "Unexpected HTTP status code"
        self._fail(
            message,
            [
                ("what went wrong", "HTTP status code did not match."),
                ("what we got (actual)", actual),
                ("what we expected", expected),
                ("response body", body[:2000] if body else "<empty>"),
            ],
            data=data,
        )

    def fits_type(self, steps, match, message=None, data=None):
        """Positive: value fits the EventsSchema type for this field."""
        field = match.get("field", "<unknown>")
        expected_type = match.get("expected_type", "<unknown>")
        actual = match.get("actual")
        self._info(
            "expect: field "
            + str(field)
            + " must fit "
            + str(expected_type)
            + "; POST->GET body unchanged"
        )
        if not steps.fits_type(actual, expected_type):
            self._attach_tested_values("type_ok", match, "failed")
            if message is None:
                message = "Type check failed for field '" + str(field) + "'"
            self._fail(
                message,
                [
                    (
                        "what went wrong",
                        "Field value does not match the EventsSchema type.",
                    ),
                    ("field", field),
                    ("what we got (actual)", actual),
                    ("what we expected", "a value of type " + str(expected_type)),
                    ("actual type", type(actual).__name__),
                    ("expected type", expected_type),
                ],
                data=data if data is not None else match,
            )
        # Pass: step log only (no Allure JSON attachment per field).
        self._info(
            str(field)
            + " got="
            + repr(actual)
            + " ("
            + type(actual).__name__
            + ")"
            + " expected_type="
            + str(expected_type)
            + " result=PASS"
        )
        return True

    def type_mismatch(self, steps, match, message=None, data=None):
        """Negative: value must NOT fit declared schema type."""
        field = match.get("field", "<unknown>")
        expected_type = match.get("expected_type", "<unknown>")
        actual = match.get("actual")
        if steps.fits_type(actual, expected_type):
            self._attach_tested_values("type_bad", match, "failed")
            if message is None:
                message = (
                    "Expected a type mismatch for field '"
                    + str(field)
                    + "', but it fit the schema"
                )
            self._fail(
                message,
                [
                    (
                        "what went wrong",
                        "This negative case expected a bad type, but the value was valid.",
                    ),
                    ("field", field),
                    ("what we got (actual)", actual),
                    (
                        "what we expected",
                        "a value that does NOT fit type " + str(expected_type),
                    ),
                    ("actual type", type(actual).__name__),
                    ("expected type", expected_type),
                ],
                data=data if data is not None else match,
            )
        # Pass: finding already logged by the flow (no Allure JSON attachment).
        return True

    def post_get_equals(self, receiver, case_id, sent, record_uuid=True):
        """
        Assert round-trip: POST event → GET it back → body must equal what we sent.

        HTTP steps live in FlowHelper; this is the assert entry point for tests.
        """
        from helpers.flows import FlowHelper

        return FlowHelper.post_get_equals(
            receiver, case_id, sent, record_uuid=record_uuid
        )

    def check_type_bad_case(self, receiver, steps, case):
        """
        Assert type_bad scenario: POST→GET validation row, then confirm
        EventsSchema type mismatches on the GET body.

        Scenario steps live in FlowHelper; this is the assert entry point for tests.
        """
        from helpers.flows import FlowHelper

        return FlowHelper.check_type_bad_case(receiver, steps, case)

    def check_corrupted_fields(self, receiver, steps, schema, event, corruptions):
        """Assert entry for intentional field corruption (expected to fail)."""
        from helpers.flows import FlowHelper

        return FlowHelper.check_corrupted_fields(
            receiver, steps, schema, event, corruptions
        )


AssertHelper = AssertHelper()
