import re

from helpers.type_validator import TypeValidator


class DatasetSteps(TypeValidator):
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
