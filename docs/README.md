# Event Validation

Simple OOP Python project.

```bash
python -m pip install -r docs/requirements.txt
python run.py all
python run.py dashboard
python -m pytest -v
```

## Allure (local)

```bash
python -m pip install -r docs/requirements.txt
npm install -g allure-commandline   # once (or: scoop install allure)

python -m pytest -v                 # writes out/allure-results
allure serve out/allure-results     # opens the HTML report

# or one command:
python run.py allure
```

## Allure on GitHub Pages

Workflow: `.github/workflows/allure-github-pages.yml`

1. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. **Push to `main`** → runs all tests and publishes the Allure report
3. **Daily at 22:00** (Israel / UTC+3) → scheduled run + Pages publish
4. **Pull requests** → run manually: Actions → *Allure → GitHub Pages* → Run workflow (pick the PR branch)
5. Report URL: `https://<user>.github.io/<repo>/`

## Layout

```
run.py          ← CLI entry (only app file at root)
src/            ← app code
helpers/        ← steps + test helpers
services/       ← shared services (HTTP client, …)
tests/          ← pytest
data/           ← input JSON
docs/           ← README + requirements
out/            ← generated outputs (gitignored)
```

## Classes

| Class | File | What it does |
|-------|------|--------------|
| `Schema` | `src/config.py` | Reads the template |
| `Finding` | `src/validate.py` | One bug |
| `Validator` | `src/validate.py` | Finds bugs |
| `Generator` | `helpers/generator.py` | Makes catalog test cases |
| `Sender` | `src/pipeline.py` | Sends events to Flask |
| `Receiver` | `src/receiver.py` | Saves Base64 bodies |
| `Report` | `src/report.py` | Writes report + dashboard |
| `App` | `run.py` | Runs the full flow |

## Flow

1. `Generator` makes events from the template  
2. `Sender` POSTs them to `Receiver`  
3. `Validator` checks the big dataset + received events  
4. `Report` writes files and can open the dashboard  

No nested classes. Plain methods and loops.

## Isolating synthetic events (production-like)

In this project, generated cases are sent only to a localhost receiver — never to a real ingest URL.

In a production-like setup, keep synthetics isolated the same way:

- Point the generator/sender only at a dedicated non-prod endpoint (separate host, topic, or queue).
- Tag synthetics clearly (fixed UUID prefix/range, `X-Case-Id`, or a synthetic env flag) so analytics and alerts can filter them out.
- Prefer a separate tenant, API key, or pipeline stage so synthetic traffic cannot mix with customer data.
- Do not run `run.py all` / catalog send against production credentials or production receivers.

## Assumptions

- Nested event shape and field expectations come from `data/synthetic_event_template.json`.
- Flat corrupted rows in `data/validation_dataset_intentionally_corrupted.json` are validated with the flat-field rules in `src/config.py` / `src/validate.py`.
- Catalog case ids (`POS-*`, `NEG-*`, etc.) are test labels; event uniqueness uses `properties.UUID`.
- Appdome fusion app token minimum length (30) is a boundary rule (`check_token_length`), not part of positive `check_nested`.
- Invalid records stay visible: the receiver accepts them (HTTP 202) and findings report problems without rewriting payloads.

## Limitations

- No authoritative vendor schema was provided; rules are inferred from the template plus flat-dataset extensions.
- Duplicate detection ignores a small set of volatile fields (see `DUPE_SKIP` in config).
- Catalog size is small and deterministic for the take-home, not a full fuzz suite.
- HTML/Allure reports are for local or CI review; they are not a production monitoring product.
