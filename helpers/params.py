"""Parametrize case lists and ids for type tests."""

from helpers import matches


class TypeParams:
    """Cached field lists for @pytest.mark.parametrize (field name only in Allure)."""

    def __init__(self):
        self.POSITIVE_FIELDS = matches.positive_fields()
        self.NEGATIVE_FIELDS = matches.negative_fields()
        self.POSITIVE_FIELD_NAMES = [m["field"] for m in self.POSITIVE_FIELDS]
        self.NEGATIVE_FIELD_NAMES = [m["field"] for m in self.NEGATIVE_FIELDS]
        self._positive_by_field = {m["field"]: m for m in self.POSITIVE_FIELDS}
        self._negative_by_field = {m["field"]: m for m in self.NEGATIVE_FIELDS}

    def positive_match(self, field):
        return self._positive_by_field[field]

    def negative_match(self, field):
        return self._negative_by_field[field]


TypeParams = TypeParams()


class ParamIds:
    """IDs shown next to parametrized test names (field string or match dict)."""

    def field_id(self, value):
        if isinstance(value, dict):
            return matches.field_id(value)
        return str(value)


ParamIds = ParamIds()
