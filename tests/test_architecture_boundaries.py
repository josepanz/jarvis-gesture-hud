"""TASK-054: final architecture audit - "Verify: Tracker != Classifier != Intent !=
Context != Command != Action != HUD. No accidental coupling SHALL remain in the
migrated areas." Rather than a one-time manual review that can silently rot as the
codebase grows, this inspects real import statements (via `ast`, not string
grepping) and asserts the forbidden couplings design.md #5.3/#16 and spec.md #28
describe are actually absent - so a future accidental import is caught by the test
suite, not just by re-reading the code by hand.

Every assertion below was verified against the real codebase before being written
into this file (see PHASE 12 task report) - this audit found one real, pre-existing
inaccuracy in ARCHITECTURE.md's os_native.py description (it claimed to be "the
only module" branching on platform.system(), which stopped being true once
overlay.py's click-through code was added several phases earlier) - corrected there
and reflected in the check below, which pins the actual, intentional set of two.
"""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SRC = Path(__file__).resolve().parents[1] / "src" / "jarvis"


def _imports_of(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class TrackerAndClassifierBoundaryTests(unittest.TestCase):
    """"A gesture detector MUST NOT directly contain operating-system business
    logic." (design.md #5.3) / GestureEngine MUST NOT directly execute pyautogui,
    OS APIs, process launches (apply.md #20)."""

    def test_gesture_engine_has_no_execution_layer_dependency(self):
        imports = _imports_of(SRC / "gestures.py")
        forbidden = {
            "pyautogui",
            "jarvis.os_native",
            "jarvis.core.commands",
            "jarvis.core.command_bus",
            "jarvis.actions.mouse",
            "jarvis.actions.system",
            "jarvis.actions.keyboard",
        }
        offending = imports & forbidden
        self.assertFalse(offending, f"gestures.py imports execution-layer modules: {offending}")

    def test_hand_tracker_has_no_command_or_hud_dependency(self):
        imports = _imports_of(SRC / "hand_tracker.py")
        forbidden = {"jarvis.core.commands", "jarvis.core.command_bus", "jarvis.overlay", "jarvis.hud_keyboard"}
        offending = imports & forbidden
        self.assertFalse(offending, f"hand_tracker.py imports command/HUD modules: {offending}")


class HUDBoundaryTests(unittest.TestCase):
    """"HUD interaction -> Intent -> CommandBus," not "HUD button -> directly
    executes OS operation." (design.md #16) HUD displays state; the Core owns it
    (apply.md #19)."""

    def test_hud_rendering_modules_never_import_the_execution_layer(self):
        forbidden = {"jarvis.core.commands", "jarvis.core.command_bus"} | {
            f"jarvis.actions.{m}" for m in ("mouse", "keyboard", "system")
        }
        for filename in ("hud_feedback.py", "contextual_hud.py", "debug_telemetry.py", "undo_feedback.py"):
            imports = _imports_of(SRC / "core" / filename)
            offending = imports & forbidden
            self.assertFalse(offending, f"{filename} imports execution-layer modules: {offending}")


class ContextBoundaryTests(unittest.TestCase):
    """"Context cannot directly execute OS commands." (spec.md #28) - reinforces
    the return-type-only guarantee already tested in test_contextual_bindings.py
    with a static import check too."""

    def test_context_modules_never_import_the_execution_layer(self):
        forbidden = {"jarvis.core.commands", "jarvis.core.command_bus", "pyautogui", "jarvis.os_native"}
        for filename in ("context.py", "contextual_bindings.py"):
            imports = _imports_of(SRC / "core" / filename)
            offending = imports & forbidden
            self.assertFalse(offending, f"{filename} imports execution-layer modules: {offending}")


class CommandLayerBoundaryTests(unittest.TestCase):
    """The Command/CommandBus layer is the execution boundary (apply.md #23) - it
    should not need to know about detection internals to do its job."""

    def test_command_layer_does_not_import_detection_internals(self):
        forbidden = {"jarvis.gestures", "jarvis.hand_tracker", "cv2", "mediapipe"}
        for filename in ("commands.py", "command_bus.py"):
            imports = _imports_of(SRC / "core" / filename)
            offending = imports & forbidden
            self.assertFalse(offending, f"{filename} imports detection internals: {offending}")


class PlatformBranchingBoundaryTests(unittest.TestCase):
    """This project's standing convention (documented across ARCHITECTURE.md's
    Decisions since the mirror/overlay/context-detection phases): platform-specific
    branching stays contained to the smallest possible set of modules, never
    scattered - `os_native.py` for OS ACTIONS, `overlay.py` for its own, unrelated
    Windows-only click-through rendering trick. Nowhere else."""

    def test_platform_system_branches_only_in_the_two_allowed_modules(self):
        allowed = {"os_native.py", "overlay.py"}
        offenders = []
        for path in SRC.rglob("*.py"):
            if path.name in allowed:
                continue
            if "platform.system()" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(SRC)))
        self.assertEqual(offenders, [], f"unexpected platform.system() branching in: {offenders}")


if __name__ == "__main__":
    unittest.main()
