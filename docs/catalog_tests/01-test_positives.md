# `test_positives`

**File:** `tests/test_catalog.py`  
**Helper:** `FlowHelper.check_positives` in `helpers/flows.py`  
**Manifest filter:** `type == "positive"`  
**Pipeline cases:** `POS-0001` (unchanged copy of the synthetic template)

---

## How this differs from the others

| Topic | This test | Others |
|--------|-----------|--------|
| Goal | Round-trip + prove nested rules stay clean | Also check bad data, headers, or pair behavior |
| Uses `validator`? | **Yes** (`check_nested` → expect `[]`) | Negatives use learned key rules; boundary uses nested + edge asserts |
| Extra after GET | Findings must be empty | See each other doc |

---

## High level

Generate the catalog → keep only positive cases → for each: POST → GET → body equals sent → `check_nested` findings empty.

---

## Test body

```python
def test_positives(initialize, catalog_receiver):
    events, positives = initialize.catalog.cases("positive")
    AssertHelper.truthy(positives, "No positive cases in manifest")
    FlowHelper.check_positives(
        catalog_receiver, initialize.validator, positives, events
    )
```

---

## Inside `check_positives`

1. `_post_case` — Base64 POST, expect HTTP 200  
2. `received_equals_sent` — GET body == sent  
3. Log event after POST / after GET  
4. `validator.check_nested(received)` → assert findings `== []`

---

## What success means

The server stored exactly what we sent, and nested validation rules report no problems.
