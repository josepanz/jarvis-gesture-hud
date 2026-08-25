"""VoiceIntentResolver (TASK-048, spec.md #38, design.md #22).

"The initial implementation SHALL NOT require STT. It SHALL only create the
abstraction necessary for future integration. Future flow: Microphone -> VAD ->
STT -> VoiceIntentResolver -> Intent -> CommandBus" (spec.md #38)

This class starts at "already-transcribed text" - it never touches a microphone or
STT (matching the project's standing ROADMAP.md deferral of that whole subsystem).
Resolution is deliberately simple substring/phrase matching, not NLU/ML - adding a
real language-understanding dependency here would be exactly the kind of
speculative dependency apply.md #12 rules out for a task that only asks for the
abstraction. See jarvis.core.voice_input_provider (PHASE 10) for the sibling
"interface only, no STT" component this pairs with.
"""

import time

from jarvis.core.intents import Intent

# A small, optional starter set matching this app's own existing Spanish actions
# (see jarvis.voice's announcements) - NOT loaded by default, opt in explicitly.
DEFAULT_PHRASE_BINDINGS = {
    "bloquear sesion": "LOCK_SESSION",
    "bloquear la sesion": "LOCK_SESSION",
    "sacar captura": "SCREENSHOT",
    "tomar captura": "SCREENSHOT",
    "subir volumen": "VOLUME_UP",
    "bajar volumen": "VOLUME_DOWN",
}


class VoiceIntentResolver:
    def __init__(self, phrase_bindings=None):
        self._bindings = dict(phrase_bindings or {})

    def register(self, phrase, intent_name):
        self._bindings[phrase.strip().lower()] = intent_name

    def resolve(self, text):
        """text: already-transcribed text (as if STT already ran). Returns an
        Intent (source="VOICE") for the first registered phrase found as a
        substring of `text`, or None if nothing matched. Never touches audio."""
        if not text:
            return None
        normalized = text.strip().lower()
        for phrase, intent_name in self._bindings.items():
            if phrase in normalized:
                return Intent(
                    name=intent_name,
                    source="VOICE",
                    confidence=1.0,
                    timestamp=time.time(),
                    parameters={"raw_text": text, "matched_phrase": phrase},
                )
        return None
