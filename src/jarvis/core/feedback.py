"""FeedbackManager: centralizes user-facing feedback across channels (spec.md #30).

Adapter over the EXISTING feedback mechanisms already in this project - it does
NOT reimplement TTS or the HUD. `jarvis.voice.VoiceJarvis` and
`jarvis.overlay.ScreenOverlay` are untouched; this wraps them behind one interface
so a future caller (main.py, once a later task migrates it) doesn't need to know
which concrete backend handles which channel.

There is no "sound" subsystem anywhere in this project (no sound effects were ever
implemented) - the `sound` channel exists at the abstraction level per spec.md #30,
but is a no-op/failure unless a sound backend callable is explicitly injected.

Per apply.md #26, a feedback failure in one channel MUST NOT crash the caller or
block the other requested channels - notify() never raises, it reports a per-channel
outcome instead.
"""

import logging


class FeedbackManager:
    def __init__(
        self,
        voice=None,
        hud=None,
        sound=None,
        enabled_channels=None,
        default_position=None,
        logger=None,
    ):
        """voice: object with .speak(text) - e.g. jarvis.voice.VoiceJarvis.
        hud: object with .show_bubble(text, x, y) - e.g. jarvis.overlay.ScreenOverlay.
        sound: optional callable(message) -> None. No concrete backend exists yet.
        default_position: (x, y) tuple or zero-arg callable returning one, used by the
            "hud" channel when notify() isn't given an explicit position.
        """
        self._voice = voice
        self._hud = hud
        self._sound = sound
        self._default_position = default_position
        self._enabled = set(enabled_channels) if enabled_channels is not None else {"hud", "tts", "sound", "silent"}
        self._logger = logger or logging.getLogger("jarvis.feedback")

    def notify(self, message, channels=("hud", "tts"), position=None):
        """Send `message` through each of `channels` that is currently enabled.
        Never raises - returns {channel: "sent" | "disabled" | "failed"}."""
        results = {}
        for channel in channels:
            if channel not in self._enabled:
                results[channel] = "disabled"
                continue
            try:
                self._dispatch_channel(channel, message, position)
                results[channel] = "sent"
            except Exception:
                self._logger.exception("feedback channel %r failed for message %r", channel, message)
                results[channel] = "failed"
        return results

    def notify_command_result(self, command, result, channels=("hud", "tts"), position=None):
        """Convenience formatter shaped to match CommandBus's `on_result(command, result)`
        hook (see command_bus.py). NOT wired to it automatically - a future task decides
        whether/how the two get connected."""
        message = result.message or result.error or f"{command.metadata.name}: {result.status}"
        return self.notify(message, channels=channels, position=position)

    def set_channel_enabled(self, channel, enabled):
        if enabled:
            self._enabled.add(channel)
        else:
            self._enabled.discard(channel)

    def is_channel_enabled(self, channel):
        return channel in self._enabled

    def _dispatch_channel(self, channel, message, position):
        if channel == "silent":
            return
        if channel == "tts":
            if self._voice is None:
                raise RuntimeError("no voice backend configured")
            self._voice.speak(message)
        elif channel == "hud":
            if self._hud is None:
                raise RuntimeError("no HUD backend configured")
            x, y = self._resolve_position(position)
            self._hud.show_bubble(message, x, y)
        elif channel == "sound":
            if self._sound is None:
                raise RuntimeError("no sound backend configured")
            self._sound(message)
        else:
            raise ValueError(f"unknown feedback channel: {channel!r}")

    def _resolve_position(self, position):
        if position is not None:
            return position
        if self._default_position is None:
            raise RuntimeError("no HUD position given and no default_position configured")
        return self._default_position() if callable(self._default_position) else self._default_position
