"""Test flows: HTTP round-trips + scenario checks (not assertions)."""

import base64
import json

from services.http_client import HttpClient
from services.http_status import HttpStatus
from helpers.asserts import AssertHelper


class FlowHelper:
    """
    POST/GET and catalog/dataset scenario checks.
    Uses AssertHelper for all assertions.
    """

    _NEG_RECEIVE_CACHE = {}
    _TYPE_BAD_RECEIVE_CACHE = {}

    def __init__(self, http=None):
        self.http = http or HttpClient(timeout=5, retries=3)

    # ---- logging / uuid (wired via AssertHelper in conftest) ----
    @property
    def log(self):
        return AssertHelper.log

    @log.setter
    def log(self, value):
        AssertHelper.log = value

    @property
    def record_uuid(self):
        return AssertHelper.record_uuid

    @record_uuid.setter
    def record_uuid(self, value):
        AssertHelper.record_uuid = value

    def _info(self, message, allure=True):
        AssertHelper._info(message, allure=allure)

    def _log_event_body(self, label, event):
        AssertHelper._log_event_body(label, event)

    def _log_roundtrip_events(self, label, sent, received):
        """Log full event after POST and after GET (dashboard + Allure)."""
        prefix = (str(label) + ": ") if label else ""
        self._log_event_body(prefix + "event after POST", sent)
        self._log_event_body(prefix + "event after GET", received)

    def _fail(self, title, details, data=None):
        AssertHelper._fail(title, details, data=data)

    def _log_expect(self, message):
        self._info("expect: " + str(message))

    def event_uuid(self, payload):
        from src.run_log import event_uuid

        return event_uuid(payload)

    def _record_uuid(self, payload):
        uuid = self.event_uuid(payload)
        if self.record_uuid is not None:
            self.record_uuid(uuid)

    def _plain(self, value):
        return AssertHelper._plain(value)

    def _log_before_after(self, key, before, after):
        # One line so Allure shows a single step (no "details" attachment).
        self._info(
            "key: "
            + str(key)
            + " before: "
            + self._plain(before)
            + " after: "
            + self._plain(after)
        )

    def _sent_by_id(self, events):
        return {item["case_id"]: item["event"] for item in events}

    def catalog_case(self, catalog, case_type, case_id):
        """Load catalog type and require one case_id; returns (events, manifest_row)."""
        events, item = catalog.case(case_type, case_id)
        AssertHelper.truthy(
            item,
            "Missing " + str(case_type) + " case " + str(case_id),
            data={"case_type": case_type, "case_id": case_id},
        )
        return events, item

    def _post_case(
        self,
        receiver,
        case_id,
        sent,
        delivery_headers=None,
        record_uuid=True,
        expected_status=None,
        log_body=False,
    ):
        """POST one event to the receiver API.

        log_body=False by default (Allure stays lean). Callers that need the
        full payload on the local dashboard pass log_body=True or log it themselves.
        """
        if expected_status is None:
            expected_status = HttpStatus.OK
        headers = {"X-Case-Id": case_id}
        headers.update(delivery_headers or {})
        if record_uuid:
            self._record_uuid(sent)
        self._info("POST " + receiver.url + " case_id=" + str(case_id))
        if delivery_headers:
            self._info("delivery_headers=" + json.dumps(delivery_headers, default=str))
        if log_body:
            self._info(json.dumps(sent))
        body = base64.b64encode(json.dumps(sent).encode("utf-8"))
        response = self.http.post(receiver.url, data=body, headers=headers)
        self._info("status=" + str(response.status_code))
        AssertHelper.status_code(
            response,
            expected_status,
            case_id + " POST should return " + str(expected_status),
            data={"case_id": case_id, "event": sent},
        )
        return response

    def post_get_equals(self, receiver, case_id, sent, record_uuid=True):
        """POST payload, GET it back, assert receiver stored exactly what we sent."""
        self._post_case(
            receiver, case_id, sent, record_uuid=record_uuid
        )
        received = self.received_equals_sent(receiver, case_id, sent)
        self._log_roundtrip_events(case_id, sent, received)
        return received

    def _get_rows(self, receiver, case_id):
        """GET stored rows for one case_id from the receiver API."""
        self._info("GET " + receiver.url + " case_id=" + str(case_id))
        response = self.http.get(receiver.url, params={"case_id": case_id})
        self._info("status=" + str(response.status_code))
        AssertHelper.status_code(
            response,
            HttpStatus.OK,
            "GET stored events should succeed for " + str(case_id),
        )
        rows = (response.json() or {}).get("events") or []
        AssertHelper.truthy(rows, case_id + " was not returned by GET API")
        return rows

    def received_equals_sent(
        self, receiver, case_id, sent, return_row=False, log_body=False
    ):
        """GET /v1/events?case_id=... and assert that payload equals what we POSTed.

        log_body=False by default — full GET body is for the dashboard when needed.
        """
        row = self._get_rows(receiver, case_id)[-1]
        received = row.get("event")
        if log_body:
            self._info(json.dumps(received))
        uuid = self.event_uuid(sent) or self.event_uuid(received) or "<missing UUID>"
        AssertHelper.equal(
            received,
            sent,
            "UUID " + str(uuid) + " GET API event must equal the event we sent",
            data={"UUID": uuid, "case_id": case_id},
        )
        if return_row:
            return row
        return received

    def check_positives(self, receiver, validator, cases, events):
        """POST → GET → same rules as negatives, but findings must be empty."""
        sent_by_id = self._sent_by_id(events)
        for item in cases:
            case_id = item["case_id"]
            sent = sent_by_id.get(case_id)
            AssertHelper.truthy(sent, "Missing event for " + case_id)
            self._log_expect(
                case_id
                + " POST->GET equals sent; check_nested findings empty"
            )
            self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
            received = self.received_equals_sent(receiver, case_id, sent)
            self._log_roundtrip_events(case_id, sent, received)
            findings = [f.to_dict() for f in validator.check_nested(received, case_id)]
            AssertHelper.equal(
                findings,
                [],
                case_id + " positive event should not produce nested rule findings",
                data={
                    "case_id": case_id,
                    "findings": findings,
                    "received_event": received,
                },
            )

    def check_type_bad_case(self, receiver, steps, case):
        """
        One type_bad test per validation event (pytest id e1 … e10).

        Flow: POST raw row → GET → list every EventsSchema type mismatch once.
        """
        from helpers.loaders import load_expected_types
        from helpers.logger import format_type_bad_finding
        from helpers.matches import schema_type_mismatches

        short_id = case.get("id") or "?"
        event_label = case.get("event_label") or (
            "event-" + str(case.get("position"))
        )
        # Raw validation-dataset row — never mutated for type_bad.
        sent = case["row"]
        http_case_id = "TYPE-BAD-" + str(event_label)
        label = str(event_label)

        self._log_expect(
            short_id
            + ": list all EventsSchema type mismatches on "
            + str(event_label)
            + " (validate after GET)"
        )
        self._info(
            "test "
            + str(short_id)
            + " — "
            + str(event_label)
            + " (POST -> GET -> EventsSchema on GET body)"
        )
        # Every test row shows this event UUID on the dashboard (right corner).
        self._record_uuid(sent)

        cache_key = (receiver.url, event_label)
        received = FlowHelper._TYPE_BAD_RECEIVE_CACHE.get(cache_key)
        if received is None:
            self._info(label + ": POST -> GET")
            self._post_case(
                receiver,
                http_case_id,
                sent,
                record_uuid=False,
                log_body=False,
            )
            received = self.received_equals_sent(
                receiver, http_case_id, sent, log_body=False
            )
            FlowHelper._TYPE_BAD_RECEIVE_CACHE[cache_key] = received
        else:
            self._info(label + ": using stored GET body from this run")

        self._log_roundtrip_events(label, sent, received)

        all_bad = schema_type_mismatches(steps, received, load_expected_types())

        self._info(label + ": found " + str(len(all_bad)) + " bad type(s):")
        for bad in all_bad:
            self._info(format_type_bad_finding(bad))
        self._info(label + ": total=" + str(len(all_bad)))

        AssertHelper.truthy(
            all_bad,
            short_id + " FAILED: expected type mismatches after GET",
            data={"case": case, "received": received},
        )
        # Confirm each listed field is still a mismatch (no type-matrix spam).
        for bad in all_bad:
            AssertHelper.type_mismatch(steps, bad)
        return all_bad

    def check_corrupted_fields(self, receiver, steps, schema, event, corruptions):
        """
        Corrupt synthetic fields, POST→GET, detect bad types, fail fits_type.

        Used by the intentional failure that proves the assert path works.
        """
        import copy

        from helpers.logger import format_type_bad_finding
        from helpers.matches import schema_type_mismatches

        sent = copy.deepcopy(event)
        props = sent.setdefault("properties", {})
        for key, bad_value in corruptions:
            props[key] = bad_value

        self._log_expect(
            "corrupt "
            + str(len(corruptions))
            + " field(s), detect them after GET, then fail fits_type"
        )
        for key, bad_value in corruptions:
            self._info(
                "corrupt: properties."
                + str(key)
                + " = "
                + repr(bad_value)
                + " ("
                + type(bad_value).__name__
                + ")"
            )

        case_id = "TYPE-CORRUPT-" + "-".join(
            str(k).lstrip("$") for k, _ in corruptions
        )
        received = self.post_get_equals(
            receiver, case_id, sent, record_uuid=True
        )

        bad = schema_type_mismatches(steps, received, schema)
        self._info("detected " + str(len(bad)) + " bad field(s):")
        for match in bad:
            self._info(
                format_type_bad_finding(match).replace(" result=PASS", " result=FAIL")
            )

        AssertHelper.truthy(
            bad,
            "Expected to detect at least one corrupted field after GET",
            data={"corruptions": list(corruptions)},
        )

        first = bad[0]
        self._info(
            "failing fits_type on field="
            + str(first.get("field"))
            + " to verify assert failure path"
        )
        AssertHelper.fits_type(steps, first)

    def check_dataset_negative_rule(self, receiver, case):
        """
        One pytest per (event, named rule) that has hits, e.g. e1-new_keys.

        Log order for every negative test:
        1) event after POST
        2) event after GET
        3) findings below that
        """
        from helpers.dataset_negatives import (
            LEARNED_RULES,
            RULE_EXPLAIN_BY_ID,
            RULE_TITLE_BY_ID,
            apply_kind,
            format_rule_finding,
        )

        event_label = case.get("event_label") or (
            "event-" + str(case.get("position"))
        )
        kind = case.get("kind")
        title = case.get("title") or RULE_TITLE_BY_ID.get(kind, kind)
        explain = RULE_EXPLAIN_BY_ID.get(kind, "listing matching keys")
        sent = case["row"]
        rules = LEARNED_RULES
        label = str(title) + " / " + str(event_label)

        uuid = self.event_uuid(sent)
        self._info(label)
        if uuid is not None:
            self._info(
                label
                + ": event id "
                + str(uuid)
                + " (dashboard label only — not a rule hit)"
            )
        self._info(label + ": " + str(explain))
        self._record_uuid(sent)

        # POST -> GET (bodies logged below in fixed order for comparison).
        row_index = case.get("index")
        cache_key = (receiver.url, row_index)
        http_case_id = "NEG-row-" + str(row_index)
        received = FlowHelper._NEG_RECEIVE_CACHE.get(cache_key)
        if received is None:
            self._info(label + ": POST -> GET")
            self._post_case(
                receiver,
                http_case_id,
                sent,
                record_uuid=False,
                log_body=False,
            )
            received = self.received_equals_sent(
                receiver, http_case_id, sent, log_body=False
            )
            FlowHelper._NEG_RECEIVE_CACHE[cache_key] = received
        else:
            self._info(label + ": using stored GET body from this run")

        self._log_roundtrip_events(label, sent, received)

        items = apply_kind(received, rules, kind)
        if not items:
            self._info("nothing to validate")
            return []

        self._info(
            label
            + ": FINDINGS — "
            + str(len(items))
            + " key(s) on GET body:"
        )
        for item in items:
            self._info(format_rule_finding(item))

        self._info(label + ": done — listed " + str(len(items)) + " key(s)")
        return items

    def check_boundary_case(
        self,
        receiver,
        validator,
        item,
        events,
        changed_key=None,
        changed_value=None,
    ):
        """POST → GET → boundary rules for one catalog case."""
        case_id = item["case_id"]
        sent_by_id = self._sent_by_id(events)
        sent = sent_by_id.get(case_id)
        AssertHelper.truthy(sent, "Missing event for " + case_id)

        from helpers.pytest_cases import BOUNDARY_CASE_BY_ID

        meta = BOUNDARY_CASE_BY_ID.get(case_id) or {}
        if changed_key is None:
            changed_key = meta.get("key", "?")
        if changed_value is None:
            changed_value = meta.get("value")

        if case_id == "BND-0001":
            self._log_expect(
                case_id + " time=0 kept after GET; no RANGE-time finding"
            )
        elif case_id == "BND-TIME-NEG":
            self._log_expect(
                case_id + " time=-1 kept after GET; RANGE-time fires"
            )
        elif case_id == "BND-TOKEN-SHORT":
            self._log_expect(
                case_id
                + " token len="
                + str(validator.TOKEN_MIN_LEN - 1)
                + " kept after GET; FMT fires"
            )
        elif case_id == "BND-TOKEN-EDGE":
            self._log_expect(
                case_id
                + " token len="
                + str(validator.TOKEN_MIN_LEN)
                + " kept after GET; no FMT finding"
            )
        else:
            self._log_expect(case_id + " boundary round-trip + edge rule")

        # Dashboard: key before=/after= (same style as negatives).
        self._log_before_after(changed_key, meta.get("before"), changed_value)

        self._post_case(
            receiver,
            case_id,
            sent,
            item.get("delivery_headers"),
            log_body=False,
        )
        received = self.received_equals_sent(
            receiver, case_id, sent, log_body=False
        )

        self._log_roundtrip_events(case_id, sent, received)

        props = received["properties"]
        token = props.get("Appdome fusion app token")
        token_findings = [
            f.to_dict() for f in validator.check_token_length(received, case_id)
        ]
        time_findings = [f.to_dict() for f in validator.check_time(received, case_id)]

        # Log what we got after GET (same clarity as negatives findings).
        self._info(
            "after GET: "
            + str(changed_key)
            + "="
            + self._plain(props.get(changed_key))
            + (
                " (len=" + str(len(str(token))) + ")"
                if changed_key == "Appdome fusion app token"
                else ""
            )
        )
        findings = token_findings + time_findings
        if findings:
            self._info("FINDINGS — " + str(len(findings)) + ":")
            for finding in findings:
                self._info(
                    str(finding.get("rule_id") or "?")
                    + " field="
                    + str(finding.get("field") or "?")
                    + " observed="
                    + self._plain(finding.get("observed"))
                    + " expected="
                    + self._plain(finding.get("expected"))
                )
        else:
            self._info("FINDINGS — none (edge accepted)")

        # Confirm the changed key still has that value after GET.
        AssertHelper.equal(
            props.get(changed_key),
            changed_value,
            case_id
            + ": changed key "
            + str(changed_key)
            + " must still equal the boundary value after GET",
            data={
                "case_id": case_id,
                "key": changed_key,
                "expected": changed_value,
                "actual": props.get(changed_key),
            },
        )

        if case_id == "BND-0001":
            AssertHelper.equal(props["time"], 0, "BND-0001 should use time=0 after GET")
            AssertHelper.equal(
                time_findings,
                [],
                "time=0 should not produce RANGE-time after GET",
            )
        elif case_id == "BND-TIME-NEG":
            AssertHelper.equal(props["time"], -1, "BND-TIME-NEG should keep time=-1 after GET")
            AssertHelper.truthy(
                "RANGE-time" in [f["rule_id"] for f in time_findings],
                "time=-1 should hit RANGE-time after GET",
                data={"findings": time_findings},
            )
        elif case_id == "BND-TOKEN-SHORT":
            AssertHelper.equal(
                len(str(token)),
                validator.TOKEN_MIN_LEN - 1,
                "short token length after GET",
            )
            AssertHelper.truthy(
                "FMT" in [f["rule_id"] for f in token_findings],
                "Short token should hit FMT after GET",
                data={"findings": token_findings},
            )
        elif case_id == "BND-TOKEN-EDGE":
            AssertHelper.equal(
                len(str(token)),
                validator.TOKEN_MIN_LEN,
                "edge token length after GET",
            )
            AssertHelper.equal(
                token_findings,
                [],
                "Token at min length should not produce FMT after GET",
            )
        else:
            AssertHelper._fail(
                "Unknown boundary case_id: " + str(case_id),
                [("case_id", case_id)],
                data={"item": item},
            )

    def check_retries(self, receiver, cases, events):
        """First POST → 500 (server could not accept); retry valid → 200 + GET."""
        AssertHelper.equal(len(cases), 1, "Expected exactly one retry case")
        item = cases[0]
        case_id = item["case_id"]
        headers = item.get("delivery_headers") or {}
        AssertHelper.has_key(headers, "Idempotency-Key", case_id + " missing Idempotency-Key")
        sent_by_id = self._sent_by_id(events)
        sent = sent_by_id.get(case_id)
        AssertHelper.truthy(sent, "Missing event for " + case_id)

        fail_headers = dict(headers)
        fail_headers["X-Retry-Count"] = "1"
        fail_headers["X-Force-Error"] = "500"
        ok_headers = dict(headers)
        ok_headers["X-Retry-Count"] = "2"

        self._log_expect(
            case_id
            + " first POST 500 (server could not accept, nothing stored); "
            + "retry POST 200 with valid event; GET equals sent"
        )

        # Attempt 1 — server error (client will retry). Do not auto-retry HTTP here.
        self._log_expect(case_id + " attempt 1: expect status=500")
        saved_retries = self.http.retries
        self.http.retries = 1
        try:
            self._post_case(
                receiver,
                case_id,
                sent,
                fail_headers,
                expected_status=HttpStatus.INTERNAL_SERVER_ERROR,
            )
        finally:
            self.http.retries = saved_retries
        self._info("GET " + receiver.url + " case_id=" + str(case_id))
        get_fail = self.http.get(receiver.url, params={"case_id": case_id})
        self._info("status=" + str(get_fail.status_code))
        AssertHelper.status_code(get_fail, HttpStatus.OK, "GET after failed POST should succeed")
        rows_after_fail = (get_fail.json() or {}).get("events") or []
        AssertHelper.equal(
            rows_after_fail,
            [],
            case_id + " must not be stored after 500",
            data={"case_id": case_id, "rows": rows_after_fail},
        )
        self._info("after 500: stored count=0")
        self._info(case_id + ": server could not accept — retrying same event")

        # Attempt 2 — retry succeeds; we get the event.
        self._log_expect(case_id + " attempt 2 (retry): expect status=200 then GET event")
        self._info(case_id + ": retry POST (X-Retry-Count=2)")
        self._post_case(
            receiver,
            case_id,
            sent,
            ok_headers,
            expected_status=HttpStatus.OK,
        )
        row = self.received_equals_sent(
            receiver, case_id, sent, return_row=True
        )
        received = (row or {}).get("event")
        self._log_roundtrip_events(case_id + " (retry)", sent, received)
        stored_headers = (row or {}).get("headers") or {}
        AssertHelper.equal(stored_headers.get("Idempotency-Key"), ok_headers["Idempotency-Key"])
        AssertHelper.equal(stored_headers.get("X-Retry-Count"), ok_headers["X-Retry-Count"])
        self._info(
            "after 200: got event UUID "
            + str(self.event_uuid(sent))
        )
        self._info(case_id + ": retry passed")

    def check_duplicates(self, receiver, cases, events):
        """POST first → 200 + GET equals sent; second same body → 409 and not stored."""
        AssertHelper.equal(len(cases), 2, "Expected exactly two duplicate cases")
        sent_by_id = self._sent_by_id(events)
        first, second = cases[0], cases[1]

        first_id = first["case_id"]
        second_id = second["case_id"]
        self._log_expect(
            first_id
            + " POST 200 + GET equals sent; "
            + second_id
            + " same body POST 409 duplicate and not stored"
        )
        first_sent = sent_by_id.get(first_id)
        AssertHelper.truthy(first_sent, "Missing event for " + first_id)
        self._post_case(
            receiver, first_id, first_sent, first.get("delivery_headers")
        )
        first_received = self.received_equals_sent(receiver, first_id, first_sent)
        self._log_roundtrip_events(first_id, first_sent, first_received)

        second_sent = sent_by_id.get(second_id)
        AssertHelper.truthy(second_sent, "Missing event for " + second_id)
        response = self._post_case(
            receiver,
            second_id,
            second_sent,
            second.get("delivery_headers"),
            expected_status=HttpStatus.CONFLICT,
        )
        body = response.json() or {}
        AssertHelper.equal(body.get("decode_status"), "duplicate", "Blocked POST should be marked duplicate")
        AssertHelper.equal(body.get("blocked"), True, "Blocked POST should set blocked=true")
        AssertHelper.equal(
            body.get("duplicate_of_case_id"),
            first_id,
            "409 should point at the first stored duplicate case",
        )
        # Blocked POST still logs the event we tried to send (nothing stored).
        self._log_event_body(second_id + ": event after POST (blocked 409)", second_sent)

        # Second case must not appear in the store.
        get_response = self.http.get(receiver.url, params={"case_id": second_id})
        AssertHelper.status_code(get_response, HttpStatus.OK, "GET after blocked POST should succeed")
        rows = (get_response.json() or {}).get("events") or []
        AssertHelper.equal(
            rows,
            [],
            second_id + " must not be stored after duplicate 409",
            data={"case_id": second_id, "rows": rows},
        )

    def check_replays(self, receiver, cases, events):
        """POST each replay delivery → GET event count must match posts; each body equals sent.

        Replay cases share one case_id. Send 2 → expect 2 events; send 1 → expect 1.
        """
        AssertHelper.truthy(cases, "Expected at least one replay case")
        case_ids = {item.get("case_id") for item in cases}
        AssertHelper.equal(
            len(case_ids),
            1,
            "Replay cases should share one case_id so GET can count deliveries",
            data={"case_ids": sorted(str(x) for x in case_ids)},
        )
        case_id = cases[0]["case_id"]
        sent_by_id = self._sent_by_id(events)
        sent = sent_by_id.get(case_id)
        AssertHelper.truthy(sent, "Missing event for " + case_id)
        self._log_expect(
            case_id
            + " replay x"
            + str(len(cases))
            + ": POST each delivery; GET count == "
            + str(len(cases))
            + "; each body equals sent"
        )

        for item in cases:
            self._post_case(receiver, case_id, sent, item.get("delivery_headers"))

        # Catalog arg is also named events — this list is what GET returned.
        received_events = [row.get("event") for row in self._get_rows(receiver, case_id)]
        AssertHelper.equal(
            len(received_events),
            len(cases),
            "Replay: GET must return one stored event per delivery we sent",
            data={
                "case_id": case_id,
                "sent_count": len(cases),
                "received_events_count": len(received_events),
            },
        )
        self._log_event_body(case_id + ": event after POST", sent)
        for index, received in enumerate(received_events):
            self._log_event_body(
                case_id + ": event after GET (delivery " + str(index + 1) + ")",
                received,
            )
            uuid = self.event_uuid(sent) or self.event_uuid(received) or "<missing UUID>"
            AssertHelper.equal(
                received,
                sent,
                "Replay delivery "
                + str(index + 1)
                + " GET event must equal what we sent (UUID "
                + str(uuid)
                + ")",
                data={"UUID": uuid, "case_id": case_id, "delivery": index + 1},
            )


FlowHelper = FlowHelper()
