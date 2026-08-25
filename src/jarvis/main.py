"""Loop de camara: captura, tracking de manos, despacho de eventos de gesto."""

import cv2
import pyautogui

from jarvis import config
from jarvis.gestures import GestureEngine
from jarvis.hand_tracker import HandTracker
from jarvis.hud_keyboard import HUDKeyboard
from jarvis.legend import build_legend_text
from jarvis.os_native import CrossPlatformOS
from jarvis.overlay import ScreenOverlay
from jarvis.voice import VoiceJarvis

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

# Solo los eventos discretos/poco frecuentes muestran globo — click/scroll/drag
# se disparan muchas veces por segundo y saturarian la pantalla de globos.
BUBBLE_LABELS = {
    "LOCK_SESSION": "🔒 Bloqueando sesión",
    "SCREENSHOT": "📸 Captura guardada",
    "SILENCE": "🔇 Silencio",
    "KEYBOARD_TOGGLE": "⌨ Teclado HUD",
    "VOLUME_UP": "🔊 Volumen +",
    "VOLUME_DOWN": "🔉 Volumen -",
    "ZOOM_IN": "🔍 Zoom +",
    "ZOOM_OUT": "🔍 Zoom -",
    "RIGHT_CLICK": "🖱 Click derecho",
}


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

        self.mirrored = config.MIRROR_CAMERA_DEFAULT
        self.is_dragging = False
        self.should_quit = False

    def _dispatch(self, event, cam_xy, screen_xy):
        bubble_at = screen_xy or (self.screen_w // 2, self.screen_h // 2)

        label = BUBBLE_LABELS.get(event)
        if label:
            self.overlay.show_bubble(label, *bubble_at)

        if event == "LOCK_SESSION":
            self.voice.speak("Bloqueando sesión.")
            CrossPlatformOS.lock_session()
        elif event == "SCREENSHOT":
            CrossPlatformOS.take_screenshot()
            self.voice.speak("Captura guardada.")
        elif event == "SILENCE":
            self.voice.silence()
        elif event == "KEYBOARD_TOGGLE":
            visible = self.keyboard.toggle()
            self.voice.speak("Teclado activado." if visible else "Teclado desactivado.")
        elif event == "VOLUME_UP":
            CrossPlatformOS.volume_up()
        elif event == "VOLUME_DOWN":
            CrossPlatformOS.volume_down()
        elif event == "SCROLL_UP":
            pyautogui.scroll(12)
        elif event == "SCROLL_DOWN":
            pyautogui.scroll(-12)
        elif event == "ZOOM_IN":
            pyautogui.keyDown("ctrl")
            pyautogui.scroll(10)
            pyautogui.keyUp("ctrl")
        elif event == "ZOOM_OUT":
            pyautogui.keyDown("ctrl")
            pyautogui.scroll(-10)
            pyautogui.keyUp("ctrl")
        elif event == "RIGHT_CLICK":
            pyautogui.rightClick()
        elif event == "PINCH_DOWN":
            if not self.keyboard.handle_click(cam_xy) and not self.is_dragging:
                pyautogui.mouseDown()
                self.is_dragging = True
        elif event == "PINCH_UP":
            if self.is_dragging:
                pyautogui.mouseUp()
                self.is_dragging = False
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

    def _handle_key(self, key):
        if key == ord("q"):
            self.should_quit = True
        elif key == ord("h"):
            self.overlay.toggle_legend_visible()
        elif key == ord("m"):
            self.mirrored = not self.mirrored
            self.voice.speak("Modo espejo activado." if self.mirrored else "Modo espejo desactivado.")
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
            for event in events:
                self._dispatch(event, cam_xy, screen_xy)

            if screen_xy:
                pyautogui.moveTo(*screen_xy)
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
