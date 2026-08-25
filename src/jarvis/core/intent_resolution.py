"""Intent convergence support (TASK-049, proposal.md #5.4, spec.md #38).

"The Intent Engine MUST NOT care whether an intent came from: gesture; voice;
keyboard; future vision. ... The Command layer SHALL remain the same." (proposal.md
#5.4) TASK-049 asks to VERIFY gesture->intent, keyboard->intent, and voice->intent
can all reach CommandBus - this module is the small, real, testable machinery that
makes that demonstrable rather than just asserted: two adapters turning a
GestureEvent (produced by PHASE 10's GestureInputProvider/KeyboardInputProvider)
into an Intent, plus a generic Intent->Command registry. See
tests/test_intent_convergence.py for the actual end-to-end verification across all
three sources.
"""

from jarvis.core.intents import Intent


def gesture_event_to_intent(event):
    """Adapts a camera GestureEvent into an Intent with the same semantic name -
    jarvis.gestures.GestureEngine already emits semantically-named strings
    (LOCK_SESSION, VOLUME_UP, ...) that work directly as intent names."""
    parameters = {"position": event.position} if event.position is not None else {}
    return Intent(
        name=event.gesture_type,
        source=event.source,
        confidence=event.confidence,
        timestamp=event.timestamp,
        parameters=parameters,
    )


def keyboard_event_to_intent(event, key_bindings):
    """key_bindings: {char: intent_name}. Returns None if `event` isn't a KEY_PRESS
    or its char has no binding - a keyboard event has no semantic meaning on its
    own without this explicit mapping."""
    if event.gesture_type != "KEY_PRESS":
        return None
    char = event.metadata.get("char")
    intent_name = key_bindings.get(char)
    if intent_name is None:
        return None
    return Intent(
        name=intent_name,
        source=event.source,
        confidence=event.confidence,
        timestamp=event.timestamp,
        parameters={"key": char},
    )


class IntentCommandResolver:
    """Maps Intent.name -> a Command instance via an explicit registry - a small,
    real registry, not a general NLU/ML resolver (apply.md #12: no speculative
    dependencies for what this task asks)."""

    def __init__(self, factories=None):
        self._factories = dict(factories or {})

    def register(self, intent_name, factory):
        """factory: callable(intent) -> Command."""
        self._factories[intent_name] = factory

    def resolve(self, intent):
        factory = self._factories.get(intent.name)
        if factory is None:
            return None
        return factory(intent)
