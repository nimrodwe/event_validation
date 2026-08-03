"""Parametrize case lists and ids for type / catalog tests."""

from helpers import matches
from helpers.dataset_negatives import NEGATIVE_RULE_CASES

# One pytest case each (see test_boundary). id = changed key (shown in test name).
# negative=True → dashboard yellow (N) tag.
# Template defaults used only for before=/after= dashboard logs.
_TEMPLATE_TIME = 1777423175525
_TEMPLATE_TOKEN = "11111111-1111-4111-8111-111111111111"

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
    import pytest

    params = []
    for case in BOUNDARY_CASES:
        marks = [pytest.mark.negative] if case.get("negative") else []
        params.append(pytest.param(case, id=case["id"], marks=marks))
    return params


# One pytest case each (see test_negatives) — new_keys-e1, missing_keys-e1, …
NEGATIVE_CASES = NEGATIVE_RULE_CASES
NEGATIVE_CASE_IDS = tuple(c["id"] for c in NEGATIVE_CASES)


def negative_pytest_params():
    """pytest.param list — four named tests per event; each gets (N)."""
    import pytest

    return [
        pytest.param(case, id=case["id"], marks=[pytest.mark.negative])
        for case in NEGATIVE_CASES
    ]


class TypeParams:
    """Cached field lists for @pytest.mark.parametrize (field name only in Allure)."""

    def __init__(self):
        self.POSITIVE_FIELDS = matches.positive_fields()
        self.NEGATIVE_FIELDS = matches.negative_fields()
        self.POSITIVE_FIELD_NAMES = [m["field"] for m in self.POSITIVE_FIELDS]
        self.NEGATIVE_FIELD_NAMES = [m["field"] for m in self.NEGATIVE_FIELDS]
        self._positive_by_field = {m["field"]: m for m in self.POSITIVE_FIELDS}
        self._negative_by_field = {m["field"]: m for m in self.NEGATIVE_FIELDS}
        # type_bad: 10 validation events (all bad fields listed once per event)
        self.TYPE_BAD_CASES = matches.type_bad_rule_cases()

    def positive_match(self, field):
        return self._positive_by_field[field]

    def negative_match(self, field):
        return self._negative_by_field[field]


TypeParams = TypeParams()


def type_bad_pytest_params():
    """pytest.param list — e1 … e10 (one test per event on the dashboard)."""
    import pytest

    return [
        pytest.param(case, id=case["id"], marks=[pytest.mark.negative])
        for case in TypeParams.TYPE_BAD_CASES
    ]


class ParamIds:
    """IDs shown next to parametrized test names (field string or match dict)."""

    def field_id(self, value):
        if isinstance(value, dict):
            return matches.field_id(value)
        return str(value)


ParamIds = ParamIds()
