"""End-to-end integration check for JarvisApp's PHASE 2 dispatch wiring.

Deliberately named without a `test_` prefix so `python -m unittest discover -s tests`
does NOT pick it up - it constructs a REAL VoiceJarvis + ScreenOverlay (a real TTS
engine thread and real native Tk windows), the same kind of manual integration check
used earlier in this project (e.g. for TASK-005/FeedbackManager).

pyautogui and CrossPlatformOS ARE mocked - this must NEVER actually move the real
mouse, lock the real session, or take a real screenshot.

Run manually:
    python tests/test_main_integration.py
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

with patch("cv2.VideoCapture"), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None):
    from jarvis.main import JarvisApp  # noqa: E402


def main():
    with patch("jarvis.actions.mouse.pyautogui") as mock_mouse_pyautogui, patch(
        "jarvis.actions.keyboard.pyautogui"
    ) as mock_kb_pyautogui, patch("jarvis.actions.system.CrossPlatformOS") as mock_os, patch(
        "cv2.VideoCapture"
    ), patch(
        "jarvis.hand_tracker.HandTracker.__init__", return_value=None
    ), patch(
        "pyautogui.size", return_value=(1920, 1080)
    ):
        mock_os.take_screenshot.return_value = "captures/fake.png"

        app = JarvisApp()
        try:
            # --- click / drag (TASK-007/009) ---
            app._dispatch("PINCH_DOWN", (100, 100), (500, 400))
            assert mock_mouse_pyautogui.mouseDown.called, "PINCH_DOWN should mouseDown when not on keyboard"
            assert app.is_dragging is True

            app._dispatch("PINCH_UP", (100, 100), (500, 400))
            assert mock_mouse_pyautogui.mouseUp.called, "PINCH_UP should mouseUp"
            assert app.is_dragging is False

            # --- right click (TASK-008) ---
            app._dispatch("RIGHT_CLICK", (100, 100), (500, 400))
            assert mock_mouse_pyautogui.rightClick.called

            # --- scroll (TASK-010) ---
            app._dispatch("SCROLL_UP", (100, 100), (500, 400))
            mock_mouse_pyautogui.scroll.assert_any_call(12)
            app._dispatch("SCROLL_DOWN", (100, 100), (500, 400))
            mock_mouse_pyautogui.scroll.assert_any_call(-12)

            # --- zoom (TASK-011) ---
            app._dispatch("ZOOM_IN", (100, 100), (500, 400))
            mock_mouse_pyautogui.scroll.assert_any_call(10)
            assert mock_mouse_pyautogui.keyDown.called and mock_mouse_pyautogui.keyUp.called

            # --- keyboard HUD (TASK-012): open the keyboard, pinch on a real key ---
            app.keyboard.visible = True
            space_pt = None
            for key, (x1, y1, x2, y2) in app.keyboard._key_rects():
                if key == "SPACE":
                    space_pt = ((x1 + x2) // 2, (y1 + y2) // 2)
            assert space_pt is not None
            mock_mouse_pyautogui.reset_mock()
            app._dispatch("PINCH_DOWN", space_pt, (500, 400))
            mock_kb_pyautogui.press.assert_called_once_with("space")
            assert not mock_mouse_pyautogui.mouseDown.called, "keyboard click must NOT also start a drag"
            app.keyboard.visible = False
            app.is_dragging = False  # PINCH_DOWN on the keyboard never set it, but be explicit

            # --- system actions (TASK-013) ---
            app._dispatch("VOLUME_UP", (100, 100), (500, 400))
            assert mock_os.volume_up.called
            app._dispatch("VOLUME_DOWN", (100, 100), (500, 400))
            assert mock_os.volume_down.called
            app._dispatch("SCREENSHOT", (100, 100), (500, 400))
            assert mock_os.take_screenshot.called
            app._dispatch("LOCK_SESSION", (100, 100), (500, 400))
            assert mock_os.lock_session.called

            # --- mouse move (TASK-006), continuous path ---
            mock_mouse_pyautogui.reset_mock()
            app._dispatch_mouse_move((640, 480))
            mock_mouse_pyautogui.moveTo.assert_called_once_with(640, 480)

            # --- failure path: CommandBus must not crash the app ---
            mock_os.lock_session.side_effect = RuntimeError("no display manager")
            app._dispatch("LOCK_SESSION", (100, 100), (500, 400))  # must not raise

            # --- untouched (non-PHASE-2) gestures still work exactly as before ---
            app._dispatch("SILENCE", (100, 100), (500, 400))  # voice.silence(), no crash
            app._dispatch("KEYBOARD_TOGGLE", (100, 100), (500, 400))
            assert app.keyboard.visible is True

            app.overlay.pump()
            time.sleep(0.3)
            print("INTEGRATION OK: all PHASE 2 dispatch paths verified against mocked OS calls")
        finally:
            app.overlay.close()


if __name__ == "__main__":
    main()
