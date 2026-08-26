"""VoiceListener: real microphone capture + STT via faster-whisper.

Lazy imports (sounddevice, faster_whisper) matching this project's convention
for optional heavy deps: the base app and its full test suite run without
these packages installed; only actual voice usage requires
requirements-voice.txt (see that file for why).

Push-to-talk (toggle-to-record via a key press, not held) beats wake-word
detection here: no extra model/dependency (openWakeWord) needed, matching
this project's standing "no speculative dependencies for what wasn't asked"
discipline. It also fits this app's per-frame `cv2.waitKey` polling, which
has no real key-up event to hold against.

poll_result() delivers ("text", value, confidence) or ("error", message, 0.0).
confidence is faster-whisper's own `1 - no_speech_prob` per segment - a real
model-provided signal, not an invented heuristic, so jarvis.core.confidence.
ConfidenceFilter has something genuine to filter on for voice (unlike camera
gestures, which are threshold/boolean - see jarvis.main's module docstring).
"""

import queue
import threading

import numpy as np

SAMPLE_RATE = 16000


class VoiceListener:
    """model_size: faster-whisper model name. "base" is the recommended
    default - solid multilingual/Spanish accuracy on CPU in real time for
    short push-to-talk utterances. "tiny" trades accuracy for speed on very
    low-end hardware; "small"/"medium" trade speed for accuracy given a GPU
    or tolerance for slower transcription."""

    def __init__(self, model_size="base", language="es"):
        self._model_size = model_size
        self._language = language
        self._model = None  # lazy-loaded on first transcription, not at construction
        self._recording = False
        self._frames = []
        self._stream = None
        self._results = queue.Queue()

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        return self._model

    def start(self):
        """Begins recording from the default microphone. No-op if already recording."""
        if self._recording:
            return
        import sounddevice as sd

        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._on_audio)
        self._stream.start()

    def _on_audio(self, indata, frames, time_info, status):
        self._frames.append(indata.copy())

    def stop(self):
        """Stops recording and transcribes in a background thread so the caller
        (the camera loop) never blocks on STT. Result arrives via poll_result().
        No-op if not currently recording."""
        if not self._recording:
            return
        self._recording = False
        self._stream.stop()
        self._stream.close()
        self._stream = None
        audio = np.concatenate(self._frames, axis=0).flatten() if self._frames else np.zeros(0, dtype="float32")
        self._frames = []
        threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()

    def _transcribe(self, audio):
        try:
            model = self._ensure_model()
            segments, _info = model.transcribe(audio, language=self._language)
            segments = list(segments)
            text = "".join(segment.text for segment in segments).strip()
            confidence = (
                sum(1.0 - getattr(segment, "no_speech_prob", 0.0) for segment in segments) / len(segments)
                if segments
                else 0.0
            )
        except Exception as exc:
            self._results.put(("error", str(exc), 0.0))
            return
        self._results.put(("text", text, confidence))

    def poll_result(self):
        """Non-blocking. Returns the next (kind, value, confidence) tuple or
        None if nothing is ready yet. Never blocks, never raises for "nothing
        yet"."""
        try:
            return self._results.get_nowait()
        except queue.Empty:
            return None

    @property
    def recording(self):
        return self._recording
