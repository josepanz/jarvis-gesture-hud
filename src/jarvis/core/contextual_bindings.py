"""Contextual gesture bindings (TASK-028, spec.md #24, design.md #13).

"SWIPE_RIGHT + PowerPoint -> next_slide / + Browser -> back / + Desktop ->
next_window. The gesture itself SHALL remain unchanged. Only intent resolution
changes." Pure function: resolves a (gesture_type, active_application) pair to an
intent name using per-application bindings with a global fallback. Deliberately
returns only a plain string (an intent NAME) and accepts no callable/command
argument, so it structurally CANNOT execute an OS command itself - satisfies
"Context cannot directly execute OS commands" by construction, not by convention.
"""


def resolve_contextual_intent(gesture_type, active_application, bindings_by_app, global_bindings=None):
    """bindings_by_app: {app_name: {gesture_type: intent_name}}.
    global_bindings: {gesture_type: intent_name}, used when there's no app-specific
    binding (or no active_application at all). Returns the resolved intent name, or
    None if nothing matches - never raises on a missing/unknown key."""
    app_bindings = bindings_by_app.get(active_application) if active_application else None
    if app_bindings:
        intent = app_bindings.get(gesture_type)
        if intent is not None:
            return intent
    if global_bindings:
        return global_bindings.get(gesture_type)
    return None
