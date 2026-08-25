"""CooldownRegistry (TASK-017, spec.md #6).

"After an action is executed, the same gesture SHALL NOT immediately trigger the
same action repeatedly." Generic, named-action cooldown tracker with configurable
per-action durations (spec.md's example defaults, converted from ms to seconds to
match this codebase's existing convention - see jarvis.config.CLICK_COOLDOWN etc.).

NOT wired into GestureEngine, which already has its own working, hardcoded
per-gesture cooldowns (jarvis.config.*_COOLDOWN + `self.last_*_time` fields) -
retrofitting them onto this generic registry is a refactor with no behavior change
and real regression risk, not something this task asks for on its own.
"""

import time

# spec.md #6 gives these in ms (click=300ms, system_action=800ms,
# gesture_navigation=500ms); stored here in seconds to match time.monotonic().
DEFAULT_COOLDOWNS = {
    "click": 0.3,
    "system_action": 0.8,
    "gesture_navigation": 0.5,
}


class CooldownRegistry:
    def __init__(self, cooldowns=None, clock=time.monotonic):
        self._cooldowns = dict(DEFAULT_COOLDOWNS)
        if cooldowns:
            self._cooldowns.update(cooldowns)
        self._last_fired = {}
        self._clock = clock

    def set_cooldown(self, action, seconds):
        if seconds < 0:
            raise ValueError(f"cooldown seconds must be >= 0, got {seconds!r}")
        self._cooldowns[action] = seconds

    def get_cooldown(self, action):
        return self._cooldowns.get(action, 0.0)

    def try_fire(self, action):
        """Returns True and records `action` as fired now if its cooldown has
        elapsed (or it has none registered - unregistered/zero-cooldown actions,
        e.g. continuous ones, are never blocked). False if still cooling down."""
        now = self._clock()
        cooldown = self._cooldowns.get(action, 0.0)
        last = self._last_fired.get(action)
        if cooldown > 0 and last is not None and (now - last) < cooldown:
            return False
        self._last_fired[action] = now
        return True

    def reset(self, action=None):
        if action is None:
            self._last_fired.clear()
        else:
            self._last_fired.pop(action, None)
