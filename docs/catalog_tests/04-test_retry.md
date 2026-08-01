# `test_retry`

**File:** `tests/test_catalog.py`  
**Helper:** `AssertHelper.check_retries`  
**Manifest filter:** `type == "retry"`  
**Pipeline cases:**

| case_id | Payload | `delivery_headers` |
|---------|---------|-------------------|
| `RTY-0001` | Same synthetic template event (template UUID) | `Idempotency-Key: k1`, `X-Retry-Count: 1` |
| `RTY-0002` | Same event | `Idempotency-Key: k1`, `X-Retry-Count: 2` |

---

## How this differs from the others

| Topic | This test | Positives |
|--------|-----------|-----------|
| Count check | **Exactly 2** cases (`equal(len(cases), 2)`) | Any non-empty list |
| Headers matter? | **Yes** — must exist on manifest and be stored after POST | Usually `{}` |
| Uses validator? | **No** | No |
| Extra after GET | Compare stored HTTP headers to what we sent | Only event body equality |
| Outer `truthy` in test? | **No** | Yes |

Closest sibling: **`test_replay`** (also a pair + headers), but replay does not re-assert stored headers the same way.

---

## High level

Load the retry pair → require exactly two cases → for each: require retry headers → POST with those headers → GET → body equal → stored headers match.

---

## Test body — line by line

```python
def test_retry(initialize, catalog_receiver):
```

- Same fixtures.

```python
    events, retries = initialize.catalog.cases("retry")
```

- Filter `"retry"`.

```python
    AssertHelper.check_retries(catalog_receiver, retries, events)
```

- **Differs:** no `validator` argument; no `truthy` in the test function.

---

## Inside `check_retries` — step by step

```python
self.equal(len(cases), 2, "Expected exactly two retry cases")
```

- **Differs:** hard requirement of a pair (not “at least one”).

```python
sent_by_id = self._sent_by_id(events)
for item in cases:
    case_id = item["case_id"]
    headers = item.get("delivery_headers") or {}
```

- Read headers from **manifest** (not from the event body).

```python
    self.has_key(headers, "Idempotency-Key", ...)
    self.has_key(headers, "X-Retry-Count", ...)
```

- **Differs:** fail if retry headers were not set when the case was generated.

```python
    sent = sent_by_id.get(case_id)
    self.truthy(sent, ...)
    self._post_case(receiver, case_id, sent, headers)
```

- POST with those delivery headers (merged with `X-Case-Id`).

```python
    self.received_equals_sent(receiver, case_id, sent)
```

- Same body round-trip as positives.

```python
    stored_headers = self._get_rows(receiver, case_id)[-1].get("headers") or {}
    self.equal(stored_headers.get("Idempotency-Key"), headers["Idempotency-Key"])
    self.equal(stored_headers.get("X-Retry-Count"), headers["X-Retry-Count"])
```

- **Differs:** assert the receiver persisted the retry headers we sent.

---

## What success means

Retry deliveries keep the event body and the retry-related headers through POST→GET.
