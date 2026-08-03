"""Paths and constants."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
INPUT_EVENT = DATA / "synthetic_event_template.json"
DATASET = DATA / "validation_dataset_intentionally_corrupted.json"
EXPECTED_TYPES = DATA / "EventsSchema.json"
TEST_RUNS = OUT / "test_runs"

# GitHub Actions / Allure (local dashboard CI panel) — all public, no auth.
GITHUB_REPO = "nimrodwe/event_validation"
GITHUB_WORKFLOW_FILE = "allure-github-pages.yml"
ALLURE_PAGES_URL = "https://nimrodwe.github.io/event_validation/"
# Per-run Allure: serve from allure-pages via raw.githack (correct text/html).
ALLURE_RUNS_URL = (
    "https://raw.githack.com/" + GITHUB_REPO + "/allure-pages/"
)
# Public catalog on the allure-pages branch. Prefer CDN mirrors — raw.githubusercontent
# often stays stale for minutes after Publish pushes the branch.
CI_RUNS_CATALOG_URL = (
    "https://raw.githack.com/" + GITHUB_REPO + "/allure-pages/ci-runs.json"
)
CI_RUNS_CATALOG_FALLBACK_URL = (
    "https://cdn.jsdelivr.net/gh/"
    + GITHUB_REPO
    + "@allure-pages/ci-runs.json"
)
CI_RUNS_CATALOG_RAW_URL = (
    "https://raw.githubusercontent.com/"
    + GITHUB_REPO
    + "/allure-pages/ci-runs.json"
)
GITHUB_ACTIONS_URL = (
    "https://github.com/"
    + GITHUB_REPO
    + "/actions/workflows/"
    + GITHUB_WORKFLOW_FILE
)


def allure_pages_run_url(run_id):
    """Public URL for one CI run's Allure report (no GitHub token)."""
    if run_id is None or str(run_id).strip() == "":
        return ""
    return ALLURE_RUNS_URL.rstrip("/") + "/runs/" + str(run_id) + "/"


GOLDEN = {
    99, 119, 139, 159, 179, 199, 219, 239, 259, 279, 299, 319, 339, 359,
    379, 399, 419, 439, 459, 479, 499, 519, 539, 3990, 3991, 3992,
}

REQUIRED = [
    "Event", "Externalid", "UUID", "Full Threat Code", "Threatcode", "Reasoncode",
    "Datetime", "Email", "Properties", "Tda", "Mp Wifi", "Country Code",
    "Deviceplatform", "Mp Os", "Devicemodel", "Mp Model",
    "Appdome Fusion App Token", "Appdome Fusion Fused App Token",
]

PROPS_OK = [
    "appdomescorekey", "appdomescorestatekey", "builddate", "context",
    "current_signature_application-identifier", "currentthreateventscore",
    "devicefacedown", "dylibnames", "eventid", "frameworkname", "functionname",
    "geosource_type", "hookframework", "identity", "installation_id", "instanceid",
    "invalidatesecret", "ip", "lastlocationretrieval", "metadata", "mp_app_release",
    "mp_app_version_string", "mp_ios_ifa", "mp_latitude", "mp_longitude",
    "mp_screen_height", "mp_screen_width", "original_signature_application-identifier",
    "releaseid", "threateventsscore", "time_since_launch", "timestamp", "token", "user_agent",
]

DUPE_SKIP = ["Datetime", "Mp Processing Time Ms", "UUID"]


class Schema:
    """Read the template file and learn which fields are required."""

    def __init__(self):
        text = INPUT_EVENT.read_text(encoding="utf-8")
        event = json.loads(text)[0]
        props = event["properties"]

        self.required = []
        self.allowed = []
        for key in props:
            self.allowed.append(key)
            if props[key] != "":
                self.required.append(key)
