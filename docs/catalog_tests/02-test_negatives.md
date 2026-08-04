# `test_negatives`

**File:** `tests/test_catalog.py`  
**Helper:** `FlowHelper.check_dataset_negative_rule`  
**Learn from:** synthetic template vs flat validation rows  

Each rule has **its own** event-1 … event-10 list (first rows that hit the rule).

After POST→GET equals sent, the test **asserts** that the named rule produces at least one finding (opposite of positives, which require empty findings), then logs every matching key.

## Dashboard

```
test_negatives
  new keys
    event-1 … event-10
  missing keys
    event-1 … event-10
  empty string got none or null
    event-1 … event-10
  string value got empty string
    event-1 … event-10
```

| Rule folder | Pytest id | What each event lists |
|-------------|-----------|------------------------|
| new keys | `new_keys-e1` | Keys on validation not on synthetic (+ value found) |
| missing keys | `missing_keys-e1` | Synthetic keys missing on validation (presence only) |
| empty string got none or null | `empty_got_null-e1` | Present keys with `null`/`None` |
| string value got empty string | `value_got_empty-e1` | Template had a value, validation is `""` |

## Logs

- Always: event after POST, event after GET, then findings.  
- Assert: at least one hit for that rule/event (else fail).  
- Then list **every** matching key for that rule/event.  

## Test body

```python
@pytest.mark.parametrize("negative", negative_pytest_params())
def test_negatives(initialize, negatives_receiver, negative):
    FlowHelper.check_dataset_negative_rule(negatives_receiver, negative)
```
