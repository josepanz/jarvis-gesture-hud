"""Concrete Commands wrapping the EXISTING jarvis.os_native.CrossPlatformOS calls
(TASK-013). Safety categories per spec.md #27's own examples: VolumeUp=SAFE,
Screenshot=SAFE, LockWorkstation=HOLD_REQUIRED.
"""

from jarvis.core.commands import Command, CommandMetadata, CommandResult
from jarvis.os_native import CrossPlatformOS


class VolumeUpCommand(Command):
    """TASK-040: reversible. There is no OS volume-level query anywhere in this
    project (CrossPlatformOS only presses relative media keys) - undo() therefore
    means "press the opposite key once" (a best-effort symmetric nudge), NOT
    "restore the exact prior volume level" the way spec.md #28's own example
    describes. That exact-restore semantics isn't achievable with what this app
    can currently observe about the OS, and pretending otherwise would violate
    spec.md #28's "MUST NOT pretend an action is reversible when it cannot safely
    restore the previous state" - so this docstring says plainly what undo here
    actually does."""

    @property
    def metadata(self):
        return CommandMetadata(name="VolumeUp", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            CrossPlatformOS.volume_up()
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="VolumeUp failed")

    def is_reversible(self):
        return True

    def undo(self):
        try:
            CrossPlatformOS.volume_down()
            return CommandResult.ok(message="volume nudge reversed (pressed volume-down once)")
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="VolumeUp undo failed")


class VolumeDownCommand(Command):
    """TASK-040: reversible - see VolumeUpCommand's docstring for the same
    best-effort-symmetric-nudge caveat (applies here in the opposite direction)."""

    @property
    def metadata(self):
        return CommandMetadata(name="VolumeDown", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            CrossPlatformOS.volume_down()
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="VolumeDown failed")

    def is_reversible(self):
        return True

    def undo(self):
        try:
            CrossPlatformOS.volume_up()
            return CommandResult.ok(message="volume nudge reversed (pressed volume-up once)")
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="VolumeDown undo failed")


class MuteCommand(Command):
    """No gesture currently triggers this - same gap that existed before this
    migration (see task report). Included for completeness of "system actions"."""

    @property
    def metadata(self):
        return CommandMetadata(name="Mute", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            CrossPlatformOS.volume_mute()
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="Mute failed")


class ScreenshotCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="Screenshot", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            path = CrossPlatformOS.take_screenshot()
            return CommandResult.ok(message=f"saved to {path}", metadata={"path": str(path)})
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="Screenshot failed")


class LockSessionCommand(Command):
    """HOLD_REQUIRED per spec.md #27's own example. The 1.5s hold is already
    enforced upstream by GestureEngine before this Command is ever dispatched -
    CommandBus doesn't gate HOLD_REQUIRED yet (see TASK-004 report NOTES), so this
    declaration documents an already-satisfied precondition rather than adding new
    runtime behavior."""

    @property
    def metadata(self):
        return CommandMetadata(name="LockSession", safety="HOLD_REQUIRED")

    def can_execute(self):
        return True

    def execute(self):
        try:
            CrossPlatformOS.lock_session()
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="LockSession failed")
