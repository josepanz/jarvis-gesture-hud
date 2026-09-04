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
        # H-11: True mientras undo()/redo() ejecuta la accion inversa/repetida
        # del propio comando - explicito, no una inferencia sobre si el
        # dispatch vino o no del CommandBus (hoy undo()/redo() llaman
        # command.undo()/command.execute() directo, sin pasar por el bus, asi
        # que JarvisApp._on_command_result() nunca corre durante esta ventana
        # - pero ese detalle de implementacion podria cambiar, y el flag deja
        # la intencion escrita en vez de depender de eso en silencio).
        self._replaying = False

    def undo(self):
        entry = self._find_last_undoable()
        if entry is None:
            return CommandResult.rejected(message="nothing to undo")
        self._replaying = True
        try:
            result = entry.command.undo()
        finally:
            self._replaying = False
        if result.success:
            self._undone_ids.add(entry.command_id)
            self._redo_stack.append(entry)
        return result

    def redo(self):
        if not self._redo_stack:
            return CommandResult.rejected(message="nothing to redo")
        entry = self._redo_stack.pop()
        self._replaying = True
        try:
            result = entry.command.execute()
        finally:
            self._replaying = False
        if result.success:
            self._undone_ids.discard(entry.command_id)
        else:
            self._redo_stack.append(entry)  # redo failed - keep it available to retry
        return result

    def can_undo(self):
        return self._find_last_undoable() is not None

    def can_redo(self):
        return bool(self._redo_stack)

    @property
    def is_replaying(self):
        """True durante la ejecucion de undo()/redo() sobre el comando
        original - JarvisApp._on_command_result() lo usa para no invalidar
        el redo stack ante un dispatch que no es realmente "nuevo"."""
        return self._replaying

    def clear_redo(self):
        """H-11: un comando genuinamente nuevo invalida cualquier redo
        pendiente - como todo undo/redo real. Llamado desde
        JarvisApp._on_command_result(), nunca desde aca mismo (undo() ya
        hace su propio push a `_redo_stack`, que esto destruiria)."""
        self._redo_stack = []

    def _find_last_undoable(self):
        for entry in reversed(self._history.entries()):
            if entry.undo_available and entry.command_id not in self._undone_ids:
                return entry
        return None
