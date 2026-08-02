"""One test per generated catalog case type (assignment requirement)."""

from helpers.asserts import AssertHelper


def test_positives(initialize, catalog_receiver):
    """
    Sends each positive catalog event, GETs it back (round-trip), then runs the
    same nested rules as negatives and expects no findings.
    """
    events, positives = initialize.catalog.cases("positive")
    AssertHelper.truthy(positives, "No positive cases in manifest")
    AssertHelper.check_positives(
        catalog_receiver, initialize.validator, positives, events
    )


def test_negatives(initialize, catalog_receiver):
    """
    Sends each negative catalog event, GETs it back, checks intentional bad
    field values (manifest expect), then expects the target rule on that field.
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
    First duplicate POST is accepted and round-trips; the second same body
    is blocked with 409 and never stored.
    """
    events, duplicates = initialize.catalog.cases("duplicate")
    AssertHelper.check_duplicates(
        catalog_receiver, initialize.validator, duplicates, events
    )


def test_replay(initialize, catalog_receiver):
    """
    Sends replay deliveries under one case_id, then asserts GET returns the
    same number of events we POSTed (2→2, 1→1) with matching payloads.
    """
    events, replays = initialize.catalog.cases("replay")
    AssertHelper.check_replays(catalog_receiver, replays, events)
