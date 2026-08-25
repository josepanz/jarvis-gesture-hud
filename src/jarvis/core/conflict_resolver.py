"""Gesture conflict resolver (TASK-022, spec.md #14/#18/#19).

"When multiple gestures are possible, the system SHALL use deterministic priority
[...] The system MUST prevent mutually exclusive gestures from triggering
simultaneously." Standalone, tested resolver over a list of candidate GestureEvents
- NOT wired into GestureEngine.

Why not wired in: this assumes a classifier that can produce several *simultaneous*
candidate gestures with confidence scores for the same frame (spec.md's own example:
"PINCH 0.92, POINT 0.81"). GestureEngine's if/elif structure is not that - most of
its branches are already mutually exclusive by construction (e.g. a pinch and a
right-click pinch use different, non-overlapping distance checks), so there is no
live "list of simultaneous candidates" for this resolver to actually receive yet.
"""

DEFAULT_PRIORITY = ["TWO_FINGER_AIM", "PINCH", "OPEN_PALM", "FIST"]


def resolve_conflict(candidates, priority=None):
    """candidates: a list of objects exposing `.gesture_type` and `.confidence`
    (e.g. GestureEvent). Returns the single winning candidate, or None if the list
    is empty. Deterministic: explicit priority order first (unranked types lose to
    any ranked type), confidence as a tiebreak within the same priority, and the
    first-seen candidate as the final tiebreak on an exact tie - the result never
    depends on iteration order of anything outside `candidates` itself."""
    if not candidates:
        return None

    order = priority if priority is not None else DEFAULT_PRIORITY

    def rank(event):
        try:
            priority_rank = order.index(event.gesture_type)
        except ValueError:
            priority_rank = len(order)
        return (priority_rank, -event.confidence)

    return min(candidates, key=rank)
