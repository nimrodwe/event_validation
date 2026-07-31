import logging

from helpers.data import load_expected_types, load_synthetic_event, load_validation_row
from helpers.dataset_steps import DatasetSteps
from helpers.synthetic_steps import SyntheticSteps


class BaseClass:
    def __init__(self, localhost, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.localhost = localhost
        self.synthetic_dataset = load_synthetic_event()
        self.validation_dataset = load_validation_row()
        self.expected_types = load_expected_types()
        self.synthetic_steps = SyntheticSteps(self.logger)
        self.dataset_steps = DatasetSteps(self.logger)
