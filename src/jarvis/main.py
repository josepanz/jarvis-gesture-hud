"""Loop de camara: captura, tracking de manos, despacho de eventos de gesto.

PHASE 2 (TASK-006 a 013): las 8 categorias de accion nombradas en tasks.md ahora
pasan por GestureEvent -> Command -> CommandBus en vez de llamar a
pyautogui/CrossPlatformOS directamente desde aca (ver `jarvis.actions`). Los
eventos que NO estan nombrados en ninguna task de PHASE 2 (pausar/reanudar,
cerrar la app, silencio, toggle de teclado HUD, espejo, panel de gestos,
transparencia) siguen exactamente igual que antes - no estan pedidos todavia.

Nota de interpretacion (ver el reporte de PHASE 2): TASK-006 describe el flujo como
"Tracker -> GestureEvent -> Intent -> Command". Se construye GestureEvent (registro
tipado y validado de la deteccion fisica) para los 11 gestos discretos migrados,
pero NO se construye un objeto Intent en cada sitio de despacho: sin un IntentEngine
real que lo consuma, esos objetos quedarian creados y descartados sin uso, lo que
viola "Implementation MUST be minimal" (apply.md #8). El mapeo gesture_type -> Command
es, en esencia, la resolucion de intent - simplemente no esta reificada como un
objeto Intent aparte todavia. El movimiento continuo del mouse (spec.md #15:
"Continuous signals MUST NOT be forced through the same execution model as discrete
gestures") va directo a Command, sin GestureEvent tampoco.
"""

import time

import cv2
import pyautogui

from jarvis import config
from jarvis.actions.keyboard import PressKeyCommand, TypeTextCommand
from jarvis.actions.mouse import (
    CanvasZoomCommand,
    MouseButtonCommand,
    MouseMoveCommand,
    RightClickCommand,
    ScrollCommand,
)
from jarvis.actions.system import (
    LockSessionCommand,
    ScreenshotCommand,
    VolumeDownCommand,
    VolumeUpCommand,
)
from jarvis.core.command_bus import CommandBus
from jarvis.core.events import GestureEvent
from jarvis.core.feedback import FeedbackManager
from jarvis.gestures import GestureEngine
from jarvis.hand_tracker import HandTracker
from jarvis.hud_keyboard import HUDKeyboard
from jarvis.legend import build_legend_text
from jarvis.overlay import ScreenOverlay
from jarvis.voice import VoiceJarvis

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

# Gestos NO cubiertos por ninguna task de PHASE 2 - bubble directo, sin pasar por
# Command/CommandBus, exactamente como antes de esta migracion.
BUBBLE_LABELS = {
    "SILENCE": "🔇 Silencio",
    "KEYBOARD_TOGGLE": "⌨ Teclado HUD",
    "TOGGLE_LEGEND": "📋 Panel de gestos",
    "LEGEND_ALPHA_UP": "🔆 Panel más opaco",
    "LEGEND_ALPHA_DOWN": "🔅 Panel más transparente",
}

# Los 11 gestos discretos que si estan cubiertos por PHASE 2 (TASK-007/008/010/011/013;
# el mouse move de TASK-006 es continuo y no pasa por aca, ver _dispatch_mouse_move).
_MIGRATED_GESTURES = frozenset(
    {
        "PINCH_DOWN",
        "PINCH_UP",
        "RIGHT_CLICK",
        "SCROLL_UP",
        "SCROLL_DOWN",
        "ZOOM_IN",
        "ZOOM_OUT",
        "VOLUME_UP",
        "VOLUME_DOWN",
        "SCREENSHOT",
        "LOCK_SESSION",
    }
)


