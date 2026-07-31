"""Fetch GitHub Actions workflow runs for the dashboard CI panel."""

import os
import time

import requests

from src.config import ALLURE_PAGES_URL, GITHUB_REPO, GITHUB_WORKFLOW_FILE

_CACHE_TTL_SECONDS = 30
_CACHE_TTL_IN_PROGRESS = 5
_cache = {"expires": 0.0, "payload": None}


def _headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "event-validation-dashboard",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _normalize(run, *, is_latest_success):
    sha = run.get("head_sha") or ""
    return {
        "run_number": run.get("run_number"),
        "status": run.get("status") or "",
        "conclusion": run.get("conclusion") or "",
        "event": run.get("event") or "",
        "head_branch": run.get("head_branch") or "",
        "head_sha": sha[:7] if sha else "",
        "created_at": run.get("created_at") or "",
        "updated_at": run.get("updated_at") or "",
        "html_url": run.get("html_url") or "",
        "display_title": run.get("display_title") or run.get("name") or "",
        "allure_url": ALLURE_PAGES_URL if is_latest_success else "",
    }


def load_ci_runs(limit=10, force=False):
    """
    Return {"runs": [...], "error": null|str, "allure_pages_url": str}.
    Cached for ~30s to avoid burning GitHub API rate limits.
    """
    now = time.time()
    if (
        not force
        and _cache["payload"] is not None
        and now < _cache["expires"]
    ):
        return _cache["payload"]

    url = (
        "https://api.github.com/repos/"
        + GITHUB_REPO
        + "/actions/workflows/"
        + GITHUB_WORKFLOW_FILE
        + "/runs"
    )
    try:
        response = requests.get(
            url,
            headers=_headers(),
            params={"per_page": limit},
            timeout=15,
        )
        if response.status_code != 200:
            payload = {
                "runs": [],
                "error": "GitHub API HTTP " + str(response.status_code),
                "allure_pages_url": ALLURE_PAGES_URL,
            }
            _cache["payload"] = payload
            _cache["expires"] = now + _CACHE_TTL_SECONDS
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
                _normalize(
                    run,
                    is_latest_success=run.get("id") == latest_success_id,
                )
            )

        payload = {
            "runs": runs,
            "error": None,
            "allure_pages_url": ALLURE_PAGES_URL,
        }
        ttl = _CACHE_TTL_SECONDS
        for run in runs:
            if (run.get("status") or "") != "completed":
                ttl = _CACHE_TTL_IN_PROGRESS
                break
    except requests.RequestException as exc:
        payload = {
            "runs": [],
            "error": "Could not reach GitHub API: " + str(exc),
            "allure_pages_url": ALLURE_PAGES_URL,
        }
        ttl = _CACHE_TTL_IN_PROGRESS

    _cache["payload"] = payload
    _cache["expires"] = now + ttl
    return payload
