import tempfile
import unittest
from pathlib import Path

from py_modules import fan_telemetry


class FanTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.hwmon = self.root / "hwmon"
        self.thermal = self.root / "thermal"
        self.hwmon.mkdir()
        self.thermal.mkdir()

    def tearDown(self):
        self.temp_directory.cleanup()

    def add_hwmon(self, index, name, values):
        device = self.hwmon / f"hwmon{index}"
        device.mkdir()
        (device / "name").write_text(name, encoding="ascii")
        for filename, value in values.items():
            (device / filename).write_text(str(value), encoding="ascii")
        return device

    def test_prefers_k10_tctl(self):
        self.add_hwmon(0, "amdgpu", {"temp1_input": 61000, "temp1_label": "edge"})
        self.add_hwmon(1, "k10temp", {"temp1_input": 72000, "temp1_label": "Tctl"})

        result = fan_telemetry.get_fan_telemetry(
            self.hwmon,
            self.thermal,
            clock=lambda: 123.5,
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["temperatureC"], 72.0)
        self.assertEqual(result["temperatureLabel"], "Tctl")
        self.assertEqual(result["sampledAt"], 123500)

    def test_uses_thermal_zone_when_hwmon_temperature_is_unavailable(self):
        zone = self.thermal / "thermal_zone0"
        zone.mkdir()
        (zone / "type").write_text("x86_pkg_temp", encoding="ascii")
        (zone / "temp").write_text("65500", encoding="ascii")

        result = fan_telemetry.get_fan_telemetry(self.hwmon, self.thermal)

        self.assertEqual(result["temperatureC"], 65.5)
        self.assertEqual(result["temperatureSource"], "thermal_zone")

    def test_ignores_malformed_and_implausible_sensor_values(self):
        self.add_hwmon(0, "broken", {
            "temp1_input": "hot",
            "temp2_input": 999000,
        })

        result = fan_telemetry.get_fan_telemetry(self.hwmon, self.thermal)

        self.assertFalse(result["available"])
        self.assertIsNone(result["temperatureC"])


if __name__ == "__main__":
    unittest.main()
