"""End-to-end integration check for the live-wiring added on
feature/full-integration-voice-llm (Telemetry, ProfileManager, CommandHistory/
UndoRedoController, debug HUD).

Same conventions as manual_main_integration_check.py: deliberately named without
a `test_` prefix so `unittest discover` does not pick it up (constructs a real
VoiceJarvis + ScreenOverlay). pyautogui and CrossPlatformOS ARE mocked - this must
never actually move the real mouse, lock the real session, or change the real
volume.

Run manually:
    python tests/manual_live_integration_check.py
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

with patch("cv2.VideoCapture"), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None):
    from jarvis.main import JarvisApp  # noqa: E402

from jarvis.core.profiles import Profile  # noqa: E402


def main():
    with patch("jarvis.actions.mouse.pyautogui"), patch("jarvis.actions.system.CrossPlatformOS") as mock_os, patch(
        "cv2.VideoCapture"
    ), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None), patch(
        "pyautogui.size", return_value=(1920, 1080)
    ):
        app = JarvisApp()
        try:
            # --- Telemetry is live and records real dispatches ---
            app._dispatch("VOLUME_UP", (100, 100), (500, 400))
            assert mock_os.volume_up.called
            command_events = app.telemetry.history(event="command")
            assert any(e.metric == "success" for e in command_events), "VolumeUp should be in telemetry"

            # --- CommandHistory records discrete commands (not MouseMove) ---
            assert len(app.history) >= 1
            assert app.history.last().command_name == "VolumeUp"
            app._dispatch_mouse_move((640, 480))
            assert app.history.last().command_name == "VolumeUp", "MouseMove must not enter history"

            # --- Undo/redo actually call the OS ---
            mock_os.reset_mock()
            app._trigger_undo()
            assert mock_os.volume_down.called, "undo of VolumeUp should press volume-down"

            mock_os.reset_mock()
            app._trigger_redo()
            assert mock_os.volume_up.called, "redo should re-execute VolumeUp"

            # --- Undo with nothing left to undo is a graceful no-op ---
            for _ in range(5):
                app._trigger_undo()  # drain whatever's left, must never raise

            # --- Profile cycling is live ---
            assert app.profiles.active.name == "default"
            app.profiles.register(Profile(name="test-profile"))
            app._cycle_profile()
            assert app.profiles.active.name == "test-profile"
            app._cycle_profile()
            assert app.profiles.active.name == "default"

            # --- smoothing_enabled was actually sourced from the profile at construction ---
            assert app.gestures.smoothing_enabled is True  # default profile matches prior behavior

            # --- Debug HUD toggles and renders without crashing on a real frame ---
            assert app.hud_renderer.debug is False
            app._toggle_debug_hud()
            assert app.hud_renderer.debug is True
            frame = np.zeros((480, 640, 3), dtype="uint8")
            app._last_fps = 30.0
            app._last_command_name = "VolumeUp"
            app.hud_renderer.render(
                frame,
                "TRACKING",
                telemetry={
                    "fps": app._last_fps,
                    "command": app._last_command_name,
                    "profile": app.profiles.active.name,
                },
            )
            assert (frame != 0).any(), "debug HUD should have drawn something"

            # --- Context tracker doesn't crash and is cached ---
            first = app.context_tracker.get()
            second = app.context_tracker.get()
            assert first == second  # same cached value within the TTL window

            # --- Performance metrics recording (as run() does per frame) ---
            app.perf_metrics.record_frame_time(16.6)
            app.perf_metrics.record_fps(60.0)
            assert len(app.telemetry.history(event="performance")) >= 2

            time.sleep(0.2)
            print("LIVE INTEGRATION OK: telemetry, history, undo/redo, profiles, debug HUD, context all verified")
        finally:
            app.overlay.close()


if __name__ == "__main__":
    main()
