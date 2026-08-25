"""HUD feedback rendering helpers (TASK-030 gesture feedback, TASK-031 intent
feedback, TASK-032 dwell reticle - spec.md #32/#33, design.md #18).

Pure formatting + cv2-drawing functions, in the same translucent-panel visual style
already used by `jarvis.legend`/`jarvis.hud_keyboard` - real, tested rendering, not
just formatted strings. NOT called from the live camera loop: see contextual_hud.py
(TASK-033) for how these would compose into one progressive-disclosure HUD, and the
PHASE 7 task report for why none of it is wired into `main.py` yet.
"""

import cv2

from jarvis.core.confidence import format_confidence

_RETICLE_COLORS = {
    "idle": (120, 120, 120),
    "targeting": (255, 200, 0),
    "confirming": (0, 200, 255),
    "selected": (0, 255, 0),
}


def format_gesture_feedback(gesture_type, confidence, state):
    """TASK-030: "Display: gesture, confidence, state.\""""
    return f"{gesture_type} ({format_confidence(confidence)}) [{state}]"


def draw_gesture_feedback(frame, gesture_type, confidence, state, position=(10, 60)):
    text = format_gesture_feedback(gesture_type, confidence, state)
    draw_panel_line(frame, text, position)


def format_intent_feedback(intent_name, target, action):
    """TASK-031: "Display: intent, target, action.\""""
    target_part = f" -> {target}" if target else ""
    action_part = f" :: {action}" if action else ""
    return f"{intent_name}{target_part}{action_part}"


def draw_intent_feedback(frame, intent_name, target, action, position=(10, 90)):
    text = format_intent_feedback(intent_name, target, action)
    draw_panel_line(frame, text, position)


def format_remaining_time(progress, duration_ms):
    remaining_ms = max(0, round(duration_ms * (1 - progress)))
    return f"{remaining_ms}ms"


def draw_dwell_reticle(frame, center, progress, duration_ms, hud_state="targeting", radius=24):
    """TASK-032: "Display: target, progress, remaining time." + spec.md #33's
    "visually distinguish idle/targeting/confirming/selected" via reticle color.
    Renders a progress ring (same mechanism as dwell.draw_dwell_progress) plus a
    remaining-time label, colored by `hud_state`."""
    color = _RETICLE_COLORS.get(hud_state, _RETICLE_COLORS["targeting"])
    cx, cy = int(center[0]), int(center[1])

    cv2.circle(frame, (cx, cy), radius, (60, 60, 60), 2)
    if progress > 0:
        end_angle = int(360 * min(1.0, progress))
        cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, end_angle, color, 3)

    label = format_remaining_time(progress, duration_ms)
    cv2.putText(
        frame, label, (cx - radius, cy + radius + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1
    )


def draw_panel_line(frame, text, position, color=(255, 255, 255), bg=(20, 20, 20)):
    """Reusable translucent-panel text line, same style as legend.py/hud_keyboard.py."""
    x, y = position
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    overlay = frame.copy()
    cv2.rectangle(overlay, (x - 4, y - th - 6), (x + tw + 4, y + 6), bg, -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
