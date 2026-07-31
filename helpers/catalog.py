"""Helpers for the generated event catalog (manifest + send)."""

import base64
import json
from pathlib import Path

from services.http_client import HttpClient
from src.pipeline import Generator

REQUIRED_CASE_TYPES = [
    "positive",
    "negative",
    "boundary",
    "retry",
    "duplicate",
    "replay",
]


def generate_catalog(out_dir):
    """Generate catalog under out_dir/generated and return that folder."""
    return Generator().generate(out_dir)


def load_manifest(generated_dir):
    path = Path(generated_dir) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_events(generated_dir):
    path = Path(generated_dir) / "events.jsonl"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def cases_of_type(manifest, case_type):
    return [item for item in manifest if item.get("type") == case_type]


def event_for_case(events, case_id):
    for item in events:
        if item.get("case_id") == case_id:
            return item["event"]
    return None


def send_case(localhost, case_id, event, headers=None):
    """POST one catalog event to localhost with optional delivery headers."""
    http = HttpClient(timeout=5, retries=3)
    body = base64.b64encode(json.dumps(event).encode("utf-8"))
    req_headers = {"X-Case-Id": case_id}
    if headers:
        req_headers.update(headers)
    return http.post(localhost.url, data=body, headers=req_headers)


def read_received(localhost):
    path = Path(localhost.out) / "events.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def received_by_case_id(localhost, case_id):
    return [row for row in read_received(localhost) if row.get("case_id") == case_id]
