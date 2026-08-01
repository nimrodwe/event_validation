# `test_boundary`

**File:** `tests/test_catalog.py`  
**Helper:** `AssertHelper.check_boundary`  
**Manifest filter:** `type == "boundary"`  
**Pipeline cases:**

| case_id | Setup | Extra expect |
|---------|--------|--------------|
| `BND-0001` | `time = 0` | After GET, `time` still `0` |
| `BND-TOKEN-SHORT` | token length 29 | After GET: length 29 + `FMT` finding |
| `BND-TOKEN-EDGE` | token length 30 (min) | After GET: length 30 + **no** `FMT` |

---

## How this differs from the others

| Topic | This test | Positives / Negatives |
|--------|-----------|------------------------|
| Outer `truthy(cases)` in test file? | **No** — done inside helper | Yes in the test function |
| Requires specific case ids? | **Yes** — must include the three BND ids | No hard-coded ids |
| Per-case branching? | **Yes** (`if case_id == ...`) | Same logic for every case |
| Validator usage | `check_token_length` (not full `check_nested` for every assert) | Negatives use `check_nested` |
| Pass condition | Mix of value checks + FMT present/absent | Positives: equality only; Negatives: target rule |

---

## High level

Load boundary cases → ensure the three known cases exist → for each: POST → GET → equal payload → then case-specific boundary checks.

---

## Test body — line by line

```python
def test_boundary(initialize, catalog_receiver):
```

- Same fixtures.

```python
    events, boundaries = initialize.catalog.cases("boundary")
```

- Filter `"boundary"`.

```python
    AssertHelper.check_boundary(
        catalog_receiver, initialize.validator, boundaries, events
    )
```

- **Differs from positives:** no separate `truthy` in the test; helper validates non-empty + required ids. Passes `validator`.

---

## Inside `check_boundary` — step by step

```python
self.truthy(cases, "No boundary cases in manifest")
```

- Same “list not empty” guard, but inside the helper.

```python
by_id = {item["case_id"]: item for item in cases}
for needed in ("BND-0001", "BND-TOKEN-SHORT", "BND-TOKEN-EDGE"):
    self.has_key(by_id, needed, "Missing " + needed)
```

- **Differs:** catalog must contain these three specific cases (not just “any boundary”).

```python
sent_by_id = self._sent_by_id(events)
for item in cases:
    case_id = item["case_id"]
    sent = sent_by_id.get(case_id)
    self.truthy(sent, ...)
    self._post_case(...)
    received = self.received_equals_sent(...)
```

- Shared round-trip (same as positives/negatives).

```python
    props = received["properties"]
    token = props.get("Appdome fusion app token")
    token_findings = [f.to_dict() for f in validator.check_token_length(received, case_id)]
```

- Prepare values for case-specific checks.

```python
    if case_id == "BND-0001":
        self.equal(props["time"], 0, ...)
```

- Edge time value still `0` after GET.

```python
    elif case_id == "BND-TOKEN-SHORT":
        self.equal(len(str(token)), validator.TOKEN_MIN_LEN - 1, ...)
        self.truthy("FMT" in [...], ...)
```

- Too-short token still short after GET, and `FMT` fires.

```python
    elif case_id == "BND-TOKEN-EDGE":
        self.equal(len(str(token)), validator.TOKEN_MIN_LEN, ...)
        self.equal(token_findings, [], ...)
```

- Exactly min length: no `FMT`.

---

## What success means

Boundary payloads round-trip, and each designed edge behaves correctly after GET (value and/or FMT).
