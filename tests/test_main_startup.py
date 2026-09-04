"""H-04: un fallo al construir HandTracker/PoseTracker en el primer arranque
(tipicamente de red - ver H-03) no puede terminar en un traceback crudo."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

with patch("cv2.VideoCapture"), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None):
    from jarvis.main import JarvisApp  # noqa: E402


class HandTrackerInitFailureTests(unittest.TestCase):
    def test_hand_tracker_init_failure_reports_the_error_and_exits_cleanly(self):
        with TemporaryDirectory() as tmp:
            temp_config_path = Path(tmp) / "bindings.json"
            with patch("cv2.VideoCapture"), patch(
                "jarvis.hand_tracker.HandTracker.__init__",
                side_effect=OSError("no se pudo descargar el modelo"),
            ), patch(
                "jarvis.core.config_store.load_bindings",
                side_effect=lambda path=temp_config_path: {},
            ), self.assertLogs("jarvis.main", level="ERROR") as logs, self.assertRaises(SystemExit) as ctx:
                JarvisApp()

            self.assertEqual(ctx.exception.code, 1)
            self.assertTrue(any("modelo de manos" in line for line in logs.output))

    def test_pose_tracker_init_failure_also_reports_and_exits_cleanly(self):
        with TemporaryDirectory() as tmp:
            temp_config_path = Path(tmp) / "bindings.json"
            with patch("cv2.VideoCapture"), patch(
                "jarvis.hand_tracker.HandTracker.__init__", return_value=None
            ), patch(
                "jarvis.pose_tracker.PoseTracker.__init__",
                side_effect=OSError("no se pudo descargar el modelo de pose"),
            ), patch("jarvis.config.POSE_HAND_OWNERSHIP_ENABLED", True), patch(
                "jarvis.core.config_store.load_bindings",
                side_effect=lambda path=temp_config_path: {},
            ), self.assertLogs("jarvis.main", level="ERROR"), self.assertRaises(SystemExit) as ctx:
                JarvisApp()

            self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
