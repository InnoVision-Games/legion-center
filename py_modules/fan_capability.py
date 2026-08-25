"""Capability detection for the firmware fan-control backend."""

import os
from pathlib import Path
import platform
import subprocess
from typing import Callable


DEFAULT_ACPI_CALL_PATH = Path("/proc/acpi/call")


def _child_env():
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ""
    return env


def ensure_acpi_call_available(
    proc_path: Path = DEFAULT_ACPI_CALL_PATH,
    runner: Callable = subprocess.run,
) -> bool:
    """Load ``acpi_call`` when needed and verify that its proc file exists."""
    if proc_path.is_file():
        return True

    try:
        result = runner(
            ["modprobe", "acpi_call"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_child_env(),
            check=False,
        )
    except OSError:
        return False

    return result.returncode == 0 and proc_path.is_file()


def dkms_installed_for_running_kernel(
    runner: Callable = subprocess.run,
    kernel_release: str = None,
) -> bool:
    """Return whether DKMS reports acpi_call installed for this kernel."""
    release = kernel_release or platform.release()
    try:
        result = runner(
            ["dkms", "status", "-m", "acpi_call", "-k", release],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_child_env(),
            check=False,
        )
    except OSError:
        return False

    return result.returncode == 0 and "installed" in (result.stdout or "")
