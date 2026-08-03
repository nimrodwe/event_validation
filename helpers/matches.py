"""Build field/type match lists for parametrized tests."""

import json

from helpers.loaders import (
    load_expected_types,
    load_synthetic_event,
)
from helpers.dataset_steps import DatasetSteps
from helpers.logger import quiet_logger
from helpers.synthetic_steps import SyntheticSteps
from src.config import DATASET

# Flat validation row has a Properties column that is the nested dict section,
# not a leaf value to type-check (schema lists it as Map, but we skip it).
TYPE_SKIP_FIELDS = frozenset({"properties"})
TYPE_BAD_EVENT_COUNT = 10


def positive_fields():
    """Synthetic event fields that map into EventsSchema (type_ok cases)."""
    steps = SyntheticSteps(quiet_logger())
    return steps.compare(load_synthetic_event(), load_expected_types())


def _row_type_mismatches(steps, row, schema):
    """EventsSchema type mismatches on one flat row."""
    bad = []
    for match in steps.compare(row, schema):
        if match["field"] in TYPE_SKIP_FIELDS:
            continue
        if not steps.fits_type(match["actual"], match["expected_type"]):
            bad.append(match)
    return bad


def type_bad_rule_cases(n=TYPE_BAD_EVENT_COUNT):
    """
    First n validation events that already fail EventsSchema.

    One pytest per event (e1 … e10): lists every bad field once.
    Rows are kept as loaded (no transforms).
    """
    rows = json.loads(DATASET.read_text(encoding="utf-8"))
    schema = load_expected_types()
    steps = DatasetSteps(quiet_logger())

    cases = []
    position = 0
    for index, row in enumerate(rows):
        mismatches = _row_type_mismatches(steps, row, schema)
        if not mismatches:
            continue
        position += 1
        event_label = "event-" + str(position)
        cases.append(
            {
                "id": "e" + str(position),
                "event_label": event_label,
                "position": position,
                "index": index,
                "row": row,  # original dataset input
                "mismatches": mismatches,
                "fields": [m["field"] for m in mismatches],
            }
        )
        if position >= n:
            break
    return cases
