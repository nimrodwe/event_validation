"""Near-duplicate event fingerprinting (shared by validator + receiver)."""

import json

from src.config import DUPE_SKIP


def dupe_fingerprint(event):
    """Serialize event body for near-dupe match — all fields except identity/noise."""
    if not isinstance(event, dict):
        return json.dumps(event, sort_keys=True)
    cleaned = {}
    for key, value in event.items():
        if key in DUPE_SKIP:
            continue
        if key == "properties" and isinstance(value, dict):
            props = {}
            for prop_key, prop_value in value.items():
                if prop_key not in DUPE_SKIP:
                    props[prop_key] = prop_value
            cleaned[key] = props
        else:
            cleaned[key] = value
    return json.dumps(cleaned, sort_keys=True)
