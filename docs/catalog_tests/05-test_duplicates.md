# `test_duplicates`

**File:** `tests/test_catalog.py`  
**Helper:** `FlowHelper.check_duplicates`  
**Manifest filter:** `type == "duplicate"`  
**Pipeline cases:**

| case_id | Setup |
|---------|--------|
| `DUP-0001` | Same near-duplicate payload (full body) |
| `DUP-0002` | Same payload again — must be **blocked** by the receiver |

---

## How this differs from the others

| Topic | This test | Positives / Negatives |
|--------|-----------|------------------------|
| Count | Exactly **2** | Any non-empty (or fixed BND set) |
| Second POST | **409 Conflict** (not stored) | Expected **200** |
| Enforcement | Receiver body fingerprint (`UUID` / noise skipped) | Rule findings on GET body |
| Needs both rows together | **Yes** — first stored, second blocked | No |

Retry / replay may still store the same body when `Idempotency-Key` or `X-Replay` is set.

---

## High level

Load the duplicate pair → POST first (200 + GET equals sent) → POST second (409, `blocked`) → GET second `case_id` returns no rows.

---

## Test body

```python
def test_duplicates(initialize, catalog_receiver):
    events, duplicates = initialize.catalog.cases("duplicate")
    FlowHelper.check_duplicates(catalog_receiver, duplicates, events)
```

---

## What success means

- First POST → `200`, GET body equals sent.  
- Second POST (same body) → `409`, `decode_status=duplicate`, `blocked=true`.  
- Second `case_id` is **not** in the store.
