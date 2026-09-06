"""Contenido del listado de gestos — fuente unica, consumida por el overlay nativo
de escritorio (`overlay.py`). Ya no se dibuja dentro de la ventana de camara.

TASK-059 (Fase 3, spec.md #3.3): cada entrada ahora tambien lleva una icon key,
resuelta via `jarvis.gesture_icons.ensure_icon()` en `build_legend_entries()` -
`build_legend_text()` se mantiene sin cambios en su salida (solo el unpacking
de la tupla cambia de 2 a 3 elementos).

Referencia visual de los 12 sellos Naruto (Y-05,
`openspec/changes/hand-sign-fidelity/`): las descripciones de ENTRIES estan
sacadas de las 14 fotos en `docs/gesture-reference/canonical/` - esa carpeta
es la fuente de verdad si una descripcion de aca queda dudosa o desactualizada."""

TITLE = "JARVIS — Gestos"

ENTRIES = [
    ("Índice movido", "Puntero", "pointer"),
    ("Pulgar + Índice (pinch)", "Click / Drag", "pinch_click"),
    ("Pulgar + Medio (pinch)", "Click derecho", "pinch_right_click"),
    ("Índice + Medio arriba, mover desde el centro", "Scroll (4 direcciones)", "scroll"),
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
    # Y-05 (`openspec/changes/hand-sign-fidelity/WORKPLAN.md`): los 12 sellos
    # del zodiaco, todos de 2 MANOS - el modelo YOLOX de `hand_sign_tracker.py`
    # los detecta y los sostiene config.NARUTO_TWOHAND_HOLD_SECONDS; ya no hay
    # geometria propia que describir aca, la forma real esta fotografiada en
    # `docs/gesture-reference/canonical/` (14 fotos, una por sello) - las
    # descripciones de abajo estan sacadas de esas fotos, no inventadas.
    # NARUTO_KAI se borro (no es uno de los 14 canonicos, AUDIT.md); su accion
    # default (Cerrar Jarvis) sigue alcanzable con las 2 manos en Shaka.
    ("Sello Tora (manos en punta, dedos entrelazados)", "Captura", "naruto_tora"),
    ("Sello Ushi (manos en cruz, dedos entrelazados)", "Deshacer", "naruto_ushi"),
    ("Sello U (manos entrelazadas, índice al costado)", "Rehacer", "naruto_u"),
    ("Sello Uma (manos en techo, dedos entrelazados)", "Zoom +", "naruto_uma"),
    ("Sello Hitsuji (manos entrelazadas, dedo asomando)", "Silenciar sistema", "naruto_hitsuji"),
    ("Sello Saru (mano envuelve la muñeca de la otra)", "Teclado HUD", "naruto_saru"),
    ("Sello Inu (puño envuelto por la otra mano)", "Volumen -", "naruto_inu"),
    ("Sello I (2 puños juntos, nudillos enfrentados)", "Bloquear sesión", "naruto_i"),
    ("Sello Ne (manos entrelazadas hacia arriba)", "Zoom -", "naruto_ne"),
    ("Sello Mi (manos entrelazadas hacia abajo)", "Scroll abajo", "naruto_mi"),
    ("Sello Tori (manos en abanico, dedos juntos)", "Scroll arriba", "naruto_tori"),
    ("Sello Tatsu (manos en rombo, dedos curvados)", "Volumen +", "naruto_tatsu"),
    # Y-06: Gassho y Mizunoe - no son sellos del zodiaco, pero el modelo los
    # distingue igual (salian gratis) y usan el mismo mecanismo de hold.
    ("Sello Gassho (manos juntas en oración, palmas planas)", "Cerrar Jarvis", "naruto_gassho"),
    ("Sello Mizunoe (manos entrelazadas, parecido a Inu)", "Scroll izquierda", "naruto_mizunoe"),
    # Y-07: secuencias de sellos (jarvis.hand_sign_sequence), decodificadas de
    # jutsu.csv del proyecto original - config.NARUTO_SEQUENCE_INTERVAL_SECONDS
    # (2s) sin ningun sello nuevo reinicia el combo a medio hacer.
    ("Secuencia Hitsuji→Mi→Tora (Bunshin)", "Doble click", "jutsu_bunshin"),
    ("Secuencia Hitsuji→I→Ushi→Inu→Mi (Kawarimi)", "Deshacer", "jutsu_kawarimi"),
    ("Secuencia Mi→Tora→Saru→I→Uma→Tora (Katon)", "Zoom +", "jutsu_katon"),
    # TASK-070 (Fase 6): sellos JJK, sostenidos config.NARUTO_TWOHAND_HOLD_SECONDS
    # (Gojo) o config.NARUTO_SEAL_HOLD_SECONDS (Megumi) - Sukuna es temporal
    # (ImpulseDetector), sin hold.
    ("Sello Gojo (marco en L, 2 manos arriba)", "Click derecho", "jjk_gojo_domain"),
    ("Sello Sukuna (chasquido pulgar-medio)", "Captura", "jjk_sukuna"),
    ("Sello Megumi (índice+medio+anular)", "Silenciar sistema", "jjk_megumi"),
    # TASK-073 (Fase 7): gestos comunes. Aplauso es temporal (ImpulseDetector,
    # sin hold); corazón coreano exige config.KOREAN_HEART_HOLD_SECONDS.
    ("Aplauso (2 manos, acercar y separar)", "Teclado HUD", "clap"),
    ("Corazón coreano (pulgar+índice, sostenido)", "Captura", "korean_heart"),
    # C-01 (WORKPLAN.md §10, workflow 8): dwell-click, apagado por defecto
    # (config.DWELL_CLICK_ENABLED) - la fila existe igual para que sea
    # reasignable desde el settings apenas se habilite.
    ("Índice quieto sobre el objetivo (dwell)", "Click izquierdo", "dwell_click"),
    # C-02 (WORKPLAN.md §10, workflow 8): doble click, re-anclado a la
    # posicion del primero - siempre activo (no tiene el riesgo de falso
    # positivo del dwell, es un pinch normal x2 dentro del intervalo).
    ("Pulgar + Índice (pinch) x2 rápido", "Doble click", "double_click"),
    # C-03 (WORKPLAN.md §10, workflow 8): swipe con puño cerrado, 1 mano.
    # UP/DOWN no tienen accion por default (ver GESTURE_DEFAULT_BINDINGS) -
    # se detectan igual y son reasignables desde el settings.
    ("Puño cerrado, movimiento rápido a la izquierda", "Atrás (navegador/explorador)", "swipe_left"),
    ("Puño cerrado, movimiento rápido a la derecha", "Adelante (navegador/explorador)", "swipe_right"),
    ("Puño cerrado, movimiento rápido hacia arriba", "Sin asignar (reasignable)", "swipe_up"),
    ("Puño cerrado, movimiento rápido hacia abajo", "Sin asignar (reasignable)", "swipe_down"),
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
