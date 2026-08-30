"""Tests for TASK-074 (Fase 8): jarvis.core.config_store."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core import config_store  # noqa: E402


class RoundTripTests(unittest.TestCase):
    def test_save_then_load_returns_the_same_data(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            data = {"schema_version": 1, "profiles": {"default": {"gesture_bindings": {"NARUTO_TORA": "SCREENSHOT"}}}}
            config_store.save_bindings(data, path=path)
            self.assertEqual(config_store.load_bindings(path=path), data)


class MissingFileTests(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "does_not_exist.json"
            self.assertEqual(config_store.load_bindings(path=path), {})


class CorruptFileTests(unittest.TestCase):
    def test_corrupt_file_is_preserved_aside_not_clobbered(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            path.write_text("{not valid json", encoding="utf-8")
            result = config_store.load_bindings(path=path)
            self.assertEqual(result, {})
            self.assertFalse(path.exists())  # se renombro, no se borro ni se sobreescribio
            backups = list(Path(tmp).glob("bindings.json.bak-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "{not valid json")

    def test_a_non_dict_json_value_is_treated_as_no_data(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            path.write_text("[1, 2, 3]", encoding="utf-8")
            self.assertEqual(config_store.load_bindings(path=path), {})


class AtomicWriteTests(unittest.TestCase):
    def test_save_does_not_leave_a_temp_file_behind(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            config_store.save_bindings({"a": 1}, path=path)
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_save_creates_the_parent_directory_if_missing(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "dir" / "bindings.json"
            config_store.save_bindings({"a": 1}, path=path)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
