"""Unit tests for CommandHistory/HistoryEntry (TASK-039)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.command_history import CommandHistory  # noqa: E402
from jarvis.core.commands import Command, CommandMetadata, CommandResult  # noqa: E402


class _MoveCommand(Command):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @property
    def metadata(self):
        return CommandMetadata(name="Move", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        return CommandResult.ok()


class _ReversibleCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="Reversible", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        return CommandResult.ok()

    def is_reversible(self):
        return True

    def undo(self):
        return CommandResult.ok()


class CommandHistoryRecordTests(unittest.TestCase):
    def test_record_returns_a_populated_entry(self):
        history = CommandHistory()
        cmd = _MoveCommand(10, 20)
        entry = history.record(cmd, CommandResult.ok())
        self.assertEqual(entry.command_name, "Move")
        self.assertEqual(entry.parameters, {"x": 10, "y": 20})
        self.assertIs(entry.command, cmd)
        self.assertTrue(entry.command_id)

    def test_each_entry_gets_a_unique_id(self):
        history = CommandHistory()
        e1 = history.record(_MoveCommand(0, 0), CommandResult.ok())
        e2 = history.record(_MoveCommand(0, 0), CommandResult.ok())
        self.assertNotEqual(e1.command_id, e2.command_id)

    def test_non_reversible_command_is_never_undo_available(self):
        history = CommandHistory()
        entry = history.record(_MoveCommand(0, 0), CommandResult.ok())
        self.assertFalse(entry.undo_available)

    def test_reversible_command_with_success_is_undo_available(self):
        history = CommandHistory()
        entry = history.record(_ReversibleCommand(), CommandResult.ok())
        self.assertTrue(entry.undo_available)

    def test_reversible_command_with_failed_result_is_not_undo_available(self):
        history = CommandHistory()
        entry = history.record(_ReversibleCommand(), CommandResult.failed(error="boom"))
        self.assertFalse(entry.undo_available)  # nothing actually changed - nothing to undo

    def test_rejects_non_command(self):
        with self.assertRaises(ValueError):
            CommandHistory().record("not a command", CommandResult.ok())

    def test_rejects_non_result(self):
        with self.assertRaises(ValueError):
            CommandHistory().record(_MoveCommand(0, 0), "not a result")


class CommandHistoryQueryTests(unittest.TestCase):
    def test_last_returns_most_recent_entry(self):
        history = CommandHistory()
        history.record(_MoveCommand(1, 1), CommandResult.ok())
        last_cmd = _MoveCommand(2, 2)
        history.record(last_cmd, CommandResult.ok())
        self.assertIs(history.last().command, last_cmd)

    def test_last_on_empty_history_is_none(self):
        self.assertIsNone(CommandHistory().last())

    def test_entries_returns_oldest_first(self):
        history = CommandHistory()
        history.record(_MoveCommand(1, 1), CommandResult.ok())
        history.record(_MoveCommand(2, 2), CommandResult.ok())
        entries = history.entries()
        self.assertEqual([e.parameters["x"] for e in entries], [1, 2])

    def test_entries_limit(self):
        history = CommandHistory()
        for i in range(5):
            history.record(_MoveCommand(i, i), CommandResult.ok())
        entries = history.entries(limit=2)
        self.assertEqual([e.parameters["x"] for e in entries], [3, 4])

    def test_len_reflects_entry_count(self):
        history = CommandHistory()
        self.assertEqual(len(history), 0)
        history.record(_MoveCommand(0, 0), CommandResult.ok())
        self.assertEqual(len(history), 1)


class CommandHistoryBoundedSizeTests(unittest.TestCase):
    def test_default_max_size_is_50(self):
        history = CommandHistory()
        for i in range(60):
            history.record(_MoveCommand(i, i), CommandResult.ok())
        self.assertEqual(len(history), 50)
        self.assertEqual(history.entries()[0].parameters["x"], 10)  # oldest 10 fell off

    def test_max_size_is_configurable(self):
        history = CommandHistory(max_size=3)
        for i in range(5):
            history.record(_MoveCommand(i, i), CommandResult.ok())
        self.assertEqual(len(history), 3)
        self.assertEqual([e.parameters["x"] for e in history.entries()], [2, 3, 4])

    def test_invalid_max_size_rejected(self):
        with self.assertRaises(ValueError):
            CommandHistory(max_size=0)


if __name__ == "__main__":
    unittest.main()
