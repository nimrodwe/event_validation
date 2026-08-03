"""Catalog helper — generate and load synthetic cases for tests."""

import json
import shutil
import tempfile
from pathlib import Path

from helpers.generator import Generator


class Catalog:
    """Owns catalog generate/load for tests."""

    def __init__(self, generator=None):
        self.generator = generator or Generator()

    def generate(self, out_dir):
        """Build a fresh synthetic catalog; returns folder with events.json + manifest.json."""
        return self.generator.generate(out_dir)

    def load_manifest(self, generated_dir):
        path = Path(generated_dir) / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def load_events(self, generated_dir):
        path = Path(generated_dir) / "events.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def cases_of_type(self, manifest, case_type):
        return [item for item in manifest if item.get("type") == case_type]

    def by_id(self, cases):
        """Map case_id → manifest row."""
        return {item["case_id"]: item for item in cases}

    def make_with_events(self, out_dir):
        generated_dir = self.generate(out_dir)
        return generated_dir, self.load_manifest(generated_dir), self.load_events(generated_dir)

    def cases(self, case_type, out_dir=None):
        """Generate catalog, load into memory, delete the folder, return events + cases."""
        cleanup = out_dir is None
        if out_dir is None:
            out_dir = Path(tempfile.mkdtemp())
        generated_dir, manifest, events = self.make_with_events(out_dir)
        cases = self.cases_of_type(manifest, case_type)
        shutil.rmtree(out_dir if cleanup else generated_dir, ignore_errors=True)
        return events, cases

    def case(self, case_type, case_id, out_dir=None):
        """events + one manifest row for case_id (row is None if missing)."""
        events, cases = self.cases(case_type, out_dir=out_dir)
        return events, self.by_id(cases).get(case_id)
