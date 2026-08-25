"""VoiceInputProvider (TASK-047): interface only, per tasks.md: "Create only the
interface. Do NOT implement STT yet."

Matches this project's standing decision (ROADMAP.md / ARCHITECTURE.md "Future
work") to defer natural-language microphone control - heavy STT/LLM dependencies
and real-time audio/gesture synchronization complexity that hasn't been requested.
`poll()` always returns an empty list (never raises, never blocks); this class
exists purely so the rest of the pipeline can already depend on the InputProvider
contract for a voice source before STT exists, without pretending voice input
works today.
"""

from jarvis.core.input_provider import InputProvider


class VoiceInputProvider(InputProvider):
    @property
    def source(self):
        return "VOICE"

    def poll(self):
        return []
