# `test_type_ok`

**File:** `tests/test_data_types.py`  
**Parametrize:** one pytest case per field in `TypeParams.POSITIVE_FIELD_NAMES`  
**Data:** `synthetic_event_template.json` + `EventsSchema.json`  
**Server:** yes — POST→GET via `catalog_receiver`

---

## How this differs from the others

| Topic | This test | `test_type_bad` | `test_corrupted_fields_fail` |
|--------|-----------|-----------------|------------------------------|
| Data source | Good synthetic event | Corrupted dataset row as-is | Synthetic with forced bad values |
| Expectation | Value **fits** schema type | Value **fails** schema type (PASS) | Value fails → test **FAILS** |
| Parametrized? | Yes (many fields) | Yes (`e1`…`e10`) | Yes (`one-field`, `three-fields`) |

---

## High level

POST the synthetic event, GET it back and assert equality, then for each schema-mapped field assert the value fits the expected type.

How the param list is built (at import time):

1. Load synthetic event + EventsSchema  
2. `SyntheticSteps.compare` → list of `{field, actual, expected_type}`  
3. `TypeParams.POSITIVE_FIELD_NAMES` = those field names  

---

## Test body

```python
@pytest.mark.parametrize("field", TypeParams.POSITIVE_FIELD_NAMES)
def test_type_ok(initialize, catalog_receiver, field):
    event = initialize.synthetic_dataset
    match = TypeParams.positive_match(field)
    AssertHelper.has_key(match, "field", "Match is missing field name")
    AssertHelper.has_key(match, "expected_type", "Match is missing expected_type")
    AssertHelper.post_get_equals(
        catalog_receiver, "TYPE-OK-" + field, event, record_uuid=True
    )
    AssertHelper.fits_type(initialize.synthetic_steps, match)
```

---

## What success means

Every schema-mapped field on the good synthetic event has a value compatible with its EventsSchema type, and the receiver round-trip is clean.
