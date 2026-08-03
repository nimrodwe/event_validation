# Catalog test case docs

One page per test in `tests/test_catalog.py`.

| Doc | Test | Filter / data | Extra beyond POST→GET equality |
|-----|------|---------------|--------------------------------|
| [01-test_positives.md](01-test_positives.md) | `test_positives` | `type == "positive"` | Nested validator findings must be empty |
| [02-test_negatives.md](02-test_negatives.md) | `test_negatives[…]` | validation dataset vs synthetic | 4 named rules × up to 10 events each |
| [03-test_boundary.md](03-test_boundary.md) | `test_boundary[…]` ×4 | `type == "boundary"` | Edge rules (`RANGE-time`, `FMT`) |
| [04-test_retry.md](04-test_retry.md) | `test_retry` | `type == "retry"` | 500 then 200; retry headers |
| [05-test_duplicates.md](05-test_duplicates.md) | `test_duplicates` | `type == "duplicate"` | First 200; second 409 blocked |
| [06-test_replay.md](06-test_replay.md) | `test_replay` | `type == "replay"` | Shared `case_id`; GET count == posts |

Interview walkthrough (HTML): [`../interview.html`](../interview.html)

Data-type tests (separate suite): [`../data_types_tests/`](../data_types_tests/README.md)

## What is the same in every test

1. Fixtures: `initialize` (catalog + helpers) and a receiver (`catalog_receiver` or `negatives_receiver`).
2. Load cases from the generated catalog (or learned negative cases).
3. **POST** → **GET** → assert on the GET body (and HTTP status where relevant).

## What differs

See the “How this differs” section at the top of each doc.
