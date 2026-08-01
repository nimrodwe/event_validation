import pytest

from helpers.asserts import AssertHelper
from helpers.params import ParamIds, TypeParams


@pytest.mark.parametrize("match", TypeParams.POSITIVE_FIELDS, ids=ParamIds.field_id)
def test_type_ok(initialize, match):
    """Each synthetic field fits its EventsSchema type (does not mutate values)."""
    initialize.record_uuid(AssertHelper.event_uuid(initialize.synthetic_dataset))
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")
    AssertHelper.fits_type(initialize.synthetic_steps, match)


@pytest.mark.parametrize("match", TypeParams.NEGATIVE_FIELDS, ids=ParamIds.field_id)
def test_type_bad(initialize, match):
    """Each already-corrupted dataset field fails its EventsSchema type (no mutation)."""
    initialize.record_uuid(AssertHelper.event_uuid(initialize.validation_dataset))
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")
    AssertHelper.type_mismatch(initialize.dataset_steps, match)
