"""Voz Jarvis offline (pyttsx3) en hilo propio, con interrupcion inmediata por gesto."""

import queue
import threading

import pyttsx3


class VoiceJarvis:
    def __init__(self, language_hint="spanish"):
        self._queue = queue.Queue()
        self._engine = pyttsx3.init()
        self._select_voice(language_hint)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _select_voice(self, language_hint):
        for voice in self._engine.getProperty("voices"):
            haystack = f"{voice.id} {voice.name} {' '.join(getattr(voice, 'languages', []) or [])}".lower()
            if language_hint in haystack or "es" in haystack.split():
                self._engine.setProperty("voice", voice.id)
                return

    def _run(self):
        while True:
            text = self._queue.get()
            self._engine.say(text)
            self._engine.runAndWait()

    def speak(self, text):
        self._queue.put(text)

    def silence(self):
        """Corta la frase actual y vacia la cola de inmediato (gesto de silencio)."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._engine.stop()
