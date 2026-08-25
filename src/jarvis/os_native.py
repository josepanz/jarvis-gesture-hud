"""Comandos nativos por sistema operativo: lock de sesion, volumen, screenshot."""

import os
import platform
import time
from pathlib import Path

import pyautogui

from jarvis import config

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0


class CrossPlatformOS:
    @staticmethod
    def lock_session():
        sys_name = platform.system()
        if sys_name == "Windows":
            import ctypes

            ctypes.windll.user32.LockWorkStation()
        elif sys_name == "Darwin":
            os.system(
                "/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend"
            )
        elif sys_name == "Linux":
            os.system("xdg-screensaver lock || gnome-screensaver-command -l || loginctl lock-session")

    @staticmethod
    def take_screenshot():
        out_dir = Path(config.CAPTURES_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filepath = out_dir / f"screenshot_{timestamp}.png"
        pyautogui.screenshot(str(filepath))
        return filepath

    @staticmethod
    def volume_up():
        pyautogui.press("volumeup")

    @staticmethod
    def volume_down():
        pyautogui.press("volumedown")

    @staticmethod
    def volume_mute():
        pyautogui.press("volumemute")

    @staticmethod
    def foreground_window_title():
        """TASK-027: best-effort foreground-window title, or None if it can't be
        determined (unsupported platform, no window focused, missing OS tooling,
        permission denied, etc.) - never raises."""
        sys_name = platform.system()
        try:
            if sys_name == "Windows":
                import ctypes

                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return None
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value or None
            elif sys_name == "Darwin":
                import subprocess

                script = (
                    'tell application "System Events" to get name of first '
                    "application process whose frontmost is true"
                )
                result = subprocess.run(
                    ["osascript", "-e", script], capture_output=True, text=True, timeout=1
                )
                return result.stdout.strip() or None
            elif sys_name == "Linux":
                import subprocess

                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=1
                )
                return result.stdout.strip() or None
        except Exception:
            return None
        return None
