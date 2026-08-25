"""ConfidenceFilter (TASK-016, spec.md #5).

"Every classified gesture SHALL have confidence in [0.0, 1.0]... The system SHALL
allow minimum_confidence configuration. Default: minimum_confidence = 0.70."

Standalone utility - `jarvis.core.events.GestureEvent` already carries and validates
a `confidence` field (TASK-001); `jarvis.gestures.GestureEngine` doesn't produce a
real probabilistic score yet (it's threshold/boolean detection, always effectively
"fully confident" when a gesture matches), so there is nothing meaningful to filter
in the live pipeline today. This is ready for whenever a real confidence-scoring
classifier exists.
"""

DEFAULT_MINIMUM_CONFIDENCE = 0.70


class ConfidenceFilter:
    def __init__(self, minimum_confidence=DEFAULT_MINIMUM_CONFIDENCE):
        if not (0.0 <= minimum_confidence <= 1.0):
            raise ValueError(f"minimum_confidence must be in [0.0, 1.0], got {minimum_confidence!r}")
        self.minimum_confidence = minimum_confidence

    def accepts(self, event_or_confidence):
        """Accepts either a raw float or any object exposing a `.confidence`
        attribute (e.g. GestureEvent)."""
        confidence = getattr(event_or_confidence, "confidence", event_or_confidence)
        return confidence >= self.minimum_confidence


def format_confidence(confidence):
    """"Debug HUD can display confidence" (TASK-016) - display-ready formatting,
    no debug HUD exists yet to call it."""
    return f"{round(confidence * 100)}%"
