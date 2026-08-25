"""Unit tests for UndoRedoController (TASK-041/042)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.command_history import CommandHistory  # noqa: E402
from jarvis.core.commands import Command, CommandMetadata, CommandResult  # noqa: E402
from jarvis.core.undo_redo import UndoRedoController  # noqa: E402


class _ReversibleCommand(Command):
    def __init__(self, name="Reversible", undo_succeeds=True, execute_succeeds=True):
        self._name = name
        self.undo_succeeds = undo_succeeds
        self.execute_succeeds = execute_succeeds
        self.execute_calls = 0
        self.undo_calls = 0

    @property
    def metadata(self):
        return CommandMetadata(name=self._name, safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        self.execute_calls += 1
        return CommandResult.ok() if self.execute_succeeds else CommandResult.failed(error="redo failed")

    def is_reversible(self):
        return True

    def undo(self):
        self.undo_calls += 1
        return CommandResult.ok() if self.undo_succeeds else CommandResult.failed(error="undo failed")


class _IrreversibleCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="Irreversible", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        return CommandResult.ok()


class UndoTests(unittest.TestCase):
    def test_undo_with_empty_history_is_rejected(self):
        controller = UndoRedoController(CommandHistory())
        result = controller.undo()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "REJECTED")

    def test_undo_calls_the_command_undo_method(self):
        history = CommandHistory()
        cmd = _ReversibleCommand()
        history.record(cmd, CommandResult.ok())
        controller = UndoRedoController(history)
        result = controller.undo()
        self.assertEqual(cmd.undo_calls, 1)
        self.assertTrue(result.success)

    def test_undo_skips_irreversible_commands(self):
        history = CommandHistory()
        history.record(_IrreversibleCommand(), CommandResult.ok())
        controller = UndoRedoController(history)
        result = controller.undo()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "REJECTED")

    def test_undo_finds_the_most_recent_undoable_skipping_irreversible_ones_after_it(self):
        history = CommandHistory()
        reversible = _ReversibleCommand()
        history.record(reversible, CommandResult.ok())
        history.record(_IrreversibleCommand(), CommandResult.ok())
        controller = UndoRedoController(history)
        controller.undo()
        self.assertEqual(reversible.undo_calls, 1)

    def test_calling_undo_twice_undoes_two_different_commands(self):
        history = CommandHistory()
        first = _ReversibleCommand(name="First")
        second = _ReversibleCommand(name="Second")
        history.record(first, CommandResult.ok())
        history.record(second, CommandResult.ok())
        controller = UndoRedoController(history)

        controller.undo()
        self.assertEqual(second.undo_calls, 1)
        self.assertEqual(first.undo_calls, 0)

        controller.undo()
        self.assertEqual(first.undo_calls, 1)

    def test_undo_does_not_repeat_once_history_is_exhausted(self):
        history = CommandHistory()
        cmd = _ReversibleCommand()
        history.record(cmd, CommandResult.ok())
        controller = UndoRedoController(history)
        controller.undo()
        result = controller.undo()
        self.assertFalse(result.success)
        self.assertEqual(cmd.undo_calls, 1)

    def test_failed_undo_does_not_mark_the_entry_as_undone(self):
        history = CommandHistory()
        cmd = _ReversibleCommand(undo_succeeds=False)
        history.record(cmd, CommandResult.ok())
        controller = UndoRedoController(history)
        controller.undo()
        self.assertTrue(controller.can_undo())  # still available - the undo itself failed

    def test_can_undo(self):
        history = CommandHistory()
        controller = UndoRedoController(history)
        self.assertFalse(controller.can_undo())
        history.record(_ReversibleCommand(), CommandResult.ok())
        self.assertTrue(controller.can_undo())


class RedoTests(unittest.TestCase):
    def test_redo_with_nothing_undone_is_rejected(self):
        controller = UndoRedoController(CommandHistory())
        result = controller.redo()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "REJECTED")

    def test_redo_re_executes_the_undone_command(self):
        history = CommandHistory()
        cmd = _ReversibleCommand()
        history.record(cmd, CommandResult.ok())
        controller = UndoRedoController(history)
        controller.undo()
        result = controller.redo()
        self.assertEqual(cmd.execute_calls, 1)
        self.assertTrue(result.success)

    def test_can_redo_after_undo(self):
        history = CommandHistory()
        history.record(_ReversibleCommand(), CommandResult.ok())
        controller = UndoRedoController(history)
        self.assertFalse(controller.can_redo())
        controller.undo()
        self.assertTrue(controller.can_redo())

    def test_undo_then_redo_then_undo_again_works(self):
        history = CommandHistory()
        cmd = _ReversibleCommand()
        history.record(cmd, CommandResult.ok())
        controller = UndoRedoController(history)

        controller.undo()
        controller.redo()
        result = controller.undo()

        self.assertTrue(result.success)
        self.assertEqual(cmd.undo_calls, 2)

    def test_failed_redo_keeps_entry_available_to_retry(self):
        history = CommandHistory()
        cmd = _ReversibleCommand(execute_succeeds=False)
        history.record(cmd, CommandResult.ok())
        controller = UndoRedoController(history)
        controller.undo()
        result = controller.redo()
        self.assertFalse(result.success)
        self.assertTrue(controller.can_redo())  # still there to retry


if __name__ == "__main__":
    unittest.main()
