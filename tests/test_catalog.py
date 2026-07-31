"""One test per generated catalog case type."""

import pytest

from helpers.asserts import AssertHelper
from helpers.catalog import (
    REQUIRED_CASE_TYPES,
    cases_of_type,
    event_for_case,
    generate_catalog,
    load_events,
    load_manifest,
    received_by_case_id,
    send_case,
)
from services.http_status import HttpStatus
from src.receiver import Receiver
from src.validate import Validator


@pytest.fixture
def catalog_receiver(tmp_path):
    """Fresh receiver so catalog tests use current server code."""
    server = Receiver.connect(tmp_path / "received")
    yield server
    server.disconnect()


def test_manifest_contains_all_case_types(tmp_path):
    """Catalog checklist: every required case type appears in the manifest."""
    generated = generate_catalog(tmp_path)
    manifest = load_manifest(generated)
    types_found = set()
    for item in manifest:
        types_found.add(item.get("type"))

    for case_type in REQUIRED_CASE_TYPES:
        AssertHelper.truthy(
            case_type in types_found,
            "Manifest is missing case type '" + case_type + "'. Found: " + str(sorted(types_found)),
        )


def test_generate_is_deterministic(tmp_path):
    """Same generator input must produce the same case IDs and payloads twice."""
    first = generate_catalog(tmp_path / "run1")
    second = generate_catalog(tmp_path / "run2")

    ids_1 = [item["case_id"] for item in load_manifest(first)]
    ids_2 = [item["case_id"] for item in load_manifest(second)]
    AssertHelper.equal(ids_1, ids_2, "Case IDs changed between two generate runs")

    events_1 = load_events(first)
    events_2 = load_events(second)
    AssertHelper.equal(events_1, events_2, "Event payloads changed between two generate runs")


def test_positive_cases_validate_and_post(catalog_receiver, tmp_path):
    """Generated POS events should validate clean and POST as accepted."""
    generated = generate_catalog(tmp_path)
    manifest = load_manifest(generated)
    events = load_events(generated)
    positives = cases_of_type(manifest, "positive")
    AssertHelper.truthy(positives, "No positive cases in manifest")

    validator = Validator()
    for item in positives:
        case_id = item["case_id"]
        event = event_for_case(events, case_id)
        AssertHelper.truthy(event, "Missing event for " + case_id)

        findings = [f.to_dict() for f in validator.check_nested(event, case_id)]
        AssertHelper.equal(
            findings,
            [],
            "Positive case " + case_id + " should have no validation findings",
        )

        response = send_case(catalog_receiver, case_id, event, item.get("delivery_headers"))
        AssertHelper.status_code(
            response,
            HttpStatus.ACCEPTED,
            "Positive case " + case_id + " POST should be accepted",
        )


def test_negative_cases_hit_target_rule(catalog_receiver, tmp_path):
    """Each NEG case should produce a finding for its target_rule_id."""
    generated = generate_catalog(tmp_path)
    manifest = load_manifest(generated)
    events = load_events(generated)
    negatives = cases_of_type(manifest, "negative")
    AssertHelper.truthy(negatives, "No negative cases in manifest")

    validator = Validator()
    for item in negatives:
        case_id = item["case_id"]
        target = item["target_rule_id"]
        event = event_for_case(events, case_id)
        AssertHelper.truthy(event, "Missing event for " + case_id)

        findings = [f.to_dict() for f in validator.check_nested(event, case_id)]
        rule_ids = [f["rule_id"] for f in findings]
        AssertHelper.truthy(
            target in rule_ids,
            "Negative case "
            + case_id
            + " should hit rule "
            + target
            + ", got "
            + str(rule_ids),
        )

        response = send_case(catalog_receiver, case_id, event, item.get("delivery_headers"))
        AssertHelper.status_code(
            response,
            HttpStatus.ACCEPTED,
            "Negative case " + case_id + " should still be accepted (kept visible)",
        )


