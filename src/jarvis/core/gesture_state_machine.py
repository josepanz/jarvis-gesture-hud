"""GestureStateMachine (TASK-014, spec.md #3).

Standalone, tested state machine matching spec.md's documented states and the two
explicit transition paths (happy path, and CANDIDATE -> CANCELLED -> IDLE). NOT
wired into `jarvis.gestures.GestureEngine` yet: that engine is a working, tested,
threshold-based detector treated as the correct baseline throughout this project
(design.md #5.1) - forcing every existing gesture through a formal
detect/candidate/confirm/activate/complete lifecycle would risk changing real,
already-shipped latency/behavior without a concrete need. See the task report for
the reasoning and what a real integration would require.
"""

_TRANSITIONS = {
    "IDLE": {"DETECTED"},
    "DETECTED": {"CANDIDATE", "CANCELLED"},
    "CANDIDATE": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"ACTIVE", "CANCELLED"},
    "ACTIVE": {"COMPLETED", "CANCELLED"},
    "COMPLETED": {"COOLDOWN"},
    "CANCELLED": {"IDLE"},
    "COOLDOWN": {"IDLE"},
}

VALID_STATES = frozenset(_TRANSITIONS)


class IllegalTransitionError(ValueError):
    pass


class GestureStateMachine:
    def __init__(self):
        self.state = "IDLE"

    def can_transition_to(self, target):
        return target in _TRANSITIONS.get(self.state, set())

    def _transition(self, target):
        if not self.can_transition_to(target):
            raise IllegalTransitionError(f"illegal transition {self.state} -> {target}")
        self.state = target
        return self.state

    def detect(self):
        return self._transition("DETECTED")

    def candidate(self):
        return self._transition("CANDIDATE")

    def confirm(self):
        return self._transition("CONFIRMED")

    def activate(self):
        return self._transition("ACTIVE")

    def complete(self):
        return self._transition("COMPLETED")

    def cooldown(self):
        return self._transition("COOLDOWN")

    def cancel(self):
        return self._transition("CANCELLED")

    def reset(self):
        return self._transition("IDLE")
