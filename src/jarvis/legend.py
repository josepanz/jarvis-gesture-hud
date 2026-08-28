"""Contenido del listado de gestos — fuente unica, consumida por el overlay nativo
de escritorio (`overlay.py`). Ya no se dibuja dentro de la ventana de camara.

TASK-059 (Fase 3, spec.md #3.3): cada entrada ahora tambien lleva una icon key,
resuelta via `jarvis.gesture_icons.ensure_icon()` en `build_legend_entries()` -
`build_legend_text()` se mantiene sin cambios en su salida (solo el unpacking
de la tupla cambia de 2 a 3 elementos)."""

TITLE = "JARVIS — Gestos"

ENTRIES = [
    ("Índice movido", "Puntero", "pointer"),
    ("Pulgar + Índice (pinch)", "Click / Drag", "pinch_click"),
    ("Pulgar + Medio (pinch)", "Click derecho", "pinch_right_click"),
    ("Índice + Medio arriba", "Scroll", "scroll"),
    ("Pulgar + Anular (pinch)", "Zoom", "pinch_zoom"),
    ("Palma abierta", "Teclado HUD", "open_palm_keyboard"),
    ("Pulgar + Meñique + mover", "Volumen", "pinch_volume"),
    ("Pulgar + Anular cerrado", "Captura", "pinch_screenshot"),
    ("Shaka 1.5s (1 mano)", "Bloquear sesión", "shaka_lock"),
    ("Palma, pulgar a meñique", "Silenciar voz", "silence"),
    ("2 puños juntos 1.2s", "Pausar / Reanudar", "two_fist_pause"),
    ("2 manos en Shaka 1.5s", "Cerrar Jarvis", "two_shaka_close"),
    ("Tecla q", "Salir", "key_quit"),
    ("Tecla h", "Mostrar/ocultar lista", "key_toggle_legend"),
    ("Tecla m", "Modo espejo on/off", "key_mirror"),
    ("Teclas +/-", "Transparencia", "key_legend_opacity"),
    # TASK-063 (Fase 4): sellos Naruto de 1 mano, sostenidos
    # config.NARUTO_SEAL_HOLD_SECONDS - accion segun el binding por default
    # (o el override del perfil activo, ver main.py NARUTO_DEFAULT_BINDINGS).
    ("Sello Tora (índice+medio)", "Captura", "naruto_tora"),
    ("Sello Ushi (índice)", "Deshacer", "naruto_ushi"),
    ("Sello U (índice+medio separados)", "Rehacer", "naruto_u"),
    ("Sello Uma (índice+medio+anular)", "Zoom +", "naruto_uma"),
    ("Sello Hitsuji (índice+medio cruzados)", "Silenciar sistema", "naruto_hitsuji"),
    ("Sello Saru (pulgar+anular)", "Teclado HUD", "naruto_saru"),
    ("Sello Inu (anular+meñique)", "Volumen -", "naruto_inu"),
    ("Sello I (puño, pulgar afuera)", "Bloquear sesión", "naruto_i"),
]


def build_legend_text():
    width = max(len(gesture) for gesture, _, _ in ENTRIES)
    lines = [TITLE, ""]
    lines += [f"{gesture.ljust(width)}  →  {action}" for gesture, action, _ in ENTRIES]
    return "\n".join(lines)


def build_legend_entries():
    """(gesture, action, icon_path) por cada entrada - spec.md #3.3, consumido
    por `overlay.ScreenOverlay.init_legend()`."""
    from jarvis.gesture_icons import ensure_icon

    return [(gesture, action, ensure_icon(icon_key)) for gesture, action, icon_key in ENTRIES]
