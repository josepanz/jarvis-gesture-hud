"""Unit tests for ForegroundApplicationTracker (TASK-027) and
CrossPlatformOS.foreground_window_title (mocked per-platform so this never queries
the real OS during tests)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.context_tracker import ForegroundApplicationTracker  # noqa: E402
from jarvis.os_native import CrossPlatformOS  # noqa: E402


class ForegroundWindowTitleTests(unittest.TestCase):
    @patch("jarvis.os_native.platform.system", return_value="Windows")
    @patch("ctypes.windll", create=True)
    def test_windows_returns_window_text(self, mock_windll, _mock_system):
        mock_windll.user32.GetForegroundWindow.return_value = 42
        mock_windll.user32.GetWindowTextLengthW.return_value = 5

        def fake_get_text(hwnd, buf, length):
            buf.value = "hello"

        mock_windll.user32.GetWindowTextW.side_effect = fake_get_text
        result = CrossPlatformOS.foreground_window_title()
        self.assertEqual(result, "hello")

    @patch("jarvis.os_native.platform.system", return_value="Windows")
    @patch("ctypes.windll", create=True)
    def test_windows_no_window_returns_none(self, mock_windll, _mock_system):
        mock_windll.user32.GetForegroundWindow.return_value = 0
        mock_windll.user32.GetWindowTextLengthW.return_value = 0
        self.assertIsNone(CrossPlatformOS.foreground_window_title())

    @patch("jarvis.os_native.platform.system", return_value="Darwin")
    @patch("subprocess.run")
    def test_macos_uses_osascript(self, mock_run, _mock_system):
        mock_run.return_value = MagicMock(stdout="Terminal\n")
        result = CrossPlatformOS.foreground_window_title()
        self.assertEqual(result, "Terminal")
        self.assertIn("osascript", mock_run.call_args[0][0])

    @patch("jarvis.os_native.platform.system", return_value="Linux")
    @patch("subprocess.run")
    def test_linux_uses_xdotool(self, mock_run, _mock_system):
        mock_run.return_value = MagicMock(stdout="gnome-terminal\n")
        result = CrossPlatformOS.foreground_window_title()
        self.assertEqual(result, "gnome-terminal")

    @patch("jarvis.os_native.platform.system", return_value="Linux")
    @patch("subprocess.run", side_effect=FileNotFoundError("xdotool not installed"))
    def test_failure_returns_none_without_raising(self, _mock_run, _mock_system):
        self.assertIsNone(CrossPlatformOS.foreground_window_title())

    @patch("jarvis.os_native.platform.system", return_value="Plan9")
    def test_unsupported_platform_returns_none(self, _mock_system):
        self.assertIsNone(CrossPlatformOS.foreground_window_title())


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class ForegroundApplicationTrackerTests(unittest.TestCase):
    def test_first_call_queries_the_detector(self):
        detector = MagicMock(return_value="App1")
        tracker = ForegroundApplicationTracker(detector=detector, clock=FakeClock())
        self.assertEqual(tracker.get(), "App1")
        detector.assert_called_once()

    def test_repeated_calls_within_ttl_use_the_cache(self):
        detector = MagicMock(return_value="App1")
        clock = FakeClock()
        tracker = ForegroundApplicationTracker(detector=detector, cache_ttl=0.5, clock=clock)
        tracker.get()
        clock.advance(0.1)
        tracker.get()
        detector.assert_called_once()  # second call was cached, not re-queried

    def test_cache_expires_after_ttl(self):
        detector = MagicMock(side_effect=["App1", "App2"])
        clock = FakeClock()
        tracker = ForegroundApplicationTracker(detector=detector, cache_ttl=0.5, clock=clock)
        self.assertEqual(tracker.get(), "App1")
        clock.advance(0.6)
        self.assertEqual(tracker.get(), "App2")

    def test_detector_exception_does_not_raise_and_yields_none(self):
        detector = MagicMock(side_effect=RuntimeError("boom"))
        tracker = ForegroundApplicationTracker(detector=detector, clock=FakeClock())
        self.assertIsNone(tracker.get())

    def test_invalidate_forces_a_fresh_query(self):
        detector = MagicMock(side_effect=["App1", "App2"])
        clock = FakeClock()
        tracker = ForegroundApplicationTracker(detector=detector, cache_ttl=10, clock=clock)
        tracker.get()
        tracker.invalidate()
        self.assertEqual(tracker.get(), "App2")


if __name__ == "__main__":
    unittest.main()
