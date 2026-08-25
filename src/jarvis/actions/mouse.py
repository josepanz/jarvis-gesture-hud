"""Concrete Commands wrapping the EXISTING mouse/pyautogui side effects
(TASK-006/007/008/009/010/011). Every execute() below calls the exact same
pyautogui function `main.py._dispatch()` used to call directly - nothing about
what happens on screen changes, only who calls it.
"""

import pyautogui

from jarvis.core.commands import Command, CommandMetadata, CommandResult


class MouseMoveCommand(Command):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @property
    def metadata(self):
        return CommandMetadata(name="MouseMove", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            pyautogui.moveTo(self.x, self.y)
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="MouseMove failed")


class MouseButtonCommand(Command):
    def __init__(self, pressed):
        self.pressed = pressed

    @property
    def metadata(self):
        return CommandMetadata(name="MouseButton" + ("Down" if self.pressed else "Up"), safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            if self.pressed:
                pyautogui.mouseDown()
            else:
                pyautogui.mouseUp()
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message=f"{self.metadata.name} failed")


class RightClickCommand(Command):
    @property
    def metadata(self):
        return CommandMetadata(name="RightClick", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            pyautogui.rightClick()
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="RightClick failed")


class ScrollCommand(Command):
    def __init__(self, amount):
        self.amount = amount

    @property
    def metadata(self):
        return CommandMetadata(name="Scroll", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        try:
            pyautogui.scroll(self.amount)
            return CommandResult.ok(message=f"scrolled {self.amount}")
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message="Scroll failed")


class CanvasZoomCommand(Command):
    """Ctrl+Scroll canvas/viewport zoom - NOT resizing a selected object (see
    ARCHITECTURE.md decisions: a generic "scale the selection" action isn't
    achievable across arbitrary apps without knowing where the resize handle is
    on screen).

    TASK-040: reversible. Unlike volume (which has no OS-queryable absolute
    level), zoom-by-scroll-amount genuinely is its own exact inverse - scrolling
    -amount after +amount returns the view to where it was, so undo() here is a
    real restore, not just a best-effort nudge."""

    def __init__(self, amount):
        self.amount = amount

    @property
    def metadata(self):
        return CommandMetadata(name="CanvasZoom", safety="SAFE")

    def can_execute(self):
        return True

    def execute(self):
        return self._ctrl_scroll(self.amount, "CanvasZoom")

    def is_reversible(self):
        return True

    def undo(self):
        return self._ctrl_scroll(-self.amount, "CanvasZoom undo")

    @staticmethod
    def _ctrl_scroll(amount, label):
        try:
            pyautogui.keyDown("ctrl")
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message=f"{label} failed (keyDown ctrl)")
        try:
            pyautogui.scroll(amount)
        except Exception as exc:
            return CommandResult.failed(error=str(exc), message=f"{label} failed (scroll)")
        finally:
            # Always release ctrl even if scroll failed - the original code had no
            # such guarantee and could leave ctrl stuck down on a mid-sequence error.
            try:
                pyautogui.keyUp("ctrl")
            except Exception:
                pass
        return CommandResult.ok(message=f"{label} {amount}")
