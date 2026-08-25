"""Battery charge-limit backends for Lenovo handhelds.

Prefer the kernel's power-supply interface when it exposes the Lenovo WMI
``Standard`` and ``Long_Life`` charge types. The legacy ACPI backend remains
available as a fallback for kernels without the native interface.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Callable, Optional, Tuple


STANDARD = "Standard"
LONG_LIFE = "Long_Life"
DEFAULT_POWER_SUPPLY_ROOT = Path("/sys/class/power_supply")


LegacyGetter = Callable[[], Optional[int]]
LegacySetter = Callable[[bool], bool]
SysfsWriter = Callable[[Path, str], None]


@dataclass(frozen=True)
class ChargeLimitStatus:
    supported: bool
    enabled: Optional[bool] = None
    backend: Optional[str] = None
    path: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


def parse_charge_types(raw_value: str) -> Tuple[Tuple[str, ...], str]:
    """Return the advertised charge types and the bracketed active type."""
    active_values = re.findall(r"\[([^\]]+)\]", raw_value)
    if len(active_values) != 1:
        raise ValueError("charge_types must contain exactly one active value")

    values = tuple(re.sub(r"[\[\]]", "", raw_value).split())
    if not values:
        raise ValueError("charge_types did not advertise any values")

    return values, active_values[0]


def _read_charge_types(path: Path) -> Tuple[Tuple[str, ...], str]:
    return parse_charge_types(path.read_text(encoding="ascii").strip())


def find_charge_types_path(
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
) -> Optional[Path]:
    """Find a battery interface supporting both normal and long-life modes."""
    try:
        candidates = sorted(power_supply_root.glob("*/charge_types"))
    except OSError:
        return None

    for path in candidates:
        try:
            values, _active = _read_charge_types(path)
        except (OSError, UnicodeError, ValueError):
            continue

        if STANDARD in values and LONG_LIFE in values:
            return path

    return None


def _sysfs_status(
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
) -> ChargeLimitStatus:
    path = find_charge_types_path(power_supply_root)
    if path is None:
        return ChargeLimitStatus(
            supported=False,
            success=False,
            error="No power-supply charge_types interface supports Standard and Long_Life",
        )

    try:
        _values, active = _read_charge_types(path)
    except (OSError, UnicodeError, ValueError) as error:
        return ChargeLimitStatus(
            supported=False,
            path=str(path),
            success=False,
            error=f"Could not read {path}: {error}",
        )

    if active not in (STANDARD, LONG_LIFE):
        return ChargeLimitStatus(
            supported=False,
            path=str(path),
            success=False,
            error=f"Unsupported active charge type: {active}",
        )

    return ChargeLimitStatus(
        supported=True,
        enabled=active == LONG_LIFE,
        backend="sysfs",
        path=str(path),
    )


def _legacy_status(legacy_get: Optional[LegacyGetter]) -> ChargeLimitStatus:
    if legacy_get is None:
        return ChargeLimitStatus(
            supported=False,
            success=False,
            error="Neither native sysfs nor legacy ACPI charge limiting is available",
        )

    try:
        value = legacy_get()
    except Exception as error:
        return ChargeLimitStatus(
            supported=False,
            success=False,
            error=f"Legacy ACPI charge-limit query failed: {error}",
        )

    if value not in (0, 1, False, True):
        return ChargeLimitStatus(
            supported=False,
            success=False,
            error=f"Legacy ACPI returned an unexpected charge-limit value: {value!r}",
        )

    return ChargeLimitStatus(
        supported=True,
        enabled=bool(value),
        backend="acpi_call",
    )


def get_charge_limit_status(
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
    legacy_get: Optional[LegacyGetter] = None,
) -> ChargeLimitStatus:
    status = _sysfs_status(power_supply_root)
    if status.supported:
        return status
    return _legacy_status(legacy_get)


def _write_sysfs_value(path: Path, value: str) -> None:
    with path.open("w", encoding="ascii") as charge_types:
        charge_types.write(f"{value}\n")


def set_charge_limit(
    enabled: bool,
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
    legacy_get: Optional[LegacyGetter] = None,
    legacy_set: Optional[LegacySetter] = None,
    sysfs_writer: SysfsWriter = _write_sysfs_value,
) -> ChargeLimitStatus:
    """Set long-life mode and verify the hardware state after the write."""
    current = get_charge_limit_status(power_supply_root, legacy_get)
    if not current.supported:
        return current
    if current.enabled == enabled:
        return current

    if current.backend == "sysfs":
        assert current.path is not None
        path = Path(current.path)
        target = LONG_LIFE if enabled else STANDARD
        try:
            sysfs_writer(path, target)
        except (OSError, UnicodeError) as error:
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                backend="sysfs",
                path=current.path,
                success=False,
                error=f"Could not write {target} to {path}: {error}",
            )
    elif current.backend == "acpi_call":
        if legacy_set is None:
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                backend="acpi_call",
                success=False,
                error="Legacy ACPI charge-limit setter is unavailable",
            )
        try:
            if not legacy_set(enabled):
                return ChargeLimitStatus(
                    supported=True,
                    enabled=current.enabled,
                    backend="acpi_call",
                    success=False,
                    error="Legacy ACPI charge-limit write failed",
                )
        except Exception as error:
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                backend="acpi_call",
                success=False,
                error=f"Legacy ACPI charge-limit write failed: {error}",
            )

    verified = get_charge_limit_status(power_supply_root, legacy_get)
    if not verified.supported or verified.enabled != enabled:
        return ChargeLimitStatus(
            supported=current.supported,
            enabled=verified.enabled,
            backend=current.backend,
            path=current.path,
            success=False,
            error="Charge-limit read-back did not match the requested state",
        )

    return verified
