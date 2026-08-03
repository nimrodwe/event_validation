import pytest

from helpers.asserts import AssertHelper
from helpers.pytest_cases import (
    TypeParams,
    corrupt_field_pytest_params,
    type_bad_pytest_params,
)


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


@pytest.mark.parametrize("case", type_bad_pytest_params())
def test_type_bad(initialize, type_bad_receiver, case):
    """
    One test per validation event (e1 … e10). POST→GET the row as-is, then
    list every EventsSchema type mismatch once.
    """
    AssertHelper.check_type_bad_case(
        type_bad_receiver, initialize.dataset_steps, case
    )


@pytest.mark.negative
@pytest.mark.parametrize("corruptions", corrupt_field_pytest_params())
def test_corrupted_fields_fail(initialize, catalog_receiver, corruptions):
    """
    Corrupt one or more synthetic fields, POST→GET, detect the bad fields, then
    fail the type check (intentional failure — proves the assert path works).
    """
    AssertHelper.check_corrupted_fields(
        catalog_receiver,
        initialize.synthetic_steps,
        initialize.expected_types,
        initialize.synthetic_dataset,
        corruptions,
    )
