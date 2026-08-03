# `test_retry`

**File:** `tests/test_catalog.py`  
**Helper:** `FlowHelper.check_retries`  
**Manifest filter:** `type == "retry"`  

| case_id | Flow |
|---------|------|
| `RTY-0001` | Attempt 1: valid body + `X-Force-Error: 500` → **500**, nothing stored. Attempt 2: same event → **200**, GET equals sent. |

Headers: `Idempotency-Key: k1`, `X-Retry-Count: 1` then `2`.

---

## High level

Simulate a server failure on the first send, then a retry with the same event. Prove the first attempt left nothing, and the retry is what we GET back.

---

## What success means

- First POST → `status=500`, GET for that `case_id` is empty.  
- Second POST → `status=200`, GET body equals the valid event; retry headers stored.
