"""H-13: jarvis.paths separa assets empaquetados (solo lectura, bajo
sys._MEIPASS cuando el .exe esta congelado) de assets escribibles (deben
persistir entre arranques, nunca bajo _MEIPASS)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis import paths  # noqa: E402


class DevModeTests(unittest.TestCase):
    def test_bundled_and_writable_both_resolve_to_repo_assets_in_dev(self):
        with patch.object(sys, "frozen", False, create=True):
            expected = Path(paths.__file__).resolve().parents[2] / "assets"
            self.assertEqual(paths.bundled_assets_dir(), expected)
            self.assertEqual(paths.writable_assets_dir(), expected)


class FrozenModeTests(unittest.TestCase):
    def test_bundled_assets_dir_uses_meipass_when_frozen(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "_MEIPASS", r"C:\fake\meipass", create=True
        ):
            self.assertEqual(paths.bundled_assets_dir(), Path(r"C:\fake\meipass") / "assets")

    def test_writable_assets_dir_never_uses_meipass_when_frozen(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "_MEIPASS", r"C:\fake\meipass", create=True
        ):
            result = paths.writable_assets_dir()
            self.assertNotIn("meipass", str(result).lower())
            self.assertEqual(result, paths.WRITABLE_ASSETS_DIR)

    def test_writable_assets_dir_lives_under_the_user_config_dir(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "_MEIPASS", r"C:\fake\meipass", create=True
        ):
            result = paths.writable_assets_dir()
            self.assertEqual(result, Path.home() / ".jarvis-gesture-hud" / "assets")


if __name__ == "__main__":
    unittest.main()
