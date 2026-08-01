"""Load CI run list for the dashboard — public catalog only, no GitHub API/auth."""

import time

import requests

from src.config import (
    ALLURE_PAGES_URL,
    ALLURE_RUNS_CDN,
    CI_RUNS_CATALOG_URL,
    GITHUB_ACTIONS_URL,
    OUT,
    allure_pages_run_url,
)


class CiRuns:
    """Dashboard CI panel data from public allure-pages/ci-runs.json.

    No GITHUB_TOKEN, no gh auth, no api.github.com (avoids anonymous 403 rate limits).
    """

    CACHE_TTL_SECONDS = 8
    CACHE_TTL_ERROR = 5
    DEFAULT_LIMIT = 30

    def __init__(self):
        self._cache = {"expires": 0.0, "payload": None}

    def _empty_payload(self, error=None):
        return {
            "runs": [],
            "error": error,
            "allure_pages_url": ALLURE_PAGES_URL,
            "allure_runs_cdn": ALLURE_RUNS_CDN,
            "actions_url": GITHUB_ACTIONS_URL,
        }

    def _normalize(self, run):
        run_id = run.get("id")
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
            "allure_url": run.get("allure_url") or allure_pages_run_url(run_id),
            "allure_latest_url": "",
        }

    def clear(self):
        self._cache["expires"] = 0.0
        self._cache["payload"] = self._empty_payload()

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
        url = CI_RUNS_CATALOG_URL
        if force:
            url = CI_RUNS_CATALOG_URL + "?t=" + str(int(now))

        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": "event-validation-dashboard",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
                timeout=15,
            )
            if response.status_code == 404:
                payload = self._empty_payload(
                    "CI catalog not published yet. Wait for the next workflow "
                    "Publish Allure job, then refresh."
                )
                self._cache["payload"] = payload
                self._cache["expires"] = now + self.CACHE_TTL_ERROR
                return payload

            if response.status_code != 200:
                err = (
                    "Could not load public CI catalog (HTTP "
                    + str(response.status_code)
                    + "). Retry shortly."
                )
                if previous and previous.get("runs"):
                    payload = dict(previous)
                    payload["error"] = err + " (showing last fetch)"
                else:
                    payload = self._empty_payload(err)
                self._cache["payload"] = payload
                self._cache["expires"] = now + self.CACHE_TTL_ERROR
                return payload

            data = response.json()
            raw_runs = data.get("runs") or []
            runs = [self._normalize(run) for run in raw_runs[:limit]]
            if runs:
                runs[0]["allure_latest_url"] = ALLURE_PAGES_URL

            payload = {
                "runs": runs,
                "error": None,
                "allure_pages_url": ALLURE_PAGES_URL,
                "allure_runs_cdn": ALLURE_RUNS_CDN,
                "actions_url": GITHUB_ACTIONS_URL,
            }
            ttl = self.CACHE_TTL_SECONDS
        except (requests.RequestException, ValueError) as exc:
            err = "Could not load public CI catalog: " + str(exc)
            if previous and previous.get("runs"):
                payload = dict(previous)
                payload["error"] = err + " (showing last fetch)"
            else:
                payload = self._empty_payload(err)
            ttl = self.CACHE_TTL_ERROR

        self._cache["payload"] = payload
        self._cache["expires"] = now + ttl
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
