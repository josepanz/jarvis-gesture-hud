"""CommandBus: the single place that actually invokes Command.execute() (spec.md #25).

Flow implemented here (tasks.md TASK-004's own, narrower flow - not yet the full
7-step spec.md #25 list, see NOTES in the task report):

    Command -> validate -> check safety -> can_execute -> execute -> CommandResult

`generate telemetry` (TASK-034), `update history when reversible` (TASK-039) and a
real `FeedbackManager` (TASK-005) don't exist yet. Rather than hardcode a dependency
on classes that aren't built, CommandBus accepts an optional `on_result` callback
invoked after every dispatch - that's the extension point those future tasks hook
into. If that callback raises, it's logged and swallowed: per apply.md #18/#26, a
feedback/telemetry failure MUST NOT take down command execution.
"""

import logging
import time
from dataclasses import replace

from jarvis.core.commands import Command, CommandResult

_DESTRUCTIVE_REJECTION = (
    "{name} is DESTRUCTIVE - spec.md #27 requires this MUST NOT run without an "
    "explicit confirmation mechanism, which does not exist yet."
)


class CommandBus:
    def __init__(self, on_result=None, logger=None):
        """`on_result(command, result)` is called after every dispatch, success or
        not. Future FeedbackManager/TelemetryManager hook in here."""
        self._on_result = on_result
        self._logger = logger or logging.getLogger("jarvis.command_bus")

    def dispatch(self, command) -> CommandResult:
        """Never raises - always returns a CommandResult, even for a completely
        malformed `command` or an internal bug in this method itself."""
        started = time.monotonic()
        try:
            result = self._dispatch(command, started)
        except Exception as exc:  # last-resort guard: dispatch() itself must not raise
            self._logger.exception("CommandBus.dispatch() internal error")
            result = CommandResult.failed(error=str(exc), message="CommandBus.dispatch() internal error")
            self._log_result("<unknown>", result, self._elapsed_ms(started))
        return result

    def _dispatch(self, command, started) -> CommandResult:
        # 1. validate
        if not isinstance(command, Command):
            result = CommandResult.failed(error=f"not a Command instance: {command!r}")
            self._log_result("<invalid>", result, self._elapsed_ms(started))
            return result

        name = command.metadata.name

        # 2. check safety
        if command.metadata.safety == "DESTRUCTIVE":
            result = CommandResult.rejected(message=_DESTRUCTIVE_REJECTION.format(name=name))
            result = self._finish(command, name, result, started)
            return result

        # 3. can_execute
        try:
            can_run = command.can_execute()
        except Exception as exc:
            result = CommandResult.failed(error=str(exc), message=f"{name}.can_execute() raised")
            result = self._finish(command, name, result, started)
            return result

        if not can_run:
            result = CommandResult.rejected(message=f"{name}.can_execute() returned False")
            result = self._finish(command, name, result, started)
            return result

        # 4. execute
        try:
            result = command.execute()
        except Exception as exc:
            result = CommandResult.failed(error=str(exc), message=f"{name}.execute() raised")

        if not isinstance(result, CommandResult):
            result = CommandResult.failed(
                error=f"{name}.execute() did not return a CommandResult (got {result!r})"
            )

        result = self._finish(command, name, result, started)
        return result

    def _finish(self, command, name, result, started):
        duration_ms = self._elapsed_ms(started)
        if result.duration_ms is None:
            result = replace(result, duration_ms=duration_ms)
        self._log_result(name, result, duration_ms)
        self._notify(command, result)
        return result

    def _notify(self, command, result):
        if self._on_result is None:
            return
        try:
            self._on_result(command, result)
        except Exception:
            self._logger.exception("on_result callback raised for %s", command.metadata.name)

    def _log_result(self, name, result, duration_ms):
        detail = result.error or result.message or ""
        if result.success:
            self._logger.info("%s -> %s (%.1fms) %s", name, result.status, duration_ms, detail)
        else:
            self._logger.warning("%s -> %s (%.1fms) %s", name, result.status, duration_ms, detail)

    @staticmethod
    def _elapsed_ms(started):
        return (time.monotonic() - started) * 1000
