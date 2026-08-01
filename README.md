# Event Validation

Local pipeline tests: generate synthetic events, POST them to a localhost receiver, then check round-trip payloads, validation rules, and field types.

## What we test

| Suite | File | Checks |
|-------|------|--------|
| Catalog | `tests/test_catalog.py` | Positive, negative, boundary, retry, duplicate, and replay cases (POST → GET → assert) |
| Data types | `tests/test_data_types.py` | Schema types on good synthetic fields and on the intentionally corrupted dataset |

## Setup

```bash
python -m pip install -r docs/requirements.txt
```

## Dashboard

```bash
python run.py              # dashboard + receiver (http://127.0.0.1:8080)
python run.py dashboard    # dashboard only
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

## Docker (Mac / Linux)

Needs Docker Desktop. From the project root:

```bash
# Dashboard + receiver (http://localhost:8080)
docker compose up --build

# All tests
docker compose --profile test run --rm test

# One test
docker compose --profile test run --rm test python -m pytest tests/test_catalog.py::test_positives -v

# Shell in the container
docker compose run --rm stack bash
```

Source is mounted at `/app`, so edits on the Mac show up in the container.

## CI

GitHub Actions (`.github/workflows/allure-github-pages.yml`) runs the full pytest suite on push/PR to `main`, on a daily schedule, and via manual dispatch. It builds an Allure report; on `main` (and the schedule) that report is published to GitHub Pages. The job fails if pytest fails, but the report is still generated first.
