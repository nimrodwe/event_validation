"""Parametrize case lists and ids for type tests."""

from helpers.matches import FieldMatches


class TypeParams:
    """Cached field lists for @pytest.mark.parametrize (field name only in Allure)."""

    POSITIVE_FIELDS = FieldMatches.positive_fields()
    NEGATIVE_FIELDS = FieldMatches.negative_fields()
    POSITIVE_FIELD_NAMES = [m["field"] for m in POSITIVE_FIELDS]
    NEGATIVE_FIELD_NAMES = [m["field"] for m in NEGATIVE_FIELDS]
    _POSITIVE_BY_FIELD = {m["field"]: m for m in POSITIVE_FIELDS}
    _NEGATIVE_BY_FIELD = {m["field"]: m for m in NEGATIVE_FIELDS}

    @classmethod
    def positive_match(cls, field):
        return cls._POSITIVE_BY_FIELD[field]

    @classmethod
    def negative_match(cls, field):
        return cls._NEGATIVE_BY_FIELD[field]


class ParamIds:
    """IDs shown next to parametrized test names (field string or match dict)."""

    @staticmethod
    def field_id(value):
        if isinstance(value, dict):
            return FieldMatches.field_id(value)
        return str(value)
