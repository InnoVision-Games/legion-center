import tempfile
import unittest
from pathlib import Path

from py_modules import battery_charge


class BatteryChargeTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.power_supply_root = Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def add_charge_types(self, supply: str, value: str) -> Path:
        supply_path = self.power_supply_root / supply
        supply_path.mkdir()
        charge_types = supply_path / "charge_types"
        charge_types.write_text(value, encoding="ascii")
        return charge_types

    def add_charge_threshold(self, supply: str, value: int) -> Path:
        supply_path = self.power_supply_root / supply
        supply_path.mkdir(exist_ok=True)
        threshold = supply_path / "charge_control_end_threshold"
        threshold.write_text(str(value), encoding="ascii")
        return threshold

    def test_parse_charge_types_finds_active_value(self):
        values, active = battery_charge.parse_charge_types("[Standard] Long_Life\n")
        self.assertEqual(values, ("Standard", "Long_Life"))
        self.assertEqual(active, "Standard")

    def test_parse_charge_types_rejects_missing_active_value(self):
        with self.assertRaises(ValueError):
            battery_charge.parse_charge_types("Standard Long_Life")

    def test_discovery_ignores_unrelated_power_supplies(self):
        self.add_charge_types("ACAD", "[Standard]")
        battery_path = self.add_charge_types("BATT", "[Standard] Long_Life")
        self.assertEqual(
            battery_charge.find_charge_types_path(self.power_supply_root),
            battery_path,
        )

    def test_status_uses_active_sysfs_value(self):
        charge_types = self.add_charge_types("BATT", "Standard [Long_Life]")
        result = battery_charge.get_charge_limit_status(self.power_supply_root)
        self.assertTrue(result.supported)
        self.assertTrue(result.enabled)
        self.assertEqual(result.limit, 80)
        self.assertFalse(result.configurable)
        self.assertEqual(result.backend, "sysfs_charge_type")
        self.assertEqual(result.path, str(charge_types))

    def test_percentage_threshold_takes_priority_and_is_configurable(self):
        self.add_charge_types("BATT", "Standard [Long_Life]")
        threshold = self.add_charge_threshold("BATT", 85)

        result = battery_charge.get_charge_limit_status(self.power_supply_root)

        self.assertTrue(result.supported)
        self.assertTrue(result.enabled)
        self.assertEqual(result.limit, 85)
        self.assertTrue(result.configurable)
        self.assertEqual(result.backend, "sysfs_threshold")
        self.assertEqual(result.path, str(threshold))

    def test_set_percentage_threshold_verifies_read_back(self):
        threshold = self.add_charge_threshold("BATT", 85)

        def threshold_writer(path: Path, target: str):
            self.assertEqual(path, threshold)
            path.write_text(target, encoding="ascii")

        result = battery_charge.set_charge_limit(
            70, self.power_supply_root, sysfs_writer=threshold_writer
        )

        self.assertTrue(result.success)
        self.assertEqual(result.limit, 70)
        self.assertTrue(result.configurable)

    def test_percentage_threshold_accepts_hardware_rounding(self):
        threshold = self.add_charge_threshold("BATT", 85)

        def rounding_writer(path: Path, _target: str):
            path.write_text("72", encoding="ascii")

        result = battery_charge.set_charge_limit(
            70, self.power_supply_root, sysfs_writer=rounding_writer
        )

        self.assertTrue(result.success)
        self.assertEqual(result.limit, 72)
        self.assertTrue(result.configurable)

    def test_read_only_percentage_threshold_falls_back_to_fixed_mode(self):
        threshold = self.add_charge_threshold("BATT", 85)
        threshold.chmod(0o444)
        self.add_charge_types("BATT2", "[Standard] Long_Life")

        result = battery_charge.get_charge_limit_status(self.power_supply_root)

        self.assertEqual(result.backend, "sysfs_charge_type")
        self.assertFalse(result.configurable)

    def test_status_reports_unsupported_without_backend(self):
        result = battery_charge.get_charge_limit_status(self.power_supply_root)
        self.assertFalse(result.supported)
        self.assertFalse(result.success)
        self.assertIsNone(result.enabled)

    def test_set_sysfs_charge_limit_verifies_read_back(self):
        charge_types = self.add_charge_types("BATT", "[Standard] Long_Life")

        def sysfs_writer(path: Path, target: str):
            self.assertEqual(path, charge_types)
            value = (
                "Standard [Long_Life]"
                if target == battery_charge.LONG_LIFE
                else "[Standard] Long_Life"
            )
            path.write_text(value, encoding="ascii")

        enabled = battery_charge.set_charge_limit(
            True, self.power_supply_root, sysfs_writer=sysfs_writer
        )
        disabled = battery_charge.set_charge_limit(
            False, self.power_supply_root, sysfs_writer=sysfs_writer
        )
        self.assertTrue(enabled.success)
        self.assertTrue(enabled.enabled)
        self.assertEqual(enabled.limit, 80)
        self.assertTrue(disabled.success)
        self.assertFalse(disabled.enabled)
        self.assertEqual(disabled.limit, 100)

    def test_fixed_charge_type_rejects_arbitrary_percentage(self):
        self.add_charge_types("BATT", "[Standard] Long_Life")

        result = battery_charge.set_charge_limit(70, self.power_supply_root)

        self.assertFalse(result.success)
        self.assertFalse(result.configurable)
        self.assertIn("fixed 80%", result.error)

    def test_set_sysfs_charge_limit_reports_write_failure(self):
        self.add_charge_types("BATT", "[Standard] Long_Life")

        def failing_writer(_path: Path, _target: str):
            raise PermissionError("read-only")

        result = battery_charge.set_charge_limit(
            True, self.power_supply_root, sysfs_writer=failing_writer
        )
        self.assertFalse(result.success)
        self.assertFalse(result.enabled)
        self.assertIn("read-only", result.error)

    def test_set_sysfs_charge_limit_reports_read_back_mismatch(self):
        self.add_charge_types("BATT", "[Standard] Long_Life")
        result = battery_charge.set_charge_limit(
            True,
            self.power_supply_root,
            sysfs_writer=lambda _path, _target: None,
        )
        self.assertFalse(result.success)
        self.assertFalse(result.enabled)
        self.assertIn("read-back", result.error)

    def test_legacy_acpi_is_used_only_when_sysfs_is_unavailable(self):
        legacy_state = {"enabled": 0}

        def legacy_get():
            return legacy_state["enabled"]

        def legacy_set(enabled: bool):
            legacy_state["enabled"] = int(enabled)
            return True

        result = battery_charge.set_charge_limit(
            True,
            self.power_supply_root,
            legacy_get=legacy_get,
            legacy_set=legacy_set,
        )
        self.assertTrue(result.success)
        self.assertTrue(result.enabled)
        self.assertEqual(result.limit, 80)
        self.assertEqual(result.backend, "acpi_call")

    def test_sysfs_takes_priority_over_legacy_acpi(self):
        self.add_charge_types("BATT", "[Standard] Long_Life")

        def unexpected_legacy_get():
            self.fail("legacy backend should not be queried")

        result = battery_charge.get_charge_limit_status(
            self.power_supply_root, legacy_get=unexpected_legacy_get
        )
        self.assertEqual(result.backend, "sysfs_charge_type")


if __name__ == "__main__":
    unittest.main()
