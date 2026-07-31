"""Build field/type match lists for parametrized tests."""

from helpers.data import load_expected_types, load_synthetic_event, load_validation_row
from helpers.dataset_steps import DatasetSteps
from helpers.logger import collect_logger
from helpers.synthetic_steps import SyntheticSteps


def synthetic_matches():
    steps = SyntheticSteps(collect_logger())
    return steps.compare(load_synthetic_event(), load_expected_types())


def dataset_matches():
    steps = DatasetSteps(collect_logger())
    return steps.compare(load_validation_row(), load_expected_types())


def dataset_mismatches():
    steps = DatasetSteps(collect_logger())
    bad = []
    for match in dataset_matches():
        if not steps.fits_type(match["actual"], match["expected_type"]):
            bad.append(match)
    return bad
