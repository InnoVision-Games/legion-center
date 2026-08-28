import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class PackageDownloader:
    def __init__(self, *_args, **_kwargs):
        pass


stub_versions = types.SimpleNamespace(
    get_kernel_headers_filename=lambda _version: "headers",
    get_kernel_modules_filename=lambda _version: "modules",
    get_os_version=lambda: {},
)
stub_downloader = types.SimpleNamespace(PackageDownloader=PackageDownloader)
sys.modules.setdefault("common.lib.dkms_supported_versions", stub_versions)
sys.modules.setdefault("common.lib.package_downloader", stub_downloader)

from py_modules.acpi_enabler.acpi_enabler import AcpiEnabler


class RecordingEnabler(AcpiEnabler):
    def __init__(self, installed=False, fail_install=False, progress_callback=None):
        self.verbose = False
        self.installed = installed
        self.fail_install = fail_install
        self._progress_callback = progress_callback
        self.calls = []
        self._build_work = None
        self._build_merged = None

    def _log(self, _message):
        pass

    def prep_steamos(self):
        self.calls.append("prep")

    def finalize_steamos(self):
        self.calls.append("finalize")

    def _acpi_call_installed(self, _kernel_release):
        return self.installed

    def download_kernel_packages(self):
        self.calls.append("download")
        return Path("modules"), Path("headers")

    def install_kernel_packages(self, _modules, _headers):
        self.calls.append("install-kernel")

    def install_acpi_call_module(self):
        self.calls.append("install-acpi")
        if self.fail_install:
            raise RuntimeError("build failed")
        self.installed = True

    def _teardown_build_overlay(self):
        self.calls.append("teardown")

    def _configure_selfheal_updates(self):
        self.calls.append("selfheal")

    def cleanup(self, _modules, _headers):
        self.calls.append("cleanup")


class AcpiEnablerTests(unittest.TestCase):
    def test_run_raises_on_required_command_failure(self):
        enabler = RecordingEnabler()
        failed = SimpleNamespace(returncode=9, stdout="", stderr="bad command")
        with patch("subprocess.run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "bad command"):
                enabler._run(["false"])

    def test_run_quiet_returns_expected_failure(self):
        enabler = RecordingEnabler()
        failed = SimpleNamespace(returncode=1, stdout="", stderr="expected")
        with patch("subprocess.run", return_value=failed):
            self.assertIs(enabler._run_quiet(["false"]), failed)

    def test_enable_skips_download_when_current_module_is_installed(self):
        enabler = RecordingEnabler(installed=True)
        with patch("pathlib.Path.is_file", return_value=True):
            enabler.enable()
        self.assertEqual(
            enabler.calls,
            [
                "prep",
                "install-acpi",
                "selfheal",
                "teardown",
                "cleanup",
                "finalize",
            ],
        )

    def test_enable_reports_monotonic_progress_through_selfheal(self):
        updates = []
        enabler = RecordingEnabler(
            installed=True,
            progress_callback=updates.append,
        )
        with patch("pathlib.Path.is_file", return_value=True):
            enabler.enable()

        self.assertEqual(updates[-1], {
            "percent": 100,
            "stage": "Complete",
            "detail": "Fan support is ready",
        })
        self.assertEqual(
            [update["percent"] for update in updates],
            sorted(update["percent"] for update in updates),
        )
        self.assertIn("Configuring self-heal", [u["stage"] for u in updates])

    def test_enable_always_cleans_up_and_restores_readonly_on_failure(self):
        enabler = RecordingEnabler(fail_install=True)
        with self.assertRaisesRegex(RuntimeError, "build failed"):
            enabler.enable()
        self.assertEqual(
            enabler.calls,
            [
                "prep",
                "download",
                "install-kernel",
                "install-acpi",
                "teardown",
                "cleanup",
                "finalize",
            ],
        )


if __name__ == "__main__":
    unittest.main()
