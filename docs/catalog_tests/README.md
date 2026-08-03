# Catalog test case docs

One page per test in `tests/test_catalog.py`.

| Doc | Test | Filter `type` | Extra beyond POST→GET equality |
|-----|------|---------------|--------------------------------|
| [01-test_positives.md](01-test_positives.md) | `test_positives` | `positive` | None (round-trip only) |
| [02-test_negatives.md](02-test_negatives.md) | `test_negatives[new_keys-e1]` … | validation dataset | Each rule has its own event-1…n cases |
| [03-test_boundary.md](03-test_boundary.md) | `test_boundary[…]` ×4 | `boundary` | One pytest test per BND edge (`time=0`, `time=-1`, token 29/30) |
| [04-test_retry.md](04-test_retry.md) | `test_retry` | `retry` | Retry headers preserved |
| [05-test_duplicates.md](05-test_duplicates.md) | `test_duplicates` | `duplicate` | First 200; second 409 blocked |
| [06-test_replay.md](06-test_replay.md) | `test_replay` | `replay` | Pair of deliveries visible |

Shared overview: [../CATALOG_TESTS.md](../CATALOG_TESTS.md)

Data-type tests (separate suite): [`../data_types_tests/`](../data_types_tests/README.md)

## What is the same in every test

1. Fixtures: `initialize` (catalog + helpers) and `catalog_receiver` (fresh localhost store).
2. Load cases: `events, cases = initialize.catalog.cases("<type>")`.
3. For each case: **POST**, **GET**, assert payload unchanged (unless noted). Negatives then require `check_nested` findings; positives require none.

## What differs

See the “How this differs” section at the top of each doc.
