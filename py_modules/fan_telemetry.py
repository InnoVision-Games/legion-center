"""Read-only temperature telemetry through Linux hwmon."""

from pathlib import Path
import re
import time
from typing import Optional


DEFAULT_HWMON_ROOT = Path("/sys/class/hwmon")
DEFAULT_THERMAL_ROOT = Path("/sys/class/thermal")
TEMP_INPUT_PATTERN = re.compile(r"^temp(\d+)_input$")


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return None


def _read_int(path: Path) -> Optional[int]:
    raw = _read_text(path)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _temperature_priority(name: str, label: str, local_gpu: bool) -> Optional[int]:
    normalized_name = name.casefold()
    normalized_label = label.casefold()
    if normalized_name == "k10temp" and "tctl" in normalized_label:
        return 0
    if normalized_name == "k10temp":
        return 1
    if normalized_name == "amdgpu" and local_gpu and "edge" in normalized_label:
        return 2
    if normalized_name == "amdgpu" and local_gpu:
        return 3
    if any(token in normalized_label for token in ("tctl", "package", "cpu")):
        return 4
    if normalized_name in ("coretemp", "zenpower"):
        return 5
    return None


def _read_hwmon_temperature(hwmon_root: Path):
    candidates = []
    try:
        devices = sorted(hwmon_root.glob("hwmon*"))
    except OSError:
        return None

    for device in devices:
        name = _read_text(device / "name") or device.name
        local_gpu = (device / "device" / "local_cpus").exists() or (
            device / "device" / "local_cpulist"
        ).exists()
        try:
            inputs = sorted(device.glob("temp*_input"))
        except OSError:
            continue
        for input_path in inputs:
            match = TEMP_INPUT_PATTERN.match(input_path.name)
            if match is None:
                continue
            raw = _read_int(input_path)
            if raw is None:
                continue
            value = raw / 1000.0
            if not -40 <= value <= 150:
                continue
            label = _read_text(device / f"temp{match.group(1)}_label") or name
            priority = _temperature_priority(name, label, local_gpu)
            if priority is None:
                continue
            candidates.append((priority, -value, value, label, name))

    if not candidates:
        return None
    _priority, _negative_value, value, label, source = min(candidates)
    return {
        "temperatureC": round(value, 1),
        "temperatureLabel": label,
        "temperatureSource": source,
    }


def _read_thermal_zone_temperature(thermal_root: Path):
    candidates = []
    try:
        zones = sorted(thermal_root.glob("thermal_zone*"))
    except OSError:
        return None
    for zone in zones:
        raw = _read_int(zone / "temp")
        if raw is None:
            continue
        value = raw / 1000.0
        if not -40 <= value <= 150:
            continue
        label = _read_text(zone / "type") or zone.name
        normalized = label.casefold()
        priority = 0 if any(token in normalized for token in ("cpu", "x86_pkg", "k10")) else 5
        candidates.append((priority, -value, value, label))
    if not candidates:
        return None
    _priority, _negative_value, value, label = min(candidates)
    return {
        "temperatureC": round(value, 1),
        "temperatureLabel": label,
        "temperatureSource": "thermal_zone",
    }


def get_fan_telemetry(
    hwmon_root: Path = DEFAULT_HWMON_ROOT,
    thermal_root: Path = DEFAULT_THERMAL_ROOT,
    clock=time.time,
):
    """Return the best available system temperature."""
    temperature = _read_hwmon_temperature(hwmon_root)
    if temperature is None:
        temperature = _read_thermal_zone_temperature(thermal_root)
    return {
        "available": temperature is not None,
        "temperatureC": temperature["temperatureC"] if temperature else None,
        "temperatureLabel": temperature["temperatureLabel"] if temperature else None,
        "temperatureSource": temperature["temperatureSource"] if temperature else None,
        "sampledAt": int(clock() * 1000),
    }
