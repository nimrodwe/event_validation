# `test_replay`

**File:** `tests/test_catalog.py`  
**Helper:** `FlowHelper.check_replays`  
**Manifest filter:** `type == "replay"`  

Replay deliveries **share one `case_id`**. Headers allow redeploy (`X-Replay`, `X-Delivery`).

---

## How this differs from the others

| Topic | This test | `test_retry` | `test_duplicates` |
|--------|-----------|--------------|-------------------|
| Cases | Several deliveries, **one** `case_id` | One case, two attempts | Two case_ids, same body |
| Headers | `X-Replay` / `X-Delivery` | `Idempotency-Key` / `X-Retry-Count` | None (fingerprint blocks) |
| Main assert | GET count == number of POSTs; each body == sent | 500 then 200 | Second POST 409 |

---

## High level

POST each replay delivery under the shared `case_id` → GET → event count matches posts; every stored body equals sent.

---

## Test body

```python
def test_replay(initialize, catalog_receiver):
    events, replays = initialize.catalog.cases("replay")
    FlowHelper.check_replays(catalog_receiver, replays, events)
```

---

## What success means

- All deliveries accepted (200).  
- GET returns one stored event per POST.  
- Each body equals what we sent.
