# DESIGN

> **Archivado.** Documento histórico en español. La versión vigente y consolidada (inglés) está en [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Pipeline

```
Cámara (640x480) → MediaPipe Hands → Filtro EMA → GestureEngine → eventos
                                                        │
                        ┌───────────────────────────────┼──────────────────────────┐
                        ▼                                ▼                          ▼
                  HUDKeyboard (overlay)          CrossPlatformOS (SO)        VoiceJarvis (TTS)
                        │                                │                          │
                        └────────────── pyautogui (mouse/teclado/scroll) ───────────┘
```

## Módulos

- **`hand_tracker.py`** — `HandTracker`: envuelve la API "Tasks" de MediaPipe (`HandLandmarker`), no la legacy `mp.solutions` (removida de los wheels de Windows desde mediapipe 0.10.30). Descarga y cachea el modelo `.task` en `assets/`, y resuelve la ruta también dentro de un `.exe` de PyInstaller (`sys._MEIPASS`). Expone `process(frame_rgb, mirrored) -> list[Hand]` (0-2 manos), con `Hand.handedness` ya corregido según si `mirrored` es True o False.
- **`config.py`** — todas las constantes ajustables (umbrales de pinch, cooldowns, alpha EMA, colores HUD, rutas). Un solo lugar para tunear comportamiento sin tocar lógica.
- **`os_native.py`** — `CrossPlatformOS`: métodos estáticos `lock_session`, `take_screenshot`, `volume_up/down/mute`, con la rama por `platform.system()` encapsulada acá y en ningún otro módulo.
- **`voice.py`** — `VoiceJarvis`: hilo dedicado + cola (`queue.Queue`) para hablar sin bloquear el loop de cámara; `speak(texto)` encola, `silence()` corta ya mismo.
- **`hud_keyboard.py`** — `HUDKeyboard`: layouts (es/num/emoji), `draw(frame, cursor)`, `handle_click(cursor) -> str | None` (tecla presionada o `None`).
- **`legend.py`** — solo contenido: `build_legend_text()` arma el string multilínea con la lista de gestos. Ya no dibuja nada (antes se pintaba sobre el frame de cámara con `cv2.addWeighted`; ahora vive en una ventana nativa vía `overlay.py`).
- **`overlay.py`** — `ScreenOverlay`, vía Tkinter (`tkinter` es stdlib — cero dependencias nuevas):
  - `show_bubble(texto, x, y)` — globo transitorio en cualquier punto de la pantalla, se autodestruye con `after()`.
  - `init_legend(texto, corner)` / `set_legend_visible` / `adjust_legend_alpha` — panel fijo anclado a una esquina, translúcido, con transparencia ajustable.
  - Ambos usan `_make_click_through(window)`: en Windows aplica `WS_EX_LAYERED | WS_EX_TRANSPARENT` al HWND real (obtenido con `GetParent(winfo_id())`) vía `ctypes` — trick estándar, verificado en este proyecto, cero dependencias nuevas. En otros SO es no-op (best-effort).
  - `pump()` se llama una vez por frame desde el loop principal en vez de `mainloop()`, porque Tk no es thread-safe y no queremos un hilo aparte compitiendo con la cámara.
- **`gestures.py`** — `GestureEngine`: mantiene el estado entre frames (timers, posición previa) y expone `process(hands, w, h, screen_w, screen_h) -> (screen_xy | None, cam_xy | None, events)`. Eventos: `LOCK_SESSION`, `SCREENSHOT`, `VOLUME_UP`, `VOLUME_DOWN`, `KEYBOARD_TOGGLE`, `PINCH_DOWN`, `PINCH_UP`, `RIGHT_CLICK`, `SCROLL_UP`, `SCROLL_DOWN`, `ZOOM_IN`, `ZOOM_OUT`, `SILENCE`, `TOGGLE_ACTIVE`, `CLOSE_APP`. Los gestos de una mano usan `hands[0]` y se saltean por completo si `self.active` es `False` (pausado) — devuelve `screen_xy=None` en ese caso, así `main.py` no mueve el mouse ni dibuja el teclado. Los gestos maestros a 2 manos (`TOGGLE_ACTIVE`, `CLOSE_APP`) se evalúan antes de mirar `active`, así siempre se puede reanudar o cerrar.
- **`main.py`** — `JarvisApp`: abre la cámara, corre MediaPipe, llama a `GestureEngine.process`, despacha cada evento al módulo correspondiente, dibuja el HUD y renderiza el frame.

## Por qué separar así

El script original (ver `jarvis-camera-sensor-like-holograph.md`) es una sola clase monolítica — funciona, pero mezcla detección de gestos con efectos de I/O (mouse, voz, SO), lo que hace imposible probar la lógica de gestos sin abrir una cámara real. Separar `GestureEngine` (puro, sin I/O) del despacho en `main.py` mantiene el mismo presupuesto de performance (mismo trabajo por frame, sin capas extra) pero permite testear gestos con landmarks sintéticos.

## Concurrencia

Un único hilo adicional (voz). Todo lo demás corre en el loop principal de cámara para no introducir jitter en el tracking de manos.
