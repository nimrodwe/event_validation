"""Make test events and send them to the local server."""

import base64
import copy
import json
import urllib.request
from pathlib import Path

from src.config import OUT, INPUT_EVENT
from src.receiver import Receiver


def free_port():
    return Receiver.find_free_port()


class Generator:
    def generate(self, out_dir=None):
        if out_dir is None:
            out_dir = OUT
        out = Path(out_dir) / "generated"
        out.mkdir(parents=True, exist_ok=True)

        base = copy.deepcopy(json.loads(INPUT_EVENT.read_text(encoding="utf-8"))[0])
        events = []
        manifest = []

        # positive cases
        for n in range(1, 4):
            event = copy.deepcopy(base)
            event["properties"]["time"] = 1777423175525 + n
            event["properties"]["UUID"] = "A" + str(n).zfill(31)
            case_id = "POS-" + str(n).zfill(4)
            events.append({"case_id": case_id, "event": event})
            manifest.append({"case_id": case_id, "type": "positive", "intended_verdict": "valid",
                             "target_rule_id": "NONE", "delivery_headers": {}})

        # negative cases
        bad = copy.deepcopy(base)
        bad["properties"]["UUID"] = ""
        events.append({"case_id": "NEG-UUID", "event": bad})
        manifest.append({"case_id": "NEG-UUID", "type": "negative", "intended_verdict": "invalid",
                         "target_rule_id": "REQ-UUID", "delivery_headers": {}})

        bad = copy.deepcopy(base)
        bad["properties"]["Threatcode"] = None
        events.append({"case_id": "NEG-TYPE", "event": bad})
        manifest.append({"case_id": "NEG-TYPE", "type": "negative", "intended_verdict": "invalid",
                         "target_rule_id": "REQ-Threatcode", "delivery_headers": {}})

        bad = copy.deepcopy(base)
        bad["properties"]["Appdome fusion app token"] = "bad"
        events.append({"case_id": "NEG-FMT", "event": bad})
        manifest.append({"case_id": "NEG-FMT", "type": "negative", "intended_verdict": "invalid",
                         "target_rule_id": "FMT", "delivery_headers": {}})

        bad = copy.deepcopy(base)
        bad["properties"]["__bad"] = 1
        events.append({"case_id": "NEG-SCHEMA", "event": bad})
        manifest.append({"case_id": "NEG-SCHEMA", "type": "negative", "intended_verdict": "invalid",
                         "target_rule_id": "SCHEMA", "delivery_headers": {}})

        bad = copy.deepcopy(base)
        bad["properties"]["devicePlatform"] = "Android"
        bad["properties"]["$os"] = "iOS"
        events.append({"case_id": "NEG-XFIELD", "event": bad})
        manifest.append({"case_id": "NEG-XFIELD", "type": "negative", "intended_verdict": "invalid",
                         "target_rule_id": "XFIELD-OS", "delivery_headers": {}})

        # boundary
        event = copy.deepcopy(base)
        event["properties"]["time"] = 0
        events.append({"case_id": "BND-0001", "event": event})
        manifest.append({"case_id": "BND-0001", "type": "boundary", "intended_verdict": "valid",
                         "target_rule_id": "NONE", "delivery_headers": {}})

        # duplicates
        dup = copy.deepcopy(base)
        dup["properties"]["UUID"] = "DUP0000000000000000000000000001"
        events.append({"case_id": "DUP-0001", "event": copy.deepcopy(dup)})
        manifest.append({"case_id": "DUP-0001", "type": "duplicate", "intended_verdict": "valid",
                         "target_rule_id": "NONE", "delivery_headers": {}})
        events.append({"case_id": "DUP-0002", "event": copy.deepcopy(dup)})
        manifest.append({"case_id": "DUP-0002", "type": "duplicate", "intended_verdict": "valid",
                         "target_rule_id": "NONE", "delivery_headers": {}})

        # retries
        event = copy.deepcopy(base)
        event["properties"]["UUID"] = "RTY1"
        events.append({"case_id": "RTY-0001", "event": copy.deepcopy(event)})
        manifest.append({"case_id": "RTY-0001", "type": "retry", "intended_verdict": "valid",
                         "target_rule_id": "NONE",
                         "delivery_headers": {"Idempotency-Key": "k1", "X-Retry-Count": "1"}})
        events.append({"case_id": "RTY-0002", "event": copy.deepcopy(event)})
        manifest.append({"case_id": "RTY-0002", "type": "retry", "intended_verdict": "valid",
                         "target_rule_id": "NONE",
                         "delivery_headers": {"Idempotency-Key": "k1", "X-Retry-Count": "2"}})

        # replay — same payload delivered again later (kept visible, not dropped)
        replay = copy.deepcopy(base)
        replay["properties"]["UUID"] = "RPL0000000000000000000000000001"
        events.append({"case_id": "RPL-0001", "event": copy.deepcopy(replay)})
        manifest.append({"case_id": "RPL-0001", "type": "replay", "intended_verdict": "valid",
                         "target_rule_id": "NONE",
                         "delivery_headers": {"X-Replay": "false", "X-Delivery": "1"}})
        events.append({"case_id": "RPL-0002", "event": copy.deepcopy(replay)})
        manifest.append({"case_id": "RPL-0002", "type": "replay", "intended_verdict": "valid",
                         "target_rule_id": "NONE",
                         "delivery_headers": {"X-Replay": "true", "X-Delivery": "2"}})

        lines = []
        for item in events:
            lines.append(json.dumps(item))
        (out / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return out


class Sender:
    def send(self, generated_dir, port=8765):
        gen = Path(generated_dir)
        manifest_list = json.loads((gen / "manifest.json").read_text(encoding="utf-8"))
        manifest = {}
        for item in manifest_list:
            manifest[item["case_id"]] = item

        url = "http://127.0.0.1:" + str(port) + "/v1/events"
        for line in (gen / "events.jsonl").read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            body = base64.b64encode(json.dumps(item["event"]).encode("utf-8"))
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("X-Case-Id", item["case_id"])
            headers = manifest[item["case_id"]].get("delivery_headers", {})
            for key in headers:
                req.add_header(key, headers[key])
            urllib.request.urlopen(req, timeout=5)