class JarvisApp:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        self.tracker = HandTracker(
            max_hands=config.MAX_HANDS, min_detection_confidence=0.7, min_tracking_confidence=0.7
        )
        self.screen_w, self.screen_h = pyautogui.size()

        self.gestures = GestureEngine()
        self.keyboard = HUDKeyboard()
        self.voice = VoiceJarvis()
        self.overlay = ScreenOverlay()
        self.overlay.init_legend(build_legend_text())

        self.feedback = FeedbackManager(voice=self.voice, hud=self.overlay)
        self.command_bus = CommandBus(on_result=self._on_command_result)

        self.mirrored = config.MIRROR_CAMERA_DEFAULT
        self.is_dragging = False
        self.should_quit = False
        self._last_screen_xy = None

    # --- PHASE 2: acciones migradas (GestureEvent -> Command -> CommandBus) ------

    def _feedback_position(self):
        return self._last_screen_xy or (self.screen_w // 2, self.screen_h // 2)

    @staticmethod
    def _build_gesture_event(gesture_type, position=None):
        return GestureEvent(
            gesture_type=gesture_type,
            confidence=1.0,
            timestamp=time.time(),
            source="CAMERA",
            state="ACTIVE",
            position=position,
        )

    def _dispatch_mouse_move(self, screen_xy):
        # Continuo (spec.md #15) - directo a Command, sin GestureEvent.
        self.command_bus.dispatch(MouseMoveCommand(screen_xy[0], screen_xy[1]))

    def _dispatch_migrated(self, gesture_type, cam_xy):
        self._build_gesture_event(gesture_type, position=cam_xy)  # registro tipado y validado

        if gesture_type == "PINCH_DOWN":
            key_action = self.keyboard.handle_click(cam_xy)
            if key_action is not None:
                self._dispatch_key_action(key_action)
            elif not self.is_dragging:
                self.command_bus.dispatch(MouseButtonCommand(pressed=True))
                self.is_dragging = True
        elif gesture_type == "PINCH_UP":
            if self.is_dragging:
                self.command_bus.dispatch(MouseButtonCommand(pressed=False))
                self.is_dragging = False
        elif gesture_type == "RIGHT_CLICK":
            self.command_bus.dispatch(RightClickCommand())
        elif gesture_type in ("SCROLL_UP", "SCROLL_DOWN"):
            amount = 12 if gesture_type == "SCROLL_UP" else -12
            self.command_bus.dispatch(ScrollCommand(amount))
        elif gesture_type in ("ZOOM_IN", "ZOOM_OUT"):
            amount = 10 if gesture_type == "ZOOM_IN" else -10
            self.command_bus.dispatch(CanvasZoomCommand(amount))
        elif gesture_type == "VOLUME_UP":
            self.command_bus.dispatch(VolumeUpCommand())
        elif gesture_type == "VOLUME_DOWN":
            self.command_bus.dispatch(VolumeDownCommand())
        elif gesture_type == "SCREENSHOT":
            self.command_bus.dispatch(ScreenshotCommand())
        elif gesture_type == "LOCK_SESSION":
            self.command_bus.dispatch(LockSessionCommand())

    def _dispatch_key_action(self, key_action):
        if key_action.kind == "layout":
            return  # cambio de layout interno, sin efecto de SO - ya aplicado por HUDKeyboard
        if key_action.kind == "key":
            self.command_bus.dispatch(PressKeyCommand(key_action.value))
        elif key_action.kind == "text":
            self.command_bus.dispatch(TypeTextCommand(key_action.value))

    def _on_command_result(self, command, result):
        """Feedback para las acciones migradas que antes tenian su bubble/voz
        directo adentro de _dispatch(). MouseMove/MouseButton/Scroll/PressKey/
        TypeText se quedan mudos aca tambien, igual que antes de la migracion
        (nunca tuvieron feedback)."""
        name = command.metadata.name
        position = self._feedback_position()

        if name == "LockSession":
            if result.success:
                self.feedback.notify("🔒 Bloqueando sesión", channels=("hud", "tts"), position=position)
            else:
                self.feedback.notify(
                    f"⚠ No se pudo bloquear la sesión: {result.error}", channels=("hud", "tts"), position=position
                )
        elif name == "Screenshot":
            if result.success:
                self.feedback.notify("📸 Captura guardada", channels=("hud", "tts"), position=position)
            else:
                self.feedback.notify(
                    f"⚠ No se pudo capturar pantalla: {result.error}", channels=("hud", "tts"), position=position
                )
        elif name == "VolumeUp":
            channels = ("hud",) if result.success else ("hud", "tts")
            label = "🔊 Volumen +" if result.success else f"⚠ Volumen falló: {result.error}"
            self.feedback.notify(label, channels=channels, position=position)
        elif name == "VolumeDown":
            channels = ("hud",) if result.success else ("hud", "tts")
            label = "🔉 Volumen -" if result.success else f"⚠ Volumen falló: {result.error}"
            self.feedback.notify(label, channels=channels, position=position)
        elif name == "RightClick" and result.success:
            self.feedback.notify("🖱 Click derecho", channels=("hud",), position=position)
        elif name == "CanvasZoom" and result.success:
            label = "🔍 Zoom +" if command.amount > 0 else "🔍 Zoom -"
            self.feedback.notify(label, channels=("hud",), position=position)

    # --- Gestos NO migrados (fuera de alcance de PHASE 2, sin cambios) -----------

    def _dispatch(self, event, cam_xy, screen_xy):
        if event in _MIGRATED_GESTURES:
            self._dispatch_migrated(event, cam_xy)
            return

        bubble_at = screen_xy or (self.screen_w // 2, self.screen_h // 2)
        label = BUBBLE_LABELS.get(event)
        if label:
            self.overlay.show_bubble(label, *bubble_at)

        if event == "SILENCE":
            self.voice.silence()
        elif event == "KEYBOARD_TOGGLE":
            visible = self.keyboard.toggle()
            self.voice.speak("Teclado activado." if visible else "Teclado desactivado.")
        elif event == "TOGGLE_ACTIVE":
            paused = not self.gestures.active
            self.overlay.show_bubble("⏸ Jarvis en pausa" if paused else "▶ Jarvis reanudado", *bubble_at)
            self.voice.speak("Jarvis en pausa." if paused else "Jarvis reanudado.")
            if self.is_dragging:
                pyautogui.mouseUp()
                self.is_dragging = False
        elif event == "CLOSE_APP":
            self.overlay.show_bubble("👋 Cerrando Jarvis", *bubble_at)
            self.voice.speak("Cerrando Jarvis.")
            self.should_quit = True
        elif event == "TOGGLE_MIRROR":
            self._toggle_mirror()
        elif event == "TOGGLE_LEGEND":
            self.overlay.toggle_legend_visible()
        elif event == "LEGEND_ALPHA_UP":
            self.overlay.adjust_legend_alpha(+0.1)
        elif event == "LEGEND_ALPHA_DOWN":
            self.overlay.adjust_legend_alpha(-0.1)

    def _toggle_mirror(self):
        self.mirrored = not self.mirrored
        self.voice.speak("Modo espejo activado." if self.mirrored else "Modo espejo desactivado.")

    def _handle_key(self, key):
        if key == ord("q"):
            self.should_quit = True
        elif key == ord("h"):
            self.overlay.toggle_legend_visible()
        elif key == ord("m"):
            self._toggle_mirror()
        elif key in (ord("+"), ord("=")):
            self.overlay.adjust_legend_alpha(+0.1)
        elif key == ord("-"):
            self.overlay.adjust_legend_alpha(-0.1)

    def run(self):
        self.voice.speak("Jarvis en línea.")
        while self.cap.isOpened() and not self.should_quit:
            ret, frame = self.cap.read()
            if not ret:
                break

            if self.mirrored:
                frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands = self.tracker.process(rgb, mirrored=self.mirrored)

            screen_xy, cam_xy, events = self.gestures.process(hands, w, h, self.screen_w, self.screen_h)
            self._last_screen_xy = screen_xy

            for event in events:
                self._dispatch(event, cam_xy, screen_xy)

            if screen_xy:
                self._dispatch_mouse_move(screen_xy)
                self.keyboard.draw(frame, cam_xy)

            if not self.gestures.active:
                cv2.putText(frame, "PAUSADO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            self.overlay.pump()

            cv2.imshow("Jarvis Gesture HUD", frame)
            self._handle_key(cv2.waitKey(1) & 0xFF)

        self.overlay.close()
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    JarvisApp().run()


if __name__ == "__main__":
    main()
