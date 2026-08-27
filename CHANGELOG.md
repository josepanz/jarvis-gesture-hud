# CHANGELOG


## v0.1.2 (2026-08-27)

### Bug Fixes

- Click izquierdo y derecho ya no comparten cooldown
  ([`910b0fb`](https://github.com/josepanz/jarvis-gesture-hud/commit/910b0fb9deaf979113bb44332b007d8fdbac428f))

PINCH_DOWN y RIGHT_CLICK usaban el mismo timer (last_click_time) para sus cooldowns. Como la rama de
  PINCH_DOWN corre primero cada frame, un click izquierdo genuino podia "tragarse" un click derecho
  genuino hecho poco despues (y viceversa, porque RIGHT_CLICK tambien escribia en el mismo timer) -
  un bug real, distinto al de TASK-055 (esa ambiguedad era dentro del mismo frame; esta es entre 2
  gestos limpios y separados en el tiempo).

Verificado revirtiendo el fix en ambas direcciones antes de confiar en el test. Fix:
  last_right_click_time propio para RIGHT_CLICK.

447 tests (2 nuevos), regresion completa y boot real de la app verificados.


## v0.1.1 (2026-08-27)

### Bug Fixes

- Resuelve la confusion de gestos de pinch en el mismo frame (TASK-055)
  ([`530747d`](https://github.com/josepanz/jarvis-gesture-hud/commit/530747de1267c8b9300b2195037c6d2f06814962))

gestures.py calculaba cada distancia pulgar-dedo de forma independiente, sin verificar que solo una
  fuera la intencional. En un puno con solo pulgar+indice desplegados y pellizcando, las puntas
  curvadas de los demas dedos quedan geometricamente cerca del pulgar (consecuencia natural de la
  forma de un puno) y pueden cumplir el umbral de otro pinch en el mismo frame - el bug reportado
  ("funciona pero se confunde").

Verificado revirtiendo el fix y reproduciendo ['SCREENSHOT', 'PINCH_DOWN'] disparando juntos desde
  un fixture sintetico (no supuesto). De paso, se encontro que PINCH_DOWN y RIGHT_CLICK comparten el
  mismo timer de cooldown (last_click_time) y por eso ese par en particular ya quedaba enmascarado
  por accidente - SCREENSHOT (cooldown independiente) fue el par que si reproducia el bug de verdad.

Fix: se resuelve un solo ganador por frame - el pinch con la distancia mas chica - antes de permitir
  que cualquier rama dispare; el resto se suprime ese frame. En un empate exacto gana el orden fijo
  (indice > medio > anular > menique), documentado y testeado.

445 tests (4 nuevos), regresion completa verde, boot real de la app y ambos checks de integracion
  manual verificados.

### Documentation

- Amplia spec de gestos - sellos completos, JJK, comunes, viz y fixes
  ([`86db22c`](https://github.com/josepanz/jarvis-gesture-hud/commit/86db22c427db0ed649f097406bd5df22884e9d82))

Revision de openspec/changes/personalization-and-config-ui/ (nada de la version anterior estaba
  implementado, se reemplaza en vez de apilar):

- 2 bugs reales encontrados leyendo gestures.py de verdad (no supuestos): el pinch pulgar+indice se
  confunde con click derecho/captura/volumen/zoom cuando la mano esta en puno con esos 2 dedos
  desplegados (las puntas curvadas de los otros dedos caen cerca del pulgar y disparan varias
  condiciones de pinch a la vez); y el tracking de 2 manos no filtra por plausibilidad, asi que una
  mano de otra persona en cuadro puede combinarse con la del usuario y disparar gestos a 2 manos
  (pausa, cerrar app) sin querer. Ambos con causa raiz documentada y fix propuesto en design.md. -
  Overlay de landmarks/cuadrantes activable, mostrando mano primaria y gesto detectado con prioridad
  (nuevo, util tambien para depurar los sellos nuevos mientras se implementan). - Sellos Naruto
  completos: 8 de una mano + 5 de dos manos (antes solo 5 de una mano), con el proceso de deteccion
  de colisiones expandido para cubrir tambien los gestos a 2 manos existentes. - Gestos Jujutsu
  Kaisen: Gojo (2 manos estatico), Megumi (1 mano estatico, 1 sola pose representativa - no las 10
  de sus shikigami), Sukuna (1 mano, snap temporal - requiere un detector de impulso nuevo y
  reutilizable). - Gestos comunes: aplauso (2 manos, reutiliza el detector de impulso de Sukuna) y
  corazon coreano (1 mano, el de mayor riesgo de colision con el pinch-click existente, requiere
  hold de confirmacion como el de bloqueo de sesion). - Cada gesto nuevo incluye su pictograma como
  parte de la misma tarea, no diferido a una fase aparte. - Reordenado de menor a mayor: fixes de
  fiabilidad y visualizacion primero (ademas de arreglar bugs reales, la visualizacion ayuda a
  verificar la geometria de los sellos nuevos), config UI y descarga de voz siguen ultimas por las
  mismas razones que antes. - Tasks renumeradas TASK-055 a TASK-082 (28 tareas, antes 15).

- Corrige nota desactualizada de ARCHITECTURE.md sobre control por voz
  ([`7557c74`](https://github.com/josepanz/jarvis-gesture-hud/commit/7557c7455ff9beedc58fa1689d0c4e9970d38167))

Decia 'diferido, no implementado' de una fase anterior a que se construyera de verdad en
  feature/full-integration-voice-llm (ya mergeado).

- Corrige superficie de colision incompleta en censo de gestos 2 manos
  ([`59305d5`](https://github.com/josepanz/jarvis-gesture-hud/commit/59305d531dd2bce74d6aeecfe84dffcd41e71f3e))

Un gesto nuevo de 2 manos no solo puede chocar con los 4 gestos de 2 manos que ya existen (shaka,
  punos, pinch-zoom, menu meta) - GestureEngine.process() tambien evalua los 9 chequeos de 1 mano
  sobre la mano "primaria" cada frame, sin importar que gesto de 2 manos este pasando con la otra.
  De esos 9, solo 2 tienen supresion cruzada hoy (bloqueo de sesion y click). Entonces un sello
  nuevo de 2 manos debe chequearse contra 13 condiciones existentes, no 4 - y esto ya era asi antes
  de este cambio, no es una regresion nueva.

Se corrige design.md (nueva seccion 1.4 con el mapeo completo + tarea opcional para cerrar el gap de
  supresion), spec.md (#4.2/#5.2 reescritos) y tasks.md (TASK-055b nueva, opcional y explicita;
  TASK-064 corregida).

De paso, se aclara en el diseno de Megumi que el numero exacto de shikigami del Ten Shadows
  Technique no es un dato que esta spec necesite fijar - la decision de usar 1 sola pose
  representativa no depende de ese numero.

- Evaluacion de robustez de percepcion (MediaPipe Pose, z, iluminacion)
  ([`4a4b3de`](https://github.com/josepanz/jarvis-gesture-hud/commit/4a4b3dee835f9e8e374c5235f2b9cb339a3c6dc5))

Nuevo Apendice A en design.md, verificado contra el entorno real instalado (no de memoria):
  mediapipe 1.0.1 ya trae PoseLandmarker en el mismo paquete que ya se usa para manos, cero
  dependencia nueva - permitiria filtrar manos de otra persona por conexion anatomica real (muneca
  de mano cerca de muneca de pose) en vez de solo tamano de bounding-box como hoy. El campo z (y
  visibility/presence) de NormalizedLandmark ya se calcula en cada frame y gestures.py nunca lo usa
  - gratis, cero descarga nueva, mejoraria el pinch a distancia 3D en vez de 2D (posible segunda
  causa del bug de confusion de pinch, a verificar durante TASK-055). cv2.createCLAHE ya esta
  disponible en el opencv-python instalado - tecnica estandar y barata para mejorar tracking en luz
  baja, cero dependencia nueva. Mejora neuronal de iluminacion (tipo Zero-DCE) evaluada y no
  recomendada por ahora - dependencia real de ML sin problema concreto que lo justifique.

Queda como evaluacion, sin numeros de TASK asignados todavia - a la espera de que se decida
  promoverla a fase real.

- Formaliza jerarquia obligatoria para gestos de 2 manos
  ([`1a3c100`](https://github.com/josepanz/jarvis-gesture-hud/commit/1a3c10014d7b3255e7ca6f12cfaf231a2f349fa7))

Nueva seccion design.md 1.5: todo gesto de 2 manos (existente o nuevo) tiene que caer en una de 4
  categorias - simetrico (ambas manos igual forma), forma conjunta (el gesto es una propiedad de
  ambas manos juntas, ej. los sellos con dedos entrelazados), ancla+modificador (una mano fija, la
  otra elige variante dentro de la misma familia, sin importar lateralidad), o senal continua
  conjunta (una sola metrica entre las 2 manos, ej. distancia del pinch-zoom o del aplauso). Se
  prohibe explicitamente el patron peligroso: una mano interpretada de forma independiente haciendo
  una cosa y la otra haciendo otra sin relacion, combinadas solo porque coinciden en el mismo frame
  - eso multiplica la ambiguedad en vez de reducirla, y es la misma clase de bug que ya causaba la
  confusion de pinch/puno (spec 1.1) pero a escala de 2 manos completas.

Verificado que ningun gesto ya propuesto en la spec (sellos Naruto 2 manos, Gojo/Ryoiki Tenkai,
  aplauso) cae en el patron prohibido - se documenta explicitamente en spec.md/design.md/tasks.md a
  que patron pertenece cada uno, y se exige que las tareas futuras (fase 5-7) declaren el patron
  usado o rediseñen el gesto si no encaja limpio en ninguno de los 4.

- Nombra explicitamente el gesto de Gojo como Dominio/Ryoiki Tenkai
  ([`d2bf4b0`](https://github.com/josepanz/jarvis-gesture-hud/commit/d2bf4b067115957ec87a7d54df1ac1adf019527c))

JJK_GOJO -> JJK_GOJO_DOMAIN en spec.md/design.md/tasks.md, con una linea aclarando que es el gesto
  de marco de manos de la Expansion de Dominio (Ryoiki Tenkai / "Unlimited Void"), no un generico
  "cualquier gesto de Gojo" (tiene varios otros igual de icononicos).

- Promueve la evaluacion de percepcion a fases reales con tareas
  ([`6a1df23`](https://github.com/josepanz/jarvis-gesture-hud/commit/6a1df23dc7b9dc815ac49a1c48e6ff995927600a))

Los 3 items recomendados del Apendice A pasan de evaluacion a fases/tareas concretas, la mejora
  neuronal de iluminacion queda afuera (no recomendada):

- 3D pinch-family distance (usa el z que ya se calcula, hoy sin usar) -> TASK-055c, dentro de la
  Fase 1 (mismo archivo/area que el fix de pinch) - CLAHE para iluminacion (cv2.createCLAHE, ya
  disponible) -> TASK-056b, tambien dentro de la Fase 1 - MediaPipe Pose para filtrar manos por
  pertenencia anatomica real -> Fase 3B nueva (TASK-060b modulo de pose, TASK-060c filtro + medicion
  de performance obligatoria antes de habilitarla por defecto)

La fase de Pose se llama "3B" a proposito, no "4" - insertarla sin renumerar las fases 4-9 y todas
  sus referencias cruzadas en los 4 archivos. Mismo criterio de minimo diff que ya se uso con
  TASK-055b.

proposal.md/design.md Apendice A actualizados para reflejar que ya estan programadas, no pendientes
  de decision.

- Spec para gestos Naruto, iconos de referencia, config UI y descarga de voz
  ([`135f06a`](https://github.com/josepanz/jarvis-gesture-hud/commit/135f06aee36efe835a77fb3f2f828f990902012f))

Nueva change de OpenSpec (openspec/changes/personalization-and-config-ui/) con
  proposal/spec/design/tasks para las 4 features pedidas, ordenadas de menor a mayor
  complejidad/esfuerzo/dependencias:

A. Iconos de referencia livianos por gesto (Pillow, generados, sin GIFs por ahora - documentado como
  diferido) B. Gestos de sellos de mano estilo Naruto (5 poses de una mano, sin deps nuevas,
  reutiliza Profile.gesture_bindings ya construido y dormido) C. Pantalla de configuracion (icono de
  engranaje) con tooltips, rebind de gestos/voz/sellos a acciones, atajos de teclado custom y macros
  (M1/M2/M3 documentado como limitado a lo que el software del teclado reenvie como tecla estandar),
  persistencia en disco - sin dependencias nuevas D. Icono de descarga del modelo de voz STT+LLM
  dentro de la pantalla de configuracion, con tooltip de peso y accion, dependiente de C

Reutiliza el protocolo de apply.md de multimodal-interaction-core en vez de duplicarlo. Continua la
  numeracion de tasks desde TASK-054 (TASK-055 a TASK-069). Sin cambios de codigo - solo
  especificacion, lista para que un agente la aplique tarea por tarea.


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
