import base64
import json
import re

from services.http_client import HttpClient
from helpers.type_validation import Step


class SyntheticSteps(Step):
    def __init__(self, logger):
        super().__init__(logger)
        self.http = HttpClient(timeout=5, retries=3)

    def compare(self, event, schema):
        props = event.get("properties", {})

        types = {}
        for col in schema:
            types[col["name"]] = col["type"]

        matches = []
        for key, value in props.items():
            name = re.sub(r"[^a-z0-9]+", "_", key.lower().replace("$", "")).strip("_")
            if name not in types:
                continue
            matches.append({"field": name, "actual": value, "expected_type": types[name]})

        return matches

    def send(self, event, localhost):
        """POST the synthetic event to localhost."""
        self.log.info("POST " + localhost.url)
        self.log.info(json.dumps(event))
        body = base64.b64encode(json.dumps(event).encode("utf-8"))
        response = self.http.post(
            localhost.url,
            data=body,
            headers={"X-Case-Id": "POS-SYNTHETIC"},
        )
        self.log.info("status=" + str(response.status_code))
        return response
