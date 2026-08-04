"""
Learn key rules from the synthetic event, then test validation-dataset rows.

Per event (event-1 … event-10), four tests:
1) new keys — validation key not on synthetic
2) missing keys — synthetic key absent on validation
3) empty string got none or null — present key is null/None
4) string value got empty string — template had a value, validation is \"\"
"""

import json
import re

from src.config import DATASET, INPUT_EVENT, Schema

SAMPLE_SIZE = 10

# Pytest id suffix → dashboard title + log explain (under each event folder).
RULE_SPECS = (
    {
        "id": "new_keys",
        "title": "new keys",
        "kind": "new_keys",
        "explain": (
            "rule: every key on the validation event must exist on synthetic; "
            "if validation has a key synthetic does not (e.g. 'ron'), it is incorrect "
            "- listing all such keys with the value found"
        ),
    },
    {
        "id": "missing_keys",
        "title": "missing keys",
        "kind": "missing_keys",
        "explain": (
            "rule: every key on synthetic must exist on the validation event; "
            "listing keys that are in synthetic but missing from validation "
            "(presence only — values are ignored)"
        ),
    },
    {
        "id": "empty_got_null",
        "title": "empty string got none or null",
        "kind": "empty_got_null",
        # Only rows that already have null hits (same as other negative rules).
        "explain": (
            "listing keys present in the validation dataset whose value is null/None"
            " (with what synthetic had); up to 10 events that hit this rule"
        ),
    },
    {
        "id": "value_got_empty",
        "title": "string value got empty string",
        "kind": "value_got_empty",
        "explain": (
            "listing keys where synthetic had a non-empty string but validation has \"\""
            " (with both values)"
        ),
    },
)

RULE_TITLE_BY_ID = {spec["id"]: spec["title"] for spec in RULE_SPECS}
RULE_EXPLAIN_BY_ID = {spec["id"]: spec["explain"] for spec in RULE_SPECS}


def load_all_validation_rows():
    return json.loads(DATASET.read_text(encoding="utf-8"))


def _norm(key):
    """Normalize names so flat keys match synthetic property keys."""
    return re.sub(r"[^a-z0-9]+", "", str(key).lower().replace("$", ""))


def learn_rules_from_synthetic():
    """
    Learn from synthetic properties:
    - allowed = every properties key
    - empty_ok = template value is \"\"
    - filled = template value is non-empty
    """
    event = json.loads(INPUT_EVENT.read_text(encoding="utf-8"))[0]
    props = event.get("properties") or {}
    schema = Schema()

    empty_ok = []
    filled = []
    template_values = {}
    for key in schema.allowed:
        template_values[key] = props.get(key)
        if props.get(key) == "":
            empty_ok.append(key)
        else:
            filled.append(key)

    return {
        "empty_ok": empty_ok,
        "filled": filled,
        "allowed": list(schema.allowed),
        "template_values": template_values,
        "allowed_by_norm": {_norm(key): key for key in schema.allowed},
        "learn_summary": (
            "synthetic keys="
            + str(len(schema.allowed))
            + " empty_ok(template \"\")="
            + str(len(empty_ok))
            + " filled(template non-empty)="
            + str(len(filled))
        ),
    }


def map_flat_to_synthetic(row, rules):
    """Map flat-row keys → synthetic property keys (normalized)."""
    mapped = {}
    for flat_key in row:
        if flat_key == "Debug Payload":
            continue
        syn = rules["allowed_by_norm"].get(_norm(flat_key))
        if syn is not None:
            mapped[flat_key] = syn
    return mapped


def unknown_flat_keys(row, rules):
    """
    Keys on the validation event that do not exist on synthetic.

    Example: validation has \"ron\" and synthetic does not -> \"ron\" is listed.
    UUID on both sides is NOT listed (it exists on synthetic).
    """
    unknown = []
    for flat_key in row:
        if flat_key == "Debug Payload":
            continue
        if rules["allowed_by_norm"].get(_norm(flat_key)) is None:
            unknown.append(flat_key)
    return unknown


