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
    ):
        events.append({"case_id": case_id, "event": event})
        manifest.append(
            {
                "case_id": case_id,
                "type": case_type,
                "intended_verdict": verdict,
                "target_rule_id": rule,
                "delivery_headers": headers or {},
            }
        )

    def add_positives(self, events, manifest, base):
        """Unchanged template copy — round-trip / happy-path cases."""
        self._add(events, manifest, "POS-0001", copy.deepcopy(base), "positive", "valid", "NONE")

    def add_boundary(self, events, manifest, base):
        """Edge values (time=0 / -1, token length short / at min). UUID stays from template."""
        event = copy.deepcopy(base)
        event["properties"]["time"] = 0
        self._add(events, manifest, "BND-0001", event, "boundary", "valid", "NONE")

        bad_time = copy.deepcopy(base)
        bad_time["properties"]["time"] = -1
        self._add(
            events,
            manifest,
            "BND-TIME-NEG",
            bad_time,
            "boundary",
            "invalid",
            "RANGE-time",
        )

        short = copy.deepcopy(base)
        short["properties"]["Appdome fusion app token"] = "x" * 29
        self._add(events, manifest, "BND-TOKEN-SHORT", short, "boundary", "invalid", "FMT")

        edge = copy.deepcopy(base)
        edge["properties"]["Appdome fusion app token"] = "x" * 30
        self._add(events, manifest, "BND-TOKEN-EDGE", edge, "boundary", "valid", "NONE")

    def add_duplicates(self, events, manifest, base):
        """Two near-identical deliveries — second POST blocked by receiver (409)."""
        dup = copy.deepcopy(base)
        self._add(events, manifest, "DUP-0001", copy.deepcopy(dup), "duplicate", "valid", "NONE")
        self._add(events, manifest, "DUP-0002", copy.deepcopy(dup), "duplicate", "valid", "NONE")

    def add_retries(self, events, manifest, base):
        """One valid event for retry: first POST fails (500), second succeeds (200)."""
        event = copy.deepcopy(base)
        self._add(
            events,
            manifest,
            "RTY-0001",
            event,
            "retry",
            "valid",
            "NONE",
            {"Idempotency-Key": "k1", "X-Retry-Count": "1"},
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
        self.add_boundary(events, manifest, base)
        self.add_duplicates(events, manifest, base)
        self.add_retries(events, manifest, base)
        self.add_replays(events, manifest, base)

        (out / "events.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return out
