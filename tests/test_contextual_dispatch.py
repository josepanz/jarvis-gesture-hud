"""Tests for A-03 (WORKPLAN.md §9, `hardening-and-polish`): gesture bindings
resolved per foreground application, via `JarvisApp._dispatch_bound_event()`.

Reuses `_AppTestCase` from test_naruto_seal_dispatch.py (same real-JarvisApp,
hardware/SO-mocked technique) instead of duplicating that setup - same
cross-file reuse pattern `tests/manual_live_integration_check.py` already uses
for `test_gesture_engine_regression.py`'s fixtures.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

with patch("cv2.VideoCapture"), patch("jarvis.hand_tracker.HandTracker.__init__", return_value=None):
    from jarvis.core.profiles import Profile  # noqa: E402

from test_naruto_seal_dispatch import _AppTestCase  # noqa: E402


def _set_foreground_app(app, title):
    """The tracker is cached (0.5s TTL) - patching its `get()` directly is
    simpler and more explicit than faking a detector + waiting out the cache."""
    app.context_tracker.get = lambda: title


class ContextualBindingDispatchTests(_AppTestCase):
    def test_no_rules_behaves_identically_to_before(self):
        # Non-regression, the most important case: context_rules is empty on
        # every profile today, so resolve_contextual_intent() must fall
        # straight through to the pre-A-03 behavior regardless of which app
        # is in the foreground.
        _set_foreground_app(self.app, "notepad.exe")
        self.app._dispatch_bound_event("NARUTO_TORA")  # default: SCREENSHOT
        self.assertTrue(self.mock_os.take_screenshot.called)

    def test_rule_for_the_foreground_app_wins(self):
        self.app.profiles.active.context_rules["notepad.exe"] = {"NARUTO_TORA": "VOLUME_UP"}
        _set_foreground_app(self.app, "notepad.exe")

        self.app._dispatch_bound_event("NARUTO_TORA")

        self.assertFalse(self.mock_os.take_screenshot.called)  # el default global NO se uso
        self.assertTrue(self.mock_os.volume_up.called)  # gano la regla de la app en foco

    def test_rule_for_a_different_app_does_not_apply(self):
        self.app.profiles.active.context_rules["notepad.exe"] = {"NARUTO_TORA": "VOLUME_UP"}
        _set_foreground_app(self.app, "chrome.exe")

        self.app._dispatch_bound_event("NARUTO_TORA")

        self.assertTrue(self.mock_os.take_screenshot.called)  # cayo al default global
        self.assertFalse(self.mock_os.volume_up.called)

    def test_no_foreground_app_detected_falls_back_to_the_profile_override(self):
        self.app.profiles.active.context_rules["notepad.exe"] = {"NARUTO_TORA": "VOLUME_UP"}
        self.app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MUTE"
        _set_foreground_app(self.app, None)

        self.app._dispatch_bound_event("NARUTO_TORA")

        self.assertTrue(self.mock_os.volume_mute.called)  # override del perfil, no la regla ni el default
        self.assertFalse(self.mock_os.take_screenshot.called)
        self.assertFalse(self.mock_os.volume_up.called)

    def test_context_rule_can_point_to_a_custom_shortcut(self):
        self.app.profiles.active.context_rules["notepad.exe"] = {"NARUTO_TORA": "MY_SHORTCUT"}
        self.app.profiles.active.custom_shortcuts["MY_SHORTCUT"] = "ctrl+alt+t"
        _set_foreground_app(self.app, "notepad.exe")

        self.app._dispatch_bound_event("NARUTO_TORA")

        self.mock_macro_pyautogui.hotkey.assert_called_once_with("ctrl", "alt", "t")
        self.assertFalse(self.mock_os.take_screenshot.called)

    def test_context_rule_cannot_grant_hold_required_on_a_non_hold_event(self):
        # H-10's gate (settings_ui.HOLD_REQUIRED_ACTIONS/HOLD_CAPABLE_EVENTS)
        # applies here too: PINCH_DOWN is instantaneous, so a per-app rule
        # aiming it at LOCK_SESSION must be rejected, same as the UI already
        # refuses to offer that combination for reassignment.
        self.app.profiles.active.context_rules["notepad.exe"] = {"PINCH_DOWN": "LOCK_SESSION"}
        _set_foreground_app(self.app, "notepad.exe")

        self.app._dispatch_bound_event("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(500, 400))

        self.assertFalse(self.mock_os.lock_session.called)
        self.assertTrue(self.mock_mouse_pyautogui.mouseDown.called)  # cayo al comportamiento normal de PINCH_DOWN


if __name__ == "__main__":
    unittest.main()
