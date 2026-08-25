"""Unit tests for the Command abstraction (TASK-003, multimodal-interaction-core)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.commands import (  # noqa: E402
    Command,
    CommandMetadata,
    CommandResult,
    VALID_SAFETY_LEVELS,
)


class _AlwaysSucceedsCommand(Command):
    """Minimal concrete command used to exercise the abstract contract."""

    def __init__(self):
        self.executed = False

    @property
    def metadata(self):
        return CommandMetadata(name="AlwaysSucceeds", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        self.executed = True
        return CommandResult.ok(message="did the thing", duration_ms=5)


class _AlwaysFailsCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="AlwaysFails", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            return CommandResult.failed(error=str(exc), message="could not do the thing")


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
        return CommandResult.ok(message="undone")


class CommandMetadataTests(unittest.TestCase):
    def test_valid_metadata(self):
        meta = CommandMetadata(name="VolumeUp", safety="SAFE")
        self.assertEqual(meta.name, "VolumeUp")
        self.assertEqual(meta.safety, "SAFE")

    def test_all_documented_safety_levels_accepted(self):
        for safety in VALID_SAFETY_LEVELS:
            CommandMetadata(name="X", safety=safety)

    def test_unknown_safety_level_rejected(self):
        with self.assertRaises(ValueError):
            CommandMetadata(name="X", safety="TOTALLY_FINE")

    def test_name_required(self):
        with self.assertRaises(ValueError):
            CommandMetadata(name="", safety="SAFE")


class CommandResultTests(unittest.TestCase):
    def test_ok_factory_produces_consistent_success_result(self):
        result = CommandResult.ok(message="volume increased", duration_ms=12)
        self.assertTrue(result.success)
        self.assertEqual(result.status, "EXECUTED")
        self.assertIsNone(result.error)

    def test_rejected_factory(self):
        result = CommandResult.rejected(message="not safe to run right now")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "REJECTED")

    def test_failed_factory_requires_error_message(self):
        result = CommandResult.failed(error="device not found")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.error, "device not found")

    def test_executed_status_requires_success_true(self):
        with self.assertRaises(ValueError):
            CommandResult(success=False, status="EXECUTED")

    def test_error_status_requires_success_false(self):
        with self.assertRaises(ValueError):
            CommandResult(success=True, status="ERROR", error="x")

    def test_error_status_requires_error_message(self):
        with self.assertRaises(ValueError):
            CommandResult(success=False, status="ERROR")
        with self.assertRaises(ValueError):
            CommandResult(success=False, status="ERROR", error="")

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            CommandResult(success=True, status="DONE_I_GUESS")

    def test_duration_ms_must_be_non_negative(self):
        with self.assertRaises(ValueError):
            CommandResult.ok(duration_ms=-1)

    def test_metadata_must_be_dict(self):
        with self.assertRaises(ValueError):
            CommandResult(success=True, status="EXECUTED", metadata=["nope"])

    def test_result_is_immutable(self):
        result = CommandResult.ok()
        with self.assertRaises(Exception):
            result.success = False


class CommandContractTests(unittest.TestCase):
    def test_command_cannot_be_instantiated_directly(self):
        with self.assertRaises(TypeError):
            Command()

    def test_concrete_command_executes(self):
        cmd = _AlwaysSucceedsCommand()
        self.assertTrue(cmd.can_execute())
        result = cmd.execute()
        self.assertTrue(result.success)
        self.assertTrue(cmd.executed)

    def test_concrete_command_can_report_failure_without_raising(self):
        cmd = _AlwaysFailsCommand()
        result = cmd.execute()
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")
        self.assertIn("boom", result.error)

    def test_default_command_is_not_reversible(self):
        cmd = _AlwaysSucceedsCommand()
        self.assertFalse(cmd.is_reversible())
        with self.assertRaises(NotImplementedError):
            cmd.undo()
        with self.assertRaises(NotImplementedError):
            cmd.redo()

    def test_command_can_opt_into_reversibility(self):
        cmd = _ReversibleCommand()
        self.assertTrue(cmd.is_reversible())
        result = cmd.undo()
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
