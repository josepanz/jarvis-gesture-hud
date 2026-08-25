"""Command: the executable-operation contract every action SHALL eventually pass
through (spec.md #2.3, #26, #27; design.md #10, #11).

This task only introduces the abstraction (Command, CommandResult, CommandMetadata)
and the closed vocabularies for safety/status - no concrete command exists yet.
That is PHASE 2 (TASK-006 onward), which wraps the existing jarvis.os_native /
jarvis.gestures side effects one at a time. CommandBus (the thing that will
actually invoke Command.execute()) is TASK-004, also not implemented here.

Per apply.md #17 ("Errors SHALL be converted into controlled results"), a Command's
execute() implementation is expected to catch its own exceptions and return a
failed CommandResult rather than letting exceptions propagate - use the
CommandResult.ok()/rejected()/failed() factories to make that easy.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

# spec.md #27
VALID_SAFETY_LEVELS = frozenset({"SAFE", "CONFIRM_REQUIRED", "HOLD_REQUIRED", "DESTRUCTIVE"})

# spec.md #26 only gives one example status (EXECUTED). REJECTED (can_execute()
# returned False) and ERROR (execute() failed) are inferred here to make "errors
# can be represented" - TASK-003's acceptance criterion - actually meaningful.
# See the task report for this being called out explicitly.
VALID_STATUSES = frozenset({"EXECUTED", "REJECTED", "ERROR"})


@dataclass(frozen=True)
class CommandMetadata:
    """Static description of a command - not the result of running it."""

    name: str
    safety: str

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"name must be a non-empty string, got {self.name!r}")
        if self.safety not in VALID_SAFETY_LEVELS:
            raise ValueError(f"safety must be one of {sorted(VALID_SAFETY_LEVELS)}, got {self.safety!r}")


@dataclass(frozen=True)
class CommandResult:
    success: bool
    status: str
    message: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.success, bool):
            raise ValueError(f"success must be a bool, got {self.success!r}")

        if self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}, got {self.status!r}")
        if self.status == "EXECUTED" and not self.success:
            raise ValueError("status EXECUTED requires success=True")
        if self.status in ("REJECTED", "ERROR") and self.success:
            raise ValueError(f"status {self.status} requires success=False")
        if self.status == "ERROR" and not (isinstance(self.error, str) and self.error):
            raise ValueError("status ERROR requires a non-empty error message")

        if self.message is not None and not isinstance(self.message, str):
            raise ValueError(f"message must be a string or None, got {self.message!r}")

        if self.duration_ms is not None:
            if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, (int, float)):
                raise ValueError(f"duration_ms must be a number or None, got {self.duration_ms!r}")
            if self.duration_ms < 0:
                raise ValueError(f"duration_ms must be >= 0, got {self.duration_ms!r}")

        if self.error is not None and not isinstance(self.error, str):
            raise ValueError(f"error must be a string or None, got {self.error!r}")

        if not isinstance(self.metadata, dict):
            raise ValueError(f"metadata must be a dict, got {self.metadata!r}")

    @classmethod
    def ok(cls, message=None, duration_ms=None, metadata=None):
        return cls(success=True, status="EXECUTED", message=message, duration_ms=duration_ms, metadata=metadata or {})

    @classmethod
    def rejected(cls, message=None, metadata=None):
        return cls(success=False, status="REJECTED", message=message, metadata=metadata or {})

    @classmethod
    def failed(cls, error, message=None, duration_ms=None, metadata=None):
        return cls(
            success=False,
            status="ERROR",
            message=message,
            error=error,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )


class Command(ABC):
    """Contract every executable operation SHALL implement (spec.md #2.3).

    Commands MUST NOT depend directly on camera landmarks - by the time an Intent
    becomes a Command, it must already be expressed in terms the command itself
    understands (e.g. a target/amount), not raw hand-tracking data.
    """

    @property
    @abstractmethod
    def metadata(self) -> CommandMetadata:
        """Static description of this command (name + safety category)."""

    @abstractmethod
    def can_execute(self) -> bool:
        """Whether this command is currently safe/valid to run."""

    @abstractmethod
    def execute(self) -> CommandResult:
        """Run the command. MUST catch its own exceptions and return a failed
        CommandResult rather than raising (apply.md #17)."""

    def is_reversible(self) -> bool:
        return False

    def undo(self) -> CommandResult:
        raise NotImplementedError(f"{self.metadata.name} is not reversible")

    def redo(self) -> CommandResult:
        raise NotImplementedError(f"{self.metadata.name} is not reversible")
