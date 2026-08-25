"""Unit tests for Profile/ProfileManager (TASK-023/024/025)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis import config  # noqa: E402
from jarvis.core.profiles import Profile, ProfileManager, SUGGESTED_PROFILE_NAMES  # noqa: E402


class ProfileModelTests(unittest.TestCase):
    def test_name_required(self):
        with self.assertRaises(ValueError):
            Profile(name="")

    def test_dict_fields_default_to_empty(self):
        p = Profile(name="x")
        self.assertEqual(p.gesture_bindings, {})
        self.assertEqual(p.sensitivity, {})

    def test_dict_fields_must_be_dicts(self):
        with self.assertRaises(ValueError):
            Profile(name="x", cooldowns=["not", "a", "dict"])

    def test_suggested_profile_names_match_spec(self):
        self.assertEqual(SUGGESTED_PROFILE_NAMES, ("default", "coding", "gaming", "presentation", "media"))


class ProfileManagerLoadSwitchTests(unittest.TestCase):
    def test_starts_on_default_profile(self):
        self.assertEqual(ProfileManager().active.name, "default")

    def test_default_profile_matches_existing_config_constants(self):
        pm = ProfileManager()
        self.assertEqual(pm.get_setting("smoothing_alpha"), config.EMA_ALPHA)
        self.assertEqual(pm.get_cooldown("click"), config.CLICK_COOLDOWN)

    def test_can_register_and_switch_to_a_new_profile(self):
        pm = ProfileManager()
        pm.register(Profile(name="gaming", sensitivity={"cursor_sensitivity": 1.8}))
        pm.switch_to("gaming")
        self.assertEqual(pm.active.name, "gaming")
        self.assertEqual(pm.get_setting("cursor_sensitivity"), 1.8)

    def test_switch_to_unknown_profile_raises(self):
        with self.assertRaises(KeyError):
            ProfileManager().switch_to("nonexistent")

    def test_switch_to_unknown_profile_does_not_change_active(self):
        pm = ProfileManager()
        try:
            pm.switch_to("nonexistent")
        except KeyError:
            pass
        self.assertEqual(pm.active.name, "default")

    def test_constructing_with_unknown_active_raises(self):
        with self.assertRaises(ValueError):
            ProfileManager(active="nonexistent")

    def test_load_returns_profile_without_switching(self):
        pm = ProfileManager()
        pm.register(Profile(name="coding"))
        loaded = pm.load("coding")
        self.assertEqual(loaded.name, "coding")
        self.assertEqual(pm.active.name, "default")  # load() does not switch


class ProfileBindingTests(unittest.TestCase):
    def test_profile_override_wins_over_global(self):
        pm = ProfileManager()
        pm.register(Profile(name="presentation", gesture_bindings={"SWIPE_RIGHT": "next_slide"}))
        pm.switch_to("presentation")
        result = pm.get_gesture_binding("SWIPE_RIGHT", global_bindings={"SWIPE_RIGHT": "forward"})
        self.assertEqual(result, "next_slide")

    def test_falls_back_to_global_when_profile_has_no_override(self):
        pm = ProfileManager()
        result = pm.get_gesture_binding("SWIPE_RIGHT", global_bindings={"SWIPE_RIGHT": "forward"})
        self.assertEqual(result, "forward")

    def test_returns_none_when_neither_has_a_binding(self):
        pm = ProfileManager()
        self.assertIsNone(pm.get_gesture_binding("UNKNOWN_GESTURE"))

    def test_invalid_gesture_bindings_type_fails_safely(self):
        pm = ProfileManager()
        broken = Profile(name="broken")
        broken.gesture_bindings = "not a dict"  # simulate bad config bypassing validation
        pm.register(broken)
        pm.switch_to("broken")
        self.assertIsNone(pm.get_gesture_binding("SWIPE_RIGHT"))  # does not raise


class ProfileSensitivityTests(unittest.TestCase):
    def test_profile_can_override_cursor_sensitivity(self):
        pm = ProfileManager()
        pm.register(Profile(name="gaming", sensitivity={"cursor_sensitivity": 2.0}))
        pm.switch_to("gaming")
        self.assertEqual(pm.get_setting("cursor_sensitivity"), 2.0)

    def test_profile_can_disable_smoothing(self):
        pm = ProfileManager()
        pm.register(Profile(name="gaming", sensitivity={"smoothing_enabled": False}))
        pm.switch_to("gaming")
        self.assertFalse(pm.get_setting("smoothing_enabled"))

    def test_profile_can_override_swipe_thresholds(self):
        pm = ProfileManager()
        pm.register(Profile(name="presentation", sensitivity={"swipe_min_distance": 0.25}))
        pm.switch_to("presentation")
        self.assertEqual(pm.get_setting("swipe_min_distance"), 0.25)

    def test_profile_can_override_dwell_duration(self):
        pm = ProfileManager()
        pm.register(Profile(name="media", dwell={"duration_ms": 900}))
        pm.switch_to("media")
        self.assertEqual(pm.get_dwell_duration_ms(), 900)

    def test_profile_can_override_cooldowns(self):
        pm = ProfileManager()
        pm.register(Profile(name="coding", cooldowns={"click": 0.1}))
        pm.switch_to("coding")
        self.assertEqual(pm.get_cooldown("click"), 0.1)

    def test_unset_setting_falls_back_to_safe_default(self):
        pm = ProfileManager()
        pm.register(Profile(name="minimal"))
        pm.switch_to("minimal")
        self.assertEqual(pm.get_setting("cursor_sensitivity"), 1.0)

    def test_completely_unknown_setting_uses_provided_default(self):
        pm = ProfileManager()
        self.assertEqual(pm.get_setting("made_up_setting", default="fallback"), "fallback")


if __name__ == "__main__":
    unittest.main()
