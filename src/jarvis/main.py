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

LIVE INTEGRATION (rama feature/full-integration-voice-llm): a partir de aca se
conectan de verdad, en la app real, las piezas de PHASE 3-11 que hasta ahora
estaban construidas y testeadas pero dormidas. El criterio para decidir que SI se
cablea y que NO fue: bajo riesgo de cambiar comportamiento default + valor real
demostrable. Lo que se cablea:

- Telemetry (siempre activa, en memoria, sin sink -> sin I/O real, overhead
  medido en PHASE 12 ~microsegundos): FPS/frame_time por frame, confianza/
  exito de cada gesto, exito/duracion de cada comando.
- ProfileManager: la app ahora LEE `smoothing_enabled` del perfil activo en vez
  de hardcodearlo - el perfil "default" tiene el mismo valor que antes (True),
  asi que el comportamiento no cambia hasta que exista un perfil distinto.
  Tecla 'p' cicla entre los perfiles registrados (hoy solo "default" - el
  mecanismo esta vivo, no invento valores para coding/gaming/presentation/media
  porque son decisiones de producto que no me pidieron).
- CommandHistory + UndoRedoController: cada comando dispatcheado (salvo
  MouseMove, continuo) se registra en el historial. Teclas 'z'/'y' deshacen/
  rehacen de verdad (hoy solo Volume/CanvasZoom son reversibles - PHASE 9).
- Debug HUD (tecla 'd'): ContextualHudRenderer + debug_telemetry overlay con
  FPS/gesto/comando/perfil - apagado por default, no cambia nada hasta que se
  activa.
- Context Engine: ForegroundApplicationTracker corre cacheado (0.5s) y se
  registra en telemetry - detecta la app en primer plano de verdad, aunque
  todavia no hay ningun binding contextual de gestos usandolo (ver mas abajo).
- Voz STT + LLM (tecla 'v', push-to-talk por toggle - no hay key-up real en
  el polling por frame de cv2.waitKey, asi que se activa/desactiva con la
  misma tecla en vez de mantenerla apretada): jarvis.voice_capture.VoiceListener
  graba con sounddevice y transcribe con faster-whisper (modelo "base",
  offline, igual de local que MediaPipe/pyttsx3). El texto pasa primero por
  VoiceIntentResolver (match de frases, PHASE 10, gratis) y si no matchea cae
  a jarvis.llm_intent.LLMIntentResolver (Qwen2.5-1.5B-Instruct GGUF via
  llama-cpp-python, vocabulario de acciones fijo y validado - nunca se confia
  en texto libre del LLM). ConfidenceFilter (PHASE 5, antes sin uso real
  porque GestureEngine no produce confianza genuina) SI se cablea de verdad
  aca: faster-whisper si da una confianza real (1 - no_speech_prob) y se
  descarta la transcripcion antes de gastar el LLM si esta por debajo del
  umbral. Dependencias pesadas (faster-whisper/llama-cpp-python/sounddevice)
  son opcionales (requirements-voice.txt, import perezoso) - la app y el
  resto de sus tests corren igual sin ellas instaladas.

Lo que NO se cablea, y por que (documentado aca en vez de forzarlo a medias):

- GestureStateMachine: no hay un punto de enganche de bajo riesgo sin
  reestructurar el loop de deteccion de GestureEngine (que sigue siendo
  boolean/umbral, no productor de estados formales).
- Debounce (ConsecutiveFrameDebouncer) / CooldownRegistry genericos:
  GestureEngine ya tiene su propio mecanismo de cooldown funcionando y testeado
  (config.py + `self.last_*_time`) - reemplazarlo es un refactor con riesgo de
  regresion real sin ningun cambio de comportamiento a cambio.
- ConfidenceFilter: GestureEngine detecta por umbral booleano, no produce un
  score de confianza real - forzar el filtro sobre un valor siempre-1.0 seria
  decorativo. Se cablea de verdad en el pipeline de voz (PHASE 14 en esta misma
  rama), donde STT/LLM si producen confianza genuina.
