# Legion Go controller HID command builder.
#
# The Legion Go's back buttons, touchpad, gyro remap and vibration settings
# are controlled through vendor-defined HID feature reports rather than any
# documented public API. The underlying protocol facts used below (vendor
# ID, usage page, report layout, command opcodes) originate from community
# reverse-engineering of the Legion Go firmware -- credited in this
# project's README to antheas's HID protocol documentation
# (https://github.com/antheas/hwinfo/tree/master/devices/legion_go, now
# continued under https://github.com/hhd-dev/hwinfo) and to corando98's
# work turning that into working backend calls. Those are hardware/protocol
# facts, not anyone's copyrightable expression, so they're free to reuse;
# the code below is a fresh implementation of that protocol, not a copy of
# any other project's source file.
#
# Device I/O goes through the `hid` package from PyPI (the pyhidapi
# bindings by Austin Morton, MIT licensed:
# https://github.com/apmorton/pyhidapi), declared as a normal dependency in
# requirements.txt rather than vendored into this repo.

import decky
import hid

# Lenovo's USB vendor ID.
VENDOR_ID = 0x17EF

# Legion Go controller USB product IDs. Lenovo has shipped more than one
# product ID across firmware revisions; both are matched below.
CONTROLLER_PRODUCT_IDS = (
    0x6180,  # firmwares released before 2025
    0x61E0,  # firmwares released 2025 and later
)

# Vendor-defined HID usage page the config interface exposes.
CONFIG_USAGE_PAGE = 0xFFA0

REPORT_SIZE = 64
REPORT_PAD_BYTE = 0xCD


def _matches_controller(product_id: int) -> bool:
    return any(product_id & 0xFFF0 == pid for pid in CONTROLLER_PRODUCT_IDS)


def _find_config_device():
    """Locate the Legion Go's vendor-defined HID config interface."""
    try:
        for dev in hid.enumerate(VENDOR_ID):
            if dev["usage_page"] == CONFIG_USAGE_PAGE and _matches_controller(dev["product_id"]):
                return dev
    except Exception as e:
        decky.logger.error(f"legion_configurator: error enumerating HID devices: {e}")
        return None

    decky.logger.error("legion_configurator: Legion Go config HID interface not found.")
    return None


def _pad_report(payload_bytes):
    if len(payload_bytes) > REPORT_SIZE:
        raise ValueError(f"HID report payload too long: {len(payload_bytes)} > {REPORT_SIZE}")
    return payload_bytes + bytes([REPORT_PAD_BYTE] * (REPORT_SIZE - len(payload_bytes)))


def send_command(command: bytes):
    """Write a fully-built 64-byte feature report to the config interface."""
    assert len(command) == REPORT_SIZE, "HID command must be exactly 64 bytes"

    dev_info = _find_config_device()
    if not dev_info:
        return

    try:
        with hid.Device(path=dev_info["path"]) as device:
            device.write(command)
    except IOError as e:
        decky.logger.error(f"legion_configurator: error writing to HID device: {e}")


# --- Command builders -------------------------------------------------
#
# Every command shares the same shape: [report id, length, opcode, ...
# opcode-specific args, 0x01 terminator], padded to 64 bytes with 0xCD.

def create_touchpad_command(enable: bool) -> bytes:
    """Enable or disable the right controller's touchpad."""
    payload = bytes([
        0x05, 0x06,             # report id, length
        0x6B,                   # opcode
        0x02,                   # sub-command
        0x04,                   # right controller
        0x01 if enable else 0x00,
        0x01,                   # terminator
    ])
    return _pad_report(payload)


def create_gyro_remap_command(gyro: int, joystick: int) -> bytes:
    """Assign gyro input to a stick (or disable it)."""
    payload = bytes([
        0x05, 0x08,
        0x6A,
        0x06, 0x01, 0x01,
        gyro, joystick,
        0x01,
    ])
    return _pad_report(payload)


def create_button_remap_command(controller: int, button: int, action: int) -> bytes:
    """
    Remap a back button to an action.

    controller: 0x03 (left) or 0x04 (right)
    button: 0x1c Y1, 0x1d Y2, 0x1e Y3, 0x21 M2, 0x22 M3
    action: e.g. 0x00 disabled, 0x03-0x0f stick/dpad directions,
            0x12-0x19 face buttons/bumpers/triggers, 0x23 view, 0x24 menu
    """
    payload = bytes([
        0x05, 0x07,
        0x6C,
        0x02, controller, button, action,
        0x01,
    ])
    return _pad_report(payload)


def create_vibration_command(controller: int, vibration_level: int) -> bytes:
    """
    Set controller vibration strength.

    vibration_level: 0x00 off, 0x01 weak, 0x02 medium, 0x03 strong
    """
    payload = bytes([
        0x05, 0x06,
        0x67,
        0x02,
        controller, vibration_level,
        0x01,
    ])
    return _pad_report(payload)


def create_fps_remap_command(controller: int, profile: int, button: int, action: int) -> bytes:
    """Remap a button within one of the four FPS-mode profiles."""
    payload = bytes([
        0x05, 0x08,
        0x6C,
        0x04,
        controller, profile, button, action,
        0x01,
    ])
    return _pad_report(payload)
