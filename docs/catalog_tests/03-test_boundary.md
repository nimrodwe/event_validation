# `test_boundary`

**File:** `tests/test_catalog.py`  
**Helper:** `FlowHelper.check_boundary_case`  
**Manifest filter:** `type == "boundary"`  
**Parametrize:** `boundary_pytest_params()` → **4 pytest tests** (one per edge)

| Pytest name | case_id | Setup | Assert after GET | (N) |
|-------------|---------|--------|------------------|-----|
| `test_boundary[time=0]` | `BND-0001` | `time = 0` | still `0`, no `RANGE-time` | |
| `test_boundary[time=-1]` | `BND-TIME-NEG` | `time = -1` | still `-1` + `RANGE-time` | yes |
| `test_boundary[Appdome fusion app token (len=29)]` | `BND-TOKEN-SHORT` | token len 29 | len 29 + `FMT` | yes |
| `test_boundary[Appdome fusion app token (len=30)]` | `BND-TOKEN-EDGE` | token len 30 (min) | len 30 + **no** `FMT` | |

---

## High level

`@parametrize` runs the same test body once per edge. Negative edges carry `@pytest.mark.negative` so the dashboard shows the yellow `(N)` tag. Each run loads one boundary case, POST→GET, then case-specific asserts.

---

## Test body

```python
@pytest.mark.parametrize("boundary", boundary_pytest_params())
def test_boundary(initialize, catalog_receiver, boundary):
    events, item = FlowHelper.catalog_case(
        initialize.catalog, "boundary", boundary["case_id"]
    )
    FlowHelper.check_boundary_case(
        catalog_receiver,
        initialize.validator,
        item,
        events,
        changed_key=boundary["key"],
        changed_value=boundary["value"],
    )
```

---

## What success means

Each boundary edge is its own pass/fail in pytest and on the dashboard (not one combined test).
