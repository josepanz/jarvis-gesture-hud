"""Intent: semantic representation of user intention, decoupled from the input
modality that produced it (spec.md #2.2, design.md #7 "Intent architecture").

Pure data model, same nature as GestureEvent - no IntentEngine exists yet to
actually produce an Intent from a GestureEvent (that wiring is a later task).
Nothing in jarvis.gestures or jarvis.main produces or consumes Intent yet.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Intent:
    name: str
    source: str
    confidence: float
    timestamp: float
    context: Optional[dict] = None
    parameters: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"name must be a non-empty string, got {self.name!r}")

        if not isinstance(self.source, str) or not self.source:
            raise ValueError(f"source must be a non-empty string, got {self.source!r}")

        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError(f"confidence must be a number, got {self.confidence!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence!r}")

        if (
            self.timestamp is None
            or isinstance(self.timestamp, bool)
            or not isinstance(self.timestamp, (int, float))
        ):
            raise ValueError(f"timestamp must be a number, got {self.timestamp!r}")

        if self.context is not None and not isinstance(self.context, dict):
            raise ValueError(f"context must be a dict or None, got {self.context!r}")

        if not isinstance(self.parameters, dict):
            raise ValueError(f"parameters must be a dict, got {self.parameters!r}")

        if not isinstance(self.metadata, dict):
            raise ValueError(f"metadata must be a dict, got {self.metadata!r}")
