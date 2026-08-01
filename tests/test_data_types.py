import pytest

from helpers.asserts import AssertHelper
from helpers.params import TypeParams


@pytest.mark.parametrize("field", TypeParams.POSITIVE_FIELD_NAMES)
def test_type_ok(initialize, field):
    """
    Checks one field on the good synthetic event against EventsSchema:
    the value must fit the expected type (no mutation).
    """
    initialize.record_uuid(AssertHelper.event_uuid(initialize.synthetic_dataset))
    match = TypeParams.positive_match(field)
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")
    AssertHelper.fits_type(initialize.synthetic_steps, match)


@pytest.mark.parametrize("field", TypeParams.NEGATIVE_FIELD_NAMES)
def test_type_bad(initialize, field):
    """
    Checks one field on the intentionally corrupted dataset against EventsSchema:
    the value must NOT fit the expected type (negative type case).
    """
    initialize.record_uuid(AssertHelper.event_uuid(initialize.validation_dataset))
    match = TypeParams.negative_match(field)
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")
    AssertHelper.type_mismatch(initialize.dataset_steps, match)
