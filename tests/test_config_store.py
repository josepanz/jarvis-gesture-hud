"""Tests for TASK-074 (Fase 8): jarvis.core.config_store."""

import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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

    def test_recursion_error_during_parse_is_quarantined_like_corrupt_json(self):
        # H-02: JSON patologicamente anidado puede hacer que json.load()
        # lance RecursionError en vez de JSONDecodeError - antes no estaba
        # en la lista de excepciones que disparan la cuarentena.
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            path.write_text("{}", encoding="utf-8")
            with patch.object(json, "load", side_effect=RecursionError("maximum recursion depth exceeded")):
                result = config_store.load_bindings(path=path)
            self.assertEqual(result, {})
            self.assertFalse(path.exists())
            self.assertEqual(len(list(Path(tmp).glob("bindings.json.bak-*"))), 1)

    def test_memory_error_during_parse_is_quarantined_like_corrupt_json(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            path.write_text("{}", encoding="utf-8")
            with patch.object(json, "load", side_effect=MemoryError()):
                result = config_store.load_bindings(path=path)
            self.assertEqual(result, {})
            self.assertFalse(path.exists())
            self.assertEqual(len(list(Path(tmp).glob("bindings.json.bak-*"))), 1)


class AtomicWriteTests(unittest.TestCase):
    def test_save_does_not_leave_a_temp_file_behind(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            config_store.save_bindings({"a": 1}, path=path)
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_temp_file_name_is_unique_per_call(self):
        """H-23: dos instancias guardando a la vez no deben pisarse el
        temporal - antes era un nombre fijo (`bindings.json.tmp`)."""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            seen_tmp_paths = []
            original_replace = os.replace

            def spy_replace(src, dst):
                seen_tmp_paths.append(str(src))
                return original_replace(src, dst)

            with patch("jarvis.core.config_store.os.replace", side_effect=spy_replace):
                config_store.save_bindings({"a": 1}, path=path)
                config_store.save_bindings({"a": 2}, path=path)

            self.assertEqual(len(seen_tmp_paths), 2)
            self.assertNotEqual(seen_tmp_paths[0], seen_tmp_paths[1])

    def test_failed_write_cleans_up_its_own_temp_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bindings.json"
            with patch("jarvis.core.config_store.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    config_store.save_bindings({"a": 1}, path=path)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_save_creates_the_parent_directory_if_missing(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "dir" / "bindings.json"
            config_store.save_bindings({"a": 1}, path=path)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
