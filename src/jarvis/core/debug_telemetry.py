"""Debug telemetry HUD (TASK-038, spec.md #36, tasks.md).

"Display optional: FPS, gesture, confidence, intent, command, latency, profile."
"Debug mode SHOULD display: FPS, Hands, Gesture, Confidence, State, Intent,
Context, Command, Latency, Profile. Debug mode MUST be optional." (spec.md #36)

Rendering counterpart to PHASE 7's hud_feedback.py - reuses its `draw_panel_line`
and jarvis.core.confidence.format_confidence for a consistent visual style.
Standalone, not wired into the live camera loop - see PHASE 8 task report.
"""

from jarvis.core.confidence import format_confidence
from jarvis.core.hud_feedback import draw_panel_line

_FIELD_ORDER = ("fps", "gesture", "confidence", "intent", "command", "latency_ms", "profile")
_FIELD_LABELS = {
    "fps": "FPS",
    "gesture": "Gesture",
    "confidence": "Confidence",
    "intent": "Intent",
    "command": "Command",
    "latency_ms": "Latency",
    "profile": "Profile",
}


def format_debug_telemetry(fps=None, gesture=None, confidence=None, intent=None, command=None, latency_ms=None, profile=None):
    values = {
        "fps": fps,
        "gesture": gesture,
        "confidence": confidence,
        "intent": intent,
        "command": command,
        "latency_ms": latency_ms,
        "profile": profile,
    }
    lines = []
    for field_name in _FIELD_ORDER:
        value = values[field_name]
        if value is None:
            continue
        label = _FIELD_LABELS[field_name]
        if field_name == "confidence":
            lines.append(f"{label}: {format_confidence(value)}")
        elif field_name == "latency_ms":
            lines.append(f"{label}: {value}ms")
        else:
            lines.append(f"{label}: {value}")
    return lines


def draw_debug_telemetry(frame, enabled=True, position=(10, 130), line_height=20, **fields):
    """"Debug mode MUST be optional" (spec.md #36) - draws nothing when disabled."""
    if not enabled:
        return []
    lines = format_debug_telemetry(**fields)
    x, y = position
    for line in lines:
        draw_panel_line(frame, line, (x, y))
        y += line_height
    return lines
