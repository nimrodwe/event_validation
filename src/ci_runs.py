"""Fetch GitHub Actions workflow runs for the dashboard CI panel."""

import time

import requests

from src.config import (
    ALLURE_PAGES_URL,
    GITHUB_ACTIONS_URL,
    GITHUB_REPO,
    GITHUB_WORKFLOW_FILE,
    OUT,
    allure_pages_run_url,
)


class CiRuns:
    """Loads and caches GitHub Actions runs for the dashboard CI panel.

    Uses anonymous public GitHub API only — no GITHUB_TOKEN / gh auth.
    Allure links are public GitHub Pages URLs (/runs/<run_id>/).
    """

    CACHE_TTL_SECONDS = 30
    CACHE_TTL_IN_PROGRESS = 5
    CACHE_TTL_ERROR = 10

    def __init__(self):
        self._cache = {"expires": 0.0, "payload": None}

    def _headers(self):
        # Never attach Authorization. A bad/expired local gh token would break
        # public API access that otherwise works without login.
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "event-validation-dashboard",
        }

    def _normalize(self, run, *, is_latest_success):
        sha = run.get("head_sha") or ""
        run_id = run.get("id")
        html_url = run.get("html_url") or ""
        if not html_url and run_id:
            html_url = (
                "https://github.com/"
                + GITHUB_REPO
                + "/actions/runs/"
                + str(run_id)
            )
        return {
            "run_number": run.get("run_number"),
            "id": run_id,
            "status": run.get("status") or "",
            "conclusion": run.get("conclusion") or "",
            "event": run.get("event") or "",
            "head_branch": run.get("head_branch") or "",
            "head_sha": sha[:7] if sha else "",
            "created_at": run.get("created_at") or "",
            "updated_at": run.get("updated_at") or "",
            "html_url": html_url,
            "display_title": run.get("display_title") or run.get("name") or "",
            # Public Pages Allure for this exact run (no login).
            "allure_url": allure_pages_run_url(run_id),
            "allure_latest_url": ALLURE_PAGES_URL if is_latest_success else "",
        }

    def _error_message(self, status_code, body_text):
        if status_code == 403:
            return "GitHub API rate limit (public). Wait a minute and refresh the page."
        if status_code == 401:
            return "GitHub API rejected the request. Retry shortly."
        detail = ""
        if body_text:
            detail = " — " + body_text.strip().replace("\n", " ")[:160]
        return "GitHub API HTTP " + str(status_code) + detail

    def clear(self):
        """Drop the in-memory CI cache (dashboard Clear button)."""
        self._cache["expires"] = 0.0
        self._cache["payload"] = {
            "runs": [],
            "error": None,
            "allure_pages_url": ALLURE_PAGES_URL,
            "actions_url": GITHUB_ACTIONS_URL,
        }

    def load(self, limit=10, force=False):
        """
        Return {"runs": [...], "error": null|str, "allure_pages_url": str, "actions_url": str}.
        Cached for ~30s to avoid burning GitHub API rate limits.
        """
        now = time.time()
        if (
            not force
            and self._cache["payload"] is not None
            and now < self._cache["expires"]
        ):
            return self._cache["payload"]

        url = (
            "https://api.github.com/repos/"
            + GITHUB_REPO
            + "/actions/workflows/"
            + GITHUB_WORKFLOW_FILE
            + "/runs"
        )
        previous = self._cache.get("payload")
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                params={"per_page": limit},
                timeout=15,
            )
            if response.status_code != 200:
                err = self._error_message(response.status_code, response.text)
                if previous and previous.get("runs"):
                    payload = {
                        "runs": previous["runs"],
                        "error": err + " (showing last successful fetch)",
                        "allure_pages_url": ALLURE_PAGES_URL,
                        "actions_url": GITHUB_ACTIONS_URL,
                    }
                else:
                    payload = {
                        "runs": [],
                        "error": err,
                        "allure_pages_url": ALLURE_PAGES_URL,
                        "actions_url": GITHUB_ACTIONS_URL,
                    }
                self._cache["payload"] = payload
                self._cache["expires"] = now + self.CACHE_TTL_ERROR
                return payload

            raw_runs = response.json().get("workflow_runs") or []
            latest_success_id = None
            for run in raw_runs:
                if run.get("conclusion") == "success":
                    latest_success_id = run.get("id")
                    break

            runs = []
            for run in raw_runs:
                runs.append(
                    self._normalize(
                        run,
                        is_latest_success=run.get("id") == latest_success_id,
                    )
                )

            payload = {
                "runs": runs,
                "error": None,
                "allure_pages_url": ALLURE_PAGES_URL,
                "actions_url": GITHUB_ACTIONS_URL,
            }
            ttl = self.CACHE_TTL_SECONDS
            for run in runs:
                if (run.get("status") or "") != "completed":
                    ttl = self.CACHE_TTL_IN_PROGRESS
                    break
        except requests.RequestException as exc:
            err = "Could not reach GitHub API: " + str(exc)
            if previous and previous.get("runs"):
                payload = {
                    "runs": previous["runs"],
                    "error": err + " (showing last successful fetch)",
                    "allure_pages_url": ALLURE_PAGES_URL,
                    "actions_url": GITHUB_ACTIONS_URL,
                }
            else:
                payload = {
                    "runs": [],
                    "error": err,
                    "allure_pages_url": ALLURE_PAGES_URL,
                    "actions_url": GITHUB_ACTIONS_URL,
                }
            ttl = self.CACHE_TTL_ERROR

        self._cache["payload"] = payload
        self._cache["expires"] = now + ttl
        return payload

    def allure_cache_dir(self, run_id):
        return OUT / "ci_allure" / str(run_id)

    def find_allure_index_dir(self, run_id):
        """Directory that contains index.html for a cached CI Allure report."""
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
        """Public Pages URL for this CI run's Allure report (no GitHub token)."""
        url = allure_pages_run_url(run_id)
        if not url:
            return {
                "ok": False,
                "error": "Missing CI run id for Allure Pages URL",
            }
        return {
            "ok": True,
            "url": url,
            "source": "pages-run",
        }


CI_RUNS = CiRuns()
