"""Profile / ProfileManager (TASK-023/024/025, spec.md #21/#22).

"Profiles SHALL define: name, gesture_bindings, sensitivity, cooldowns, dwell, HUD,
context_rules. Suggested profiles: default, coding, gaming, presentation, media."
Configuration precedence (spec.md #22): profile override > profile configuration >
global configuration > hardcoded safe default.

Standalone, tested - NOT wired into GestureEngine (which still reads directly from
`jarvis.config` module constants). "default" is seeded so its values exactly match
today's `jarvis.config` constants: switching TO "default" is defined to be a no-op
relative to current behavior, which is what "Existing default behavior preserved"
(TASK-023) actually requires without touching GestureEngine itself.
"""

from dataclasses import dataclass, field

from jarvis import config

SUGGESTED_PROFILE_NAMES = ("default", "coding", "gaming", "presentation", "media")

_SAFE_DEFAULTS = {
    "cursor_sensitivity": 1.0,
    "smoothing_enabled": True,
    "smoothing_alpha": config.EMA_ALPHA,
    "swipe_min_distance": 0.15,
    "swipe_min_velocity": 0.5,
    "dwell_duration_ms": 600,
    "cooldowns": {
        "click": config.CLICK_COOLDOWN,
        "system_action": 0.8,
        "gesture_navigation": 0.5,
    },
}


@dataclass
class Profile:
    name: str
    gesture_bindings: dict = field(default_factory=dict)
    sensitivity: dict = field(default_factory=dict)
    cooldowns: dict = field(default_factory=dict)
    dwell: dict = field(default_factory=dict)
    hud: dict = field(default_factory=dict)
    context_rules: dict = field(default_factory=dict)
    # TASK-075 (Fase 8, design.md §5.2): {nombre_de_atajo: "ctrl+alt+t"} y
    # {"MACRO:<nombre>": [pasos]} - un gesture_bindings[event] puede apuntar
    # a una clave de cualquiera de los 2 (ademas de al vocabulario fijo de
    # VALID_ACTIONS), resuelto en main.py._dispatch_gesture_event().
    custom_shortcuts: dict = field(default_factory=dict)
    macros: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"name must be a non-empty string, got {self.name!r}")
        for field_name in (
            "gesture_bindings",
            "sensitivity",
            "cooldowns",
            "dwell",
            "hud",
            "context_rules",
            "custom_shortcuts",
            "macros",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, dict):
                raise ValueError(f"{field_name} must be a dict, got {value!r}")


def _default_profile():
    return Profile(
        name="default",
        sensitivity={
            "cursor_sensitivity": _SAFE_DEFAULTS["cursor_sensitivity"],
            "smoothing_enabled": _SAFE_DEFAULTS["smoothing_enabled"],
            "smoothing_alpha": _SAFE_DEFAULTS["smoothing_alpha"],
            "swipe_min_distance": _SAFE_DEFAULTS["swipe_min_distance"],
            "swipe_min_velocity": _SAFE_DEFAULTS["swipe_min_velocity"],
        },
        cooldowns=dict(_SAFE_DEFAULTS["cooldowns"]),
        dwell={"duration_ms": _SAFE_DEFAULTS["dwell_duration_ms"]},
    )


