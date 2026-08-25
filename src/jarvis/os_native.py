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
