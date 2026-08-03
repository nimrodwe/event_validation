# `test_corrupted_fields_fail`

**File:** `tests/test_data_types.py`  
**Helper:** `AssertHelper.check_corrupted_fields` → `FlowHelper.check_corrupted_fields`  
**Data:** synthetic template with intentional bad property values  
**Parametrize:** `one-field`, `three-fields`

---

## Purpose

**Intentional failure demo.** Corrupt one or more synthetic fields, POST→GET, detect the bad types, then call `fits_type` so the test **fails**. Proves the assert / dashboard / Allure failure path works.

These two cases make a full `pytest` run report **2 failed** unless you skip them (`-k "not corrupted"`).

---

## Corruptions

| Pytest id | Bad values |
|-----------|------------|
| `one-field` | `UUID = 12345` (int) |
| `three-fields` | `UUID = 12345`, token `= 999`, `devicePlatform = ["Android"]` |

---

## Test body

```python
@pytest.mark.negative
@pytest.mark.parametrize("corruptions", corrupt_field_pytest_params())
def test_corrupted_fields_fail(initialize, catalog_receiver, corruptions):
    AssertHelper.check_corrupted_fields(
        catalog_receiver,
        initialize.synthetic_steps,
        initialize.expected_types,
        initialize.synthetic_dataset,
        corruptions,
    )
```

---

## What “success” means here

There is no green outcome for these cases by design: after GET, `fits_type` on a corrupted field must raise so you see a clear failure in the dashboard and Allure.
