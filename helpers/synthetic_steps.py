import re

from helpers.type_validator import TypeValidator


class SyntheticSteps(TypeValidator):
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
