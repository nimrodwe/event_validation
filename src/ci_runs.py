"""Load CI run list for the dashboard — public catalog only, no GitHub API/auth."""

import time

import requests

from src.config import (
    ALLURE_PAGES_URL,
    CI_RUNS_CATALOG_FALLBACK_URL,
    CI_RUNS_CATALOG_URL,
    GITHUB_ACTIONS_URL,
    OUT,
    allure_pages_run_url,
)


class CiRuns:
    """Dashboard CI panel data from public allure-pages/ci-runs.json.

    No GITHUB_TOKEN, no gh auth, no api.github.com (avoids anonymous 403 rate limits).
    Same catalog URL on every machine — Windows and Mac should show the same runs.
    """

    CACHE_TTL_SECONDS = 5
    CACHE_TTL_ERROR = 3
    DEFAULT_LIMIT = 30

    def __init__(self):
        self._cache = {"expires": 0.0, "payload": None}

    def _empty_payload(self, error=None):
        return {
            "runs": [],
            "error": error,
            "updated_at": "",
            "allure_pages_url": ALLURE_PAGES_URL,
            "actions_url": GITHUB_ACTIONS_URL,
            "catalog_url": CI_RUNS_CATALOG_URL,
        }

    def _normalize(self, run):
        run_id = run.get("id")
        # Always build raw.githack URLs — catalog may still store github.io / CDN links.
        return {
            "run_number": run.get("run_number"),
            "id": run_id,
            "status": run.get("status") or "completed",
            "conclusion": run.get("conclusion") or "",
            "event": run.get("event") or "",
            "head_branch": run.get("head_branch") or "",
            "head_sha": run.get("head_sha") or "",
            "created_at": run.get("created_at") or "",
            "updated_at": run.get("updated_at") or "",
            "html_url": run.get("html_url") or "",
            "display_title": run.get("display_title") or "",
            "allure_url": allure_pages_run_url(run_id),
            "allure_latest_url": "",
        }

    def clear(self):
        self._cache["expires"] = 0.0
        self._cache["payload"] = self._empty_payload()

    def _catalog_sort_key(self, data):
        """Prefer newest catalog (CDN edges can return stale copies)."""
        updated = str((data or {}).get("updated_at") or "")
        count = len((data or {}).get("runs") or [])
        return (updated, count)

    def _fetch_catalog(self, force=False):
        """GET catalog from both mirrors; keep the newest updated_at."""
        stamp = str(int(time.time() * 1000))
        urls = [CI_RUNS_CATALOG_URL, CI_RUNS_CATALOG_FALLBACK_URL]
        headers = {
            "User-Agent": "event-validation-dashboard",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        last_error = None
        best = None
        for base in urls:
            # Always bust query string — raw CDN may ignore Cache-Control.
            url = base + "?t=" + stamp
            try:
                response = requests.get(url, headers=headers, timeout=15)
            except requests.RequestException as exc:
                last_error = str(exc)
                continue
            if response.status_code == 404:
                last_error = "404"
                continue
            if response.status_code != 200:
                last_error = "HTTP " + str(response.status_code)
                continue
            try:
                data = response.json()
            except ValueError as exc:
                last_error = str(exc)
                continue
            if best is None or self._catalog_sort_key(data) > self._catalog_sort_key(best):
                best = data
        if best is not None:
            return best, None
        if last_error == "404":
            return None, (
                "CI catalog not published yet. Wait for the next workflow "
                "Publish Allure job, then refresh."
            )
        return None, (
            "Could not load public CI catalog ("
            + (last_error or "unknown")
            + "). Check network access to raw.githubusercontent.com."
        )

    def load(self, limit=None, force=False):
        if limit is None:
            limit = self.DEFAULT_LIMIT
        now = time.time()
        if (
            not force
            and self._cache["payload"] is not None
            and now < self._cache["expires"]
        ):
            return self._cache["payload"]

        previous = self._cache.get("payload")
        data, err = self._fetch_catalog(force=True)
        if data is None:
            if previous and previous.get("runs"):
                payload = dict(previous)
                payload["error"] = err + " (showing last fetch)"
            else:
                payload = self._empty_payload(err)
            self._cache["payload"] = payload
            self._cache["expires"] = now + self.CACHE_TTL_ERROR
            return payload

        raw_runs = data.get("runs") or []
        runs = [self._normalize(run) for run in raw_runs[:limit]]
        if runs:
            runs[0]["allure_latest_url"] = ALLURE_PAGES_URL

        payload = {
            "runs": runs,
            "error": None,
            "updated_at": data.get("updated_at") or "",
            "allure_pages_url": ALLURE_PAGES_URL,
            "actions_url": GITHUB_ACTIONS_URL,
            "catalog_url": CI_RUNS_CATALOG_URL,
        }
        self._cache["payload"] = payload
        self._cache["expires"] = now + self.CACHE_TTL_SECONDS
        return payload

    def allure_cache_dir(self, run_id):
        return OUT / "ci_allure" / str(run_id)

    def find_allure_index_dir(self, run_id):
        base = self.allure_cache_dir(run_id)
        if not base.exists():
            return None
        direct = base / "index.html"
        if direct.exists():
            return base
        matches = sorted(base.rglob("index.html"))
        if matches:
            return matches[0].parent
        return None

    def prepare_allure_report(self, run_id):
        url = allure_pages_run_url(run_id)
        if not url:
            return {"ok": False, "error": "Missing CI run id for Allure URL"}
        return {"ok": True, "url": url, "source": "pages-run"}


CI_RUNS = CiRuns()
