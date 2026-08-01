"""Load input JSON fixtures used by type checks and tests."""

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


class DataLoader:
    """Reads project input JSON files into Python objects."""

    def open_json(self, path):
        return open_json(path)

    def load_synthetic_event(self):
        return load_synthetic_event()

    def load_validation_row(self):
        return load_validation_row()

    def load_expected_types(self):
        return load_expected_types()
