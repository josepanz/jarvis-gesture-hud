"""CommandHistory (TASK-039, spec.md #29, design.md #12).

"History SHOULD store: command_id, command_name, timestamp, parameters, result,
undo_available. Default history size: 50. This MUST be configurable." (spec.md #29)

"The command history SHALL NOT contain raw camera data." (design.md #12) - every
concrete Command in this project (jarvis.actions.*) only ever stores simple values
(ints, floats, short strings) as constructor parameters, never landmarks/frames, so
reflecting a command's public attributes into `parameters` (see `_extract_parameters`
below) can't leak camera data as long as that convention holds.

`CommandHistory.record(command, result)` has the exact same `(command, result)`
signature as `jarvis.core.command_bus.CommandBus`'s `on_result` hook - a natural
fit if a future integration wants to wire them together directly. NOT done
automatically here (see PHASE 9 task report).
"""

import time
import uuid
from collections import deque
from dataclasses import dataclass

from jarvis.core.commands import Command, CommandResult

DEFAULT_MAX_SIZE = 50


def _extract_parameters(command):
    if isinstance(getattr(command, "parameters", None), dict):
        return dict(command.parameters)
    return {k: v for k, v in vars(command).items() if not k.startswith("_")}


@dataclass(frozen=True)
class HistoryEntry:
    command_id: str
    command_name: str
    timestamp: float
    parameters: dict
    result: CommandResult
    undo_available: bool
    command: Command

    def __post_init__(self):
        if not isinstance(self.command_id, str) or not self.command_id:
            raise ValueError(f"command_id must be a non-empty string, got {self.command_id!r}")
        if not isinstance(self.command_name, str) or not self.command_name:
            raise ValueError(f"command_name must be a non-empty string, got {self.command_name!r}")
        if self.timestamp is None or isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)):
            raise ValueError(f"timestamp must be a number, got {self.timestamp!r}")
        if not isinstance(self.parameters, dict):
            raise ValueError(f"parameters must be a dict, got {self.parameters!r}")
        if not isinstance(self.result, CommandResult):
            raise ValueError(f"result must be a CommandResult, got {self.result!r}")
        if not isinstance(self.undo_available, bool):
            raise ValueError(f"undo_available must be a bool, got {self.undo_available!r}")
        if not isinstance(self.command, Command):
            raise ValueError(f"command must be a Command instance, got {self.command!r}")


class CommandHistory:
    def __init__(self, max_size=DEFAULT_MAX_SIZE):
        if max_size < 1:
            raise ValueError(f"max_size must be >= 1, got {max_size!r}")
        self._entries = deque(maxlen=max_size)

    def record(self, command, result):
        if not isinstance(command, Command):
            raise ValueError(f"command must be a Command instance, got {command!r}")
        if not isinstance(result, CommandResult):
            raise ValueError(f"result must be a CommandResult, got {result!r}")

        entry = HistoryEntry(
            command_id=uuid.uuid4().hex,
            command_name=command.metadata.name,
            timestamp=time.time(),
            parameters=_extract_parameters(command),
            result=result,
            # A failed execution didn't actually change anything, so there's
            # nothing meaningful to undo even if the command class supports it.
            undo_available=command.is_reversible() and result.success,
            command=command,
        )
        self._entries.append(entry)
        return entry

    def entries(self, limit=None):
        items = list(self._entries)
        if limit is not None:
            items = items[-limit:]
        return items

    def last(self):
        return self._entries[-1] if self._entries else None

    def __len__(self):
        return len(self._entries)
