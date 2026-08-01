# Event Validation

Local pipeline tests: generate synthetic events, POST them to a localhost receiver, then check round-trip payloads, validation rules, and field types.

## What we test


| Suite      | File                       | Checks                                                                                 |
| ---------- | -------------------------- | -------------------------------------------------------------------------------------- |
| Catalog    | `tests/test_catalog.py`    | Positive, negative, boundary, retry, duplicate, and replay cases (POST → GET → assert) |
| Data types | `tests/test_data_types.py` | Schema types on good synthetic fields and on the intentionally corrupted dataset       |




## Setup

```bash
python -m pip install -r requirements.txt
```



## Dashboard

```bash
python run.py              # dashboard + receiver (http://127.0.0.1:8080)
```



## Run all tests

```bash
python -m pytest -v
```



## Run one file or one test

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



## Docker (Windows / Mac / Linux)

Needs Docker Desktop. This starts Docker if needed, builds, and runs the dashboard + receiver (`http://localhost:8080`):

```bash
python run.py docker
```

Source is mounted at `/app`, so local edits show up in the container. To run tests in Docker instead: `python run.py docker -- compose --profile test run --rm test`.

## CI

GitHub Actions (`.github/workflows/allure-github-pages.yml`) runs the full pytest suite on every push (any branch), on PRs, on a daily schedule, and via manual dispatch. Each run’s Allure report is pushed to the `allure-pages` branch and opened from a public CDN (`/runs/<run_id>/`) so **Open Allure report** works on every machine with no GitHub login — including failed runs and non-`main` branches. The job fails if pytest fails, but that run’s Allure is still published first.