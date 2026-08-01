"""Load input JSON fixtures used by type checks and tests."""

import json

from src.config import DATASET, EXPECTED_TYPES, INPUT_EVENT


class DataLoader:
    """Reads project input JSON files into Python objects."""

    @staticmethod
    def open_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def load_synthetic_event(cls):
        return cls.open_json(INPUT_EVENT)[0]

    @classmethod
    def load_validation_row(cls):
        return cls.open_json(DATASET)[0]

    @classmethod
    def load_expected_types(cls):
        return cls.open_json(EXPECTED_TYPES)
