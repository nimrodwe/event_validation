# Catalog test case docs

One page per test in `tests/test_catalog.py`.

| Doc | Test | Filter `type` | Extra beyond POST→GET equality |
|-----|------|---------------|--------------------------------|
| [01-test_positives.md](01-test_positives.md) | `test_positives` | `positive` | None (round-trip only) |
| [02-test_negatives.md](02-test_negatives.md) | `test_negatives` | `negative` | Target rule must appear |
| [03-test_boundary.md](03-test_boundary.md) | `test_boundary` | `boundary` | Per-case boundary asserts |
| [04-test_retry.md](04-test_retry.md) | `test_retry` | `retry` | Retry headers preserved |
| [05-test_duplicates.md](05-test_duplicates.md) | `test_duplicates` | `duplicate` | First 202; second 409 blocked |
| [06-test_replay.md](06-test_replay.md) | `test_replay` | `replay` | Pair of deliveries visible |

Shared overview: [../CATALOG_TESTS.md](../CATALOG_TESTS.md)

Data-type tests (separate suite): [`../data_types_tests/`](../data_types_tests/README.md)

## What is the same in every test

1. Fixtures: `initialize` (catalog + helpers) and `catalog_receiver` (fresh localhost store).
2. Load cases: `events, cases = initialize.catalog.cases("<type>")`.
3. For each case in the filtered list: look up payload by `case_id`, **POST**, **GET**, assert payload unchanged (unless noted).

## What differs

See the “How this differs” section at the top of each doc.
