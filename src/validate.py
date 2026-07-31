"""Find problems in events. Returns a list of Finding objects."""

import json
import re
from datetime import datetime
from pathlib import Path

from src.config import DATASET, DUPE_SKIP, GOLDEN, PROPS_OK, REQUIRED, Schema

UUID_RE = re.compile(r"^[0-9a-f-]{36}$", re.I)
FTC_RE = re.compile(r"^\d+:[0-9a-f]{4}:[A-Z0-9]{6}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
DATE_FMT = "%B %d, %Y, %H:%M:%S"
MP_FMT = "%B %d, %Y, %H:%M"


class Finding:
    """One problem found by the validator."""

    def __init__(self, locator, rule_id, field, observed, expected, category, source="dataset"):
        self.source = source
        self.locator = locator
        self.rule_id = rule_id
        self.category = category
        self.severity = "error"
        self.field = field
        self.observed = observed
        self.expected = expected

    def to_dict(self):
        return {
            "source": self.source,
            "locator": self.locator,
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "field": self.field,
            "observed": self.observed,
            "expected": self.expected,
        }


class Validator:
    def __init__(self):
        self.schema = Schema()

    def make_finding(self, locator, rule_id, field, observed, expected, category, source="dataset"):
        return Finding(locator, rule_id, field, observed, expected, category, source)

    def check_row(self, row, index, declared_keys):
        findings = []

        # required fields
        for field in REQUIRED:
            if field not in row:
                findings.append(self.make_finding(index, "REQ-" + field, field, "<missing>", "present", "required"))
            elif row[field] is None:
                findings.append(self.make_finding(index, "REQ-" + field, field, None, "non-null", "required"))
            elif row[field] == "":
                findings.append(self.make_finding(index, "REQ-" + field, field, '""', "non-empty", "required"))

        # unknown top-level keys
        for key in row:
            if key not in declared_keys:
                findings.append(self.make_finding(index, "SCHEMA-TOP", key, key, "declared key", "schema compliance"))

        # Event type
        if row.get("Event") is not None and type(row["Event"]) is not str:
            findings.append(self.make_finding(index, "TYPE-Event", "Event", type(row["Event"]).__name__, "str", "type"))

        # tokens
        for field in ["Appdome Fusion App Token", "Appdome Fusion Fused App Token"]:
            value = row.get(field)
            if type(value) is int:
                findings.append(self.make_finding(index, "TYPE-" + field, field, "int", "str UUID", "type"))
            elif type(value) is str and value != "" and not UUID_RE.match(value):
                findings.append(self.make_finding(index, "FMT-" + field, field, value, "UUID", "format"))

        # wifi
        wifi = row.get("Mp Wifi")
        if type(wifi) is dict:
            findings.append(self.make_finding(index, "TYPE-Mp Wifi", "Mp Wifi", "dict", "str", "type"))
        elif type(wifi) is str and wifi not in ["true", "false"]:
            findings.append(self.make_finding(index, "ENUM-Mp Wifi", "Mp Wifi", wifi, "true|false", "format"))

        # country
        country = row.get("Country Code")
        if type(country) is str and country != "" and not COUNTRY_RE.match(country):
            findings.append(self.make_finding(index, "FMT-Country Code", "Country Code", country, "ISO alpha-2", "format"))

        # email
        if type(row.get("Email")) is list:
            findings.append(self.make_finding(index, "TYPE-Email", "Email", "list", "str", "type"))

        # datetime
        dt = row.get("Datetime")
        if type(dt) is int:
            findings.append(self.make_finding(index, "TYPE-Datetime", "Datetime", "int", "str", "type"))
        elif type(dt) is str:
            try:
                datetime.strptime(dt, DATE_FMT)
            except ValueError:
                findings.append(self.make_finding(index, "TS-Datetime", "Datetime", dt, DATE_FMT, "timestamp"))

        # processing time
        mpt = row.get("Mp Processing Time Ms")
        if type(mpt) is str and mpt != "":
            try:
                datetime.strptime(mpt, MP_FMT)
            except ValueError:
                findings.append(self.make_finding(index, "TS-Mp Processing Time Ms", "Mp Processing Time Ms", mpt, MP_FMT, "timestamp"))

        # full threat code
        ftc = row.get("Full Threat Code")
        if type(ftc) is str and ftc != "" and not FTC_RE.match(ftc):
            findings.append(self.make_finding(index, "FMT-Full Threat Code", "Full Threat Code", ftc, "NNNN:hex:CODE", "format"))

        # Properties must be a JSON string
        props = row.get("Properties")
        if props is not None and type(props) is not str:
            findings.append(self.make_finding(index, "TYPE-Properties", "Properties", type(props).__name__, "str", "type"))
        elif type(props) is str:
            try:
                obj = json.loads(props)
                if type(obj) is not dict:
                    findings.append(self.make_finding(index, "TYPE-Properties", "Properties", type(obj).__name__, "object", "type"))
                else:
                    for key in obj:
                        if key not in PROPS_OK:
                            findings.append(self.make_finding(index, "SCHEMA-PROP", "Properties." + key, key, "allowed key", "schema compliance"))
            except json.JSONDecodeError:
                findings.append(self.make_finding(index, "PARSE-Properties", "Properties", "invalid JSON", "parseable", "type"))

        # Tda must be string
        if row.get("Tda") is not None and type(row["Tda"]) is not str:
            findings.append(self.make_finding(index, "TYPE-Tda", "Tda", type(row["Tda"]).__name__, "str", "type"))

        # platform vs os
        platform = row.get("Deviceplatform")
        mp_os = row.get("Mp Os")
        model = row.get("Mp Model") or row.get("Devicemodel") or ""
        ipad_ok = platform == "iOS" and mp_os == "iPadOS" and "iPad" in model
        if platform and mp_os and platform != mp_os and not ipad_ok:
            findings.append(self.make_finding(index, "XFIELD-OS", "Deviceplatform/Mp Os", str(platform) + "!=" + str(mp_os), "equal", "cross-field"))

        # reasoncode matches threat code prefix
        if type(ftc) is str and ftc != "" and row.get("Reasoncode") is not None:
            prefix = ftc.split(":")[0]
            if str(row["Reasoncode"]) != prefix:
                findings.append(self.make_finding(index, "XFIELD-REASON", "Reasoncode/FTC", row["Reasoncode"], prefix, "cross-field"))

        # model consistency
        device_model = row.get("Devicemodel") or ""
        mp_model = row.get("Mp Model") or ""
        if device_model and mp_model:
            left = device_model.split(",")[0]
            right = mp_model.split(",")[0]
            if left not in mp_model and right not in device_model:
                if not (mp_os == "iPadOS" and "iPad" in mp_model):
                    findings.append(self.make_finding(index, "XFIELD-MODEL", "Devicemodel/Mp Model", device_model + "!=" + mp_model, "consistent", "cross-field"))

        # manufacturer
        mfg1 = row.get("Mp Manufacturer")
        mfg2 = row.get("Devicemanufacturer")
        if mfg1 and mfg2 and mfg1 != mfg2:
            findings.append(self.make_finding(index, "XFIELD-MFG", "Manufacturer", str(mfg1) + "!=" + str(mfg2), "equal", "cross-field"))

        # message rules
        event_name = row.get("Event")
        message = row.get("Message")
        if event_name == "First Use" and message:
            findings.append(self.make_finding(index, "XFIELD-MSG", "Message", message, "empty", "cross-field"))
        elif event_name and event_name != "First Use" and not message:
            findings.append(self.make_finding(index, "XFIELD-MSG", "Message", "", "non-empty", "cross-field"))

        return findings

    def check_nested(self, event, case_id):
        """Check a generated/received nested event."""
        findings = []
        source = "received"

        if not event.get("event"):
            findings.append(self.make_finding(case_id, "REQ-event", "event", event.get("event"), "non-empty", "required", source))

        props = event.get("properties")
        if type(props) is not dict:
            findings.append(self.make_finding(case_id, "REQ-properties", "properties", type(props).__name__, "dict", "required", source))
            return findings

        for key in self.schema.required:
            if key not in props or props[key] is None or props[key] == "":
                findings.append(self.make_finding(case_id, "REQ-" + key, key, props.get(key), "non-empty", "required", source))

        for key in props:
            if key not in self.schema.allowed:
                findings.append(self.make_finding(case_id, "SCHEMA", key, key, "template key", "schema compliance", source))

        if props.get("devicePlatform") and props.get("$os"):
            if props["devicePlatform"] != props["$os"]:
                findings.append(self.make_finding(case_id, "XFIELD-OS", "platform/$os", "mismatch", "equal", "cross-field", source))

        token = props.get("Appdome fusion app token")
        if token is not None and token != "" and len(str(token)) < 30:
            findings.append(
                self.make_finding(
                    case_id, "FMT", "Appdome fusion app token", token, "UUID-like", "format", source
                )
            )

        return findings

    def check_dupes(self, rows):
        """Find near-duplicate rows."""
        groups = {}
        for i, row in enumerate(rows):
            cleaned = {}
            for key in row:
                if key not in DUPE_SKIP:
                    cleaned[key] = row[key]
            key = json.dumps(cleaned, sort_keys=True)
            if key not in groups:
                groups[key] = []
            groups[key].append(i)

        findings = []
        for locs in groups.values():
            if len(locs) < 2:
                continue
            original = min(locs)
            for loc in locs:
                if loc != original:
                    findings.append(self.make_finding(loc, "DUP-NEAR", "*", "dup of " + str(original), "unique", "duplicates"))
        return findings

    def validate_dataset(self):
        rows = json.loads(DATASET.read_text(encoding="utf-8"))
        declared_keys = list(rows[0].keys())
        if "Debug Payload" in declared_keys:
            declared_keys.remove("Debug Payload")

        findings = []
        for i, row in enumerate(rows):
            findings.extend(self.check_row(row, i, declared_keys))
        findings.extend(self.check_dupes(rows))

        result = []
        for f in findings:
            result.append(f.to_dict())
        return result

    def validate_received(self, path):
        path = Path(path)
        if not path.exists():
            return []

        items = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() == "":
                continue
            items.append(json.loads(line))

        findings = []
        for item in items:
            case_id = item.get("case_id", "?")
            event = item.get("event", item)
            findings.extend(self.check_nested(event, case_id))
        findings.extend(self.check_received_dupes(items))

        result = []
        for f in findings:
            result.append(f.to_dict())
        return result

    def check_received_dupes(self, items):
        """Flag duplicate UUIDs among received nested events (keep all visible)."""
        by_uuid = {}
        for item in items:
            case_id = item.get("case_id", "?")
            props = item.get("event", {}).get("properties", {})
            uuid = props.get("UUID")
            if not uuid:
                continue
            if uuid not in by_uuid:
                by_uuid[uuid] = []
            by_uuid[uuid].append(case_id)

        findings = []
        for uuid, case_ids in by_uuid.items():
            if len(case_ids) < 2:
                continue
            original = case_ids[0]
            for case_id in case_ids[1:]:
                findings.append(
                    self.make_finding(
                        case_id, "DUP-NEAR", "UUID", "dup of " + original, "unique", "duplicates", "received"
                    )
                )
        return findings

    def golden_ok(self, findings):
        rows = set()
        for f in findings:
            if f["source"] == "dataset":
                rows.add(f["locator"])
        return rows == GOLDEN
