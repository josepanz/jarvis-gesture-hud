"""Unit tests for system action Commands (TASK-013).

CrossPlatformOS is fully mocked - these tests NEVER lock the real session, change
the real volume, or take a real screenshot.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.actions.system import (  # noqa: E402
    LockSessionCommand,
    MuteCommand,
    ScreenshotCommand,
    VolumeDownCommand,
    VolumeUpCommand,
)


class SystemCommandTests(unittest.TestCase):
    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_volume_up_calls_os_native(self, mock_os):
        result = VolumeUpCommand().execute()
        mock_os.volume_up.assert_called_once()
        self.assertTrue(result.success)

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_volume_down_calls_os_native(self, mock_os):
        result = VolumeDownCommand().execute()
        mock_os.volume_down.assert_called_once()
        self.assertTrue(result.success)

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_mute_calls_os_native(self, mock_os):
        result = MuteCommand().execute()
        mock_os.volume_mute.assert_called_once()
        self.assertTrue(result.success)

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_screenshot_calls_os_native_and_reports_path(self, mock_os):
        mock_os.take_screenshot.return_value = "captures/screenshot_x.png"
        result = ScreenshotCommand().execute()
        mock_os.take_screenshot.assert_called_once()
        self.assertTrue(result.success)
        self.assertIn("captures/screenshot_x.png", result.message)

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_lock_session_calls_os_native(self, mock_os):
        result = LockSessionCommand().execute()
        mock_os.lock_session.assert_called_once()
        self.assertTrue(result.success)

    def test_lock_session_declares_hold_required_safety(self):
        self.assertEqual(LockSessionCommand().metadata.safety, "HOLD_REQUIRED")

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_failure_is_reported_not_raised(self, mock_os):
        mock_os.lock_session.side_effect = RuntimeError("no display manager")
        result = LockSessionCommand().execute()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")


class ReversibilityTests(unittest.TestCase):
    """TASK-040: volume is a best-effort symmetric nudge, not an exact restore
    (no OS volume-level query exists in this project) - see VolumeUpCommand's
    docstring."""

    def test_volume_up_declares_reversible(self):
        self.assertTrue(VolumeUpCommand().is_reversible())

    def test_volume_down_declares_reversible(self):
        self.assertTrue(VolumeDownCommand().is_reversible())

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_volume_up_undo_presses_volume_down(self, mock_os):
        result = VolumeUpCommand().undo()
        mock_os.volume_down.assert_called_once()
        self.assertTrue(result.success)

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_volume_down_undo_presses_volume_up(self, mock_os):
        result = VolumeDownCommand().undo()
        mock_os.volume_up.assert_called_once()
        self.assertTrue(result.success)

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_volume_up_undo_failure_is_reported_not_raised(self, mock_os):
        mock_os.volume_down.side_effect = RuntimeError("no audio device")
        result = VolumeUpCommand().undo()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")

    def test_other_system_commands_are_not_reversible(self):
        self.assertFalse(MuteCommand().is_reversible())
        self.assertFalse(ScreenshotCommand().is_reversible())
        self.assertFalse(LockSessionCommand().is_reversible())
        with self.assertRaises(NotImplementedError):
            ScreenshotCommand().undo()


if __name__ == "__main__":
    unittest.main()
