import json
import tempfile
import unittest
from pathlib import Path

from py_modules import fan_profiles


def profile(value=50):
    result = {str(temperature): value for temperature in range(10, 101, 10)}
    result["fullFanSpeedEnabled"] = False
    return result


class FanProfileTests(unittest.TestCase):
    def test_round_trip_preserves_valid_profiles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exported = fan_profiles.export_profile_bundle(
                {"default": profile(55), "123": profile(70)},
                temp_dir,
                "0.1.2",
            )
            imported = fan_profiles.load_profile_bundle(exported)

        self.assertEqual(imported["default"]["10"], 55)
        self.assertEqual(imported["123"]["100"], 70)
        self.assertFalse(imported["123"]["fullFanSpeedEnabled"])

    def test_import_rejects_invalid_or_incomplete_profiles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "profiles.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "fanProfiles": {"default": {"10": 50}},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Fan value"):
                fan_profiles.load_profile_bundle(path)

    def test_import_requires_default_profile(self):
        with self.assertRaisesRegex(ValueError, "default profile"):
            fan_profiles.normalize_fan_profiles({"123": profile()})

    def test_backup_is_reimportable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backup = fan_profiles.write_import_backup(
                {"default": profile(60)},
                temp_dir,
                "0.1.2",
            )
            imported = fan_profiles.load_profile_bundle(backup)

        self.assertEqual(imported["default"]["50"], 60)


if __name__ == "__main__":
    unittest.main()