- SwipeDetector/DoubleClickDetector/DwellDetector + bindings contextuales de
  gestos: activarlos por default significaria inventar mapeos gesto->accion
  nuevos (que swipe hace que cosa) que nadie pidio, con riesgo real de falsos
  positivos durante uso normal (un swipe rapido de la mano ya pasa moviendo el
  mouse). Quedan construidos y testeados, sin activar.
- Reescribir el loop de camara para pasar por GestureInputProvider/
  KeyboardInputProvider: el loop actual funciona y esta bien testeado: cambiar
  su estructura interna es riesgo real por cero cambio de comportamiento.
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
    MuteCommand,
    ScreenshotCommand,
    VolumeDownCommand,
    VolumeUpCommand,
)
from jarvis.core.command_bus import CommandBus
from jarvis.core.command_history import CommandHistory
from jarvis.core.command_metrics import CommandMetricsRecorder
from jarvis.core.confidence import ConfidenceFilter, format_confidence
from jarvis.core.context_tracker import ForegroundApplicationTracker
from jarvis.core.contextual_hud import ContextualHudRenderer
from jarvis.core.events import GestureEvent
from jarvis.core.feedback import FeedbackManager
from jarvis.core.gesture_metrics import GestureMetricsRecorder
from jarvis.core.performance_metrics import PerformanceMetricsRecorder
from jarvis.core.profiles import ProfileManager
from jarvis.core.telemetry import TelemetryManager
from jarvis.core.undo_redo import UndoRedoController
from jarvis.core.voice_intent_resolver import DEFAULT_PHRASE_BINDINGS, VoiceIntentResolver
from jarvis.gestures import GestureEngine
from jarvis.hand_tracker import HandTracker
from jarvis.hand_visualizer import draw_hand_overlay
from jarvis.hud_keyboard import HUDKeyboard
from jarvis.legend import build_legend_text
from jarvis.llm_intent import LLMIntentResolver
from jarvis.overlay import ScreenOverlay
from jarvis.pose_tracker import PoseTracker, filter_hands_by_pose_ownership
from jarvis.voice import VoiceJarvis
from jarvis.voice_capture import VoiceListener

# Umbral de confianza real de faster-whisper (1 - no_speech_prob) por debajo
# del cual se descarta la transcripcion antes de gastar el LLM.
_VOICE_MIN_CONFIDENCE = 0.5

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

# Comandos continuos - no van al historial de undo/redo (serian ruido puro:
# MouseMove dispara ~30-60 veces por segundo).
_CONTINUOUS_COMMANDS = frozenset({"MouseMove"})