class ProfileManager:
    def __init__(self, profiles=None, active="default"):
        self._profiles = {"default": _default_profile()}
        if profiles:
            for profile in profiles:
                self._profiles[profile.name] = profile
        if active not in self._profiles:
            raise ValueError(f"unknown active profile {active!r} - register it first")
        self._active_name = active

    def register(self, profile):
        self._profiles[profile.name] = profile

    @property
    def profile_names(self):
        """Registered profile names, in registration order (insertion-ordered
        dict) - "default" is always first since it's seeded in __init__."""
        return list(self._profiles.keys())

    def load(self, name):
        if name not in self._profiles:
            raise KeyError(f"no such profile: {name!r}")
        return self._profiles[name]

    def switch_to(self, name):
        self.load(name)  # raises KeyError if unknown - fail loudly on a real typo
        self._active_name = name
        return self._active_name

    @property
    def active(self):
        return self._profiles[self._active_name]

    def get_gesture_binding(self, gesture_type, global_bindings=None):
        """TASK-024: profile override > global default > None. Never raises on a
        malformed/unknown gesture_type - returns None (fails safely)."""
        try:
            profile_value = self.active.gesture_bindings.get(gesture_type)
        except (AttributeError, TypeError):
            profile_value = None
        if profile_value is not None:
            return profile_value
        if global_bindings:
            return global_bindings.get(gesture_type)
        return None

    def get_setting(self, key, default=None):
        """TASK-025: cursor_sensitivity/smoothing_*/swipe_*/etc. Precedence: active
        profile's `sensitivity` dict -> hardcoded safe default -> `default` param."""
        try:
            value = self.active.sensitivity.get(key)
        except (AttributeError, TypeError):
            value = None
        if value is not None:
            return value
        if key in _SAFE_DEFAULTS:
            return _SAFE_DEFAULTS[key]
        return default

    def get_cooldown(self, action, default=0.0):
        try:
            value = self.active.cooldowns.get(action)
        except (AttributeError, TypeError):
            value = None
        if value is not None:
            return value
        return _SAFE_DEFAULTS["cooldowns"].get(action, default)

    def get_dwell_duration_ms(self):
        try:
            value = self.active.dwell.get("duration_ms")
        except (AttributeError, TypeError):
            value = None
        return value if value is not None else _SAFE_DEFAULTS["dwell_duration_ms"]

    # TASK-075 (Fase 8, design.md §5.2/spec.md §8.6): (de)serializacion a/desde
    # el schema versionado que persiste `jarvis.core.config_store`. Solo
    # gesture_bindings/custom_shortcuts/macros se persisten - sensitivity/
    # cooldowns/dwell/hud/context_rules siguen siendo solo-codigo por ahora
    # (spec.md #8 no pide persistirlos, y `apply.md` §14 pide no inventar una
    # segunda representacion en memoria para lo que SI se persiste: este
    # metodo lee directo de los `Profile` ya vivos, no de una copia aparte).
    def to_dict(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "profiles": {name: _profile_to_dict(profile) for name, profile in self._profiles.items()},
        }

    @classmethod
    def from_dict(cls, data):
        """Nunca lanza ante datos malformados/vacios - construye un
        ProfileManager con los defaults de codigo de siempre en ese caso
        (spec.md #8.6: "fail gracefully (defaults) on a missing/corrupt
        file"). El perfil "default" ya sembrado (sensitivity/cooldowns/dwell
        de `_default_profile()`) se ACTUALIZA con lo persistido en vez de
        reemplazarse entero - esos campos nunca vinieron del disco."""
        manager = cls()
        profiles_data = data.get("profiles") if isinstance(data, dict) else None
        if not isinstance(profiles_data, dict):
            return manager
        for name, profile_data in profiles_data.items():
            if not isinstance(profile_data, dict):
                continue
            if name in manager._profiles:
                _apply_persisted_fields(manager._profiles[name], profile_data)
            else:
                manager.register(_profile_from_dict(name, profile_data))
        return manager


SCHEMA_VERSION = 1


def _profile_to_dict(profile):
    return {
        "gesture_bindings": dict(profile.gesture_bindings),
        "custom_shortcuts": dict(profile.custom_shortcuts),
        "macros": {name: list(steps) for name, steps in profile.macros.items()},
    }


def _apply_persisted_fields(profile, data):
    profile.gesture_bindings.update(data.get("gesture_bindings") or {})
    profile.custom_shortcuts.update(data.get("custom_shortcuts") or {})
    profile.macros.update({name: list(steps) for name, steps in (data.get("macros") or {}).items()})


def _profile_from_dict(name, data):
    return Profile(
        name=name,
        gesture_bindings=dict(data.get("gesture_bindings") or {}),
        custom_shortcuts=dict(data.get("custom_shortcuts") or {}),
        macros={macro_name: list(steps) for macro_name, steps in (data.get("macros") or {}).items()},
    )
