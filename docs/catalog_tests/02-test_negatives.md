# `test_negatives`

**File:** `tests/test_catalog.py`  
**Helper:** `FlowHelper.check_dataset_negative_rule`  
**Learn from:** synthetic template  

Each rule has **its own** event-1 … event-10 list.

- `new_keys` / `missing_keys` / `value_got_empty`: first 10 rows that hit the rule.  
- `empty_got_null`: always 10 events — hit rows first, then pad with more validation rows; log findings or `nothing to validate`.

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
| empty string got none or null | `empty_got_null-e1` | Present keys with `null`/`None` (10 events always) |
| string value got empty string | `value_got_empty-e1` | Template had a value, validation is `""` |

## Logs

- Always: event after POST, event after GET, then findings.  
- Hits → list **every** matching key for that rule/event.  
- No hits → `nothing to validate` (`empty_got_null` still keeps the event case).  

## Test body

```python
@pytest.mark.parametrize("negative", negative_pytest_params())
def test_negatives(initialize, negatives_receiver, negative):
    AssertHelper.check_dataset_negative_rule(
        negatives_receiver, initialize.validator, negative
    )
```
