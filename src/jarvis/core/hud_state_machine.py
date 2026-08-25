"""HUDStateMachine (TASK-029, spec.md #31, design.md #17).

States per spec.md #31: IDLE, TRACKING, GESTURE_DETECTED, CONFIRMING, EXECUTING,
SUCCESS, ERROR, PAUSED (`LISTENING` is explicitly future voice support, spec.md
#31, not implemented here). design.md #17's diagram only shows the happy path
(IDLE->TRACKING->GESTURE_DETECTED->CONFIRMING->EXECUTING->SUCCESS->IDLE) and the
error path (EXECUTING->ERROR->IDLE) - it doesn't place PAUSED anywhere. PAUSED is
reachable from IDLE/TRACKING here, back to IDLE or TRACKING, as a reasonable
extension matching this app's own existing pause/resume gesture. Flagged as an
interpretation, not literal spec.

Standalone, tested - NOT wired into the live HUD (`jarvis.overlay`/`jarvis.legend`),
which has its own simpler, already-working display model (bubbles + a static
gesture-legend panel). See hud_feedback.py / contextual_hud.py for the rendering
pieces that would consume this state if wired in.
"""

_TRANSITIONS = {
    "IDLE": {"TRACKING", "PAUSED"},
    "TRACKING": {"GESTURE_DETECTED", "PAUSED", "IDLE"},
    "GESTURE_DETECTED": {"CONFIRMING", "TRACKING"},
    "CONFIRMING": {"EXECUTING", "TRACKING"},
    "EXECUTING": {"SUCCESS", "ERROR"},
    "SUCCESS": {"IDLE"},
    "ERROR": {"IDLE"},
    "PAUSED": {"IDLE", "TRACKING"},
}

VALID_STATES = frozenset(_TRANSITIONS)


class IllegalHudTransitionError(ValueError):
    pass


class HUDStateMachine:
    def __init__(self):
        self.state = "IDLE"

    def can_transition_to(self, target):
        return target in _TRANSITIONS.get(self.state, set())

    def _transition(self, target):
        if not self.can_transition_to(target):
            raise IllegalHudTransitionError(f"illegal HUD transition {self.state} -> {target}")
        self.state = target
        return self.state

    def track(self):
        return self._transition("TRACKING")

    def gesture_detected(self):
        return self._transition("GESTURE_DETECTED")

    def confirming(self):
        return self._transition("CONFIRMING")

    def executing(self):
        return self._transition("EXECUTING")

    def success(self):
        return self._transition("SUCCESS")

    def error(self):
        return self._transition("ERROR")

    def pause(self):
        return self._transition("PAUSED")

    def reset(self):
        return self._transition("IDLE")
