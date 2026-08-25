"""Unit tests for CommandBus (TASK-004, multimodal-interaction-core)."""

import logging
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.core.command_bus import CommandBus  # noqa: E402
from jarvis.core.commands import Command, CommandMetadata, CommandResult  # noqa: E402


class _SucceedsCommand(Command):
    def __init__(self, name="Succeeds", safety="SAFE"):
        self._name = name
        self._safety = safety
        self.executed = False

    @property
    def metadata(self):
        return CommandMetadata(name=self._name, safety=self._safety)

    def can_execute(self):
        return True

    def execute(self):
        self.executed = True
        return CommandResult.ok(message="done")


class _RejectsCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="Rejects", safety="SAFE")

    def can_execute(self):
        return False

    def execute(self):
        raise AssertionError("execute() must not be called when can_execute() is False")


class _CanExecuteRaisesCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="CanExecuteRaises", safety="SAFE")

    def can_execute(self):
        raise RuntimeError("sensor unavailable")

    def execute(self):
        raise AssertionError("execute() must not be called when can_execute() raised")


class _ExecuteRaisesCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="ExecuteRaises", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        raise RuntimeError("device on fire")


class _BadReturnCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="BadReturn", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        return "not a CommandResult"


class _MetadataRaisesCommand(Command):
    @property
    def metadata(self):
        raise RuntimeError("metadata construction failed")

    def can_execute(self):
        return True

    def execute(self):
        return CommandResult.ok()


class CommandBusDispatchTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_dispatch_runs_successful_command(self):
        bus = CommandBus()
        cmd = _SucceedsCommand()
        result = bus.dispatch(cmd)
        self.assertTrue(cmd.executed)
        self.assertTrue(result.success)
        self.assertEqual(result.status, "EXECUTED")

    def test_dispatch_fills_in_duration_when_command_did_not_report_one(self):
        bus = CommandBus()
        result = bus.dispatch(_SucceedsCommand())
        self.assertIsNotNone(result.duration_ms)
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_dispatch_does_not_call_execute_when_can_execute_is_false(self):
        bus = CommandBus()
        result = bus.dispatch(_RejectsCommand())
        self.assertFalse(result.success)
        self.assertEqual(result.status, "REJECTED")

    def test_dispatch_never_raises_when_can_execute_raises(self):
        bus = CommandBus()
        result = bus.dispatch(_CanExecuteRaisesCommand())
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")
        self.assertIn("sensor unavailable", result.error)

    def test_dispatch_never_raises_when_execute_raises(self):
        bus = CommandBus()
        result = bus.dispatch(_ExecuteRaisesCommand())
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")
        self.assertIn("device on fire", result.error)

    def test_dispatch_handles_command_returning_wrong_type(self):
        bus = CommandBus()
        result = bus.dispatch(_BadReturnCommand())
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")

    def test_dispatch_handles_metadata_property_raising(self):
        bus = CommandBus()
        result = bus.dispatch(_MetadataRaisesCommand())
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")

    def test_dispatch_rejects_non_command_objects_without_raising(self):
        bus = CommandBus()
        result = bus.dispatch("not a command")
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")

    def test_destructive_commands_are_always_rejected(self):
        bus = CommandBus()
        cmd = _SucceedsCommand(name="DeleteEverything", safety="DESTRUCTIVE")
        result = bus.dispatch(cmd)
        self.assertFalse(cmd.executed)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "REJECTED")

    def test_on_result_callback_is_invoked_with_command_and_result(self):
        seen = []
        bus = CommandBus(on_result=lambda cmd, result: seen.append((cmd, result)))
        cmd = _SucceedsCommand()
        result = bus.dispatch(cmd)
        self.assertEqual(len(seen), 1)
        self.assertIs(seen[0][0], cmd)
        self.assertEqual(seen[0][1], result)

    def test_on_result_callback_failure_does_not_break_dispatch(self):
        def bad_callback(cmd, result):
            raise RuntimeError("feedback manager exploded")

        bus = CommandBus(on_result=bad_callback)
        result = bus.dispatch(_SucceedsCommand())
        self.assertTrue(result.success)  # dispatch's own result is unaffected

    def test_on_result_called_even_for_rejected_and_failed_commands(self):
        seen = []
        bus = CommandBus(on_result=lambda cmd, result: seen.append(result.status))
        bus.dispatch(_RejectsCommand())
        bus.dispatch(_ExecuteRaisesCommand())
        self.assertEqual(seen, ["REJECTED", "ERROR"])


class CommandBusLoggingTests(unittest.TestCase):
    def test_successful_dispatch_is_logged(self):
        bus = CommandBus(logger=logging.getLogger("jarvis.command_bus.test"))
        with self.assertLogs("jarvis.command_bus.test", level="INFO") as cm:
            bus.dispatch(_SucceedsCommand())
        self.assertTrue(any("Succeeds" in line for line in cm.output))

    def test_failed_dispatch_is_logged_as_warning(self):
        bus = CommandBus(logger=logging.getLogger("jarvis.command_bus.test2"))
        with self.assertLogs("jarvis.command_bus.test2", level="WARNING") as cm:
            bus.dispatch(_ExecuteRaisesCommand())
        self.assertTrue(any("ExecuteRaises" in line for line in cm.output))


if __name__ == "__main__":
    unittest.main()
