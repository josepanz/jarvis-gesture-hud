"""UndoRedoController (TASK-041 undo(), TASK-042 redo(), spec.md #28).

"Only commands that can reliably restore previous state SHALL support undo...
The system MUST NOT pretend an action is reversible when it cannot safely restore
the previous state." Sits on top of a CommandHistory (TASK-039): undo() finds the
most recent undoable, not-yet-undone entry and calls its command.undo(); redo()
re-executes the most recently undone entry via command.execute().

`HistoryEntry` is immutable (matching this project's data-model convention
throughout PHASE 1-9), so "already undone" state is tracked here rather than by
mutating history entries in place - keeps CommandHistory a pure, simple store and
this class the only place that knows about undo/redo state.

Standalone, not wired into jarvis.main.JarvisApp - see PHASE 9 task report.
"""

from jarvis.core.commands import CommandResult


class UndoRedoController:
    def __init__(self, history):
        self._history = history
        self._undone_ids = set()
        self._redo_stack = []

    def undo(self):
        entry = self._find_last_undoable()
        if entry is None:
            return CommandResult.rejected(message="nothing to undo")
        result = entry.command.undo()
        if result.success:
            self._undone_ids.add(entry.command_id)
            self._redo_stack.append(entry)
        return result

    def redo(self):
        if not self._redo_stack:
            return CommandResult.rejected(message="nothing to redo")
        entry = self._redo_stack.pop()
        result = entry.command.execute()
        if result.success:
            self._undone_ids.discard(entry.command_id)
        else:
            self._redo_stack.append(entry)  # redo failed - keep it available to retry
        return result

    def can_undo(self):
        return self._find_last_undoable() is not None

    def can_redo(self):
        return bool(self._redo_stack)

    def _find_last_undoable(self):
        for entry in reversed(self._history.entries()):
            if entry.undo_available and entry.command_id not in self._undone_ids:
                return entry
        return None
