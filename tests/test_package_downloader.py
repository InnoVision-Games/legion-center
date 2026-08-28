import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from py_modules.common.lib.package_downloader import PackageDownloader


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.offset = 0
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size):
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class PackageDownloaderTests(unittest.TestCase):
    def test_download_streams_progress_and_reports_completion(self):
        payload = b"package-data"
        updates = []
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = PackageDownloader(temp_dir, progress=lambda *args: updates.append(args))
            with patch(
                "urllib.request.urlopen",
                return_value=FakeResponse(payload),
            ):
                path = downloader.download("https://example.test/kernel.pkg")

            self.assertEqual(Path(path).read_bytes(), payload)

        self.assertEqual(updates[0], (0, len(payload), "kernel.pkg"))
        self.assertEqual(updates[-1], (len(payload), len(payload), "kernel.pkg"))

    def test_cached_download_reports_complete_without_network(self):
        updates = []
        with tempfile.TemporaryDirectory() as temp_dir:
            cached = Path(temp_dir) / "kernel.pkg"
            cached.write_bytes(b"cached")
            downloader = PackageDownloader(temp_dir, progress=lambda *args: updates.append(args))
            with patch("urllib.request.urlopen") as urlopen:
                path = downloader.download(
                    "https://example.test/kernel.pkg",
                    "kernel.pkg",
                )

            urlopen.assert_not_called()
            self.assertEqual(path, cached)

        self.assertEqual(updates, [(6, 6, "kernel.pkg")])


if __name__ == "__main__":
    unittest.main()
