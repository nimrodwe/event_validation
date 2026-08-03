# Data-type test docs

One page per test in `tests/test_data_types.py`.

These tests are **not** the catalog (`events.json` / `manifest.json`). They use:

| File | Role |
|------|------|
| `data/synthetic_event_template.json` | Good nested event (positive types) |
| `data/validation_dataset_intentionally_corrupted.json` | 10 events with bad types (`e1` … `e10`) |
| `data/EventsSchema.json` | Expected field types (not a live DB) |

| Doc | Test | Touches server? | What it proves |
|-----|------|-----------------|----------------|
| [01-test_type_ok.md](01-test_type_ok.md) | `test_type_ok` | Yes | POST→GET synthetic; field **fits** schema type |
| [02-test_type_bad.md](02-test_type_bad.md) | `test_type_bad` | Yes | 10 corrupted events; wrong type → **PASS** (negative) |
| [03-test_corrupted_fields_fail.md](03-test_corrupted_fields_fail.md) | `test_corrupted_fields_fail` | Yes | Intentional corruption → `fits_type` **FAIL** (demo) |

Catalog docs: [`../catalog_tests/`](../catalog_tests/README.md)  
Interview walkthrough: [`../interview.html`](../interview.html)

## Shared idea

```mermaid
flowchart LR
  schema[EventsSchema.json]
  good[synthetic_event_template.json]
  bad[validation_dataset rows]
  typeOk[test_type_ok]
  typeBad[test_type_bad]
  corrupt[test_corrupted_fields_fail]

  schema --> typeOk
  good --> typeOk
  schema --> typeBad
  bad --> typeBad
  schema --> corrupt
  good --> corrupt
```

**Type tests** POST→GET through the local receiver, then check field types against the schema.
