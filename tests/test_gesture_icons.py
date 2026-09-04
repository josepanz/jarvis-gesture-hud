"""Tests for gesture_icons (TASK-058, Fase 3, spec.md #3.1-3.2)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.gesture_icons import ICON_SIZE, ICON_SPECS, ensure_icon, generate_all_icons  # noqa: E402


class EnsureIconTests(unittest.TestCase):
    def test_produces_a_valid_png_at_or_under_48x48(self):
        from PIL import Image

        path = ensure_icon("pinch_click")
        self.assertTrue(path.exists())
        self.assertEqual(path.suffix, ".png")
        with Image.open(path) as img:
            self.assertLessEqual(img.width, ICON_SIZE)
            self.assertLessEqual(img.height, ICON_SIZE)

    def test_second_call_does_not_regenerate(self):
        path = ensure_icon("scroll")
        first_mtime = path.stat().st_mtime_ns
        path_again = ensure_icon("scroll")
        self.assertEqual(path, path_again)
        self.assertEqual(path.stat().st_mtime_ns, first_mtime)


class GenerateAllIconsTests(unittest.TestCase):
    def test_generates_one_file_per_spec(self):
        paths = generate_all_icons()
        self.assertEqual(set(paths), set(ICON_SPECS))
        for path in paths.values():
            self.assertTrue(path.exists())

    def test_every_icon_is_structurally_distinct_from_every_other(self):
        paths = generate_all_icons()
        contents = {key: path.read_bytes() for key, path in paths.items()}
        self.assertEqual(len(set(contents.values())), len(contents))


if __name__ == "__main__":
    unittest.main()
