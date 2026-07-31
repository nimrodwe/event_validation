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
| `Generator` | `src/pipeline.py` | Makes test events |
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
