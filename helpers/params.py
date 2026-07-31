"""Parametrize case lists for type tests."""

from helpers.matches import dataset_mismatches, synthetic_matches

POSITIVE_FIELDS = synthetic_matches()
NEGATIVE_FIELDS = dataset_mismatches()
