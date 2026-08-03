# `test_type_bad`

**File:** `tests/test_data_types.py`  
**Helper:** `FlowHelper.check_type_bad_case`  
**Data:** 10 validation-dataset events + `EventsSchema.json`  
**Parametrize:** one test per event — `e1` … `e10`

---

## High level

**10 events.** Each event is one pytest that lists **all** bad typed fields once (no per-field folders).

**No transforms** — the row from the validation dataset is POSTed exactly as loaded.

1. Scan validation dataset → events that fail `fits_type`  
2. POST → GET that raw row  
3. Log **event after POST**, then **event after GET**  
4. Validate the **GET body** vs EventsSchema — list every failing field + `total=`

## Dashboard

```
test_type_bad
  event-1
    bad types
  event-2
    …
```

---

## Test body

```python
@pytest.mark.parametrize("case", type_bad_pytest_params())
def test_type_bad(initialize, type_bad_receiver, case):
    AssertHelper.check_type_bad_case(
        type_bad_receiver, initialize.dataset_steps, case
    )
```
