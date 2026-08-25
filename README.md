# Jarvis Gesture HUD

Control de PC por gestos de mano (cámara web) con feedback de voz tipo "Jarvis", en Python, multiplataforma (Windows/macOS/Linux), sin dependencias pesadas y empaquetable como ejecutable portable.

**Descarga el ejecutable**: cada release en [Releases](https://github.com/josepanz/jarvis-gesture-hud/releases) trae un binario listo para Windows/macOS/Linux — no hace falta instalar Python. Se generan automáticamente (`.github/workflows/release.yml`, ver [ARCHITECTURE.md § Releases](ARCHITECTURE.md#releases)); macOS/Linux quedan sin firmar (ver esa sección para el detalle).

## Qué hace

- Mueve el mouse con el dedo índice, click/drag con pinch, scroll, zoom.
- Teclado virtual HUD flotante (español, símbolos, emojis) controlable por gestos.
- Controles de sistema: captura de pantalla, volumen, bloqueo de sesión — multiplataforma.
- Voz Jarvis (offline, `pyttsx3`) que anuncia acciones clave en español.
- **Gesto de silencio**: mano abierta con el pulgar recogido hacia el meñique interrumpe la voz al instante.
- **Panel nativo de gestos**: ventana de Windows real anclada a una esquina de la pantalla (no dentro de la ventana de cámara), translúcida, no-clickeable, con transparencia ajustable (`+`/`-`) y toggle de visibilidad (`h`).
- **Globos translúcidos en toda la pantalla**: al bloquear sesión, sacar captura, silenciar, tocar volumen/zoom, pausar/reanudar o cerrar, aparece un aviso translúcido junto al cursor — no solo dentro de la ventana de cámara.
- **Hasta 2 manos**, con gestos maestros: 2 puños juntos (1.2s) pausa/reanuda toda la lectura de gestos; 2 manos en Shaka (1.5s) cierra la app; 2 manos pellizcando y separándolas/juntándolas hace zoom de lienzo (no escala el objeto seleccionado — eso ya funciona arrastrando el handle de la app con una mano).
- **Menú de gestos secundarios**: puño ancla (cualquiera de las 2 manos) + 1/2/3/4 dedos en la otra, sostenido 0.6s, hace lo mismo que `h`/`m`/`+`/`-` sin tocar el teclado.
- **Modo espejo conmutable** (tecla `m`, en caliente): cámara frontal/selfie (espejada) vs. trasera/externa (sin espejar) — corrige también la lateralidad Left/Right que reporta MediaPipe.

Documentación completa (arquitectura, estado actual, decisiones de diseño, [referencia de configuración](ARCHITECTURE.md#configuration-reference), [línea base de performance](ARCHITECTURE.md#performance-baseline), [instrucciones de desarrollo](ARCHITECTURE.md#development) y limitaciones conocidas) en **[ARCHITECTURE.md](ARCHITECTURE.md)**. El proyecto tiene una migración de arquitectura en curso, guiada por OpenSpec, en [`openspec/changes/multimodal-interaction-core/`](openspec/changes/multimodal-interaction-core/) — todas sus 12 fases están completas y documentadas ahí. Los documentos de planificación originales en español quedaron archivados en [`docs/archive-es/`](docs/archive-es/).

## Requisitos

Python 3.10–3.12. Ver [`requirements.txt`](requirements.txt).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Con la ventana de cámara enfocada:

| Tecla | Acción |
|---|---|
| `q` | Salir |
| `h` | Mostrar/ocultar el panel de gestos |
| `m` | Alternar modo espejo (frontal/trasera) |
| `+` / `-` | Más / menos transparencia del panel de gestos |

Todas las teclas tienen gesto equivalente (`q` = 2 manos en Shaka, ver arriba) — ver [ARCHITECTURE.md](ARCHITECTURE.md#gesture-map).

> Primer arranque: descarga una sola vez el modelo `hand_landmarker.task` (~10MB) a `assets/` — mediapipe quitó la API legacy `mp.solutions` de los wheels de Windows desde la 0.10.30, así que `hand_tracker.py` usa la API "Tasks" nueva. Corridas siguientes usan el modelo ya cacheado, sin red.

## Empaquetar como ejecutable portable

```bash
pip install pyinstaller
pyinstaller build/jarvis.spec --distpath dist --workpath build/work
```

Genera `dist/Jarvis.exe` (Windows) o `dist/Jarvis` (macOS/Linux). Scripts listos:
[`build/build_windows.ps1`](build/build_windows.ps1), [`build/build_macos.sh`](build/build_macos.sh), [`build/build_linux.sh`](build/build_linux.sh).

> El build de PyInstaller es nativo del SO donde se ejecuta — no hay cross-compilación. Corré el script correspondiente en cada plataforma. Ya probado en Windows: `Jarvis.exe` (117MB) arranca y corre sin errores — ver detalles en [ARCHITECTURE.md](ARCHITECTURE.md#status).

## Estructura

```
jarvis-gesture-hud/
├── README.md
├── ARCHITECTURE.md         # arquitectura, estado, decisiones y limitaciones (inglés)
├── requirements.txt
├── run.py                  # entry point
├── docs/archive-es/        # specs originales en español (histórico)
├── openspec/changes/       # propuesta OpenSpec en curso (arquitectura Command/CommandBus)
├── tests/                  # suite automática (unittest, stdlib) + checks de integración manuales
├── src/jarvis/
│   ├── config.py            # umbrales, colores, cooldowns
│   ├── os_native.py         # lock/volumen/screenshot por SO
│   ├── voice.py             # TTS Jarvis + gesto de silencio
│   ├── hand_tracker.py      # wrapper de MediaPipe Tasks (HandLandmarker)
│   ├── hud_keyboard.py      # teclado virtual en pantalla
│   ├── legend.py            # contenido del listado de gestos
│   ├── overlay.py           # panel nativo + globos translúcidos (Tkinter)
│   ├── gestures.py          # motor de reconocimiento de gestos
│   ├── main.py              # loop de cámara y despacho de eventos
│   ├── core/                # GestureEvent, Intent, Command, CommandBus, FeedbackManager
│   └── actions/             # Commands concretos: mouse, keyboard, system
├── build/                   # PyInstaller spec + scripts por plataforma
└── captures/                # screenshots guardados
```

Correr los tests: `python -m unittest discover -s tests -v` (422 tests, sin dependencias nuevas). Detalles de qué está probado, cómo, y las convenciones para agregar módulos nuevos en [ARCHITECTURE.md § Development](ARCHITECTURE.md#development).
