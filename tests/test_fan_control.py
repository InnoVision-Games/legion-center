import unittest

from py_modules import fan_control


def profile(**overrides):
    result = {str(temperature): temperature // 10 for temperature in range(10, 101, 10)}
    result["fullFanSpeedEnabled"] = False
    result.update(overrides)
    return result


class FanControlTests(unittest.TestCase):
    def test_profile_is_ordered_by_temperature_not_mapping_order(self):
        reversed_profile = dict(reversed(tuple(profile().items())))
        full_speed, curve = fan_control.parse_fan_profile(reversed_profile)
        self.assertFalse(full_speed)
        self.assertEqual(curve, tuple(range(1, 11)))

    def test_profile_rejects_missing_non_integer_and_out_of_range_values(self):
        missing = profile()
        del missing["50"]
        with self.assertRaises(ValueError):
            fan_control.parse_fan_profile(missing)
        with self.assertRaises(ValueError):
            fan_control.parse_fan_profile(profile(**{"50": True}))
        with self.assertRaises(ValueError):
            fan_control.parse_fan_profile(profile(**{"50": 116}))

    def test_curve_application_clears_full_speed_before_setting_curve(self):
        calls = []
        result = fan_control.apply_fan_profile(
            profile(),
            lambda enabled: calls.append(("full", enabled)) or True,
            lambda curve: calls.append(("curve", tuple(curve))) or True,
            sleeper=lambda seconds: calls.append(("sleep", seconds)),
        )
        self.assertTrue(result)
        self.assertEqual(
            calls,
            [
                ("full", False),
                ("sleep", 0.5),
                ("curve", tuple(range(1, 11))),
            ],
        )

    def test_full_speed_profile_does_not_write_curve(self):
        calls = []
        result = fan_control.apply_fan_profile(
            profile(fullFanSpeedEnabled=True),
            lambda enabled: calls.append(("full", enabled)) or True,
            lambda _curve: self.fail("curve should not be written"),
        )
        self.assertTrue(result)
        self.assertEqual(calls, [("full", True)])

    def test_restore_always_disables_full_speed_before_reset(self):
        calls = []
        result = fan_control.restore_firmware_fan_control(
            lambda enabled: calls.append(("full", enabled)) or True,
            lambda mode: calls.append(("mode", mode)) or True,
            True,
            sleeper=lambda seconds: calls.append(("sleep", seconds)),
        )
        self.assertTrue(result)
        self.assertEqual(
            calls,
            [
                ("full", False),
                ("mode", "performance"),
                ("sleep", 0.5),
                ("mode", "custom"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
