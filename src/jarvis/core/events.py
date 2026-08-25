"""GestureEvent: canonical, immutable representation of one detected gesture.

Foundational data model for the openspec change `multimodal-interaction-core`
(see openspec/changes/multimodal-interaction-core/spec.md #2.1). This is a pure
data model with validation only - it does not execute anything, and nothing in
`jarvis.gestures` or `jarvis.main` produces or consumes it yet. That wiring is
explicitly out of scope for TASK-001 (PHASE 2 migrates existing gestures to emit
these events).
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional, Tuple

# Mirrors spec.md #3 "Gesture states" - the GestureStateMachine (TASK-014) will be
# the thing that actually drives transitions between these; for now this is just
# the closed set of values a GestureEvent.state is allowed to carry.
VALID_STATES = frozenset(
    {
        "IDLE",
        "DETECTED",
        "CANDIDATE",
        "CONFIRMED",
        "ACTIVE",
        "COMPLETED",
        "CANCELLED",
        "COOLDOWN",
    }
)


def _validate_pair(value, field_name):
    pair = tuple(value)
    if len(pair) != 2 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in pair):
        raise ValueError(f"{field_name} must be a 2-tuple of numbers or None, got {value!r}")
    return pair


@dataclass(frozen=True)
class GestureEvent:
    gesture_type: str
    confidence: float
    timestamp: float
    source: str
    state: str
    hand: Optional[str] = None
    position: Optional[Tuple[float, float]] = None
    velocity: Optional[Tuple[float, float]] = None
    duration_ms: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    id: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.gesture_type, str) or not self.gesture_type:
            raise ValueError(f"gesture_type must be a non-empty string, got {self.gesture_type!r}")

        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError(f"confidence must be a number, got {self.confidence!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence!r}")

        if self.timestamp is None or isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)):
            raise ValueError(f"timestamp must be a number, got {self.timestamp!r}")

        if not isinstance(self.source, str) or not self.source:
            raise ValueError(f"source must be a non-empty string, got {self.source!r}")

        if self.state not in VALID_STATES:
            raise ValueError(f"state must be one of {sorted(VALID_STATES)}, got {self.state!r}")

        if self.hand is not None and not isinstance(self.hand, str):
            raise ValueError(f"hand must be a string or None, got {self.hand!r}")

        if self.position is not None:
            object.__setattr__(self, "position", _validate_pair(self.position, "position"))

        if self.velocity is not None:
            object.__setattr__(self, "velocity", _validate_pair(self.velocity, "velocity"))

        if self.duration_ms is not None:
            if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, (int, float)):
                raise ValueError(f"duration_ms must be a number or None, got {self.duration_ms!r}")
            if self.duration_ms < 0:
                raise ValueError(f"duration_ms must be >= 0, got {self.duration_ms!r}")

        if not isinstance(self.metadata, dict):
            raise ValueError(f"metadata must be a dict, got {self.metadata!r}")

        if self.id is None:
            object.__setattr__(self, "id", uuid.uuid4().hex)
        elif not isinstance(self.id, str) or not self.id:
            raise ValueError(f"id must be a non-empty string or None, got {self.id!r}")