def _format_found(value):
    """Readable value for logs."""
    if value is None:
        return "null"
    if value == "":
        return '""'
    return repr(value)


def apply_new_keys(row, rules):
    """
    Find all keys on the validation event that are not on synthetic.

    Example: validation has key \"ron\" with any value, synthetic has no \"ron\"
    -> one incorrect hit for \"ron\".
    """
    results = []
    for flat_key in unknown_flat_keys(row, rules):
        value = row.get(flat_key)
        results.append(
            {
                "kind": "new_keys",
                "title": RULE_TITLE_BY_ID["new_keys"],
                "field": flat_key,
                "flat_field": flat_key,
                "expected": "key must exist on synthetic",
                "rule": "NEW-" + str(flat_key),
                "template_value": None,
                "source": "synthetic_event_template",
                "actual": value,
                "result": "FAIL",
            }
        )
    return results


def apply_missing_keys(row, rules):
    """Synthetic keys missing from the validation event (presence only; ignore values)."""
    mapped = map_flat_to_synthetic(row, rules)
    flat_by_syn = {syn: flat for flat, syn in mapped.items()}
    results = []

    for syn_key in rules["allowed"]:
        if syn_key in flat_by_syn:
            continue
        results.append(
            {
                "kind": "missing_keys",
                "title": RULE_TITLE_BY_ID["missing_keys"],
                "field": syn_key,
                "flat_field": None,
                "expected": "key present on validation (value ignored)",
                "rule": "MISSING-" + syn_key,
                "template_value": None,
                "source": "synthetic_event_template",
                "actual": None,
                "result": "FAIL",
            }
        )
    return results


def apply_empty_got_null(row, rules):
    """
    Present mapped keys whose value is null/None.
    (Empty-string template may be \"\" or a value; null is never allowed.)
    """
    mapped = map_flat_to_synthetic(row, rules)
    flat_by_syn = {syn: flat for flat, syn in mapped.items()}
    template_values = rules.get("template_values") or {}
    results = []

    for syn_key in rules["allowed"]:
        flat_key = flat_by_syn.get(syn_key)
        if flat_key is None:
            continue
        value = row.get(flat_key)
        if value is not None:
            continue
        template_value = template_values.get(syn_key)
        results.append(
            {
                "kind": "empty_got_null",
                "title": RULE_TITLE_BY_ID["empty_got_null"],
                "field": syn_key,
                "flat_field": flat_key,
                "expected": '"" or value (not null/None)',
                "rule": "NULL-" + syn_key,
                "template_value": template_value,
                "source": "synthetic_event_template",
                "actual": value,
                "result": "FAIL",
            }
        )
    return results


def apply_value_got_empty(row, rules):
    """Template had a non-empty string value; validation has \"\"."""
    mapped = map_flat_to_synthetic(row, rules)
    flat_by_syn = {syn: flat for flat, syn in mapped.items()}
    template_values = rules.get("template_values") or {}
    results = []

    for syn_key in rules["filled"]:
        flat_key = flat_by_syn.get(syn_key)
        if flat_key is None:
            continue
        value = row.get(flat_key)
        if value != "":
            continue
        results.append(
            {
                "kind": "value_got_empty",
                "title": RULE_TITLE_BY_ID["value_got_empty"],
                "field": syn_key,
                "flat_field": flat_key,
                "expected": "non-empty value (template had a string value)",
                "rule": "EMPTY-" + syn_key,
                "template_value": template_values.get(syn_key),
                "source": "synthetic_event_template",
                "actual": value,
                "result": "FAIL",
            }
        )
    return results


def apply_kind(row, rules, kind):
    """Run one named rule kind; returns every matching key for that test."""
    if kind == "new_keys":
        return apply_new_keys(row, rules)
    if kind == "missing_keys":
        return apply_missing_keys(row, rules)
    if kind == "empty_got_null":
        return apply_empty_got_null(row, rules)
    if kind == "value_got_empty":
        return apply_value_got_empty(row, rules)
    raise ValueError("unknown negative rule kind: " + str(kind))


