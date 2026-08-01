# `test_type_bad`

**File:** `tests/test_data_types.py`  
**Parametrize:** one pytest case per field in `TypeParams.NEGATIVE_FIELDS`  
**Data:** first row of `validation_dataset_intentionally_corrupted.json` + `EventsSchema.json`  
**Server:** not used

---

## How this differs from the others

| Topic | This test | `test_type_ok` |
|--------|-----------|----------------|
| Source row | Corrupted flat dataset (first row) | Good nested synthetic |
| Which fields | Only fields that **already** fail `fits_type` | All schema-mapped synthetic fields |
| Assert helper | `type_mismatch` (must **not** fit) | `fits_type` (must fit) |
| Mutates data? | No — corruption is already in the file | No |

---

## High level

Build the list of fields on the corrupted row that disagree with EventsSchema. For each such field, assert it still fails the type check (negative type test).

How the param list is built:

1. Load first corrupted row + EventsSchema  
2. `DatasetSteps.compare` → all overlapping fields  
3. Keep only those where `fits_type` is already false → `TypeParams.NEGATIVE_FIELDS`

---

## Test body — line by line

```python
@pytest.mark.parametrize("match", TypeParams.NEGATIVE_FIELDS, ids=ParamIds.field_id)
def test_type_bad(initialize, match):
```

- One run per known-bad field (e.g. `test_type_bad[datetime]`).

```python
    initialize.record_uuid(AssertHelper.event_uuid(initialize.validation_dataset))
```

- UUID from the flat row (top-level `UUID` on that dataset).

```python
    AssertHelper.has_key(match, "field", ...)
    AssertHelper.has_key(match, "expected_type", ...)
```

- Same param sanity checks as `test_type_ok`.

```python
    AssertHelper.type_mismatch(initialize.dataset_steps, match)
```

- **Differs from type_ok:** passes only if `fits_type(actual, expected_type)` is **false**.
- If the value unexpectedly fits the schema, the test fails.

---

## What success means

The intentionally bad fields on the corrupted row still look wrong vs EventsSchema. This does not send anything to the server.
