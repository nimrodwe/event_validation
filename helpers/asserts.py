"""Simple assertion helpers with clear failure messages (interview-friendly)."""

import base64
import json

from services.http_client import HttpClient
from services.http_status import HttpStatus


class AssertError(AssertionError):
    """Test failed — message explains why."""


class AssertHelper:
    """
    One object with easy checks.

    Example:
        AssertHelper.equal(findings, [])
        AssertHelper.truthy(positives)
        AssertHelper.all_received_equals_sent(receiver, cases, events)
    """

    def __init__(self, http=None):
        self.http = http or HttpClient(timeout=5, retries=3)
        self.log = None
        self.record_uuid = None

    def _info(self, message):
        if self.log is not None:
            self.log.info(message)

    def event_uuid(self, payload):
        """UUID from a nested event or a flat dataset row."""
        if not isinstance(payload, dict):
            return None
        if "UUID" in payload:
            return payload.get("UUID")
        props = payload.get("properties")
        if isinstance(props, dict) and "UUID" in props:
            return props.get("UUID")
        return None

    def _record_uuid(self, payload):
        if not callable(self.record_uuid):
            return
        self.record_uuid(self.event_uuid(payload))

    def _format(self, value):
        """Turn data into readable text for the error message."""
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            try:
                return json.dumps(value, indent=2, default=str, ensure_ascii=False)
            except (TypeError, ValueError):
                return repr(value)
        return repr(value)

    def _attach_to_allure(self, message, details, data):
        """Optional: put the same failure info into Allure."""
        try:
            import allure
            from allure_commons.types import AttachmentType

            allure.attach(message, name="Why it failed", attachment_type=AttachmentType.TEXT)

            payload = {"summary": message.splitlines()[0] if message else ""}
            for key, value in details:
                payload[str(key)] = value
            if data is not None:
                payload["failed_data"] = data
            allure.attach(
                json.dumps(payload, indent=2, default=str, ensure_ascii=False),
                name="failure-details",
                attachment_type=AttachmentType.JSON,
            )
            if data is not None:
                kind = AttachmentType.JSON if isinstance(data, (dict, list)) else AttachmentType.TEXT
                allure.attach(self._format(data), name="failed-data", attachment_type=kind)
        except Exception:
            pass

    def _fail(self, title, details, data=None):
        """Build a clear error and stop the test."""
        # Prefer a fixed reading order so the dashboard ERROR step is easy to scan.
        order = [
            "what went wrong",
            "mismatched fields",
            "what we got (actual)",
            "what we expected",
            "must not equal",
            "field",
            "expected type",
            "actual type",
            "key",
            "response body",
            "why",
            "expected",
            "actual value",
        ]
        detail_map = {}
        for key, value in details:
            detail_map[str(key)] = value

        lines = [
            "FAILED: " + title,
            "",
            "Read this to understand the failure:",
            "",
        ]

        def add_block(label, value):
            lines.append(label + ":")
            text = self._format(value)
            for part in str(text).splitlines() or [""]:
                lines.append("  " + part)
            lines.append("")

        for key in order:
            if key not in detail_map:
                continue
            value = detail_map.pop(key)
            if key in (
                "mismatched fields",
                "what we got (actual)",
                "what we expected",
                "must not equal",
                "expected",
                "actual value",
                "response body",
            ):
                add_block(key, value)
            else:
                lines.append(key + ": " + str(value))
                lines.append("")

        for key, value in detail_map.items():
            if key in ("mismatched fields", "expected", "actual value", "response body"):
                add_block(key, value)
            else:
                lines.append(str(key) + ": " + str(value))
                lines.append("")

        message = "\n".join(lines).rstrip() + "\n"
        if self.log is not None:
            self.log.error(message)
        self._attach_to_allure(message, details, data)
        raise AssertError(message)

    def truthy(self, value, message="Expected a truthy value", data=None):
        """Pass if value is not empty / False / None. Example: list of cases exists."""
        if value:
            return value
        self._fail(
            message,
            [
                ("what went wrong", "Value was missing, empty, or false — the test needed a real value."),
                ("what we got (actual)", value),
                ("what we expected", "a non-empty / truthy value"),
            ],
            data=data,
        )

    def _short(self, value):
        """Compact value for mismatch lines (avoid dumping huge nested blobs)."""
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
        """Return leaf-level mismatches: (path, got, expected)."""
        diffs = []
        if isinstance(actual, dict) and isinstance(expected, dict):
            for key in sorted(set(actual) | set(expected), key=str):
                child = (path + "." + str(key)) if path else str(key)
                if key not in actual:
                    diffs.append((child, "<missing>", expected[key]))
                elif key not in expected:
                    diffs.append((child, actual[key], "<missing>"))
                elif actual[key] != expected[key]:
                    diffs.extend(
                        self._collect_diffs(actual[key], expected[key], child)
                    )
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
                    child = (path + "[" + str(index) + "]") if path else "[" + str(index) + "]"
                    diffs.extend(
                        self._collect_diffs(actual[index], expected[index], child)
                    )
            return diffs

        if actual != expected:
            diffs.append((path or "<value>", actual, expected))
        return diffs

    def _leaf_key(self, path):
        """Field name only (e.g. properties.message -> message)."""
        text = str(path or "<value>")
        if "." in text:
            text = text.rsplit(".", 1)[-1]
        return text

    def _format_mismatches(self, diffs):
        """Show key + value before (expected) and after (actual) for each mismatch."""
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
        """Pass if actual == expected. Example: findings == []."""
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

        # Non-structured values: show the two values only (they are usually small).
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

    def is_true(self, value, message="Expected True", data=None):
        """Pass only if value is exactly True."""
        if value is True:
            return value
        self._fail(
            message,
            [
                ("what went wrong", "Value was not exactly True."),
                ("what we got (actual)", value),
                ("what we expected", True),
            ],
            data=data,
        )

    def is_false(self, value, message="Expected False", data=None):
        """Pass only if value is exactly False."""
        if value is False:
            return value
        self._fail(
            message,
            [
                ("what went wrong", "Value was not exactly False."),
                ("what we got (actual)", value),
                ("what we expected", False),
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
                ("what we got (actual)", mapping.get(key) if isinstance(mapping, dict) else None),
                ("what we expected", "a non-empty value for that key"),
            ],
            data=data if data is not None else mapping,
        )

    def status_code(self, response, expected, message=None, data=None):
        """Pass if HTTP response status matches expected (e.g. 202)."""
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

    def _log_type_check(self, kind, field, expected_type):
        """Short dashboard line after POST→GET; payload is already in POST/GET steps."""
        self._info(
            "Type check ("
            + kind
            + ") field="
            + str(field)
            + " expected_type="
            + str(expected_type)
        )

    def fits_type(self, steps, match, message=None, data=None):
        """Positive type check: value matches expected schema type."""
        field = match.get("field", "<unknown>")
        expected_type = match.get("expected_type", "<unknown>")
        actual = match.get("actual")
        if steps.fits_type(actual, expected_type):
            self._log_type_check("type_ok", field, expected_type)
            return True
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

    def type_mismatch(self, steps, match, message=None, data=None):
        """Negative type check: value must NOT match expected schema type."""
        field = match.get("field", "<unknown>")
        expected_type = match.get("expected_type", "<unknown>")
        actual = match.get("actual")
        if not steps.fits_type(actual, expected_type):
            self._log_type_check("type_bad", field, expected_type)
            return True
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
                ("what we expected", "a value that does NOT fit type " + str(expected_type)),
                ("actual type", type(actual).__name__),
                ("expected type", expected_type),
            ],
            data=data if data is not None else match,
        )

    def _sent_by_id(self, events):
        return {item["case_id"]: item["event"] for item in events}

    def _post_case(self, receiver, case_id, sent, delivery_headers=None, record_uuid=True):
        """POST one event to the receiver API."""
        headers = {"X-Case-Id": case_id}
        headers.update(delivery_headers or {})
        if record_uuid:
            self._record_uuid(sent)
        self._info("POST " + receiver.url + " case_id=" + str(case_id))
        if delivery_headers:
            self._info(json.dumps({"delivery_headers": delivery_headers}))
        self._info(json.dumps(sent))
        body = base64.b64encode(json.dumps(sent).encode("utf-8"))
        response = self.http.post(receiver.url, data=body, headers=headers)
        self._info("status=" + str(response.status_code))
        self.status_code(
            response,
            HttpStatus.ACCEPTED,
            case_id + " POST should be accepted",
            data={"case_id": case_id, "event": sent},
        )
        return response

    def post_get_equals(self, receiver, case_id, sent, record_uuid=True):
        """POST payload, GET it back, assert receiver stored exactly what we sent."""
        self._post_case(
            receiver, case_id, sent, record_uuid=record_uuid
        )
        return self.received_equals_sent(receiver, case_id, sent)

    def _get_rows(self, receiver, case_id):
        """GET stored rows for one case_id from the receiver API."""
        self._info("GET " + receiver.url + " case_id=" + str(case_id))
        response = self.http.get(receiver.url, params={"case_id": case_id})
        self._info("status=" + str(response.status_code))
        self.status_code(
            response,
            HttpStatus.OK,
            "GET stored events should succeed for " + str(case_id),
        )
        rows = (response.json() or {}).get("events") or []
        self.truthy(rows, case_id + " was not returned by GET API")
        return rows

    def received_equals_sent(self, receiver, case_id, sent):
        """GET /v1/events?case_id=... and assert that payload equals what we POSTed."""
        row = self._get_rows(receiver, case_id)[-1]
        received = row.get("event")
        uuid = self.event_uuid(sent) or self.event_uuid(received) or "<missing UUID>"
        self.equal(
            received,
            sent,
            "UUID " + str(uuid) + " GET API event must equal the event we sent",
            data={"UUID": uuid},
        )
        return received

    def all_received_equals_sent(self, receiver, cases, events):
        """For each case, GET payload must equal the event we POSTed."""
        sent_by_id = self._sent_by_id(events)
        for item in cases:
            case_id = item["case_id"]
            sent = sent_by_id.get(case_id)
            self.truthy(sent, "Missing sent event for " + case_id)
            self.received_equals_sent(receiver, case_id, sent)

    def check_positives(self, receiver, cases, events):
        """POST → GET → received event keys/values equal what was sent."""
        sent_by_id = self._sent_by_id(events)
        for item in cases:
            case_id = item["case_id"]
            sent = sent_by_id.get(case_id)
            self.truthy(sent, "Missing event for " + case_id)
            self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
            self.received_equals_sent(receiver, case_id, sent)

    def check_negatives(self, receiver, validator, cases, events):
        """POST → GET → received equals sent → target rule present on received data."""
        sent_by_id = self._sent_by_id(events)
        for item in cases:
            case_id = item["case_id"]
            target = item["target_rule_id"]
            sent = sent_by_id.get(case_id)
            self.truthy(sent, "Missing event for " + case_id)
            self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
            received = self.received_equals_sent(receiver, case_id, sent)
            findings = [f.to_dict() for f in validator.check_nested(received, case_id)]
            rule_ids = [f["rule_id"] for f in findings]
            self.truthy(
                target in rule_ids,
                "Negative case "
                + case_id
                + " should hit rule "
                + target
                + " after GET, got "
                + str(rule_ids),
                data={
                    "case_id": case_id,
                    "target_rule_id": target,
                    "rule_ids_found": rule_ids,
                    "findings": findings,
                    "received_event": received,
                },
            )

    def check_boundary(self, receiver, validator, cases, events):
        """POST → GET → received equals sent → boundary rules on received data."""
        self.truthy(cases, "No boundary cases in manifest")
        by_id = {item["case_id"]: item for item in cases}
        for needed in ("BND-0001", "BND-TOKEN-SHORT", "BND-TOKEN-EDGE"):
            self.has_key(by_id, needed, "Missing " + needed)

        sent_by_id = self._sent_by_id(events)
        for item in cases:
            case_id = item["case_id"]
            sent = sent_by_id.get(case_id)
            self.truthy(sent, "Missing event for " + case_id)
            self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
            received = self.received_equals_sent(receiver, case_id, sent)
            props = received["properties"]
            token = props.get("Appdome fusion app token")
            token_findings = [
                f.to_dict() for f in validator.check_token_length(received, case_id)
            ]

            if case_id == "BND-0001":
                self.equal(props["time"], 0, "BND-0001 should use time=0 after GET")
            elif case_id == "BND-TOKEN-SHORT":
                self.equal(len(str(token)), validator.TOKEN_MIN_LEN - 1, "short token length after GET")
                self.truthy(
                    "FMT" in [f["rule_id"] for f in token_findings],
                    "Short token should hit FMT after GET",
                    data={"findings": token_findings},
                )
            elif case_id == "BND-TOKEN-EDGE":
                self.equal(len(str(token)), validator.TOKEN_MIN_LEN, "edge token length after GET")
                self.equal(token_findings, [], "Token at min length should not produce FMT after GET")

    def check_retries(self, receiver, cases, events):
        """POST → GET → received equals sent → retry headers preserved."""
        self.equal(len(cases), 2, "Expected exactly two retry cases")
        sent_by_id = self._sent_by_id(events)
        for item in cases:
            case_id = item["case_id"]
            headers = item.get("delivery_headers") or {}
            self.has_key(headers, "Idempotency-Key", case_id + " missing Idempotency-Key")
            self.has_key(headers, "X-Retry-Count", case_id + " missing X-Retry-Count")
            sent = sent_by_id.get(case_id)
            self.truthy(sent, "Missing event for " + case_id)
            self._post_case(receiver, case_id, sent, headers)
            self.received_equals_sent(receiver, case_id, sent)
            stored_headers = self._get_rows(receiver, case_id)[-1].get("headers") or {}
            self.equal(stored_headers.get("Idempotency-Key"), headers["Idempotency-Key"])
            self.equal(stored_headers.get("X-Retry-Count"), headers["X-Retry-Count"])

    def check_duplicates(self, receiver, validator, cases, events):
        """POST both → GET → received equals sent → DUP-NEAR on received rows."""
        self.equal(len(cases), 2, "Expected exactly two duplicate cases")
        sent_by_id = self._sent_by_id(events)
        received_items = []
        for item in cases:
            case_id = item["case_id"]
            sent = sent_by_id.get(case_id)
            self.truthy(sent, "Missing event for " + case_id)
            self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
            self.received_equals_sent(receiver, case_id, sent)
            received_items.append(self._get_rows(receiver, case_id)[-1])

        findings = [f.to_dict() for f in validator.check_received_dupes(received_items)]
        self.truthy(findings, "Duplicate cases should produce a duplicate finding")
        self.equal(findings[0]["rule_id"], "DUP-NEAR", "Expected DUP-NEAR")

    def check_replays(self, receiver, cases, events):
        """POST both → GET → received equals sent (both deliveries visible)."""
        self.equal(len(cases), 2, "Expected exactly two replay cases")
        sent_by_id = self._sent_by_id(events)
        for item in cases:
            case_id = item["case_id"]
            sent = sent_by_id.get(case_id)
            self.truthy(sent, "Missing event for " + case_id)
            self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
            self.received_equals_sent(receiver, case_id, sent)


# One shared instance — call AssertHelper.equal(...) with normal methods (no cls/staticmethod)
AssertHelper = AssertHelper()
