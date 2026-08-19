"""Fan-profile validation and application helpers."""

from time import sleep
from typing import Callable, Mapping, Sequence, Tuple


FAN_TEMPERATURE_POINTS = tuple(str(value) for value in range(10, 101, 10))
MIN_FAN_PERCENT = 0
MAX_FAN_PERCENT = 115


def parse_fan_profile(profile: Mapping) -> Tuple[bool, Sequence[int]]:
    """Return full-speed state and an ordered, validated ten-point curve."""
    if not isinstance(profile, Mapping):
        raise ValueError("Fan profile must be a mapping")

    curve = []
    for temperature in FAN_TEMPERATURE_POINTS:
        value = profile.get(temperature)
        if type(value) is not int:
            raise ValueError(f"Fan value at {temperature} C must be an integer")
        if not MIN_FAN_PERCENT <= value <= MAX_FAN_PERCENT:
            raise ValueError(
                f"Fan value at {temperature} C must be between "
                f"{MIN_FAN_PERCENT} and {MAX_FAN_PERCENT}"
            )
        curve.append(value)

    return bool(profile.get("fullFanSpeedEnabled", False)), tuple(curve)


def apply_fan_profile(
    profile: Mapping,
    set_full_fan_speed: Callable[[bool], bool],
    set_active_fan_curve: Callable[[Sequence[int]], bool],
    sleeper: Callable[[float], None] = sleep,
) -> bool:
    """Apply a validated profile, always clearing full-speed mode first."""
    full_speed_enabled, curve = parse_fan_profile(profile)

    if full_speed_enabled:
        return bool(set_full_fan_speed(True))

    if not set_full_fan_speed(False):
        return False
    sleeper(0.5)
    return bool(set_active_fan_curve(curve))


def restore_firmware_fan_control(
    set_full_fan_speed: Callable[[bool], bool],
    set_tdp_mode: Callable[[str], bool],
    reset_curve: bool,
    sleeper: Callable[[float], None] = sleep,
) -> bool:
    """Disable full-speed mode and optionally reset the custom firmware curve."""
    if not set_full_fan_speed(False):
        return False
    if not reset_curve:
        return True
    if not set_tdp_mode("performance"):
        return False
    sleeper(0.5)
    return bool(set_tdp_mode("custom"))
