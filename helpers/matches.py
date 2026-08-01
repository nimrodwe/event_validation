"""Build field/type match lists for parametrized tests."""

from helpers.loaders import DataLoader
from helpers.dataset_steps import DatasetSteps
from helpers.logger import LoggerHelper
from helpers.synthetic_steps import SyntheticSteps


class FieldMatches:
    """Builds positive/negative field match lists for pytest parametrize."""

    @staticmethod
    def field_id(match):
        return match["field"]

    @classmethod
    def synthetic_matches(cls):
        steps = SyntheticSteps(LoggerHelper.collect())
        return steps.compare(
            DataLoader.load_synthetic_event(),
            DataLoader.load_expected_types(),
        )

    @classmethod
    def dataset_matches(cls):
        steps = DatasetSteps(LoggerHelper.collect())
        return steps.compare(
            DataLoader.load_validation_row(),
            DataLoader.load_expected_types(),
        )

    @classmethod
    def dataset_mismatches(cls):
        steps = DatasetSteps(LoggerHelper.collect())
        bad = []
        for match in cls.dataset_matches():
            if not steps.fits_type(match["actual"], match["expected_type"]):
                bad.append(match)
        return bad

    @classmethod
    def positive_fields(cls):
        return cls.synthetic_matches()

    @classmethod
    def negative_fields(cls):
        return cls.dataset_mismatches()
