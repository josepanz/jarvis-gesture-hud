"""Context model (TASK-026, spec.md #23).

"Context SHALL contain: active_application, window_title, mode, profile,
timestamp." Frozen, validated dataclass - same style as GestureEvent/Intent.

NOT produced anywhere in the live pipeline yet - see context_tracker.py (TASK-027)
for the piece that could populate `window_title`/`active_application`, and
contextual_bindings.py (TASK-028) for what would consume a Context once one exists.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Context:
    timestamp: float
    active_application: Optional[str] = None
    window_title: Optional[str] = None
    mode: Optional[str] = None
    profile: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None or isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)):
            raise ValueError(f"timestamp must be a number, got {self.timestamp!r}")
        for field_name in ("active_application", "window_title", "mode", "profile"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field_name} must be a string or None, got {value!r}")
