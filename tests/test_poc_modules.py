"""B-01 (WORKPLAN.md §9, `hardening-and-polish`): pins the set of `core/`
modules deliberately left as proof-of-concept, never wired into production
code. Same technique as test_architecture_boundaries.py (real `ast` import
inspection, not string grepping) - the inverse of that file's checks: this
pins what must NOT be imported from live code, so wiring one of these up
becomes a conscious decision (update this list) instead of an accident.

The list below must match `grep -rn "PoC / no cableado" src/` exactly - each
module's docstring carries that one-line marker (see §9's decision table for
the "why not" per module, already in each docstring; this test is what makes
"what's actually live" grep-and-test-able instead of tribal knowledge).
"""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SRC = Path(__file__).resolve().parents[1] / "src" / "jarvis"

# The exact PoC set from WORKPLAN.md §9's decision table - modules whose
# decision is "PoC" (or "PoC (superado)"), NOT the ones marked "CABLEAR" (those
# either are already wired - cooldown.py/debounce.py/contextual_bindings.py,
# A-01/A-02/A-03 - or have a concrete wiring plan of their own - double_click.py/
# swipe.py/dwell.py, workflow 8 - a different category from "intentionally
# dormant.")
POC_MODULES = {
    "context.py",
    "gesture_state_machine.py",
    "conflict_resolver.py",
    "input_provider.py",
    "gesture_input_provider.py",
    "keyboard_input_provider.py",
    "voice_input_provider.py",
    "intent_resolution.py",
    "hud_state_machine.py",
    "undo_feedback.py",
}

POC_MARKER = "PoC / no cableado (ver openspec/changes/hardening-and-polish/WORKPLAN.md §9)."


def _module_name(filename):
    return f"jarvis.core.{filename[:-len('.py')]}"


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


class PocModuleMarkerTests(unittest.TestCase):
    def test_every_poc_module_carries_the_marker(self):
        for filename in POC_MODULES:
            with self.subTest(module=filename):
                text = (SRC / "core" / filename).read_text(encoding="utf-8")
                self.assertIn(POC_MARKER, text)

    def test_the_marker_appears_in_exactly_the_pinned_modules(self):
        # The other direction: nothing outside POC_MODULES claims to be PoC
        # (a module marked PoC without being in this list would silently
        # escape the import check below).
        marked = {
            path.relative_to(SRC / "core").as_posix()
            for path in (SRC / "core").glob("*.py")
            if POC_MARKER in path.read_text(encoding="utf-8")
        }
        self.assertEqual(marked, POC_MODULES)


class PocModuleNotWiredTests(unittest.TestCase):
    """Fails the moment a PoC module starts being imported from live code -
    `src/jarvis/*.py` (main.py included) or any `core/` module NOT itself in
    the PoC set - without this list being updated first."""

    def test_no_poc_module_is_imported_from_top_level_src(self):
        poc_module_names = {_module_name(f) for f in POC_MODULES}
        for path in SRC.glob("*.py"):
            with self.subTest(file=path.name):
                offending = _imports_of(path) & poc_module_names
                self.assertFalse(offending, f"{path.name} imports PoC module(s): {offending}")

    def test_no_poc_module_is_imported_from_a_non_poc_core_module(self):
        poc_module_names = {_module_name(f) for f in POC_MODULES}
        for path in (SRC / "core").glob("*.py"):
            if path.name in POC_MODULES:
                continue  # a PoC module referencing another PoC module is fine
            with self.subTest(file=path.name):
                offending = _imports_of(path) & poc_module_names
                self.assertFalse(offending, f"core/{path.name} imports PoC module(s): {offending}")

    def test_no_poc_module_is_imported_from_actions_or_other_subpackages(self):
        poc_module_names = {_module_name(f) for f in POC_MODULES}
        for path in SRC.rglob("*.py"):
            if path.parent == SRC / "core" or path.parent == SRC:
                continue  # covered by the two tests above
            with self.subTest(file=str(path.relative_to(SRC))):
                offending = _imports_of(path) & poc_module_names
                self.assertFalse(offending, f"{path.relative_to(SRC)} imports PoC module(s): {offending}")


if __name__ == "__main__":
    unittest.main()
