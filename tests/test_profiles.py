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

    def test_profile_names_starts_with_just_default(self):
        self.assertEqual(ProfileManager().profile_names, ["default"])

    def test_profile_names_includes_registered_profiles_in_order(self):
        pm = ProfileManager()
        pm.register(Profile(name="gaming"))
        pm.register(Profile(name="coding"))
        self.assertEqual(pm.profile_names, ["default", "gaming", "coding"])

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


class ProfileSerializationTests(unittest.TestCase):
    def test_custom_shortcuts_and_macros_default_to_empty_dicts(self):
        p = Profile(name="x")
        self.assertEqual(p.custom_shortcuts, {})
        self.assertEqual(p.macros, {})

    def test_custom_shortcuts_and_macros_must_be_dicts(self):
        with self.assertRaises(ValueError):
            Profile(name="x", custom_shortcuts=["not", "a", "dict"])
        with self.assertRaises(ValueError):
            Profile(name="x", macros=["not", "a", "dict"])


class ProfileManagerToFromDictTests(unittest.TestCase):
    def test_to_dict_round_trips_through_from_dict(self):
        pm = ProfileManager()
        pm.active.gesture_bindings["NARUTO_TORA"] = "SCREENSHOT"
        pm.active.custom_shortcuts["MY_SHORTCUT"] = "ctrl+alt+t"
        pm.active.macros["MACRO:greeting"] = [
            {"kind": "type-text", "value": "hola"},
            {"kind": "wait-ms", "value": 300},
            {"kind": "press-key", "value": "enter"},
        ]

        pm.active.context_rules["notepad.exe"] = {"NARUTO_TORA": "VOLUME_UP"}

        data = pm.to_dict()
        # A-03b: 1 -> 2, se agrega context_rules a lo persistido.
        self.assertEqual(data["schema_version"], 2)

        restored = ProfileManager.from_dict(data)
        self.assertEqual(restored.active.gesture_bindings, pm.active.gesture_bindings)
        self.assertEqual(restored.active.custom_shortcuts, pm.active.custom_shortcuts)
        self.assertEqual(restored.active.macros, pm.active.macros)
        self.assertEqual(restored.active.context_rules, pm.active.context_rules)

    def test_from_dict_preserves_the_default_profile_safe_settings(self):
        # gesture_bindings/custom_shortcuts/macros no son lo unico que trae
        # "default" - sensitivity/cooldowns/dwell nunca vienen del disco, y
        # from_dict() no debe perderlos al aplicar lo persistido.
        pm = ProfileManager.from_dict({"schema_version": 1, "profiles": {"default": {"gesture_bindings": {}}}})
        self.assertEqual(pm.get_setting("cursor_sensitivity"), 1.0)

    def test_from_dict_registers_non_default_profiles_too(self):
        data = {"schema_version": 1, "profiles": {"default": {}, "gaming": {"gesture_bindings": {"CLAP": "MUTE"}}}}
        pm = ProfileManager.from_dict(data)
        self.assertIn("gaming", pm.profile_names)
        pm.switch_to("gaming")
        self.assertEqual(pm.active.gesture_bindings, {"CLAP": "MUTE"})

    def test_from_dict_with_missing_or_malformed_data_falls_back_to_defaults(self):
        for malformed in ({}, {"profiles": "not a dict"}, {"profiles": {"default": "not a dict"}}, None, []):
            with self.subTest(malformed=malformed):
                pm = ProfileManager.from_dict(malformed)
                self.assertEqual(pm.active.name, "default")
                self.assertEqual(pm.active.gesture_bindings, {})

    def test_from_dict_discards_macro_with_unknown_step_kind(self):
        # H-01: un bindings.json editado a mano/corrupto no debe impedir el
        # arranque - la macro invalida se descarta, no rompe from_dict().
        data = {
            "schema_version": 1,
            "profiles": {"default": {"macros": {"MACRO:rota": [{"kind": "no-existe"}]}}},
        }
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.macros, {})

    def test_from_dict_discards_macro_with_non_list_steps(self):
        data = {
            "schema_version": 1,
            "profiles": {"default": {"macros": {"MACRO:rota": "no-soy-una-lista"}}},
        }
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.macros, {})

    def test_from_dict_keeps_valid_macro_and_discards_invalid_sibling(self):
        data = {
            "schema_version": 1,
            "profiles": {
                "default": {
                    "macros": {
                        "MACRO:ok": [{"kind": "press-key", "value": "a"}],
                        "MACRO:rota": [{"kind": "no-existe"}],
                    }
                }
            },
        }
        pm = ProfileManager.from_dict(data)
        self.assertEqual(list(pm.active.macros.keys()), ["MACRO:ok"])

    def test_from_dict_discards_macro_for_a_non_default_profile_too(self):
        data = {
            "schema_version": 1,
            "profiles": {"gaming": {"macros": {"MACRO:rota": [{"kind": "no-existe"}]}}},
        }
        pm = ProfileManager.from_dict(data)
        pm.switch_to("gaming")
        self.assertEqual(pm.active.macros, {})

    def test_from_dict_does_not_raise_for_wrong_types_with_valid_json(self):
        # H-02: JSON sintacticamente valido con tipos equivocados no debe
        # explotar mas arriba del filtro de config_store (que solo atrapa
        # JSON invalido/errores de I/O, no tipos incorrectos).
        cases = (
            {"schema_version": 1, "profiles": {"default": {"macros": "no-soy-un-dict"}}},
            {"schema_version": 1, "profiles": {"default": {"macros": {"m": 42}}}},
            {"schema_version": 1, "profiles": "tampoco-soy-un-dict"},
            {"profiles": {"default": {"gesture_bindings": ["lista", "no", "dict"]}}},
        )
        for data in cases:
            with self.subTest(data=data):
                pm = ProfileManager.from_dict(data)
                self.assertEqual(pm.active.name, "default")

    def test_from_dict_with_wrong_type_gesture_bindings_falls_back_to_empty(self):
        data = {"schema_version": 1, "profiles": {"default": {"gesture_bindings": ["lista", "no", "dict"]}}}
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.gesture_bindings, {})

    def test_from_dict_with_wrong_type_custom_shortcuts_falls_back_to_empty(self):
        data = {"schema_version": 1, "profiles": {"default": {"custom_shortcuts": "no-soy-un-dict"}}}
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.custom_shortcuts, {})

    def test_from_dict_mixed_valid_and_invalid_types_keeps_the_valid_field(self):
        # Una macro valida y una invalida en el mismo perfil: se conserva la
        # valida y se descarta la invalida, sin perder ninguna otra.
        data = {
            "schema_version": 1,
            "profiles": {
                "default": {
                    "gesture_bindings": {"NARUTO_TORA": "SCREENSHOT"},
                    "custom_shortcuts": "tipo-incorrecto",
                }
            },
        }
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.gesture_bindings, {"NARUTO_TORA": "SCREENSHOT"})
        self.assertEqual(pm.active.custom_shortcuts, {})

    def test_from_dict_with_wrong_types_preserves_default_profile_safe_settings(self):
        # Regresion explicita: sensitivity/cooldowns/dwell del perfil default
        # nunca vienen del disco y tienen que sobrevivir aunque otros campos
        # persistidos tengan tipos incorrectos.
        data = {"schema_version": 1, "profiles": {"default": {"macros": "no-soy-un-dict"}}}
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.get_setting("cursor_sensitivity"), 1.0)

    def test_from_dict_reads_a_v1_file_without_context_rules(self):
        # A-03b: compatibilidad hacia atras - un archivo de antes de que
        # existiera esta clave sigue cargando igual, con context_rules vacio.
        data = {"schema_version": 1, "profiles": {"default": {"gesture_bindings": {"NARUTO_TORA": "SCREENSHOT"}}}}
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.context_rules, {})
        self.assertEqual(pm.active.gesture_bindings, {"NARUTO_TORA": "SCREENSHOT"})

    def test_from_dict_restores_context_rules_for_a_non_default_profile_too(self):
        data = {
            "schema_version": 2,
            "profiles": {"gaming": {"context_rules": {"notepad.exe": {"NARUTO_TORA": "VOLUME_UP"}}}},
        }
        pm = ProfileManager.from_dict(data)
        pm.switch_to("gaming")
        self.assertEqual(pm.active.context_rules, {"notepad.exe": {"NARUTO_TORA": "VOLUME_UP"}})

    def test_from_dict_discards_context_rules_with_non_dict_top_level(self):
        data = {"schema_version": 2, "profiles": {"default": {"context_rules": "no-soy-un-dict"}}}
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.context_rules, {})

    def test_from_dict_discards_context_rules_entry_with_non_dict_app_bindings(self):
        # H-02: JSON sintacticamente valido, pero el valor por app no es un
        # dict - _validated_dict_field() no lo atrapa (el dict de arriba SI es
        # un dict), asi que necesita su propio chequeo (_valid_context_rules).
        data = {
            "schema_version": 2,
            "profiles": {"default": {"context_rules": {"notepad.exe": ["no", "es", "un", "dict"]}}},
        }
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.context_rules, {})

    def test_from_dict_keeps_valid_context_rules_entry_and_discards_invalid_sibling(self):
        data = {
            "schema_version": 2,
            "profiles": {
                "default": {
                    "context_rules": {
                        "notepad.exe": {"NARUTO_TORA": "VOLUME_UP"},
                        "chrome.exe": "no-es-un-dict",
                    }
                }
            },
        }
        pm = ProfileManager.from_dict(data)
        self.assertEqual(pm.active.context_rules, {"notepad.exe": {"NARUTO_TORA": "VOLUME_UP"}})


if __name__ == "__main__":
    unittest.main()
