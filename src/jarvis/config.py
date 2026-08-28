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

NARUTO_SEAL_HOLD_SECONDS = 0.6  # TASK-062: mismo orden que META_HOLD_SECONDS - deliberado pero rapido
# Verificado en camara real (2026-08-27): incluso con la forma correcta
# sostenida a proposito, la clasificacion parpadea a None por 1 frame suelto
# de tanto en tanto (ruido de landmark/deteccion, no un cambio real de
# pose). Sin tolerancia, CUALQUIER parpadeo reinicia el hold entero y hace
# casi imposible acumular 0.6s seguidos en la practica. Mismo principio que
# PINCH_CONFIRM_FRAMES (TASK-055/1.5), aplicado del lado de "no perder el
# progreso" en vez de "no confirmar de mas".
NARUTO_SEAL_MISS_TOLERANCE = 3  # frames seguidos sin match tolerados antes de reiniciar el hold

MAX_HANDS = 2
MIRROR_CAMERA_DEFAULT = True  # True = camara frontal/selfie (se espeja). False = camara trasera/externa.

# TASK-056: filtro de manos implausibles (fondo/otra persona) antes de la
# logica de gestos. Medido 2026-08-27 con datos reales de camara (DroidCam),
# usuario en posicion normal de escritorio: el bbox de una mano propia (sola
# o de a 2, en uso normal, no necesariamente juntas) fue de 0.0028 a 0.0126
# de fraccion del area del frame. MIN_HAND_AREA_FRACTION queda bien por
# debajo del minimo real observado (una mano de fondo, a mayor distancia de
# la camara, cae por debajo mucho mas rapido porque el area escala con el
# cuadrado de la distancia). La distancia entre centros de las 2 manos
# propias, en uso normal (no necesariamente un gesto de 2 manos deliberado),
# fue 0.384-0.398 de la diagonal del frame; TWO_HAND_MAX_CENTER_DISTANCE_FRACTION
# queda con margen holgado por encima de ese maximo real para no rechazar las
# 2 manos del usuario. Ver ARCHITECTURE.md para el detalle de la medicion.
MIN_HAND_AREA_FRACTION = 0.0015
TWO_HAND_MAX_CENTER_DISTANCE_FRACTION = 0.55

# TASK-060c (Fase 3B): filtro de propiedad anatomica mano-cuerpo via
# MediaPipe Pose. Deshabilitado por default: medido en camara real
# (2026-08-27) que PoseLandmarker cuesta ~10.4ms/frame promedio (p95 ~12.6ms),
# practicamente el mismo costo que HandLandmarker (~10.0ms/frame promedio) -
# activarlo DUPLICA el costo de inferencia por frame (~20ms combinado), un
# costo real y no trivial contra el presupuesto de "menos de 1 frame" de
# design.md #25 (~16-33ms a 30-60fps). No es un costo "claramente malo" (el
# heuristico de TASK-056 sigue funcionando solo, sin esto), pero tampoco es
# gratis - se deja togglable y apagado por default en vez de descartarlo,
# per design.md §3B.3. Ver ARCHITECTURE.md para el detalle completo.
POSE_HAND_OWNERSHIP_ENABLED = False
# Distancia maxima (fraccion de la diagonal del frame) entre la muñeca que
# reporta HandTracker y la muñeca correspondiente que reporta PoseTracker
# para considerar que son el mismo punto fisico (2 modelos distintos
# detectando el mismo punto del cuerpo, no 2 manos distintas - por eso el
# margen es chico, muy por debajo de TWO_HAND_MAX_CENTER_DISTANCE_FRACTION
# de arriba, que es entre 2 MANOS DISTINTAS de la misma persona). No pudo
# verificarse con datos reales de cuerpo completo en esta sesion (la camara
# disponible estaba encuadrada en la mano/escritorio, no en el torso) -
# valor razonado, no medido; documentado como limitacion conocida.
POSE_MAX_WRIST_DISTANCE_FRACTION = 0.08

CAPTURES_DIR = "captures"

HUD_KEY_COLOR = (255, 0, 0)
HUD_KEY_HOVER_COLOR = (0, 255, 255)
HUD_TEXT_COLOR = (255, 255, 255)
HUD_START_Y = 50
HUD_ROW_HEIGHT = 35
HUD_KEY_WIDTH = 52

# TASK-057 (Fase 2): overlay toggleable de landmarks/cuadrante de mano.
HAND_OVERLAY_PRIMARY_COLOR = (0, 255, 0)  # mano primaria (BGR, verde)
HAND_OVERLAY_OTHER_COLOR = (120, 120, 120)  # cualquier otra mano detectada (BGR, gris)
