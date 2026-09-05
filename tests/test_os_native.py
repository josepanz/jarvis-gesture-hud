"""H-21: lock_session() invoca por subprocess.run en vez de os.system en las
ramas de macOS/Linux. Sin maquina macOS/Linux disponible: verificado solo con
subprocess.run mockeado por plataforma, sin ejecutar comandos reales."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.os_native import CrossPlatformOS  # noqa: E402


class LockSessionWindowsTests(unittest.TestCase):
    @patch("jarvis.os_native.platform.system", return_value="Windows")
    @patch("jarvis.os_native.subprocess.run")
    def test_windows_does_not_shell_out(self, mock_run, _mock_platform):
        with patch("ctypes.windll.user32.LockWorkStation", create=True) as mock_lock:
            CrossPlatformOS.lock_session()
            mock_lock.assert_called_once()
        mock_run.assert_not_called()


class LockSessionDarwinTests(unittest.TestCase):
    @patch("jarvis.os_native.platform.system", return_value="Darwin")
    @patch("jarvis.os_native.subprocess.run")
    def test_darwin_runs_cgsession_as_argv_list(self, mock_run, _mock_platform):
        mock_run.return_value = MagicMock(returncode=0)
        CrossPlatformOS.lock_session()
        mock_run.assert_called_once()
        (args,), kwargs = mock_run.call_args
        self.assertIsInstance(args, list)
        self.assertTrue(args[0].endswith("CGSession"))
        self.assertIn("-suspend", args)
        self.assertNotIn("shell", kwargs)


class LockSessionLinuxTests(unittest.TestCase):
    @patch("jarvis.os_native.platform.system", return_value="Linux")
    @patch("jarvis.os_native.subprocess.run")
    def test_linux_stops_at_first_successful_fallback(self, mock_run, _mock_platform):
        mock_run.return_value = MagicMock(returncode=0)
        CrossPlatformOS.lock_session()
        mock_run.assert_called_once()
        (args,), _kwargs = mock_run.call_args
        self.assertEqual(args, ["xdg-screensaver", "lock"])

    @patch("jarvis.os_native.platform.system", return_value="Linux")
    @patch("jarvis.os_native.subprocess.run")
    def test_linux_falls_back_when_first_command_missing(self, mock_run, _mock_platform):
        mock_run.side_effect = [FileNotFoundError(), MagicMock(returncode=0)]
        CrossPlatformOS.lock_session()
        self.assertEqual(mock_run.call_count, 2)
        second_args = mock_run.call_args_list[1].args[0]
        self.assertEqual(second_args, ["gnome-screensaver-command", "-l"])

    @patch("jarvis.os_native.platform.system", return_value="Linux")
    @patch("jarvis.os_native.subprocess.run")
    def test_linux_falls_back_when_first_command_fails_nonzero(self, mock_run, _mock_platform):
        mock_run.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]
        CrossPlatformOS.lock_session()
        self.assertEqual(mock_run.call_count, 2)
        second_args = mock_run.call_args_list[1].args[0]
        self.assertEqual(second_args, ["gnome-screensaver-command", "-l"])

    @patch("jarvis.os_native.platform.system", return_value="Linux")
    @patch("jarvis.os_native.subprocess.run")
    def test_linux_raises_when_every_fallback_is_unavailable(self, mock_run, _mock_platform):
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaises(RuntimeError):
            CrossPlatformOS.lock_session()
        self.assertEqual(mock_run.call_count, 3)


if __name__ == "__main__":
    unittest.main()
