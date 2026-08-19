# Lenovo Legion Go firmware control via ACPI WMI methods.
#
# The Legion Go's BIOS exposes fan curve, TDP mode, charge limit and power
# LED control through a handful of WMI methods under \_SB.GZFD (the same
# interface Lenovo's own "Legion Space" Windows app uses), invoked here via
# the kernel's /proc/acpi/call interface (requires the `acpi_call` module).
#
# The specific WMI method names and byte layouts below are hardware/
# firmware facts, not anyone's copyrightable code -- they were originally
# documented publicly by the hhd-dev/adjustor project
# (https://github.com/hhd-dev/adjustor/blob/072411bff14bb5996b0fe00da06f36d17f31a389/src/adjustor/core/lenovo.py),
# itself GPLv3-licensed. Because copyright protects expression, not facts,
# this file reuses only the underlying protocol facts (method names, opcode
# values, byte offsets) and implements the calling code independently
# rather than copying adjustor's source.

from time import sleep
from typing import Sequence

import decky

ACPI_CALL_PATH = "/proc/acpi/call"

# WMI method paths exposed by the Legion Go BIOS.
WMI_TDP_FAN = r"\_SB.GZFD.WMAA"
WMI_FEATURE = r"\_SB.GZFD.WMAE"
WMI_FAN_CURVE = r"\_SB.GZFD.WMAB"
WMI_POWER_LIGHT = r"\_SB.GZFD.WMAF"

FEATURE_ID_FULL_FAN_SPEED = 0x04020000
FEATURE_ID_CHARGE_LIMIT = 0x03010001

TDP_MODE_BYTES = {
    "quiet": 0x01,
    "balanced": 0x02,
    "performance": 0x03,
    "custom": 0xFF,
}
TDP_MODE_NAMES = {v: k for k, v in TDP_MODE_BYTES.items()}


def _acpi_call(method: str, args: Sequence, risky: bool = True) -> bool:
    """Write a raw ACPI method invocation to /proc/acpi/call."""
    cmd = method
    for arg in args:
        cmd += f" 0x{arg:02x}" if isinstance(arg, int) else f" b{arg.hex()}"

    decky.logger.info(f"legion_space: ACPI call: '{cmd}'")
    try:
        with open(ACPI_CALL_PATH, "wb") as f:
            f.write(cmd.encode())
        return True
    except Exception as e:
        decky.logger.error(f"legion_space: ACPI call failed: {e}")
        return False


def _acpi_read():
    """Read back the result of the last ACPI call."""
    with open(ACPI_CALL_PATH, "rb") as f:
        raw = f.read().decode().strip()

    if raw == "not called\0":
        return None
    if raw.startswith("0x") and raw.endswith("\0"):
        return int(raw[:-1], 16)
    if raw.startswith("{") and raw.endswith("}\0"):
        return bytes(int(b, 16) for b in raw[1:-2].split(", "))

    raise ValueError(f"legion_space: unsupported /proc/acpi/call return value: {raw!r}")


def _get_feature(feature_id: int):
    ok = _acpi_call(
        WMI_FEATURE,
        [0, 0x11, int.to_bytes(feature_id, length=4, byteorder="little", signed=False)],
        risky=False,
    )
    return _acpi_read() if ok else None


def _set_feature(feature_id: int, value: int) -> bool:
    payload = int.to_bytes(feature_id, length=4, byteorder="little", signed=False) + \
        int.to_bytes(value, length=4, byteorder="little", signed=False)
    return _acpi_call(WMI_FEATURE, [0, 0x12, payload])


# --- TDP mode / fan speed ----------------------------------------------

def set_tdp_mode(mode: str) -> bool:
    decky.logger.info(f"legion_space: setting TDP mode to '{mode}'")
    mode_byte = TDP_MODE_BYTES.get(mode)
    if mode_byte is None:
        decky.logger.error(f"legion_space: unknown TDP mode '{mode}'")
        return False
    return _acpi_call(WMI_TDP_FAN, [0, 0x2C, mode_byte])


def get_tdp_mode():
    if not _acpi_call(WMI_TDP_FAN, [0, 0x2D, 0], risky=False):
        decky.logger.error("legion_space: failed retrieving TDP mode")
        return None

    value = _acpi_read()
    mode = TDP_MODE_NAMES.get(value)
    if mode is None:
        decky.logger.error(f"legion_space: unrecognized TDP mode value '{value}'")
    return mode


def set_full_fan_speed(enable: bool) -> bool:
    return _set_feature(FEATURE_ID_FULL_FAN_SPEED, int(enable))


def set_fan_curve(points: Sequence[int]) -> bool:
    decky.logger.info(f"legion_space: setting fan curve to {list(points)}")
    if len(points) != 10:
        decky.logger.error(f"legion_space: fan curve needs 10 points, got {len(points)}")
        return False
    if any(type(p) is not int for p in points):
        decky.logger.error("legion_space: fan curve has a non-integer point, refusing to set")
        return False
    if any(p < 0 or p > 115 for p in points):
        decky.logger.error("legion_space: fan curve points must be between 0 and 115")
        return False

    # Byte layout: 10 duty-cycle points, followed by 10 fixed temperature
    # breakpoints (10, 20, 30 ... 100 C) that the BIOS pairs them against.
    temperature_breakpoints = [0x0A, 0x14, 0x1E, 0x28, 0x32, 0x3C, 0x46, 0x50, 0x5A, 0x64]

    payload = bytes([0x00, 0x00, 0x0A, 0x00, 0x00, 0x00])
    for point in points:
        payload += bytes([point, 0x00])
    payload += bytes([0x00, 0x0A, 0x00, 0x00, 0x00])
    for temp in temperature_breakpoints:
        payload += bytes([temp, 0x00])
    payload += bytes([0x00])

    return _acpi_call(WMI_FAN_CURVE, [0, 0x06, payload])


def set_active_fan_curve(points: Sequence[int]) -> bool:
    if get_tdp_mode() != "custom":
        if not set_tdp_mode("custom"):
            decky.logger.error("legion_space: failed to switch to custom TDP mode")
            return False
    sleep(0.3)
    return set_fan_curve(points)


# --- Charge limit --------------------------------------------------------

def get_charge_limit():
    decky.logger.info("legion_space: retrieving charge limit state")
    return _get_feature(FEATURE_ID_CHARGE_LIMIT)


def set_charge_limit(enabled: bool) -> bool:
    current = get_charge_limit()

    if enabled and current == 0:
        return _acpi_call(WMI_FEATURE, [0, 0x12, bytes([0x01, 0x00, 0x01, 0x03, 0x01, 0x00, 0x00, 0x00])])
    if not enabled and current == 1:
        return _acpi_call(WMI_FEATURE, [0, 0x12, bytes([0x01, 0x00, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00])])

    return True  # already in the desired state


# --- Power LED -------------------------------------------------------------

def get_power_light():
    decky.logger.info("legion_space: getting power light state")
    if not _acpi_call(WMI_POWER_LIGHT, [0, 0x01, 0x03], risky=False):
        return None
    value = _acpi_read()
    if isinstance(value, bytes) and len(value) == 2:
        return bool(value[0])
    return None


def set_power_light(enabled: bool):
    if get_power_light() == enabled:
        return True
    decky.logger.info(f"legion_space: setting power light to {enabled}")
    return _acpi_call(WMI_POWER_LIGHT, [0, 0x02, bytes([0x03, int(enabled), 0x00])])
