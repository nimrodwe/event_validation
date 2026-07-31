import pytest

from helpers import NEGATIVE_FIELDS, POSITIVE_FIELDS, field_id
from helpers.asserts import AssertError, AssertHelper
from helpers.logger import LoggerHelper
from services.http_status import HttpStatus


@pytest.mark.parametrize("match", POSITIVE_FIELDS, ids=field_id)
def test_positive_property_type(initialize, match):
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")

    try:
        AssertHelper.fits_type(initialize.synthetic_steps, match)
    except AssertError:
        initialize.logger.error(LoggerHelper.type_line(match))
        raise


def test_positive_send_to_localhost(initialize):
    response = initialize.synthetic_steps.send(initialize.synthetic_dataset, initialize.localhost)
    AssertHelper.status_code(
        response,
        HttpStatus.ACCEPTED,
        "Synthetic event POST should be accepted by localhost",
    )


def test_negative_dataset_has_mismatches():
    AssertHelper.truthy(
        NEGATIVE_FIELDS,
        "Negative test expected type mismatches, but all fields looked valid",
    )


@pytest.mark.parametrize("match", NEGATIVE_FIELDS, ids=field_id)
def test_negative_property_type_mismatch(initialize, match):
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")

    initialize.logger.info(LoggerHelper.type_line(match))
    AssertHelper.type_mismatch(initialize.dataset_steps, match)


def test_negative_send_to_localhost(initialize):
    response = initialize.dataset_steps.send(initialize.validation_dataset, initialize.localhost)
    AssertHelper.status_code(
        response,
        HttpStatus.ACCEPTED,
        "Dataset row POST should be accepted by localhost",
    )
