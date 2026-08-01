"""Build field/type match lists for parametrized tests."""

from helpers.loaders import (
    load_expected_types,
    load_synthetic_event,
    load_validation_row,
)
from helpers.dataset_steps import DatasetSteps
from helpers.logger import quiet_logger
from helpers.synthetic_steps import SyntheticSteps

# Flat validation row has a Properties column that is the nested dict section,
# not a leaf value to type-check (schema lists it as Map, but we skip it).
TYPE_SKIP_FIELDS = frozenset({"properties"})


def field_id(match):
    return match["field"]


def synthetic_matches():
    steps = SyntheticSteps(quiet_logger())
    return steps.compare(load_synthetic_event(), load_expected_types())


def dataset_matches():
    steps = DatasetSteps(quiet_logger())
    matches = steps.compare(load_validation_row(), load_expected_types())
    return [m for m in matches if m["field"] not in TYPE_SKIP_FIELDS]


def dataset_mismatches():
    steps = DatasetSteps(quiet_logger())
    bad = []
    for match in dataset_matches():
        if not steps.fits_type(match["actual"], match["expected_type"]):
            bad.append(match)
    return bad


def positive_fields():
    return synthetic_matches()


def negative_fields():
    return dataset_mismatches()


class FieldMatches:
    """Builds positive/negative field match lists for pytest parametrize."""

    def field_id(self, match):
        return field_id(match)

    def synthetic_matches(self):
        return synthetic_matches()

    def dataset_matches(self):
        return dataset_matches()

    def dataset_mismatches(self):
        return dataset_mismatches()

    def positive_fields(self):
        return positive_fields()

    def negative_fields(self):
        return negative_fields()
