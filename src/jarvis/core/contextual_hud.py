"""ContextualHudRenderer (TASK-033, spec.md #32 "Contextual HUD").

"The HUD SHALL use progressive disclosure. Idle HUD MUST remain minimal. Debug HUD
MAY show all telemetry." Composes HUDStateMachine.state with the hud_feedback.py
rendering helpers into one decision: what to draw, given the current state and
whatever data is available. NOT wired into main.py's live frame loop -
`jarvis.overlay`/`jarvis.legend` already provide this app's real, working HUD; see
the PHASE 7 task report for why this stays a standalone, tested composition layer.
"""

from jarvis.core import hud_feedback

_INTENT_VISIBLE_STATES = {"CONFIRMING", "EXECUTING", "SUCCESS", "ERROR"}


class ContextualHudRenderer:
    def __init__(self, debug=False):
        self.debug = debug

    def render(self, frame, hud_state, gesture=None, intent=None, dwell=None, telemetry=None):
        """gesture: {"gesture_type", "confidence", "state"} or None.
        intent: {"name", "target", "action"} or None.
        dwell: {"center", "progress", "duration_ms", "reticle_state"} or None.
        telemetry: dict of label -> value, drawn only when self.debug is True.
        Returns the list of element names actually drawn (for testability)."""
        drawn = []

        if hud_state == "IDLE" and not self.debug:
            return drawn  # progressive disclosure: stay minimal at rest

        if gesture:
            hud_feedback.draw_gesture_feedback(
                frame, gesture["gesture_type"], gesture["confidence"], gesture.get("state", hud_state)
            )
            drawn.append("gesture")

        if intent and hud_state in _INTENT_VISIBLE_STATES:
            hud_feedback.draw_intent_feedback(frame, intent["name"], intent.get("target"), intent.get("action"))
            drawn.append("intent")

        if dwell:
            hud_feedback.draw_dwell_reticle(
                frame,
                dwell["center"],
                dwell["progress"],
                dwell["duration_ms"],
                hud_state=dwell.get("reticle_state", "targeting"),
            )
            drawn.append("dwell")

        if self.debug and telemetry:
            y = 130
            for label, value in telemetry.items():
                hud_feedback.draw_panel_line(frame, f"{label}: {value}", (10, y))
                y += 20
            drawn.append("telemetry")

        return drawn
