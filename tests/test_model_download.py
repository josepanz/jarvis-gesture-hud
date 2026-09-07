"""H-03: tests/test_model_download.py (nuevo) - descarga atomica y
verificada de modelos, con urllib.request.urlretrieve mockeado (nunca se
golpea la red de verdad en la suite)."""

import sys
import unittest
from email.message import Message
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.downloads import download_atomically  # noqa: E402

URL = "https://example.invalid/model.task"


def _headers(content_length=None):
    msg = Message()
    if content_length is not None:
        msg["Content-Length"] = str(content_length)
    return msg


class SuccessfulDownloadTests(unittest.TestCase):
    def test_leaves_only_the_final_file_no_part_left_behind(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "model.task"

            def fake_urlretrieve(url, filename):
                Path(filename).write_bytes(b"x" * 10)
                return filename, _headers(content_length=10)

            with patch("jarvis.downloads.urllib.request.urlretrieve", side_effect=fake_urlretrieve):
                result = download_atomically(URL, dest)

            self.assertEqual(result, dest)
            self.assertTrue(dest.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [dest])

    def test_no_content_length_header_still_succeeds(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "model.task"

            def fake_urlretrieve(url, filename):
                Path(filename).write_bytes(b"x" * 10)
                return filename, _headers(content_length=None)

            with patch("jarvis.downloads.urllib.request.urlretrieve", side_effect=fake_urlretrieve):
                download_atomically(URL, dest)

            self.assertTrue(dest.exists())


class InterruptedDownloadTests(unittest.TestCase):
    def test_exception_mid_download_leaves_no_file_with_the_final_name(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "model.task"

            def fake_urlretrieve(url, filename):
                Path(filename).write_bytes(b"partial")
                raise ConnectionError("wifi se corto")

            with patch("jarvis.downloads.urllib.request.urlretrieve", side_effect=fake_urlretrieve):
                with self.assertRaises(ConnectionError):
                    download_atomically(URL, dest)

            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])  # el .part tampoco queda


class SizeMismatchTests(unittest.TestCase):
    def test_size_inconsistent_with_content_length_is_rejected(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "model.task"

            def fake_urlretrieve(url, filename):
                Path(filename).write_bytes(b"x" * 5)  # menos de lo prometido
                return filename, _headers(content_length=10)

            with patch("jarvis.downloads.urllib.request.urlretrieve", side_effect=fake_urlretrieve):
                with self.assertRaises(RuntimeError):
                    download_atomically(URL, dest)

            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])


class AlreadyDownloadedTests(unittest.TestCase):
    def test_existing_final_file_is_not_downloaded_again(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "model.task"
            dest.write_bytes(b"ya estaba")

            with patch("jarvis.downloads.urllib.request.urlretrieve") as mock_urlretrieve:
                result = download_atomically(URL, dest)

            mock_urlretrieve.assert_not_called()
            self.assertEqual(result, dest)
            self.assertEqual(dest.read_bytes(), b"ya estaba")


if __name__ == "__main__":
    unittest.main()
