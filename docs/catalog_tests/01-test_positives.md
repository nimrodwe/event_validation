# `test_positives`

**File:** `tests/test_catalog.py`  
**Helper:** `AssertHelper.check_positives` in `helpers/asserts.py`  
**Manifest filter:** `type == "positive"`  
**Pipeline cases:** `POS-0001` (unchanged copy of the synthetic template)

---

## How this differs from the others

| Topic | This test | Others |
|--------|-----------|--------|
| Goal | Only prove POST→GET leaves keys/values unchanged | Also check rules, headers, or pair behavior |
| Uses `validator`? | **No** | Negatives / boundary / duplicates yes |
| Explicit `truthy(cases)` in the test? | **Yes** | Negatives yes; boundary does it inside helper; retry/dup/replay use `equal(len, 2)` instead |
| Extra asserts after GET | **None** | See each other doc |

---

## High level

Generate the catalog → keep only positive cases → ensure we got some → for each: POST to localhost → GET back → assert received event equals what we sent.

---

## Test body — line by line

```python
def test_positives(initialize, catalog_receiver):
```

- Pytest injects fixtures.
- `initialize`: catalog, logger, etc.
- `catalog_receiver`: clean receiver for this test only.

```python
    events, positives = initialize.catalog.cases("positive")
```

- Regenerates the full catalog in a temp folder.
- `events`: all payloads (`case_id` + `event`).
- `positives`: only manifest rows with `"type": "positive"`.
- Temp folder is deleted; lists stay in memory.

```python
    AssertHelper.truthy(positives, "No positive cases in manifest")
```

- Fails if the positive list is empty (filter/generator problem).
- Does **not** mean “manifest has no validation errors.”

```python
    AssertHelper.check_positives(catalog_receiver, positives, events)
```

- Runs the real checks (see below).

---

## Inside `check_positives` — step by step

```python
sent_by_id = self._sent_by_id(events)
```

- Builds `{case_id: event}` for fast lookup.

```python
for item in cases:   # each positive manifest row
```

```python
    case_id = item["case_id"]
```

- e.g. `"POS-0001"`.

```python
    sent = sent_by_id.get(case_id)
```

- Payload we intend to POST.

```python
    self.truthy(sent, "Missing event for " + case_id)
```

- Fail if manifest points at a `case_id` with no matching event.

```python
    self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
```

- Base64-POST to receiver with `X-Case-Id` (+ empty headers for POS).
- Assert HTTP 202.

```python
    self.received_equals_sent(receiver, case_id, sent)
```

- GET `?case_id=...`
- Assert stored `event == sent` (deep equality of all keys/values).

---

## What success means

The server stored exactly what we sent for every positive case. Nothing more is claimed.
