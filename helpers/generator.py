"""Build catalog cases (events.json + manifest.json) from the synthetic template."""

import copy
import json
from pathlib import Path

from src.config import OUT, INPUT_EVENT


class Generator:
    def _add(
        self,
        events,
        manifest,
        case_id,
        event,
        case_type,
        verdict,
        rule,
        headers=None,
        expect=None,
    ):
        events.append({"case_id": case_id, "event": event})
        row = {
            "case_id": case_id,
            "type": case_type,
            "intended_verdict": verdict,
            "target_rule_id": rule,
            "delivery_headers": headers or {},
        }
        # Optional property values the test must still see after GET (negatives).
        if expect is not None:
            row["expect"] = expect
        manifest.append(row)

    def add_positives(self, events, manifest, base):
        """Unchanged template copy — round-trip / happy-path cases."""
        self._add(events, manifest, "POS-0001", copy.deepcopy(base), "positive", "valid", "NONE")

    def add_negatives(self, events, manifest, base):
        """Broken fields — each targets a specific validation rule.

        Keep the synthetic template UUID except NEG-UUID (must be empty for REQ-UUID).
        """
        bad = copy.deepcopy(base)
        bad["properties"]["UUID"] = ""
        self._add(
            events,
            manifest,
            "NEG-UUID",
            bad,
            "negative",
            "invalid",
            "REQ-UUID",
            expect={"UUID": ""},
        )

        bad = copy.deepcopy(base)
        bad["properties"]["Threatcode"] = None
        self._add(
            events,
            manifest,
            "NEG-TYPE",
            bad,
            "negative",
            "invalid",
            "REQ-Threatcode",
            expect={"Threatcode": None},
        )

        bad = copy.deepcopy(base)
        bad["properties"]["__bad"] = 1
        self._add(
            events,
            manifest,
            "NEG-SCHEMA",
            bad,
            "negative",
            "invalid",
            "SCHEMA",
            expect={"__bad": 1},
        )

        bad = copy.deepcopy(base)
        bad["properties"]["devicePlatform"] = "Android"
        bad["properties"]["$os"] = "iOS"
        self._add(
            events,
            manifest,
            "NEG-XFIELD",
            bad,
            "negative",
            "invalid",
            "XFIELD-OS",
            expect={"devicePlatform": "Android", "$os": "iOS"},
        )

    def add_boundary(self, events, manifest, base):
        """Edge values (time=0, token length short / at min). UUID stays from template."""
        event = copy.deepcopy(base)
        event["properties"]["time"] = 0
        self._add(events, manifest, "BND-0001", event, "boundary", "valid", "NONE")

        short = copy.deepcopy(base)
        short["properties"]["Appdome fusion app token"] = "x" * 29
        self._add(events, manifest, "BND-TOKEN-SHORT", short, "boundary", "invalid", "FMT")

        edge = copy.deepcopy(base)
        edge["properties"]["Appdome fusion app token"] = "x" * 30
        self._add(events, manifest, "BND-TOKEN-EDGE", edge, "boundary", "valid", "NONE")

    def add_duplicates(self, events, manifest, base):
        """Two near-identical deliveries — expect DUP-NEAR (full body match, UUID skipped)."""
        dup = copy.deepcopy(base)
        self._add(events, manifest, "DUP-0001", copy.deepcopy(dup), "duplicate", "valid", "NONE")
        self._add(events, manifest, "DUP-0002", copy.deepcopy(dup), "duplicate", "valid", "NONE")

    def add_retries(self, events, manifest, base):
        """Same template payload twice with retry headers."""
        event = copy.deepcopy(base)
        self._add(
            events,
            manifest,
            "RTY-0001",
            copy.deepcopy(event),
            "retry",
            "valid",
            "NONE",
            {"Idempotency-Key": "k1", "X-Retry-Count": "1"},
        )
        self._add(
            events,
            manifest,
            "RTY-0002",
            copy.deepcopy(event),
            "retry",
            "valid",
            "NONE",
            {"Idempotency-Key": "k1", "X-Retry-Count": "2"},
        )

    def add_replays(self, events, manifest, base):
        """Same template payload twice; shared case_id so GET can count both deliveries."""
        replay = copy.deepcopy(base)
        case_id = "RPL-0001"
        self._add(
            events,
            manifest,
            case_id,
            copy.deepcopy(replay),
            "replay",
            "valid",
            "NONE",
            {"X-Replay": "false", "X-Delivery": "1"},
        )
        self._add(
            events,
            manifest,
            case_id,
            copy.deepcopy(replay),
            "replay",
            "valid",
            "NONE",
            {"X-Replay": "true", "X-Delivery": "2"},
        )

    def generate(self, out_dir=None):
        if out_dir is None:
            out_dir = OUT
        out = Path(out_dir) / "generated"
        out.mkdir(parents=True, exist_ok=True)

        base = copy.deepcopy(json.loads(INPUT_EVENT.read_text(encoding="utf-8"))[0])
        events = []
        manifest = []

        self.add_positives(events, manifest, base)
        self.add_negatives(events, manifest, base)
        self.add_boundary(events, manifest, base)
        self.add_duplicates(events, manifest, base)
        self.add_retries(events, manifest, base)
        self.add_replays(events, manifest, base)

        (out / "events.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return out
