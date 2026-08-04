"""One test per generated catalog case type (assignment requirement)."""

import pytest

from helpers.asserts import AssertHelper
from helpers.flows import FlowHelper
from helpers.pytest_cases import boundary_pytest_params, negative_pytest_params


def test_positives(initialize, catalog_receiver):
    """
    Sends each positive catalog event, GETs it back (round-trip), then runs the
    same nested rules as negatives and expects no findings.
    """
    events, positives = initialize.catalog.cases("positive")
    AssertHelper.truthy(positives, "No positive cases in manifest")
    FlowHelper.check_positives(
        catalog_receiver, initialize.validator, positives, events
    )


@pytest.mark.parametrize("negative", negative_pytest_params())
def test_negatives(initialize, negatives_receiver, negative):
    """
    Each rule has its own events (new_keys-e1, missing_keys-e1, …).
    POST→GET equals sent, then asserts the named rule produces findings
    (opposite of positives), and logs every matching key.
    """
    FlowHelper.check_dataset_negative_rule(negatives_receiver, negative)


@pytest.mark.parametrize("boundary", boundary_pytest_params())
def test_boundary(initialize, catalog_receiver, boundary):
    """
    One boundary case per pytest run (named by the key we changed).
    Negative edges (time=-1, short token) get the dashboard (N) tag.
    """
    events, item = FlowHelper.catalog_case(
        initialize.catalog, "boundary", boundary["case_id"]
    )
    FlowHelper.check_boundary_case(
        catalog_receiver,
        initialize.validator,
        item,
        events,
        changed_key=boundary["key"],
        changed_value=boundary["value"],
    )


def test_retry(initialize, catalog_receiver):
    """
    First POST fails (500, server could not accept); retry with the valid event succeeds
    (200) and GET returns that event.
    """
    events, retries = initialize.catalog.cases("retry")
    FlowHelper.check_retries(catalog_receiver, retries, events)


def test_duplicates(initialize, catalog_receiver):
    """
    First duplicate POST is accepted and round-trips; the second same body
    is blocked with 409 and never stored.
    """
    events, duplicates = initialize.catalog.cases("duplicate")
    FlowHelper.check_duplicates(catalog_receiver, duplicates, events)


def test_replay(initialize, catalog_receiver):
    """
    Sends replay deliveries under one case_id, then asserts GET returns the
    same number of events we POSTed (2→2, 1→1) with matching payloads.
    """
    events, replays = initialize.catalog.cases("replay")
    FlowHelper.check_replays(catalog_receiver, replays, events)
