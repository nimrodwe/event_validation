# `test_replay`

**File:** `tests/test_catalog.py`  
**Helper:** `AssertHelper.check_replays`  
**Manifest filter:** `type == "replay"`  
**Pipeline cases:**

| case_id | Payload | `delivery_headers` |
|---------|---------|-------------------|
| `RPL-0001` | Same synthetic template payload (template UUID) | `X-Replay: false`, `X-Delivery: 1` |
| `RPL-0002` | Same payload | `X-Replay: true`, `X-Delivery: 2` |

---

## How this differs from the others

| Topic | This test | `test_retry` | Positives |
|--------|-----------|--------------|-----------|
| Pair of cases | Yes (exactly 2) | Yes | One (or more) |
| Headers on POST | Yes (from manifest) | Yes | Usually empty |
| Re-check stored headers after GET? | **No** (current code) | **Yes** | N/A |
| Validator / findings? | **No** | No | No |
| Main assert | Body round-trip for both deliveries | Body + header equality | Body only |

So: like retry (pair + headers on send), but **lighter** — it does not currently assert that replay headers were stored; it mainly proves both deliveries are accepted and payloads round-trip.

---

## High level

Load replay pair → require two cases → for each: POST (with replay headers) → GET → event body equals what was sent.

---

## Test body — line by line

```python
def test_replay(initialize, catalog_receiver):
```

- Same fixtures.

```python
    events, replays = initialize.catalog.cases("replay")
```

- Filter `"replay"`.

```python
    AssertHelper.check_replays(catalog_receiver, replays, events)
```

- No `validator`. No outer `truthy`.

---

## Inside `check_replays` — step by step

```python
self.equal(len(cases), 2, "Expected exactly two replay cases")
```

- Pair required.

```python
sent_by_id = self._sent_by_id(events)
for item in cases:
    case_id = item["case_id"]
    sent = sent_by_id.get(case_id)
    self.truthy(sent, ...)
    self._post_case(receiver, case_id, sent, item.get("delivery_headers"))
```

- POST includes replay `delivery_headers` from the manifest.

```python
    self.received_equals_sent(receiver, case_id, sent)
```

- Same body equality as positives.
- **Does not** currently assert stored header values (unlike `check_retries`).

---

## What success means

Both replay deliveries are accepted and each GET returns the same event body that was sent. (Header persistence is not asserted here today.)
