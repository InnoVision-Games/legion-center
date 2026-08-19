import sys
import types
import unittest
from unittest.mock import patch


class Logger:
    def info(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


sys.modules.setdefault("decky", types.SimpleNamespace(logger=Logger()))

from py_modules import legion_space


class LegionSpaceTests(unittest.TestCase):
    def test_curve_rejects_invalid_values_without_acpi_write(self):
        invalid_curves = [
            [10] * 9,
            [10] * 9 + [True],
            [10] * 9 + [116],
            [10] * 9 + [-1],
        ]
        with patch.object(legion_space, "_acpi_call") as acpi_call:
            for curve in invalid_curves:
                with self.subTest(curve=curve):
                    self.assertFalse(legion_space.set_fan_curve(curve))
            acpi_call.assert_not_called()

    def test_curve_builds_expected_firmware_payload(self):
        curve = list(range(5, 105, 10))
        with patch.object(legion_space, "_acpi_call", return_value=True) as acpi_call:
            self.assertTrue(legion_space.set_fan_curve(curve))
        method, args = acpi_call.call_args.args
        self.assertEqual(method, r"\_SB.GZFD.WMAB")
        self.assertEqual(args[:2], [0, 0x06])
        payload = args[2]
        self.assertEqual(tuple(payload[6:26:2]), tuple(curve))

    def test_active_curve_propagates_mode_failure(self):
        with patch.object(
            legion_space, "get_tdp_mode", return_value="performance"
        ), patch.object(
            legion_space, "set_tdp_mode", return_value=False
        ), patch.object(legion_space, "set_fan_curve") as set_curve:
            self.assertFalse(legion_space.set_active_fan_curve([10] * 10))
            set_curve.assert_not_called()

    def test_active_curve_returns_curve_result(self):
        with patch.object(
            legion_space, "get_tdp_mode", return_value="custom"
        ), patch.object(legion_space, "sleep"), patch.object(
            legion_space, "set_fan_curve", return_value=False
        ):
            self.assertFalse(legion_space.set_active_fan_curve([10] * 10))


if __name__ == "__main__":
    unittest.main()
