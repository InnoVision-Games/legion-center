"""Validated JSON import/export helpers for Legion Center fan profiles."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Mapping

try:
    import fan_control
except ModuleNotFoundError:  # Repository unit tests import through py_modules.
    from . import fan_control


SCHEMA_VERSION = 1
MAX_IMPORT_BYTES = 1024 * 1024
MAX_PROFILE_COUNT = 512
PROFILE_FILENAME_PREFIX = "legion-center-fan-profiles"


def normalize_fan_profiles(profiles: Mapping):
    if not isinstance(profiles, Mapping):
        raise ValueError("Fan profiles must be a JSON object")
    if len(profiles) > MAX_PROFILE_COUNT:
        raise ValueError(f"Fan profile file contains more than {MAX_PROFILE_COUNT} profiles")

    normalized = {}
    for profile_id, profile in profiles.items():
        if not isinstance(profile_id, str) or not profile_id or len(profile_id) > 128:
            raise ValueError("Every fan profile needs a non-empty ID up to 128 characters")
        if any(ord(character) < 32 for character in profile_id):
            raise ValueError(f"Fan profile ID contains control characters: {profile_id!r}")
        full_speed, curve = fan_control.parse_fan_profile(profile)
        normalized[profile_id] = {
            **dict(zip(fan_control.FAN_TEMPERATURE_POINTS, curve)),
            "fullFanSpeedEnabled": full_speed,
        }
    if "default" not in normalized:
        raise ValueError("Fan profile file must contain a default profile")
    return normalized


def make_profile_bundle(profiles: Mapping, plugin_version: str):
    return {
        "schemaVersion": SCHEMA_VERSION,
        "plugin": "Legion Center",
        "pluginVersion": plugin_version,
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "fanProfiles": normalize_fan_profiles(profiles),
    }


def load_profile_bundle(path):
    source = Path(path)
    if source.suffix.casefold() != ".json":
        raise ValueError("Fan profile imports must be JSON files")
    try:
        size = source.stat().st_size
    except OSError as error:
        raise ValueError(f"Could not access fan profile file: {error}") from error
    if size > MAX_IMPORT_BYTES:
        raise ValueError("Fan profile file is larger than 1 MiB")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read fan profile JSON: {error}") from error
    if not isinstance(payload, dict) or payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported fan profile schema (expected version {SCHEMA_VERSION})")
    return normalize_fan_profiles(payload.get("fanProfiles"))


def _match_directory_owner(path: Path, directory: Path):
    try:
        owner = directory.stat()
        os.chown(path, owner.st_uid, owner.st_gid)
    except OSError:
        # Non-root development/test environments cannot always chown. The
        # file is still valid and readable by the process that created it.
        pass


def export_profile_bundle(profiles: Mapping, directory, plugin_version: str):
    destination = Path(directory)
    if not destination.is_dir():
        raise ValueError("Choose an existing folder for the profile export")
    bundle = make_profile_bundle(profiles, plugin_version)
    body = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for suffix in range(100):
        qualifier = "" if suffix == 0 else f"-{suffix}"
        path = destination / f"{PROFILE_FILENAME_PREFIX}-{timestamp}{qualifier}.json"
        try:
            with path.open("x", encoding="utf-8") as export_file:
                export_file.write(body)
            _match_directory_owner(path, destination)
            return path
        except FileExistsError:
            continue
        except OSError as error:
            raise ValueError(f"Could not export fan profiles: {error}") from error
    raise ValueError("Could not choose a unique fan profile export filename")


def write_import_backup(profiles: Mapping, directory, plugin_version: str):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{PROFILE_FILENAME_PREFIX}-before-last-import.json"
    temporary = destination / f".{path.name}.tmp"
    body = json.dumps(make_profile_bundle(profiles, plugin_version), indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(body, encoding="utf-8")
        os.replace(temporary, path)
        _match_directory_owner(path, destination)
        return path
    except OSError as error:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise ValueError(f"Could not back up existing fan profiles: {error}") from error
