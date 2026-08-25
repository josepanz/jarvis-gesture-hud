# SPEC — Jarvis Gesture HUD

> **Archivado.** Documento histórico en español. La versión vigente y consolidada (inglés) está en [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Target

Windows, macOS, Linux — hooks nativos por SO aislados en un único módulo (`os_native.py`).

## Presupuesto de performance

- ≤ 7% CPU en quad-core.
- ≤ 30ms de latencia de gesto a acción.
- Resolución de cámara 640x480 (fijo, evita reescalado costoso).

## Mapeo de gestos → acción

| Gesto | Acción |
|---|---|
| Índice (8) movido | Puntero de mouse (EMA, alpha configurable) |
| Pinch pulgar(4)+índice(8) < 30px | Click izquierdo / drag / selección en teclado HUD |
| Pinch pulgar(4)+medio(12) < 30px | Click derecho |
| Índice+medio extendidos, anular recogido | Scroll vertical |
| Pinch pulgar(4)+anular(16), índice extendido | Zoom (Ctrl+Scroll) |
| Palma abierta (índice/medio/anular/meñique extendidos, pulgar separado >60px) | Toggle teclado HUD |
| Pinch pulgar(4)+meñique(20) + movimiento vertical | Volumen arriba/abajo |
| Pulgar+anular pinch con índice y meñique recogidos | Captura de pantalla |
| Shaka (pulgar+meñique extendidos, índice/medio recogidos) > 1.5s | Bloqueo de sesión |
| Palma abierta con pulgar recogido hacia base del meñique | **Silencio de voz** (interrumpe TTS al instante) |
| 2 puños cerrados juntos, sostenido 1.2s | **Pausar/reanudar** la lectura de gestos (funciona incluso en pausa) |
| 2 manos en Shaka, sostenido 1.5s | **Cerrar Jarvis** (funciona incluso en pausa) |

## Cámara frontal vs. trasera

- **Frontal/selfie** (default, `config.MIRROR_CAMERA_DEFAULT = True`): el frame se espeja (`cv2.flip`) antes de procesar — natural para un webcam integrado donde el usuario se ve como en un espejo.
- **Trasera/externa**: sin espejar. MediaPipe asume por defecto que la imagen ya viene espejada al estimar lateralidad (Left/Right); si no se espeja, `hand_tracker.py` invierte esa etiqueta para que corresponda a la mano real.
- Toggle en caliente con la tecla `m`, sin reiniciar la app.
- Los gestos de una sola mano (pinch, palma abierta, shaka, etc.) no dependen de lateralidad, solo de posiciones relativas y — no se ven afectados por el espejado. Donde sí importa la lateralidad es para diferenciar mano izquierda/derecha en gestos a 2 manos futuros que necesiten saber cuál es cuál (los actuales — puños/shaka simultáneos — no lo necesitan).

## Manos simultáneas

Hasta 2 manos (`config.MAX_HANDS`). Los gestos de una sola mano siempre usan la primera mano detectada (`hands[0]`); los gestos maestros a 2 manos requieren exactamente 2 manos presentes y se evalúan aparte, sin importar el estado de pausa.

## Voz Jarvis

- Motor: `pyttsx3` (offline, sin red).
- Idioma: español si hay voz `es-*` instalada en el SO; si no, la voz por defecto del sistema.
- No bloqueante: cola de frases en un hilo separado para no afectar el frame rate de la cámara.
- El gesto de silencio detiene la frase actual y vacía la cola inmediatamente (`engine.stop()`), no es un mute permanente.

## Llamadas nativas por SO

- **Lock**: Windows `ctypes.windll.user32.LockWorkStation()` · macOS `CGSession -suspend` · Linux `xdg-screensaver lock || gnome-screensaver-command -l || loginctl lock-session`.
- **Volumen/Mute**: teclas multimedia vía `pyautogui.press(...)` — funciona igual en los tres SO.
- **Screenshot**: `pyautogui.screenshot()`, guardado en `captures/` con timestamp.

## Feedback visual

- **Panel de gestos nativo**: ventana Windows real (Tkinter `Toplevel`, sin bordes, siempre-encima) anclada a una esquina de la pantalla — no se dibuja dentro de la ventana de cámara. Translúcida (`-alpha`), click-through nativo en Windows (no bloquea clicks al escritorio), transparencia ajustable con `+`/`-`, visibilidad con `h`.
- **Globos translúcidos en pantalla**: al disparar un evento discreto (lock, screenshot, silencio, toggle de teclado, volumen, zoom, click derecho, pausa/reanudación, cierre) aparece un globo translúcido en la posición actual del cursor de pantalla — no solo dentro de la ventana de cámara — que se auto-destruye a los ~1.3s. Se excluyen deliberadamente click/drag/scroll (disparan varias veces por segundo; un globo por evento saturaría la pantalla).
- Ambos comparten el mismo mecanismo de click-through: solo garantizado en Windows (WinAPI `WS_EX_LAYERED | WS_EX_TRANSPARENT` vía `ctypes`, sin dependencias nuevas); en macOS/Linux la ventana igual se muestra pero puede capturar clicks (best-effort, no bloqueante).

## Fuera de alcance

Ver [`REQUIREMENTS.md`](REQUIREMENTS.md#fuera-de-alcance-esta-fase).
