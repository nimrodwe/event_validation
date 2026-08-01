# `test_negatives`

**File:** `tests/test_catalog.py`  
**Helper:** `AssertHelper.check_negatives`  
**Manifest filter:** `type == "negative"`  
**Pipeline cases:**

| case_id | What was broken | `target_rule_id` |
|---------|-----------------|------------------|
| `NEG-UUID` | `UUID` set to `""` | `REQ-UUID` |
| `NEG-TYPE` | `Threatcode` set to `None` | `REQ-Threatcode` |
| `NEG-SCHEMA` | Extra key `__bad` | `SCHEMA` |
| `NEG-XFIELD` | `devicePlatform` ≠ `$os` | `XFIELD-OS` |

---

## How this differs from the others

| Topic | This test | Positives |
|--------|-----------|-----------|
| Round-trip equality | Yes (same) | Yes |
| After GET | Run `validator.check_nested` on **received** data | Stop after equality |
| Pass condition | `target_rule_id` must be in findings | No rule check |
| Uses `initialize.validator` | **Yes** | No |
| Cases | Intentionally broken copies of template | Unbroken copy |

Same outer shape as positives (`cases` + `truthy` + `check_*`). Different helper logic after GET.

---

## High level

Load negative cases → for each: POST → GET → payload unchanged → validate received event → assert the designed rule fired.

---

## Test body — line by line

```python
def test_negatives(initialize, catalog_receiver):
```

- Same fixtures as positives.

```python
    events, negatives = initialize.catalog.cases("negative")
```

- Same as positives, but filter `"negative"`.

```python
    AssertHelper.truthy(negatives, "No negative cases in manifest")
```

- Same idea as positives: list must be non-empty.

```python
    AssertHelper.check_negatives(
        catalog_receiver, initialize.validator, negatives, events
    )
```

- **Differs:** passes `validator` so rules can run on received data.

---

## Inside `check_negatives` — step by step

```python
sent_by_id = self._sent_by_id(events)
for item in cases:
    case_id = item["case_id"]
```

- Same loop setup as positives.

```python
    target = item["target_rule_id"]
```

- **Differs:** read which rule this case was built to trigger (from manifest).

```python
    sent = sent_by_id.get(case_id)
    self.truthy(sent, "Missing event for " + case_id)
    self._post_case(...)
    received = self.received_equals_sent(...)
```

- Same POST → GET → equality as positives.
- Keeps `received` for the next steps.

```python
    findings = [f.to_dict() for f in validator.check_nested(received, case_id)]
```

- **Differs:** run nested validation rules on what came back from the server (not on the in-memory copy before send).

```python
    rule_ids = [f["rule_id"] for f in findings]
    self.truthy(target in rule_ids, ...)
```

- **Differs:** pass only if the designed `target_rule_id` appears in findings.

---

## What success means

1. Broken payload survived round-trip unchanged.  
2. After GET, the validator reports the expected rule for that case.
