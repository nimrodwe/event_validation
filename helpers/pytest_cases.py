"""Pytest case lists for @pytest.mark.parametrize (boundary, negatives, types)."""

from helpers import matches
from helpers.dataset_negatives import NEGATIVE_RULE_CASES

# Template defaults used only for before=/after= dashboard logs.
_TEMPLATE_TIME = 1777423175525
_TEMPLATE_TOKEN = "11111111-1111-4111-8111-111111111111"


def _params(cases, *, id_key="id", always_negative=False, negative_key=None):
    """Build pytest.param list; optional @pytest.mark.negative for (N) tags."""
    import pytest

    params = []
    for case in cases:
        is_negative = always_negative or (
            negative_key is not None and case.get(negative_key)
        )
        marks = [pytest.mark.negative] if is_negative else []
        params.append(pytest.param(case, id=case[id_key], marks=marks))
    return params


# One pytest case each (see test_boundary). id = changed key (shown in test name).
# negative=True → dashboard yellow (N) tag.
BOUNDARY_CASES = (
    {
        "case_id": "BND-0001",
        "key": "time",
        "value": 0,
        "before": _TEMPLATE_TIME,
        "id": "time=0",
        "negative": False,
    },
    {
        "case_id": "BND-TIME-NEG",
        "key": "time",
        "value": -1,
        "before": _TEMPLATE_TIME,
        "id": "time=-1",
        "negative": True,
    },
    {
        "case_id": "BND-TOKEN-SHORT",
        "key": "Appdome fusion app token",
        "value": "x" * 29,
        "before": _TEMPLATE_TOKEN,
        "id": "Appdome fusion app token (len=29)",
        "negative": True,
    },
    {
        "case_id": "BND-TOKEN-EDGE",
        "key": "Appdome fusion app token",
        "value": "x" * 30,
        "before": _TEMPLATE_TOKEN,
        "id": "Appdome fusion app token (len=30)",
        "negative": False,
    },
)
BOUNDARY_CASE_IDS = tuple(c["case_id"] for c in BOUNDARY_CASES)
BOUNDARY_CASE_BY_ID = {c["case_id"]: c for c in BOUNDARY_CASES}


def boundary_pytest_params():
    """pytest.param list — negative cases get @pytest.mark.negative for (N)."""
    return _params(BOUNDARY_CASES, negative_key="negative")


# One pytest case each (see test_negatives) — new_keys-e1, missing_keys-e1, …
NEGATIVE_CASES = NEGATIVE_RULE_CASES
NEGATIVE_CASE_IDS = tuple(c["id"] for c in NEGATIVE_CASES)


def negative_pytest_params():
    """pytest.param list — four named tests per event; each gets (N)."""
    return _params(NEGATIVE_CASES, always_negative=True)


class TypeParams:
    """Cached field lists for @pytest.mark.parametrize (field name only in Allure)."""

    def __init__(self):
        positives = matches.positive_fields()
        self.POSITIVE_FIELD_NAMES = [m["field"] for m in positives]
        self._positive_by_field = {m["field"]: m for m in positives}
        # type_bad: 10 validation events (all bad fields listed once per event)
        self.TYPE_BAD_CASES = matches.type_bad_rule_cases()

    def positive_match(self, field):
        return self._positive_by_field[field]


TypeParams = TypeParams()


def type_bad_pytest_params():
    """pytest.param list — e1 … e10 (one test per event on the dashboard)."""
    return _params(TypeParams.TYPE_BAD_CASES, always_negative=True)


# Intentional corruptions on synthetic event (property key → bad value).
# Keys must exist on synthetic AND map into EventsSchema.
_CORRUPT_FIELD_RAW = (
    {
        "id": "one-field",
        "corruptions": (("UUID", 12345),),
    },
    {
        "id": "three-fields",
        "corruptions": (
            ("UUID", 12345),
            ("Appdome fusion app token", 999),
            ("devicePlatform", ["Android"]),
        ),
    },
)


def corrupt_field_pytest_params():
    """pytest.param list for intentional synthetic field corruption cases."""
    import pytest

    return [
        pytest.param(case["corruptions"], id=case["id"])
        for case in _CORRUPT_FIELD_RAW
    ]
