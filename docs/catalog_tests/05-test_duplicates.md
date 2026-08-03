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
| Enforcement | Receiver body fingerprint (`UUID` skipped) | Negatives: `check_nested` + `target_rule_id` |
| Needs both rows together | **No** — second never lands | No |
| Outer `truthy` in test? | **No** | Yes for pos/neg |

Retry / replay may still store the same body when `Idempotency-Key` or `X-Replay` is set.

---

## High level

Load the duplicate pair → POST first (200 + GET equals sent) → POST second (409, `blocked`) → GET second case_id returns no rows.

---

## Test body — line by line

```python
def test_duplicates(initialize, catalog_receiver):
```

- Same fixtures.

```python
    events, duplicates = initialize.catalog.cases("duplicate")
```

- Filter `"duplicate"`.

```python
    AssertHelper.check_duplicates(
        catalog_receiver, initialize.validator, duplicates, events
    )
```

- No outer `truthy`.

---

## Inside `check_duplicates` — step by step

```python
self.equal(len(cases), 2, "Expected exactly two duplicate cases")
```

- Pair required.

```python
self._post_case(..., first_id, first_sent, ...)
self.received_equals_sent(...)
```

- First delivery accepted and round-trips.

```python
self._post_case(..., second_id, second_sent, ..., expected_status=HttpStatus.CONFLICT)
```

- Second same body → **409**; receipt has `decode_status: "duplicate"`, `blocked: true`, `duplicate_of_case_id` = first.

```python
GET ?case_id=DUP-0002 → events == []
```

- Blocked POST must not appear in the store.

---

## What success means

The receiver is idempotent for plain duplicate bodies: first wins, second is rejected with 409.
