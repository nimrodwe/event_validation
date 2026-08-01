"""Parametrize case lists and ids for type tests."""

from helpers.matches import FieldMatches


class TypeParams:
    """Cached field lists for @pytest.mark.parametrize."""

    POSITIVE_FIELDS = FieldMatches.positive_fields()
    NEGATIVE_FIELDS = FieldMatches.negative_fields()


class ParamIds:
    """IDs shown next to parametrized test names."""

    @staticmethod
    def field_id(match):
        return FieldMatches.field_id(match)
