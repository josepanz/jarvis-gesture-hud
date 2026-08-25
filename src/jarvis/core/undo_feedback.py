"""Undo feedback rendering (TASK-043, tasks.md: "HUD SHALL display: UNDO,
command name, result").

Rendering counterpart, same style as PHASE 7/8's hud_feedback.py / debug_telemetry.py
(reuses draw_panel_line for a consistent visual style). Standalone, not wired into
the live camera loop - see PHASE 9 task report.
"""

from jarvis.core.hud_feedback import draw_panel_line


def format_undo_feedback(command_name, result):
    outcome = "OK" if result.success else "FAILED"
    return f"UNDO {command_name}: {outcome}"


def draw_undo_feedback(frame, command_name, result, position=(10, 160)):
    text = format_undo_feedback(command_name, result)
    draw_panel_line(frame, text, position)
    return text
