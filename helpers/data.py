"""Load input JSON used by type checks."""

import json

from src.config import DATASET, EXPECTED_TYPES, INPUT_EVENT


def open_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_synthetic_event():
    return open_json(INPUT_EVENT)[0]


def load_validation_row():
    return open_json(DATASET)[0]


def load_expected_types():
    return open_json(EXPECTED_TYPES)
