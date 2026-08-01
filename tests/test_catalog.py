"""One test per generated catalog case type (assignment requirement)."""

from helpers.asserts import AssertHelper


def test_positives(initialize, catalog_receiver):
    """
    Sends each positive catalog event to the local receiver, then GETs it back
    and checks the stored payload matches what was sent (round-trip).
    """
    events, positives = initialize.catalog.cases("positive")
    AssertHelper.truthy(positives, "No positive cases in manifest")
    AssertHelper.check_positives(catalog_receiver, positives, events)


def test_negatives(initialize, catalog_receiver):
    """
    Sends each negative catalog event, confirms GET returns the same payload,
    and checks the target validation rule fires on the received event.
    """
    events, negatives = initialize.catalog.cases("negative")
    AssertHelper.truthy(negatives, "No negative cases in manifest")
    AssertHelper.check_negatives(
        catalog_receiver, initialize.validator, negatives, events
    )


def test_boundary(initialize, catalog_receiver):
    """
    Sends boundary catalog events (edge values), confirms GET round-trip,
    and checks boundary-specific rules such as token length.
    """
    events, boundaries = initialize.catalog.cases("boundary")
    AssertHelper.check_boundary(
        catalog_receiver, initialize.validator, boundaries, events
    )


def test_retry(initialize, catalog_receiver):
    """
    Sends the retry case pair with Idempotency-Key / X-Retry-Count headers,
    confirms GET round-trip, and checks those headers were stored.
    """
    events, retries = initialize.catalog.cases("retry")
    AssertHelper.check_retries(catalog_receiver, retries, events)


def test_duplicates(initialize, catalog_receiver):
    """
    Sends the near-duplicate case pair, confirms GET round-trip for each,
    and checks validator reports DUP-NEAR on the received rows.
    """
    events, duplicates = initialize.catalog.cases("duplicate")
    AssertHelper.check_duplicates(
        catalog_receiver, initialize.validator, duplicates, events
    )


def test_replay(initialize, catalog_receiver):
    """
    Sends the replay case pair (same logical delivery twice), confirms both
    POSTs are accepted and GET returns each payload unchanged.
    """
    events, replays = initialize.catalog.cases("replay")
    AssertHelper.check_replays(catalog_receiver, replays, events)
