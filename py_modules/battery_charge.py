"""Battery charge-limit backends for Lenovo handhelds.

Prefer the kernel's standard percentage threshold when the hardware exposes
one. Lenovo's ``Standard``/``Long_Life`` charge types and the legacy ACPI
feature remain available as fixed 100%/80% fallbacks.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Callable, Optional, Tuple


STANDARD = "Standard"
LONG_LIFE = "Long_Life"
FIXED_LIMIT_PERCENT = 80
DEFAULT_LIMIT_PERCENT = 100
MIN_CONFIGURABLE_LIMIT_PERCENT = 50
MAX_CONFIGURABLE_LIMIT_PERCENT = 100
DEFAULT_POWER_SUPPLY_ROOT = Path("/sys/class/power_supply")


LegacyGetter = Callable[[], Optional[int]]
LegacySetter = Callable[[bool], bool]
SysfsWriter = Callable[[Path, str], None]


@dataclass(frozen=True)
class ChargeLimitStatus:
    supported: bool
    enabled: Optional[bool] = None
    limit: Optional[int] = None
    configurable: bool = False
    minimum: Optional[int] = None
    maximum: Optional[int] = None
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


def _read_threshold(path: Path) -> int:
    value = int(path.read_text(encoding="ascii").strip())
    if not 1 <= value <= 100:
        raise ValueError(f"charge threshold must be between 1 and 100, got {value}")
    return value


def find_charge_threshold_path(
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
) -> Optional[Path]:
    """Find a readable, writable standard percentage-based threshold."""
    try:
        candidates = sorted(
            power_supply_root.glob("*/charge_control_end_threshold")
        )
    except OSError:
        return None

    for path in candidates:
        try:
            _read_threshold(path)
            if (path.stat().st_mode & 0o222) == 0:
                continue
        except (OSError, UnicodeError, ValueError):
            continue
        return path

    return None


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


def _threshold_status(
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
) -> ChargeLimitStatus:
    path = find_charge_threshold_path(power_supply_root)
    if path is None:
        return ChargeLimitStatus(
            supported=False,
            success=False,
            error="No percentage-based charge threshold is available",
        )

    try:
        limit = _read_threshold(path)
    except (OSError, UnicodeError, ValueError) as error:
        return ChargeLimitStatus(
            supported=False,
            path=str(path),
            success=False,
            error=f"Could not read {path}: {error}",
        )

    return ChargeLimitStatus(
        supported=True,
        enabled=limit < DEFAULT_LIMIT_PERCENT,
        limit=limit,
        configurable=True,
        minimum=min(MIN_CONFIGURABLE_LIMIT_PERCENT, limit),
        maximum=MAX_CONFIGURABLE_LIMIT_PERCENT,
        backend="sysfs_threshold",
        path=str(path),
    )


def _charge_types_status(
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
        limit=(
            FIXED_LIMIT_PERCENT
            if active == LONG_LIFE
            else DEFAULT_LIMIT_PERCENT
        ),
        configurable=False,
        minimum=FIXED_LIMIT_PERCENT,
        maximum=DEFAULT_LIMIT_PERCENT,
        backend="sysfs_charge_type",
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
        limit=FIXED_LIMIT_PERCENT if bool(value) else DEFAULT_LIMIT_PERCENT,
        configurable=False,
        minimum=FIXED_LIMIT_PERCENT,
        maximum=DEFAULT_LIMIT_PERCENT,
        backend="acpi_call",
    )


def get_charge_limit_status(
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
    legacy_get: Optional[LegacyGetter] = None,
) -> ChargeLimitStatus:
    status = _threshold_status(power_supply_root)
    if status.supported:
        return status
    status = _charge_types_status(power_supply_root)
    if status.supported:
        return status
    return _legacy_status(legacy_get)


def _write_sysfs_value(path: Path, value: str) -> None:
    with path.open("w", encoding="ascii") as charge_types:
        charge_types.write(f"{value}\n")


def set_charge_limit(
    limit,
    power_supply_root: Path = DEFAULT_POWER_SUPPLY_ROOT,
    legacy_get: Optional[LegacyGetter] = None,
    legacy_set: Optional[LegacySetter] = None,
    sysfs_writer: SysfsWriter = _write_sysfs_value,
) -> ChargeLimitStatus:
    """Set a charge threshold and verify the hardware state after the write.

    Boolean inputs remain accepted for compatibility with v0.1.x callers:
    ``True`` selects the fixed 80% protection level and ``False`` restores
    normal 100% charging.
    """
    if isinstance(limit, bool):
        target_limit = FIXED_LIMIT_PERCENT if limit else DEFAULT_LIMIT_PERCENT
    elif type(limit) is int:
        target_limit = limit
    else:
        return ChargeLimitStatus(
            supported=False,
            success=False,
            error="Charge limit must be an integer percentage",
        )

    if not MIN_CONFIGURABLE_LIMIT_PERCENT <= target_limit <= DEFAULT_LIMIT_PERCENT:
        return ChargeLimitStatus(
            supported=False,
            success=False,
            error=(
                "Charge limit must be between "
                f"{MIN_CONFIGURABLE_LIMIT_PERCENT}% and {DEFAULT_LIMIT_PERCENT}%"
            ),
        )

    current = get_charge_limit_status(power_supply_root, legacy_get)
    if not current.supported:
        return current
    if current.limit == target_limit:
        return current

    if current.backend == "sysfs_threshold":
        assert current.path is not None
        path = Path(current.path)
        try:
            sysfs_writer(path, str(target_limit))
        except (OSError, UnicodeError) as error:
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                limit=current.limit,
                configurable=True,
                minimum=current.minimum,
                maximum=current.maximum,
                backend=current.backend,
                path=current.path,
                success=False,
                error=f"Could not write {target_limit}% to {path}: {error}",
            )
    elif current.backend == "sysfs_charge_type":
        if target_limit not in (FIXED_LIMIT_PERCENT, DEFAULT_LIMIT_PERCENT):
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                limit=current.limit,
                configurable=False,
                minimum=current.minimum,
                maximum=current.maximum,
                backend=current.backend,
                path=current.path,
                success=False,
                error=(
                    "This device firmware supports only the fixed 80% "
                    "battery-protection limit"
                ),
            )
        assert current.path is not None
        path = Path(current.path)
        target = (
            LONG_LIFE
            if target_limit == FIXED_LIMIT_PERCENT
            else STANDARD
        )
        try:
            sysfs_writer(path, target)
        except (OSError, UnicodeError) as error:
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                limit=current.limit,
                configurable=False,
                minimum=current.minimum,
                maximum=current.maximum,
                backend=current.backend,
                path=current.path,
                success=False,
                error=f"Could not write {target} to {path}: {error}",
            )
    elif current.backend == "acpi_call":
        if target_limit not in (FIXED_LIMIT_PERCENT, DEFAULT_LIMIT_PERCENT):
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                limit=current.limit,
                configurable=False,
                minimum=current.minimum,
                maximum=current.maximum,
                backend=current.backend,
                success=False,
                error=(
                    "The Legion Go firmware supports only the fixed 80% "
                    "battery-protection limit"
                ),
            )
        if legacy_set is None:
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                limit=current.limit,
                backend="acpi_call",
                success=False,
                error="Legacy ACPI charge-limit setter is unavailable",
            )
        try:
            if not legacy_set(target_limit == FIXED_LIMIT_PERCENT):
                return ChargeLimitStatus(
                    supported=True,
                    enabled=current.enabled,
                    limit=current.limit,
                    backend="acpi_call",
                    success=False,
                    error="Legacy ACPI charge-limit write failed",
                )
        except Exception as error:
            return ChargeLimitStatus(
                supported=True,
                enabled=current.enabled,
                limit=current.limit,
                backend="acpi_call",
                success=False,
                error=f"Legacy ACPI charge-limit write failed: {error}",
            )

    verified = get_charge_limit_status(power_supply_root, legacy_get)
    # The standard Linux ABI explicitly permits hardware to round a requested
    # percentage to its nearest supported value. The read-back is therefore
    # the source of truth for a configurable threshold.
    if current.backend == "sysfs_threshold" and verified.supported:
        return verified
    if not verified.supported or verified.limit != target_limit:
        return ChargeLimitStatus(
            supported=current.supported,
            enabled=verified.enabled,
            limit=verified.limit,
            configurable=current.configurable,
            minimum=current.minimum,
            maximum=current.maximum,
            backend=current.backend,
            path=current.path,
            success=False,
            error="Charge-limit read-back did not match the requested state",
        )

    return verified
