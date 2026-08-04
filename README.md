# Event Validation

Local pipeline tests: generate synthetic events, POST them to a localhost receiver, then check round-trip payloads, validation rules, and field types.

## What we test

| Suite | File | Checks |
| ----- | ---- | ------ |
| Catalog | `tests/test_catalog.py` | Positives, negatives (4 rules × events), boundary, retry, duplicate, replay |
| Data types | `tests/test_data_types.py` | `type_ok`, `type_bad`, plus intentional `test_corrupted_fields_fail` (expected red) |

Docs: [`docs/interview.html`](docs/interview.html) · [`docs/catalog_tests/`](docs/catalog_tests/README.md) · [`docs/data_types_tests/`](docs/data_types_tests/README.md)

## Quick start (Mac — Docker)

1. Install **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** and start it (whale icon running).
2. From the project root, create a venv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# Windows PowerShell: .\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
```

3. Start the stack with Docker:

```bash
python run.py docker
```

That starts Docker if needed, builds, and runs the dashboard + receiver at **http://localhost:8080**.

Source is mounted at `/app`, so local edits show up in the container.

### Run tests in Docker

```bash
# Full pytest suite inside the container
python run.py docker -- compose --profile test run --rm test
```

Open the dashboard in the browser while / after tests: **http://localhost:8080**  
(local pytest runs + shared **Pytest CI runs** panel with public Allure links — no GitHub token).

Stop the stack:

```bash
python run.py docker -- compose down
```

---

## Local runs (optional — without Docker)

With the same venv activated (`source .venv/bin/activate`):

### Dashboard (local)

```bash
python run.py              # http://127.0.0.1:8080
```

### Run all tests (local)

```bash
python -m pytest -v
```

### Run one file or one test (local)

```bash
# One file
python -m pytest tests/test_catalog.py -v
python -m pytest tests/test_data_types.py -v

# One test by name
python -m pytest tests/test_catalog.py::test_positives -v
python -m pytest tests/test_data_types.py::test_type_ok -v

# One parametrized case
python -m pytest "tests/test_data_types.py::test_type_ok[packagename]" -v

# Match by keyword
python -m pytest -k positives -v
```

## CI

GitHub Actions (`.github/workflows/allure-github-pages.yml`) runs the full pytest suite on every push (any branch), on PRs, on a daily schedule, and via manual dispatch. Each run’s Allure report and a public `ci-runs.json` catalog are pushed to the `allure-pages` branch. The local dashboard reads that catalog (not the GitHub API), so **Pytest CI runs** and **Open Allure report** work on every machine with no GitHub login or token. The job fails if pytest fails, but that run’s Allure is still published first.

## Tests — what each one does

Shared pattern for most cases: **POST** event → **GET** it back → assert on the GET body (and HTTP status where relevant).

### Catalog (`tests/test_catalog.py`)

| Test | What it does | Rules / setup | What it asserts |
| ---- | ------------ | ------------- | --------------- |
| `test_positives` | POST unchanged synthetic template (`POS-0001`) | Nested validator rules (`check_nested`) | GET body equals sent; **no** nested findings |
| `test_negatives` | POST validation-dataset rows; compare to synthetic keys | Four named rules (below), up to 10 events each `(N)` | After GET: assert the named rule produces findings, then list them |
| `test_boundary` | POST synthetic with one edge change | `time=0`, `time=-1`, token len 29, token len 30 | Changed value still present after GET; edge rule fires or not as expected |
| `test_retry` | First POST forced to fail, then retry | Attempt 1 → 500; attempt 2 → 200 | Nothing stored after 500; after retry GET equals sent |
| `test_duplicates` | Same body twice | Receiver fingerprint / duplicate block | First POST 200 + GET ok; second POST **409**, not stored |
| `test_replay` | Several POSTs under one `case_id` | Replay deliveries (2 then 1) | GET count equals number of POSTs; each body equals sent |

#### Negative rules (`test_negatives`)

Learned from `synthetic_event_template.json` vs flat validation rows:

| Rule (dashboard folder) | Pytest id example | Meaning | Assert / log |
| ----------------------- | ----------------- | ------- | ------------ |
| new keys | `new_keys-e1` | Validation has a key synthetic does not | List each unknown key + value found |
| missing keys | `missing_keys-e1` | Synthetic key missing on validation | List missing keys (presence only — no values) |
| empty string got none or null | `empty_got_null-e1` | Mapped key present as `null`/`None` | List key + null + what synthetic had (always 10 events: hits first, then pad) |
| string value got empty string | `value_got_empty-e1` | Template had a non-empty value; validation is `""` | List key + `""` + synthetic value |

Log order for negatives: **event after POST** → **event after GET** → **findings**.

#### Boundary edges (`test_boundary`)

| Pytest id | Change | Assert |
| --------- | ------ | ------ |
| `time=0` | `time = 0` | Still `0` after GET; no `RANGE-time` |
| `time=-1` *(N)* | `time = -1` | Still `-1`; `RANGE-time` fires |
| `Appdome fusion app token (len=29)` *(N)* | token length 29 | Length 29; `FMT` fires |
| `Appdome fusion app token (len=30)` | token length 30 (min) | Length 30; no `FMT` |

### Data types (`tests/test_data_types.py`)

| Test | What it does | Rules | What it asserts |
| ---- | ------------ | ----- | --------------- |
| `test_type_ok` | One pytest per EventsSchema-mapped field on the **synthetic** event | `EventsSchema.json` type for that field | POST→GET equals sent; value **fits** schema type |
| `test_type_bad` | One pytest per event (`e1`…`e10`) from the **corrupted** validation dataset | Same EventsSchema; fields that already fail `fits_type` | POST→GET; list all bad types on GET body (`got` vs `expected`); wrong type → **PASS** (negative test) |
| `test_corrupted_fields_fail` | Corrupt synthetic fields on purpose (`one-field`, `three-fields`) | Same EventsSchema | Detect bad types after GET, then `fits_type` → **FAIL** (failure-path demo) |

Typical `type_bad` fields: `datetime` / `mp_processing_time_ms` (string vs `DateTime64`), `tda` (JSON string vs `Map(String, String)`).

Green suite without the intentional failures:

```bash
python -m pytest -k "not corrupted" -v
```
