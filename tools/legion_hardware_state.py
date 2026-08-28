#!/usr/bin/env python3
"""Read Legion Go firmware state for on-device acceptance tests."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace


class Logger:
    def info(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


sys.modules.setdefault("decky", SimpleNamespace(logger=Logger()))

import legion_space
import fan_telemetry


def main():
    charge_types = Path("/sys/class/power_supply/BATT/charge_types")
    state = {
        "charge_types": (
            charge_types.read_text(encoding="ascii").strip()
            if charge_types.is_file()
            else None
        ),
        "full_fan_speed": legion_space._get_feature(
            legion_space.FEATURE_ID_FULL_FAN_SPEED
        ),
        "tdp_mode": legion_space.get_tdp_mode(),
        "fan_telemetry": fan_telemetry.get_fan_telemetry(),
    }
    print(json.dumps(state, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
