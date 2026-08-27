"""Constantes ajustables: umbrales de gestos, cooldowns, colores, rutas."""

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

EMA_ALPHA = 0.35
POINTER_MARGIN = 0.1  # recorte de bordes al mapear cámara -> pantalla

# Umbrales de pinch/distancia (px sobre el frame). Recalibrados 2026-08-27 con
# datos reales de camara (DroidCam): mano relajada (sin pellizcar a proposito)
# llego a 15.5px en indice / 19.2px en medio / 34.2px en anular / 51.3px en
# menique por momentos de movimiento natural, mientras que un pinch
# intencional (indice) tuvo mediana 9.6px. Los valores viejos (25-30 para
# todos) quedaban demasiado cerca del ruido de mano relajada, sobre todo para
# indice/medio - de ahi el reporte de "todo dispara muy facil". Bajados con
# margen de seguridad sobre indice/medio (los mas expuestos); anular/menique
# ya tenian margen razonable, se ajustan un poco igual por consistencia. Ver
# ARCHITECTURE.md para el detalle completo de la medicion.
PINCH_CLICK = 18
PINCH_RIGHT_CLICK = 20
PINCH_ZOOM = 25
PINCH_VOLUME = 28
PINCH_SCREENSHOT = 20
PINCH_CONFIRM_FRAMES = 2  # frames seguidos bajo el umbral antes de confirmar un pinch - absorbe ruido de un solo frame
PALM_OPEN_MIN_SPREAD = 60
SILENCE_TUCK_MAX = 40

# Cooldowns (segundos)
CLICK_COOLDOWN = 0.3
RIGHT_CLICK_COOLDOWN = 0.4
KEYBOARD_TOGGLE_COOLDOWN = 1.0
SCREENSHOT_COOLDOWN = 1.5
SILENCE_COOLDOWN = 0.8
LOCK_HOLD_SECONDS = 1.5
CLOSE_APP_HOLD_SECONDS = 1.5
PAUSE_HOLD_SECONDS = 1.2
META_HOLD_SECONDS = 0.6
VOLUME_DELTA_THRESHOLD = 0.03
TWO_HAND_ZOOM_DELTA_PX = 15

MAX_HANDS = 2
MIRROR_CAMERA_DEFAULT = True  # True = camara frontal/selfie (se espeja). False = camara trasera/externa.

CAPTURES_DIR = "captures"

HUD_KEY_COLOR = (255, 0, 0)
HUD_KEY_HOVER_COLOR = (0, 255, 255)
HUD_TEXT_COLOR = (255, 255, 255)
HUD_START_Y = 50
HUD_ROW_HEIGHT = 35
HUD_KEY_WIDTH = 52
