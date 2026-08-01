"""Fetch GitHub Actions workflow runs for the dashboard CI panel."""

import io
import os
import shutil
import subprocess
import time
import zipfile

import requests

from src.config import (
    ALLURE_PAGES_URL,
    GITHUB_ACTIONS_URL,
    GITHUB_REPO,
    GITHUB_WORKFLOW_FILE,
    OUT,
)


class CiRuns:
    """Loads and caches GitHub Actions runs for the dashboard CI panel."""

    CACHE_TTL_SECONDS = 30
    CACHE_TTL_IN_PROGRESS = 5
    CACHE_TTL_ERROR = 10

    def __init__(self):
        self._cache = {"expires": 0.0, "payload": None}

    def _gh_commands(self):
        commands = ["gh"]
        windir = os.environ.get("ProgramFiles", r"C:\Program Files")
        commands.append(os.path.join(windir, "GitHub CLI", "gh.exe"))
        return commands

    def _token(self):
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            return token.strip()
        for gh_cmd in self._gh_commands():
            try:
                out = subprocess.check_output(
                    [gh_cmd, "auth", "token"],
                    text=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL,
                )
                token = (out or "").strip()
                if token:
                    return token
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _headers(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "event-validation-dashboard",
        }
        token = self._token()
        if token:
            headers["Authorization"] = "Bearer " + token
        return headers

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
            # Per-run Actions URL (unique for every CI run).
            "html_url": html_url,
            "display_title": run.get("display_title") or run.get("name") or "",
            # Shared Pages site — only for the latest successful deploy.
            "allure_url": ALLURE_PAGES_URL if is_latest_success else "",
        }

    def _error_message(self, status_code, body_text):
        if status_code == 403:
            return (
                "GitHub API HTTP 403 (rate limit or auth). "
                "Set GITHUB_TOKEN / GH_TOKEN, or run: gh auth login"
            )
        if status_code == 401:
            return "GitHub API HTTP 401 (bad token). Check GITHUB_TOKEN / GH_TOKEN."
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
        """
        Download the allure-report Actions artifact for this run, unzip locally,
        and return a dashboard URL to open it in the browser.
        """
        run_id = str(run_id)
        existing = self.find_allure_index_dir(run_id)
        if existing is not None:
            return {
                "ok": True,
                "url": "/ci-allure/" + run_id + "/",
                "cached": True,
            }

        if not self._token():
            return {
                "ok": False,
                "error": (
                    "GitHub auth required to download artifacts. "
                    "Run: gh auth login (or set GITHUB_TOKEN)"
                ),
            }

        list_url = (
            "https://api.github.com/repos/"
            + GITHUB_REPO
            + "/actions/runs/"
            + run_id
            + "/artifacts"
        )
        try:
            listed = requests.get(list_url, headers=self._headers(), timeout=30)
        except requests.RequestException as exc:
            return {"ok": False, "error": "Could not reach GitHub API: " + str(exc)}

        if listed.status_code != 200:
            return {
                "ok": False,
                "error": self._error_message(listed.status_code, listed.text),
            }

        artifacts = listed.json().get("artifacts") or []
        chosen = None
        for item in artifacts:
            name = (item.get("name") or "").lower()
            if name == "allure-report" or "allure" in name:
                chosen = item
                break
        if chosen is None:
            return {
                "ok": False,
                "error": "No allure-report artifact for this run (expired or not uploaded).",
            }
        if chosen.get("expired"):
            return {"ok": False, "error": "Allure artifact for this run has expired."}

        download_url = chosen.get("archive_download_url") or ""
        if not download_url:
            return {"ok": False, "error": "Artifact has no download URL."}

        try:
            downloaded = requests.get(
                download_url,
                headers=self._headers(),
                timeout=120,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return {"ok": False, "error": "Artifact download failed: " + str(exc)}

        if downloaded.status_code != 200:
            return {
                "ok": False,
                "error": self._error_message(downloaded.status_code, downloaded.text),
            }

        dest = self.allure_cache_dir(run_id)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
                archive.extractall(dest)
        except zipfile.BadZipFile:
            shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": "Downloaded artifact is not a valid zip."}

        index_dir = self.find_allure_index_dir(run_id)
        if index_dir is None:
            return {
                "ok": False,
                "error": "Artifact unzipped but index.html was not found.",
            }

        return {
            "ok": True,
            "url": "/ci-allure/" + run_id + "/",
            "cached": False,
        }


CI_RUNS = CiRuns()