class JarvisApp:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        self.profiles = ProfileManager()

        self.tracker = HandTracker(
            max_hands=config.MAX_HANDS, min_detection_confidence=0.7, min_tracking_confidence=0.7
        )
        # TASK-060c (Fase 3B): PoseTracker solo se construye si esta habilitado -
        # deshabilitado por default (costo de inferencia medido, ver config.py),
        # asi que en el caso default no se paga ni el costo de construccion ni
        # la descarga del modelo de pose.
        self.pose_tracker = PoseTracker() if config.POSE_HAND_OWNERSHIP_ENABLED else None
        self.screen_w, self.screen_h = pyautogui.size()

        self.gestures = GestureEngine(smoothing_enabled=self.profiles.get_setting("smoothing_enabled"))
        self.keyboard = HUDKeyboard()
        self.voice = VoiceJarvis()
        self.overlay = ScreenOverlay()
        self.overlay.init_legend(build_legend_text())

        self.feedback = FeedbackManager(voice=self.voice, hud=self.overlay)

        self.telemetry = TelemetryManager()
        self.perf_metrics = PerformanceMetricsRecorder(self.telemetry)
        self.gesture_metrics = GestureMetricsRecorder(self.telemetry)
        self.command_metrics = CommandMetricsRecorder(self.telemetry)

        self.history = CommandHistory()
        self.undo_redo = UndoRedoController(self.history)

        self.context_tracker = ForegroundApplicationTracker()
        self.hud_renderer = ContextualHudRenderer(debug=False)

        self.command_bus = CommandBus(on_result=self._on_command_result)

        self.voice_listener = VoiceListener()
        self.voice_intent_resolver = VoiceIntentResolver(phrase_bindings=DEFAULT_PHRASE_BINDINGS)
        self.llm_intent_resolver = LLMIntentResolver()
        self.voice_confidence_filter = ConfidenceFilter(minimum_confidence=_VOICE_MIN_CONFIDENCE)

        self.mirrored = config.MIRROR_CAMERA_DEFAULT
        self._show_hand_overlay = False  # TASK-057: tecla 'l', apagado por default
        self.is_dragging = False
        self.should_quit = False
        self._last_screen_xy = None
        self._last_command_name = None
        self._last_fps = 0.0

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
        # Telemetria (PHASE 8, cableada en vivo): GestureEngine detecta por umbral
        # booleano, no produce confianza real - se registra 1.0/exito por
        # construccion (ver docstring del modulo, seccion "que NO se cablea").
        self.gesture_metrics.record_gesture(gesture_type, confidence=1.0, success=True)

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
        (nunca tuvieron feedback).

        Live integration: ademas del feedback, cada resultado ahora alimenta
        telemetry (siempre) y el historial de comandos (salvo los continuos)."""
        name = command.metadata.name
        position = self._feedback_position()

        self._last_command_name = name
        self.command_metrics.record_from_command_result(command, result)
        if name not in _CONTINUOUS_COMMANDS:
            self.history.record(command, result)

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
        elif name == "Mute":
            channels = ("hud",) if result.success else ("hud", "tts")
            label = "🔇 Silenciado" if result.success else f"⚠ Silenciar falló: {result.error}"
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

    # --- Live integration: undo/redo, perfiles, debug HUD ------------------------

    def _trigger_undo(self):
        result = self.undo_redo.undo()
        if result.success:
            label = "↶ Deshecho"
        elif result.status == "REJECTED":
            label = "↶ Nada para deshacer"
        else:
            label = f"↶ Error al deshacer: {result.error}"
        self.feedback.notify(label, channels=("hud",), position=self._feedback_position())

    def _trigger_redo(self):
        result = self.undo_redo.redo()
        if result.success:
            label = "↷ Rehecho"
        elif result.status == "REJECTED":
            label = "↷ Nada para rehacer"
        else:
            label = f"↷ Error al rehacer: {result.error}"
        self.feedback.notify(label, channels=("hud",), position=self._feedback_position())

    def _cycle_profile(self):
        names = self.profiles.profile_names
        current_index = names.index(self.profiles.active.name)
        next_name = names[(current_index + 1) % len(names)]
        self.profiles.switch_to(next_name)
        self.feedback.notify(f"👤 Perfil: {next_name}", channels=("hud",), position=self._feedback_position())

    def _toggle_debug_hud(self):
        self.hud_renderer.debug = not self.hud_renderer.debug

    def _toggle_hand_overlay(self):
        self._show_hand_overlay = not self._show_hand_overlay

    # --- PHASE 14: voz STT + LLM (cableado en vivo) -------------------------------

    def _toggle_voice_listening(self):
        position = self._feedback_position()
        if self.voice_listener.recording:
            self.voice_listener.stop()
            self.overlay.show_bubble("🎙 Procesando…", *position)
        else:
            self.voice_listener.start()
            self.overlay.show_bubble("🎙 Escuchando…", *position)
            self.voice.speak("Escuchando.")

    def _handle_voice_result(self, result):
        kind, text, confidence = result
        position = self._feedback_position()

        if kind == "error" or not text:
            self.feedback.notify("⚠ No entendí", channels=("hud",), position=position)
            return
        if not self.voice_confidence_filter.accepts(confidence):
            self.feedback.notify(
                f"⚠ Audio poco claro ({format_confidence(confidence)})", channels=("hud",), position=position
            )
            return

        intent = self.voice_intent_resolver.resolve(text) or self.llm_intent_resolver.resolve(text)
        if intent is None:
            self.feedback.notify(f"⚠ Comando de voz no reconocido: “{text}”", channels=("hud",), position=position)
            return
        self._dispatch_voice_action(intent.name)

    def _dispatch_voice_action(self, action_name):
        """action_name: validado por VoiceIntentResolver/LLMIntentResolver
        (jarvis.llm_intent.VALID_ACTIONS). Reusa exactamente el mismo camino de
        Command que el gesto equivalente cuando existe, asi que voz y gesto
        disparando la misma accion se comportan identico (mismo feedback,
        misma entrada en el historial de undo/redo)."""
        if action_name == "UNDO":
            self._trigger_undo()
        elif action_name == "REDO":
            self._trigger_redo()
        elif action_name == "MUTE":
            self.command_bus.dispatch(MuteCommand())
        elif action_name in ("KEYBOARD_TOGGLE", "CLOSE_APP"):
            self._dispatch(action_name, None, self._last_screen_xy)
        elif action_name in _MIGRATED_GESTURES:
            self._dispatch_migrated(action_name, None)

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
        elif key == ord("z"):
            self._trigger_undo()
        elif key == ord("y"):
            self._trigger_redo()
        elif key == ord("p"):
            self._cycle_profile()
        elif key == ord("d"):
            self._toggle_debug_hud()
        elif key == ord("v"):
            self._toggle_voice_listening()
        elif key == ord("l"):
            self._toggle_hand_overlay()

    def run(self):
        self.voice.speak("Jarvis en línea.")
        while self.cap.isOpened() and not self.should_quit:
            frame_start = time.perf_counter()

            ret, frame = self.cap.read()
            if not ret:
                break

            if self.mirrored:
                frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands = self.tracker.process(rgb, mirrored=self.mirrored)

            if self.pose_tracker is not None:
                pose_start = time.perf_counter()
                pose_landmarks = self.pose_tracker.process(rgb)
                self.telemetry.record("performance", "pose_inference_ms", (time.perf_counter() - pose_start) * 1000)
                # TASK-060c: None (sin cuerpo trackeado este frame) deja `hands`
                # sin tocar - cae al heuristico de TASK-056, que ya corre dentro
                # de GestureEngine.process() de todas formas (design.md §3B.2:
                # una falla de pose NUNCA debe dejar a la app sin responder).
                owned_hands = filter_hands_by_pose_ownership(hands, pose_landmarks, w, h)
                if owned_hands is not None:
                    hands = owned_hands

            screen_xy, cam_xy, events = self.gestures.process(hands, w, h, self.screen_w, self.screen_h)
            self._last_screen_xy = screen_xy

            for event in events:
                self._dispatch(event, cam_xy, screen_xy)

            if screen_xy:
                self._dispatch_mouse_move(screen_xy)
                self.keyboard.draw(frame, cam_xy)

            voice_result = self.voice_listener.poll_result()
            if voice_result is not None:
                self._handle_voice_result(voice_result)

            if not self.gestures.active:
                cv2.putText(frame, "PAUSADO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if self._show_hand_overlay and hands:
                draw_hand_overlay(frame, hands, self.gestures.last_primary_landmarks, events[-1] if events else None)

            if self.hud_renderer.debug:
                self.hud_renderer.render(
                    frame,
                    "TRACKING" if hands else "IDLE",
                    telemetry={
                        "fps": self._last_fps,
                        "gesture": events[-1] if events else None,
                        "command": self._last_command_name,
                        "profile": self.profiles.active.name,
                    },
                )

            self.overlay.pump()

            cv2.imshow("Jarvis Gesture HUD", frame)
            self._handle_key(cv2.waitKey(1) & 0xFF)

            frame_time_ms = (time.perf_counter() - frame_start) * 1000
            self._last_fps = round(1000 / frame_time_ms, 1) if frame_time_ms > 0 else 0.0
            self.perf_metrics.record_frame_time(frame_time_ms)
            self.perf_metrics.record_fps(self._last_fps)
            self.context_tracker.get()  # cached (0.5s TTL) - cheap, keeps context "live"

        self.overlay.close()
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    JarvisApp().run()


if __name__ == "__main__":
    main()
