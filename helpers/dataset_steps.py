import base64
import json
import re

from services.http_client import HttpClient
from helpers.steps import Step


class DatasetSteps(Step):
    def __init__(self, logger):
        super().__init__(logger)
        self.http = HttpClient(timeout=5, retries=3)

    def compare(self, row, schema):
        """Compare one flat dataset row to EventsSchema types."""
        values = {}
        for key, value in row.items():
            name = re.sub(r"[^a-z0-9]+", "_", key.lower().replace("$", "")).strip("_")
            values[name] = value

        matches = []
        for col in schema:
            field = col["name"]
            if field not in values:
                continue
            matches.append(
                {
                    "field": field,
                    "actual": values[field],
                    "expected_type": col["type"],
                }
            )

        return matches

    def send(self, row, localhost, case_id="NEG-DATASET"):
        """POST the validation dataset row to localhost."""
        self.log.info("POST " + localhost.url)
        self.log.info(json.dumps(row))
        body = base64.b64encode(json.dumps(row).encode("utf-8"))
        response = self.http.post(
            localhost.url,
            data=body,
            headers={"X-Case-Id": case_id},
        )
        self.log.info("status=" + str(response.status_code))
        return response
