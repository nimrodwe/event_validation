# `test_duplicates`

**File:** `tests/test_catalog.py`  
**Helper:** `AssertHelper.check_duplicates`  
**Manifest filter:** `type == "duplicate"`  
**Pipeline cases:**

| case_id | Setup |
|---------|--------|
| `DUP-0001` | Same near-duplicate payload (`UUID` = `DUP000…001`) |
| `DUP-0002` | Same payload again |

---

## How this differs from the others

| Topic | This test | Positives / Negatives |
|--------|-----------|------------------------|
| Count | Exactly **2** | Any non-empty (or fixed BND set) |
| When rules run | **After both** cases are posted | Negatives: per case after each GET |
| Rule checked | `DUP-NEAR` via `check_received_dupes` | Negatives: `check_nested` + `target_rule_id` |
| Needs both rows together | **Yes** — duplicate detection is across received items | No |
| Outer `truthy` in test? | **No** | Yes for pos/neg |

---

## High level

Load the duplicate pair → require two cases → POST+GET each (body equal) → collect stored rows → run duplicate detector → expect `DUP-NEAR`.

---

## Test body — line by line

```python
def test_duplicates(initialize, catalog_receiver):
```

- Same fixtures.

```python
    events, duplicates = initialize.catalog.cases("duplicate")
```

- Filter `"duplicate"`.

```python
    AssertHelper.check_duplicates(
        catalog_receiver, initialize.validator, duplicates, events
    )
```

- Passes `validator` (for dupe check). No outer `truthy`.

---

## Inside `check_duplicates` — step by step

```python
self.equal(len(cases), 2, "Expected exactly two duplicate cases")
```

- Pair required (like retry/replay).

```python
sent_by_id = self._sent_by_id(events)
received_items = []
for item in cases:
    case_id = item["case_id"]
    sent = sent_by_id.get(case_id)
    self.truthy(sent, ...)
    self._post_case(...)
    self.received_equals_sent(...)
    received_items.append(self._get_rows(receiver, case_id)[-1])
```

- Round-trip each case (same as positives).
- **Differs:** keep the full stored rows (not just the event) for the dupe check.

```python
findings = [f.to_dict() for f in validator.check_received_dupes(received_items)]
```

- **Differs:** validate **across** the two received deliveries, not nested field rules on one event.

```python
self.truthy(findings, "Duplicate cases should produce a duplicate finding")
self.equal(findings[0]["rule_id"], "DUP-NEAR", "Expected DUP-NEAR")
```

- Must produce at least one finding, and the first rule id must be `DUP-NEAR`.

---

## What success means

Two near-duplicate catalog deliveries round-trip, and together they trigger `DUP-NEAR`.
