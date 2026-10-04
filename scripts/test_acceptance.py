import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("acceptance", Path(__file__).with_name("verify-acceptance.py"))
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


class AcceptanceGate(unittest.TestCase):
    def setUp(self):
        # Synthetic unit fixture, not an acceptance report and never published.
        self.record = {"schema": 1, "commit": "a" * 40, "artifact_sha256": "b" * 64,
            "platform": {"os": "Fedora 44", "desktop": "GNOME 50", "session": "Wayland",
                         "device": "ThinkPad X1 Yoga Gen 8", "architecture": "x86_64"},
            "reviewer": "unit fixture", "date": "2026-10-04", "limitations": [],
            "checks": dict.fromkeys(acceptance.REQUIRED, "passed"),
            "animation": {"refresh_hz": 60, "frames": 200, "within_budget": 190, "recurring_stalls": False}}

    def test_exact_threshold(self):
        acceptance.validate(self.record, "a" * 40, "b" * 64)
        self.record["animation"]["within_budget"] = 189
        with self.assertRaises(ValueError): acceptance.validate(self.record, "a" * 40, "b" * 64)

    def test_unverified_or_different_artifact_cannot_pass(self):
        for key, value in [("limitations", ["untested"]), ("reviewer", ""),
                           ("commit", "c" * 40), ("artifact_sha256", "c" * 64),
                           ("checks", {}), ("platform", {})]:
            record = copy.deepcopy(self.record)
            record[key] = value
            with self.assertRaises(ValueError): acceptance.validate(record, "a" * 40, "b" * 64)


if __name__ == "__main__": unittest.main()
