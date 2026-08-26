# CHANGELOG


## v0.1.0 (2026-08-26)

### Bug Fixes

- Ci rota en macOS/Linux por dependencias headless de mediapipe/pyautogui
  ([`b267e9c`](https://github.com/josepanz/jarvis-gesture-hud/commit/b267e9caab24e552de985768771582c31fc74762))

Dos fallas reales encontradas en la primera corrida real de ci.yml (nunca se habia disparado hasta
  el merge de hoy):

- HandLandmarker.create_from_options() aborta el proceso (SIGABRT) en macOS headless y falla por
  libEGL faltante en Linux headless - el runtime nativo de mediapipe necesita un servicio de
  GPU/graficos incluso antes de correr inferencia. Confirmado funcionando de verdad en Windows (esta
  maquina y CI). Se salta la clase de test que construye un HandTracker real en macOS/Linux (unico
  archivo que lo hace), documentado el motivo en el propio skip.

- pyautogui.mouseinfo abre un Display() X11 real al importarse en Linux (a diferencia de
  Windows/macOS, que usan API nativa) - sin DISPLAY, cualquier test que importe
  jarvis.actions/jarvis.main falla antes de correr. Se instala xvfb y se corre la suite bajo
  xvfb-run solo en el job de Linux.

- Release CI roto por bug de gitpython 3.1.60 con python-semantic-release
  ([`8337811`](https://github.com/josepanz/jarvis-gesture-hud/commit/8337811357cc6ce271d53c79e5dd3f800a273a87))

GitPython 3.1.60 (publicado hoy) removio Actor.name_email_regex, que el config loader de
  python-semantic-release llama directo - rompe toda invocacion, incluida la Docker action oficial
  (instala gitpython~=3.0 sin pin superior al buildear la imagen). Bug abierto y sin fix upstream
  (python-semantic-release/python-semantic-release#1475).

Se reemplaza la Docker action por el CLI instalado directo en el runner, pineando gitpython<3.1.60,
  asi el pin realmente aplica. Confirmado local: sin el pin el config loader crashea con el mismo
  AttributeError; con el pin carga limpio.

De paso, corrige el warning de deprecacion de changelog_file (se movio a
  changelog.default_templates.changelog_file en preparacion para v10).

### Continuous Integration

- Add semantic-release versioning and multi-OS release binaries
  ([`76c7fa2`](https://github.com/josepanz/jarvis-gesture-hud/commit/76c7fa230f635529598a83b7374112f79b8f8cb8))

- pyproject.toml + python-semantic-release config, driven by Conventional Commits on main
  (feat/fix/perf bump the version, others don't but still land in CHANGELOG.md). -
  .github/workflows/ci.yml: run the full test suite on every push/PR across windows/macos/ubuntu. -
  .github/workflows/release.yml: on a release-worthy push to main, tag + changelog + GitHub Release
  via semantic-release, then build Jarvis natively on each OS (PyInstaller can't cross-compile) and
  attach it as a download. - Documented the release process and its known gap (macOS/Linux binaries
  are unsigned) in ARCHITECTURE.md; not yet triggered for real since this is an unmerged branch.

### Features

- Control por voz local (STT + LLM) con push-to-talk
  ([`7fcec77`](https://github.com/josepanz/jarvis-gesture-hud/commit/7fcec772a2f28cdcf5b054435eb96102dae2d2bf))

VoiceListener (sounddevice + faster-whisper) transcribe en un hilo aparte; el texto se resuelve
  primero por frase exacta (VoiceIntentResolver) y si no matchea cae a LLMIntentResolver
  (Qwen2.5-1.5B-Instruct GGUF via llama-cpp-python), restringido a un vocabulario de acciones fijo y
  validado. ConfidenceFilter descarta transcripciones de baja confianza (senal real de
  faster-whisper) antes de gastar el LLM. Tecla 'v' activa/desactiva el microfono; ambas rutas
  reusan el mismo Command/CommandBus que los gestos.

Dependencias pesadas opcionales en requirements-voice.txt, import perezoso - la app base y su suite
  de tests corren igual sin ellas instaladas.

Extrae jarvis.paths.assets_dir() de hand_tracker.py para compartir la logica de resolucion de rutas
  con el nuevo modulo de LLM.

- Wire Telemetry, Profiles, undo/redo, and a debug HUD into the live app
  ([`8de44d9`](https://github.com/josepanz/jarvis-gesture-hud/commit/8de44d974cfe9a4b7e4d5e9390f5dc411a6164fd))

Connects the previously-dormant PHASE 3-11 infrastructure into main.py where it's genuinely low-risk
  and demonstrably useful, following the same discipline used throughout the OpenSpec migration -
  every wiring choice is justified in main.py's module docstring, including what was deliberately
  left unwired and why.

- Telemetry: always-on, in-memory only (no sink configured) - records per-frame FPS/frame_time,
  gesture confidence/success, and command success/duration. - ProfileManager: GestureEngine's
  smoothing_enabled is now sourced from the active profile instead of hardcoded ('default' matches
  prior behavior exactly); 'p' cycles registered profiles. - CommandHistory + UndoRedoController:
  every dispatched command except the continuous MouseMove is recorded; 'z'/'y' trigger real
  undo/redo of whichever commands declare themselves reversible (Volume*/CanvasZoom). - Debug HUD
  ('d'): ContextualHudRenderer + debug_telemetry overlay, off by default. -
  ForegroundApplicationTracker: runs cached (0.5s TTL), feeds telemetry.

Not wired, on purpose: GestureStateMachine, generic debounce/cooldown, ConfidenceFilter
  (GestureEngine has no real confidence signal to filter on), swipe/dwell/double-click gesture
  bindings (would mean inventing new gesture->action mappings with real false-positive risk), and an
  InputProvider-based loop rewrite (high risk, zero behavior change).

Added a new profiles.py accessor (profile_names) and a manual integration check script
  (tests/manual_live_integration_check.py, same pattern as the PHASE 2 one) exercising
  undo/redo/profile-cycling/debug-HUD/telemetry against a real JarvisApp with only
  pyautogui/CrossPlatformOS mocked.
