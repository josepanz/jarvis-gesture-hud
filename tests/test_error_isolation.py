"""TASK-052: verify the 4 error-isolation claims from apply.md #26 / #17-19 as
real, named tests - not just re-pointing at scattered coverage elsewhere. Where the
underlying mechanism was already exercised indirectly by an earlier phase's tests,
this file re-demonstrates it explicitly under the exact claim it's supposed to
satisfy, so "verify every error-isolation guarantee" has one obvious place to look.
"""

import sys
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jarvis.actions.system import LockSessionCommand  # noqa: E402
from jarvis.core.command_bus import CommandBus  # noqa: E402
from jarvis.core.commands import Command, CommandMetadata, CommandResult  # noqa: E402
from jarvis.core.feedback import FeedbackManager  # noqa: E402
from jarvis.core.telemetry import TelemetryManager  # noqa: E402
from jarvis.gestures import GestureEngine  # noqa: E402
from jarvis.hand_tracker import Hand  # noqa: E402

Landmark = namedtuple("Landmark", "x y z")


def _flat_hand():
    # Landmark 0 (muñeca) separado del resto para que el bbox no tenga area 0
    # (TASK-056 filtra manos por area de bbox) - ver misma nota en
    # test_gesture_engine_regression.py's flat().
    pts = [Landmark(0.5, 0.5, 0) for _ in range(21)]
    pts[0] = Landmark(0.42, 0.7, 0)
    return pts


class _AlwaysFailsCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="AlwaysFails", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        raise RuntimeError("boom")


class TTSFailureDoesNotStopTrackingTests(unittest.TestCase):
    """"A failure in TTS MUST NOT stop gesture tracking." (apply.md #26)"""

    def test_gesture_engine_has_zero_import_dependency_on_voice(self):
        import jarvis.gestures as gestures_module

        source = Path(gestures_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("voice", source.lower())

    def test_gesture_processing_is_unaffected_regardless_of_voice_state(self):
        # GestureEngine never touches VoiceJarvis at all - there is nothing for a
        # broken TTS engine to even propagate through. Demonstrated by running
        # detection to completion with no voice object involved anywhere.
        engine = GestureEngine()
        engine.process([Hand(_flat_hand(), "Right")], 640, 480, 1920, 1080)  # confirm-frame warmup
        screen_xy, _, events = engine.process([Hand(_flat_hand(), "Right")], 640, 480, 1920, 1080)
        self.assertIsNotNone(screen_xy)
        self.assertIn("PINCH_DOWN", events)


class HUDFailureDoesNotCrashCommandsTests(unittest.TestCase):
    """"A failure in HUD MUST NOT necessarily stop command execution." (apply.md #26)"""

    def test_broken_hud_backend_does_not_prevent_command_dispatch(self):
        class BrokenHud:
            def show_bubble(self, *args, **kwargs):
                raise RuntimeError("HUD window destroyed")

        feedback = FeedbackManager(hud=BrokenHud())
        results = feedback.notify("test", channels=("hud",), position=(0, 0))
        self.assertEqual(results["hud"], "failed")  # reported, not raised

    @patch("jarvis.actions.system.CrossPlatformOS")
    def test_command_bus_dispatch_succeeds_even_when_feedback_hud_is_broken(self, mock_os):
        class BrokenHud:
            def show_bubble(self, *args, **kwargs):
                raise RuntimeError("HUD window destroyed")

        feedback = FeedbackManager(hud=BrokenHud())

        def on_result(command, result):
            feedback.notify("done", channels=("hud",), position=(0, 0))  # this WILL fail internally

        bus = CommandBus(on_result=on_result)
        result = bus.dispatch(LockSessionCommand())

        self.assertTrue(result.success)  # command itself is unaffected by the broken HUD
        mock_os.lock_session.assert_called_once()


class CommandFailureDoesNotCrashApplicationTests(unittest.TestCase):
    """"A command failure MUST NOT crash the entire application." (apply.md #26)"""

    def test_failing_command_returns_a_result_instead_of_raising(self):
        bus = CommandBus()
        result = bus.dispatch(_AlwaysFailsCommand())  # must not raise out of this call
        self.assertFalse(result.success)
        self.assertEqual(result.status, "ERROR")
        self.assertIn("boom", result.error)

    def test_bus_keeps_working_after_a_failing_command(self):
        bus = CommandBus()
        bus.dispatch(_AlwaysFailsCommand())

        class _Succeeds(Command):
            @property
            def metadata(self):
                return CommandMetadata(name="Succeeds", safety="SAFE")

            def can_execute(self):
                return True

            def execute(self):
                return CommandResult.ok()

        result = bus.dispatch(_Succeeds())
        self.assertTrue(result.success)


class TelemetryFailureDoesNotStopProcessingTests(unittest.TestCase):
    """"Telemetry MUST NEVER become a hard dependency for normal operation. If
    telemetry fails: application continues" (apply.md #18)"""

    def test_broken_sink_does_not_raise_from_record(self):
        def broken_sink(event):
            raise RuntimeError("disk full")

        telemetry = TelemetryManager(sink=broken_sink)
        event = telemetry.record("performance", "fps", 30)  # must not raise
        self.assertEqual(event.metric, "fps")

    def test_recording_keeps_working_after_a_sink_failure(self):
        def broken_sink(event):
            raise RuntimeError("disk full")

        telemetry = TelemetryManager(sink=broken_sink)
        telemetry.record("performance", "fps", 1)
        telemetry.record("performance", "fps", 2)
        self.assertEqual(len(telemetry.history()), 2)  # both landed locally regardless


if __name__ == "__main__":
    unittest.main()
