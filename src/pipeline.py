"""Send generated catalog events to the local receiver."""

import base64
import json
import urllib.request
from pathlib import Path


class Sender:
    def send(self, generated_dir, port=8765):
        gen = Path(generated_dir)
        manifest_list = json.loads((gen / "manifest.json").read_text(encoding="utf-8"))
        manifest = {item["case_id"]: item for item in manifest_list}
        events = json.loads((gen / "events.json").read_text(encoding="utf-8"))

        url = "http://127.0.0.1:" + str(port) + "/v1/events"
        for item in events:
            body = base64.b64encode(json.dumps(item["event"]).encode("utf-8"))
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("X-Case-Id", item["case_id"])
            for key, value in manifest[item["case_id"]].get("delivery_headers", {}).items():
                req.add_header(key, value)
            urllib.request.urlopen(req, timeout=5)
