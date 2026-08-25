"""Contenido del listado de gestos — fuente unica, consumida por el overlay nativo
de escritorio (`overlay.py`). Ya no se dibuja dentro de la ventana de camara."""

TITLE = "JARVIS — Gestos"

ENTRIES = [
    ("Índice movido", "Puntero"),
    ("Pulgar + Índice (pinch)", "Click / Drag"),
    ("Pulgar + Medio (pinch)", "Click derecho"),
    ("Índice + Medio arriba", "Scroll"),
    ("Pulgar + Anular (pinch)", "Zoom"),
    ("Palma abierta", "Teclado HUD"),
    ("Pulgar + Meñique + mover", "Volumen"),
    ("Pulgar + Anular cerrado", "Captura"),
    ("Shaka 1.5s (1 mano)", "Bloquear sesión"),
    ("Palma, pulgar a meñique", "Silenciar voz"),
    ("2 puños juntos 1.2s", "Pausar / Reanudar"),
    ("2 manos en Shaka 1.5s", "Cerrar Jarvis"),
    ("Tecla q", "Salir"),
    ("Tecla h", "Mostrar/ocultar lista"),
    ("Tecla m", "Modo espejo on/off"),
    ("Teclas +/-", "Transparencia"),
]


def build_legend_text():
    width = max(len(gesture) for gesture, _ in ENTRIES)
    lines = [TITLE, ""]
    lines += [f"{gesture.ljust(width)}  →  {action}" for gesture, action in ENTRIES]
    return "\n".join(lines)
