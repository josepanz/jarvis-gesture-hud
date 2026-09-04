"""LLMIntentResolver: resolves freeform transcribed speech into one of a fixed,
validated action vocabulary via a small local LLM (llama-cpp-python + a
quantized GGUF model) - no cloud, fully offline, matching this project's
existing offline-only design (pyttsx3 TTS, on-device MediaPipe, local
faster-whisper STT).

Model choice: Qwen2.5-1.5B-Instruct (Q4_K_M quantization, ~1GB) - the
practical "lightweight and capable enough" pick for this task: strong
multilingual (incl. Spanish) instruction-following at a size that runs in
real time on CPU, without a 3B+ model's latency or the 0.5B tier's
unreliability. Downloaded once and cached under jarvis.paths.assets_dir(),
same pattern as jarvis.hand_tracker's mediapipe model.

The LLM's raw output is NEVER trusted directly (spec.md #38's safety
requirement - same rule jarvis.core.voice_intent_resolver.VoiceIntentResolver
already follows): resolve() requires the model to emit strict
{"action": "NAME"} JSON and validates NAME against VALID_ACTIONS before
returning anything. Any parse/validation failure returns None rather than
guessing.

This is the fallback path only - jarvis.main tries the free, deterministic
VoiceIntentResolver phrase match first and only reaches this (heavier) model
when that finds nothing.
"""

import json
import re
import time
import urllib.request

from jarvis.core.intents import Intent
from jarvis.paths import assets_dir

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"

VALID_ACTIONS = frozenset(
    {
        "LOCK_SESSION",
        "SCREENSHOT",
        "VOLUME_UP",
        "VOLUME_DOWN",
        "MUTE",
        "RIGHT_CLICK",
        "SCROLL_UP",
        "SCROLL_DOWN",
        "SCROLL_LEFT",
        "SCROLL_RIGHT",
        "ZOOM_IN",
        "ZOOM_OUT",
        "KEYBOARD_TOGGLE",
        "CLOSE_APP",
        "UNDO",
        "REDO",
    }
)

_SYSTEM_PROMPT = (
    "Eres un interprete de comandos de voz para un asistente de escritorio. "
    "Tu unica tarea es leer una frase en espanol y devolver la accion mas "
    "parecida de esta lista fija, en JSON estricto: "
    f"{sorted(VALID_ACTIONS)}. "
    'Responde SOLO con {"action": "NOMBRE"}. Si ninguna accion de la lista '
    'corresponde a la frase, responde {"action": "NONE"}.'
)

_JSON_RE = re.compile(r"\{[^{}]*\}")


def _ensure_model_path():
    model_path = assets_dir() / MODEL_FILENAME
    model_path.parent.mkdir(parents=True, exist_ok=True)
    if not model_path.exists():
        urllib.request.urlretrieve(MODEL_URL, model_path)
    return model_path


class LLMIntentResolver:
    def __init__(self, model_path=None):
        self._model_path = model_path
        self._llm = None  # lazy-loaded on first resolve(), not at construction

    def _ensure_llm(self):
        if self._llm is None:
            from llama_cpp import Llama

            path = self._model_path or _ensure_model_path()
            self._llm = Llama(model_path=str(path), n_ctx=512, verbose=False)
        return self._llm

    def resolve(self, text):
        """text: already-transcribed speech. Returns an Intent (source=
        "VOICE_LLM") for a validated action, or None if the model produced no
        parseable JSON, an action outside VALID_ACTIONS, or explicitly
        returned NONE. Never raises on a malformed model response - treated
        the same as "no match"."""
        if not text or not text.strip():
            return None

        llm = self._ensure_llm()
        prompt = (
            f"<|im_start|>system\n{_SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n"
        )
        response = llm(prompt, max_tokens=32, temperature=0.0, stop=["<|im_end|>"])
        raw = response["choices"][0]["text"]

        match = _JSON_RE.search(raw)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

        action = parsed.get("action")
        if action not in VALID_ACTIONS:
            return None

        return Intent(
            name=action,
            source="VOICE_LLM",
            confidence=1.0,
            timestamp=time.time(),
            parameters={"raw_text": text},
        )