def sample_events_for_kind(kind, n=SAMPLE_SIZE, rules=None, always_sample=False):
    """
    Build event-1 … event-n for one rule.

    Default: first n validation rows that have at least one hit for this rule.
    always_sample=True: take hit rows first, then pad with more rows until n
    (so empty_got_null always has 10 events like new keys, and still keeps real nulls).
    """
    if rules is None:
        rules = learn_rules_from_synthetic()
    rows = load_all_validation_rows()
    found = []
    used = set()

    # Prefer rows that actually hit this rule.
    for index, row in enumerate(rows):
        items = apply_kind(row, rules, kind)
        if not items:
            continue
        found.append(
            {
                "position": len(found) + 1,
                "index": index,
                "row": row,
                "items": items,
            }
        )
        used.add(index)
        if len(found) >= n:
            return found

    if not always_sample:
        return found

    # Pad to n with further validation rows (may have zero findings).
    for index, row in enumerate(rows):
        if index in used:
            continue
        found.append(
            {
                "position": len(found) + 1,
                "index": index,
                "row": row,
                "items": apply_kind(row, rules, kind),
            }
        )
        if len(found) >= n:
            break
    return found


def _field_name(item):
    """Key name for logs — validation/flat name when present, else synthetic."""
    flat = item.get("flat_field")
    field = item.get("field")
    return str(flat or field)


def format_rule_finding(item):
    """
    One clear log line for a key that belongs in this named test.
    Same style for every rule: what mismatched + what we found.
    """
    kind = item.get("kind")
    key = _field_name(item)
    found = _format_found(item.get("actual"))
    synthetic = _format_found(item.get("template_value"))

    if kind == "new_keys":
        # Example: key "ron" in validation, not in synthetic -> incorrect.
        return (
            "incorrect: key "
            + repr(str(key))
            + " is in validation dataset but NOT in synthetic"
            + " | found value = "
            + found
        )
    if kind == "missing_keys":
        # Presence only — do not log synthetic/validation values.
        return (
            "missing key: "
            + repr(str(key))
            + " is in synthetic but NOT in validation dataset"
        )
    if kind == "empty_got_null":
        return (
            "empty string got none or null "
            "(key present in validation as null/None): "
            + str(key)
            + " = "
            + found
            + " | synthetic had "
            + synthetic
        )
    if kind == "value_got_empty":
        return (
            "string value got empty string "
            "(synthetic had a value, validation has \"\"): "
            + str(key)
            + " = "
            + found
            + " | synthetic had "
            + synthetic
        )

    title = item.get("title") or RULE_TITLE_BY_ID.get(kind, kind)
    return (
        str(title)
        + ": "
        + str(key)
        + " = "
        + found
        + " | synthetic had "
        + synthetic
    )


def build_rule_cases(rules=None, n=SAMPLE_SIZE):
    """
    Each negative rule gets its own cases (event-1 … event-n).

    Ids: new_keys-e1, missing_keys-e1, empty_got_null-e1, value_got_empty-e1, …
    empty_got_null always samples n events; other rules sample up to n with hits.
    """
    if rules is None:
        rules = learn_rules_from_synthetic()

    cases = []
    for spec in RULE_SPECS:
        events = sample_events_for_kind(
            spec["id"],
            n=n,
            rules=rules,
            always_sample=bool(spec.get("always_sample")),
        )
        for event in events:
            position = event["position"]
            label = "event-" + str(position)
            case_id = spec["id"] + "-e" + str(position)
            cases.append(
                {
                    "id": case_id,
                    "event_label": label,
                    "position": position,
                    "index": event["index"],
                    "row": event["row"],
                    "kind": spec["id"],
                    "title": spec["title"],
                    "items": event["items"],
                }
            )
    return cases


LEARNED_RULES = learn_rules_from_synthetic()
NEGATIVE_RULE_CASES = build_rule_cases(LEARNED_RULES)
