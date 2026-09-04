"""Tests for gesture_icons (TASK-058, Fase 3, spec.md #3.1-3.2)."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis import gesture_icons  # noqa: E402
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


class WriteFailureTests(unittest.TestCase):
    """H-14: un fallo de escritura (permisos, disco lleno) no puede crashear
    el arranque - ensure_icon() lo loguea y degrada devolviendo None."""

    def test_save_failure_does_not_propagate_and_returns_none(self):
        with TemporaryDirectory() as tmp:
            with patch.object(gesture_icons, "writable_assets_dir", return_value=Path(tmp)):
                with patch(
                    "jarvis.gesture_icons._render_icon"
                ) as mock_render:
                    mock_render.return_value.save.side_effect = OSError("disco lleno")
                    result = ensure_icon("pinch_click")

            self.assertIsNone(result)

    def test_save_failure_leaves_no_tmp_file_behind(self):
        with TemporaryDirectory() as tmp:
            with patch.object(gesture_icons, "writable_assets_dir", return_value=Path(tmp)):
                with patch("jarvis.gesture_icons._render_icon") as mock_render:
                    def _fake_save(path, **kwargs):
                        Path(path).write_bytes(b"parcial")
                        raise OSError("disco lleno")

                    mock_render.return_value.save.side_effect = _fake_save
                    ensure_icon("pinch_click")

            leftover_files = [p for p in Path(tmp).glob("**/*") if p.is_file()]
            self.assertEqual(leftover_files, [])


class AtomicWriteTests(unittest.TestCase):
    """H-15: una escritura interrumpida no puede dejar un PNG parcial
    cacheado con el nombre final para siempre."""

    def test_interrupted_save_leaves_no_file_with_the_final_name(self):
        with TemporaryDirectory() as tmp:
            with patch.object(gesture_icons, "writable_assets_dir", return_value=Path(tmp)):
                with patch("jarvis.gesture_icons._render_icon") as mock_render:
                    def _fake_save(path, **kwargs):
                        Path(path).write_bytes(b"parcial")
                        raise OSError("interrumpido")

                    mock_render.return_value.save.side_effect = _fake_save
                    ensure_icon("pinch_click")

                final_path = Path(tmp) / "gesture_icons" / "pinch_click.png"
                self.assertFalse(final_path.exists())

    def test_successful_generation_is_reused_without_regenerating(self):
        with TemporaryDirectory() as tmp:
            with patch.object(gesture_icons, "writable_assets_dir", return_value=Path(tmp)):
                first = ensure_icon("scroll")
                with patch("jarvis.gesture_icons._render_icon") as mock_render:
                    second = ensure_icon("scroll")

            mock_render.assert_not_called()
            self.assertEqual(first, second)


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
