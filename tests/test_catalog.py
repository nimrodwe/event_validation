"""One test per generated catalog case type (assignment requirement)."""

from helpers.asserts import AssertHelper


def test_positives(initialize, catalog_receiver):
    """POS cases: POST → GET → keys/values unchanged."""

    # step 1:
    # generateing events.


    # step 2:
    # getting the events and positives from the catalog
    events, positives = initialize.catalog.cases("positive")
 
    # step 3:
    # checking if the positives are in the manifest -> stop us if we did not create the positive case correclty / not pulled 
    AssertHelper.truthy(positives, "No positive cases in manifest")

    # step 4:
    # sending the events to the catalog receiver
    
    AssertHelper.check_positives(catalog_receiver, positives, events)


def test_negatives(initialize, catalog_receiver):
    """NEG cases: POST → GET → same payload → target rule on received data."""
    events, negatives = initialize.catalog.cases("negative")
    AssertHelper.truthy(negatives, "No negative cases in manifest")
    AssertHelper.check_negatives(
        catalog_receiver, initialize.validator, negatives, events
    )


def test_boundary(initialize, catalog_receiver):
    """Boundary cases: POST → GET → same payload → boundary rules on received data."""
    events, boundaries = initialize.catalog.cases("boundary")
    AssertHelper.check_boundary(
        catalog_receiver, initialize.validator, boundaries, events
    )


def test_retry(initialize, catalog_receiver):
    """Retry pair: POST → GET → same payload → retry headers preserved."""
    events, retries = initialize.catalog.cases("retry")
    AssertHelper.check_retries(catalog_receiver, retries, events)


def test_duplicates(initialize, catalog_receiver):
    """Duplicates: POST → GET → same payload → DUP-NEAR on received rows."""
    events, duplicates = initialize.catalog.cases("duplicate")
    AssertHelper.check_duplicates(
        catalog_receiver, initialize.validator, duplicates, events
    )


def test_replay(initialize, catalog_receiver):
    """Replay pair: POST → GET → same payload (both deliveries visible)."""
    events, replays = initialize.catalog.cases("replay")
    AssertHelper.check_replays(catalog_receiver, replays, events)