def test_boundary_case_accepted(catalog_receiver, tmp_path):
    """Boundary case BND-0001 is valid enough to POST successfully."""
    generated = generate_catalog(tmp_path)
    manifest = load_manifest(generated)
    events = load_events(generated)
    boundaries = cases_of_type(manifest, "boundary")
    AssertHelper.truthy(boundaries, "No boundary cases in manifest")

    item = boundaries[0]
    case_id = item["case_id"]
    AssertHelper.equal(case_id, "BND-0001", "Expected boundary case id BND-0001")
    event = event_for_case(events, case_id)
    AssertHelper.equal(event["properties"]["time"], 0, "Boundary case should use time=0")

    response = send_case(catalog_receiver, case_id, event, item.get("delivery_headers"))
    AssertHelper.status_code(
        response,
        HttpStatus.ACCEPTED,
        "Boundary case should be accepted by localhost",
    )
    AssertHelper.truthy(
        received_by_case_id(catalog_receiver, case_id),
        "Boundary case was not stored by the receiver",
    )


def test_retry_cases_stored_with_headers(catalog_receiver, tmp_path):
    """Retry pair is stored twice with idempotency / retry headers."""
    generated = generate_catalog(tmp_path)
    manifest = load_manifest(generated)
    events = load_events(generated)
    retries = cases_of_type(manifest, "retry")
    AssertHelper.equal(len(retries), 2, "Expected exactly two retry cases")

    for item in retries:
        case_id = item["case_id"]
        headers = item.get("delivery_headers", {})
        AssertHelper.has_key(headers, "Idempotency-Key", case_id + " missing Idempotency-Key")
        AssertHelper.has_key(headers, "X-Retry-Count", case_id + " missing X-Retry-Count")

        event = event_for_case(events, case_id)
        response = send_case(catalog_receiver, case_id, event, headers)
        AssertHelper.status_code(response, HttpStatus.ACCEPTED, case_id + " POST failed")

        stored = received_by_case_id(catalog_receiver, case_id)
        AssertHelper.truthy(stored, case_id + " was not stored")
        stored_headers = stored[-1].get("headers", {})
        AssertHelper.equal(
            stored_headers.get("Idempotency-Key"),
            headers["Idempotency-Key"],
            case_id + " stored Idempotency-Key mismatch",
        )
        AssertHelper.equal(
            stored_headers.get("X-Retry-Count"),
            headers["X-Retry-Count"],
            case_id + " stored X-Retry-Count mismatch",
        )


def test_duplicate_cases_kept_with_finding(catalog_receiver, tmp_path):
    """Duplicate pair stays visible and produces a duplicate finding."""
    generated = generate_catalog(tmp_path)
    manifest = load_manifest(generated)
    events = load_events(generated)
    duplicates = cases_of_type(manifest, "duplicate")
    AssertHelper.equal(len(duplicates), 2, "Expected exactly two duplicate cases")

    validator = Validator()
    received_items = []
    for item in duplicates:
        case_id = item["case_id"]
        event = event_for_case(events, case_id)
        response = send_case(catalog_receiver, case_id, event, item.get("delivery_headers"))
        AssertHelper.status_code(response, HttpStatus.ACCEPTED, case_id + " POST failed")
        stored = received_by_case_id(catalog_receiver, case_id)
        AssertHelper.truthy(stored, case_id + " was dropped by the receiver")
        received_items.append(stored[-1])

    findings = [f.to_dict() for f in validator.check_received_dupes(received_items)]
    AssertHelper.truthy(
        findings,
        "Duplicate cases should produce a duplicate finding (both kept visible)",
    )
    AssertHelper.equal(
        findings[0]["rule_id"],
        "DUP-NEAR",
        "Expected DUP-NEAR finding for duplicate cases",
    )


def test_replay_cases_both_visible(catalog_receiver, tmp_path):
    """Replay pair: same payload delivered twice, both stay visible."""
    generated = generate_catalog(tmp_path)
    manifest = load_manifest(generated)
    events = load_events(generated)
    replays = cases_of_type(manifest, "replay")
    AssertHelper.equal(len(replays), 2, "Expected exactly two replay cases")

    for item in replays:
        case_id = item["case_id"]
        event = event_for_case(events, case_id)
        response = send_case(catalog_receiver, case_id, event, item.get("delivery_headers"))
        AssertHelper.status_code(response, HttpStatus.ACCEPTED, case_id + " POST failed")
        AssertHelper.truthy(
            received_by_case_id(catalog_receiver, case_id),
            "Replay case " + case_id + " is not visible in the receiver store",
        )
