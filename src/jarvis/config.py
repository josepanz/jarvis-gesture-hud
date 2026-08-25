"""Constantes ajustables: umbrales de gestos, cooldowns, colores, rutas."""

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

EMA_ALPHA = 0.35
POINTER_MARGIN = 0.1  # recorte de bordes al mapear cámara -> pantalla

# Umbrales de pinch/distancia (px sobre el frame)
PINCH_CLICK = 30
PINCH_RIGHT_CLICK = 30
PINCH_ZOOM = 30
PINCH_VOLUME = 30
PINCH_SCREENSHOT = 25
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
VOLUME_DELTA_THRESHOLD = 0.03

MAX_HANDS = 2
MIRROR_CAMERA_DEFAULT = True  # True = camara frontal/selfie (se espeja). False = camara trasera/externa.

CAPTURES_DIR = "captures"

HUD_KEY_COLOR = (255, 0, 0)
HUD_KEY_HOVER_COLOR = (0, 255, 255)
HUD_TEXT_COLOR = (255, 255, 255)
HUD_START_Y = 50
HUD_ROW_HEIGHT = 35
HUD_KEY_WIDTH = 52
