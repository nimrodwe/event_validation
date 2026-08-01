# `test_type_ok`

**File:** `tests/test_data_types.py`  
**Parametrize:** one pytest case per field in `TypeParams.POSITIVE_FIELDS`  
**Data:** `synthetic_event_template.json` + `EventsSchema.json`  
**Server:** not used

---

## How this differs from the others

| Topic | This test | `test_type_bad` |
|--------|-----------|----------------|
| Data source | Good synthetic event | Corrupted dataset row |
| Expectation | Value **fits** schema type | Value **fails** schema type |
| Parametrized? | Yes (many fields) | Yes (mismatch fields only) |
| Hits localhost? | No | No |

---

## High level

For each property on the synthetic event that also exists in `EventsSchema`, assert the actual value matches the expected ClickHouse-style type (via `fits_type`). Values are **not** changed by the test.

How the param list is built (at import time):

1. Load synthetic event + EventsSchema  
2. `SyntheticSteps.compare` → list of `{field, actual, expected_type}`  
3. That list is `TypeParams.POSITIVE_FIELDS`

---

## Test body — line by line

```python
@pytest.mark.parametrize("match", TypeParams.POSITIVE_FIELDS, ids=ParamIds.field_id)
def test_type_ok(initialize, match):
```

- Runs once per field match.
- Test name ends with the field id (e.g. `test_type_ok[uuid]`).
- `match` looks like: `{"field": "uuid", "actual": "...", "expected_type": "String"}`.

```python
    initialize.record_uuid(AssertHelper.event_uuid(initialize.synthetic_dataset))
```

- Records / logs the synthetic event UUID for the dashboard step list.
- Not part of the type assert itself.

```python
    AssertHelper.has_key(match, "field", ...)
    AssertHelper.has_key(match, "expected_type", ...)
```

- Sanity: the param dict must include `field` and `expected_type`.

```python
    AssertHelper.fits_type(initialize.synthetic_steps, match)
```

- Calls `synthetic_steps.fits_type(actual, expected_type)`.
- Pass if the value matches the schema type; fail with a clear message if not.

---

## What success means

Every schema-mapped field on the good synthetic event has a value compatible with its EventsSchema type.
