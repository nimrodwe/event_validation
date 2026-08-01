import pytest

from helpers.asserts import AssertHelper
from helpers.params import TypeParams


@pytest.mark.parametrize("field", TypeParams.POSITIVE_FIELD_NAMES)
def test_type_ok(initialize, catalog_receiver, field):
    """
    POSTs the synthetic event, GETs it back and checks the receiver stored the
    same payload, then checks one field against EventsSchema (must fit).
    """
    event = initialize.synthetic_dataset
    match = TypeParams.positive_match(field)
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")
    AssertHelper.post_get_equals(
        catalog_receiver, "TYPE-OK-" + field, event, record_uuid=True
    )
    AssertHelper.fits_type(initialize.synthetic_steps, match)


@pytest.mark.parametrize("field", TypeParams.NEGATIVE_FIELD_NAMES)
def test_type_bad(initialize, catalog_receiver, field):
    """
    POSTs the corrupted validation row, GETs it back and checks the receiver
    stored the same payload, then checks one field against EventsSchema
    (must NOT fit). Does not record UUID (validation JSON keeps its own id).
    """
    row = initialize.validation_dataset
    match = TypeParams.negative_match(field)
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")
    AssertHelper.post_get_equals(
        catalog_receiver, "TYPE-BAD-" + field, row, record_uuid=False
    )
    AssertHelper.type_mismatch(initialize.dataset_steps, match)
