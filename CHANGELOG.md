# CHANGELOG


## v0.5.0 (2026-09-07)

### Bug Fixes

- Aislar fallos de macro/atajo para que no tumben el loop de camara
  ([`b0ee9e4`](https://github.com/josepanz/jarvis-gesture-hud/commit/b0ee9e410d398d4b82cde5b767fd9ce7b82b21b1))

Causa raiz: build_macro_steps() corria como argumento de CommandBus.dispatch() dentro de
  _dispatch_macro_or_shortcut(), evaluado ANTES de entrar al bus - el ValueError por un "kind"
  desconocido nunca pasaba por el try/except del bus y subia sin frenos hasta el for-event-in-events
  de run(), matando la camara entera.

- _dispatch_macro_or_shortcut() construye los pasos dentro de un try/except y avisa por
  FeedbackManager en vez de propagar. - run() ahora atrapa y loguea por evento individual (defensa
  en profundidad): un gesto que falla no tumba los demas ni la camara. - ProfileManager.from_dict()
  descarta (con log) cualquier macro persistida cuyos pasos no tengan forma ejecutable, reusando
  build_macro_steps() como validador en vez de duplicar el vocabulario de kinds - un binding roto en
  disco es preferible a un arranque roto.

8 tests nuevos (602 en total). Documentado en ARCHITECTURE.md.

- Cerrar el stream de microfono al salir de la app
  ([`3f2d32d`](https://github.com/josepanz/jarvis-gesture-hud/commit/3f2d32d7c9e6b297ad5e237ebae32d5a6b6a6a7c))

- Controles del panel de leyenda inclickeables por z-order
  ([`57084b5`](https://github.com/josepanz/jarvis-gesture-hud/commit/57084b5bce951ce11a48ab3c5bb8bbf4ee26d4ee))

Verificado en camara real (Jose, 2026-09-07): las flechas quedaban debajo del panel y no se podian
  clickear. 2 ventanas Tk con "-topmost" no tienen un orden entre si garantizado - lift() no
  alcanzaba.

Reemplazado por geometria que nunca se superpone: se reserva una franja para los controles (mismo
  lado del panel) y el panel se corre para dejarle lugar, en vez de superponerlos y confiar en el
  z-order. Confirmado en vivo tras el fix: las 3 flechas (paginar/colapsar) funcionan.

- Correcciones de uso real en camara (voz, Shaka, scroll, Sukuna, puntero)
  ([`2ef30b4`](https://github.com/josepanz/jarvis-gesture-hud/commit/2ef30b4fa89226618244fe35b5b0f1172f5ffc20))

Hallazgos reportados por José probando la app de verdad (2026-08-30), guardados en memoria y ahora
  corregidos:

1. Voz "no respondia": LLMIntentResolver.resolve() descargaba (~1GB, primer uso) y cargaba su modelo
  GGUF de forma SINCRONICA desde el hilo principal de camara - congelaba TODA la app sin feedback.
  Confirmado el root cause antes de arreglar: el modelo nunca se descargo, la URL respondia bien
  (200, ~1.1GB). Se mueve a un hilo de fondo (mismo patron que VoiceListener._transcribe), con
  bubble de espera y guard anti-solapamiento.

2. Pinch de click confundido con Shaka (LOCK_SESSION falso): ninguna de las 5 condiciones de
  _is_shaka chequeaba distancia pulgar-indice. Se agrega SHAKA_MIN_THUMB_INDEX_GAP, con test de
  regresion que reproduce exactamente la colision real.

3. Scroll rediseñado: la forma se mantiene igual (pedido explicito), pero la direccion ahora sale de
  la posicion respecto a una base fijada al entrar al gesto (como un joystick), no de un delta
  cuadro-a-cuadro - elimina la inversion de signo por temblor. Se agrega scroll horizontal
  (SCROLL_LEFT/RIGHT, HScrollCommand) con el mismo criterio.

4. Chasquido de Sukuna lento: JJK_SUKUNA_MAX_WINDOW_SECONDS de 0.35 a 0.6s - un snap deliberado
  frente a webcam probablemente tarda mas de 350ms.

5. Puntero impreciso: EMA_ALPHA de 0.35 a 0.25 (mas suavizado) - unico cambio de esta lista NO
  verificado con datos reales, marcado como tal.

Bug de aislamiento de tests encontrado de paso: _AppTestCase en test_naruto_seal_dispatch.py
  leia/escribia el bindings.json REAL del usuario (Jose reasigno JJK_GOJO_DOMAIN->REDO probando el
  settings screen, lo que rompio un test) - aislado a un path temporal.

Pendiente, NO resuelto en este commit (necesita diagnostico en camara real con José, misma
  disciplina que Fase 4): "ningun sello Naruto se reconoce bien" y la colision general restante con
  Shaka/Screenshot.

594 tests en verde (+17 sobre Fase 8), ambos scripts de integracion manual actualizados y en verde.

- Descarga atomica y verificada de los modelos para no reusar parciales
  ([`75c12f3`](https://github.com/josepanz/jarvis-gesture-hud/commit/75c12f384d751f9116bb224dab9cfe59287a9880))

Causa raiz: hand_tracker.py/pose_tracker.py/llm_intent.py tenian cada uno su propio _ensure_model():
  si el archivo final no existia, descargaban directo a ese nombre. Una descarga cortada (wifi,
  cierre de la app, disco lleno) dejaba un parcial CON el nombre final, que el arranque siguiente
  asumia completo y pasaba tal cual a un parser nativo (MediaPipe/llama.cpp) - fallo opaco o crash
  nativo, sin mas salida que borrar el archivo a mano.

jarvis.downloads.download_atomically() centraliza el fix para los tres llamadores (evita triplicar
  la logica, mismo motivo por el que ya existe paths.py): descarga a <destino>.part, verifica el
  tamaño contra Content-Length cuando el servidor lo informa, os.replace() al nombre final solo si
  coincide, y borra el .part ante cualquier fallo. Sin hash conocido y estable de estos artefactos
  (URLs "latest"/HuggingFace sin checksum fijo) la verificacion es solo de tamaño - documentado en
  el modulo, no es defensa contra un atacante en este proyecto offline.

5 tests nuevos con HTTP mockeado (614 en total). Documentado en ARCHITECTURE.md.

- El anular ya no gana prioridad de pinch con un umbral que no puede disparar
  ([`b260d07`](https://github.com/josepanz/jarvis-gesture-hud/commit/b260d079f20c415dd80a5ea870863a33e4165f2d))

- El legend invadia la franja de sus controles por clamping de Y en macOS
  ([`9e14aaf`](https://github.com/josepanz/jarvis-gesture-hud/commit/9e14aaf7a222474817b354f75da9a01ed70bac9f))

Con el crash de CI resuelto (commit anterior), la suite corria completa pero
  test_controls_never_overlap_the_panel seguia fallando en CI real (no localmente con Tk 9 de
  Homebrew - otra diferencia de version de Tcl/Tk que casi esconde el problema; reproducido con
  _tkinter recompilado contra 8.6.18, la misma rama que usa actions/setup-python).

El punto 3 de WORKPLAN 12.1 atribuia esto a timing/mapeo de winfo_width()/height(). Es otra cosa,
  100% deterministica: macOS clampea la posicion Y de una ventana overrideredirect para que nunca
  quede debajo de la barra de menu, sin importar lo que pida geometry() - confirmado con repro
  minimo sin nada de jarvis (pedir geometry("+16+16") puede terminar en winfo_y()==25, no 16).
  _position_legend() calculaba la franja reservada para los controles asumiendo que quedaban
  exactamente en LEGEND_MARGIN (16px); el panel invadia los ~9px que el SO le robaba a los
  controles.

No es solo un artefacto de test - es el mismo tipo de bug de posicionamiento que origino H-28
  (controles inclickeables por solaparse con el panel). Fix en _position_legend(): en vez de
  recalcular una posicion asumida, lee la posicion YA RESUELTA de la ventana de controles
  (winfo_y()/winfo_height(), post-clamping) y ancla el panel a partir de ahi - funciona sea cual sea
  el offset que el SO haya aplicado, sin duplicar esa logica de clamping.

Verificado en Mac real: 763 tests, 3 corridas seguidas, OK (skipped=9) - cero failures, cero
  crashes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- El rebinding ya no puede evadir el hold de las acciones HOLD_REQUIRED
  ([`a22c212`](https://github.com/josepanz/jarvis-gesture-hud/commit/a22c212ac2c9a975e78da14e5b57ad0f9493ecff))

- Generacion de iconos atomica y tolerante a fallos de escritura
  ([`a5a2dcc`](https://github.com/josepanz/jarvis-gesture-hud/commit/a5a2dcc0b227d53dba69d077dff3905da7d0ef1a))

H-14: ensure_icon() no manejaba errores de mkdir()/save() - un fallo de escritura (permisos, disco
  lleno) crasheaba el arranque entero por una leyenda puramente visual. Ahora un OSError se loguea y
  devuelve None; los consumidores (overlay.init_legend, settings_ui._refresh_bindings_table)
  degradan mostrando la fila sin icono en vez de propagar.

H-15: la escritura no era atomica (exists() y despues save() directo al destino), asi que un save()
  interrumpido dejaba un PNG parcial cacheado para siempre con el nombre final. Ahora escribe a un
  .tmp y hace os.replace(), mismo patron que config_store.py/downloads.py.

H-16: evaluado y descartado - opcional segun la propia auditoria, y H-13 ya resuelve la perdida de
  cache entre arranques del .exe; pre-empaquetar los iconos solo ahorraria el primer arranque
  (sub-segundo, ~30 glifos). H-17: generate_all_icons() se mantiene, documentada como utilitaria de
  test (uso real en tests/test_gesture_icons.py), no del codigo de runtime.

- Geometria del panel de leyenda usaba tamaño no confiable entre plataformas
  ([`0a8a829`](https://github.com/josepanz/jarvis-gesture-hud/commit/0a8a8292c1338dfa6f59c2f086b6acfb54daa1bf))

Detectado en CI (macOS): test_controls_never_overlap_the_panel fallaba ahi (Windows no mostro el
  problema). winfo_width()/winfo_height() reflejan el tamaño YA MAPEADO en pantalla - en macOS
  pueden seguir siendo 1x1 en el momento en que _position_legend()/_update_legend_controls() los
  leen, si la ventana todavia no termino de mapearse via el window manager. Cambiado a
  winfo_reqwidth()/reqheight() (tamaño pedido al geometry manager, disponible de inmediato tras
  update_idletasks() sin depender del mapeo) + un piso de seguridad de 20px para la franja reservada
  de los controles.

- Invalidar la pila de redo al ejecutar un comando nuevo
  ([`7263e03`](https://github.com/josepanz/jarvis-gesture-hud/commit/7263e0318c1eda4668f689d35afb571b8420aa00))

- La limpieza del drag ya no depende del binding de PINCH_UP
  ([`dc45474`](https://github.com/josepanz/jarvis-gesture-hud/commit/dc45474449e43554d7006df448ea3ae74b16eebf))

- Mensaje accionable si falla la carga del modelo al arrancar
  ([`0200623`](https://github.com/josepanz/jarvis-gesture-hud/commit/02006230c94768b90a196d0d10b71efe1d769db1))

Si construir HandTracker/PoseTracker falla (tipicamente red, ver H-03), la excepcion salia cruda de
  JarvisApp.__init__ como traceback sin procesar. Ahora se atrapa, se loguea un mensaje accionable
  (jarvis.main) que nombra donde va el modelo (paths.assets_dir()), y se sale con SystemExit(1) -
  codigo limpio en vez de traceback. El overlay todavia no existe en ese punto de __init__, asi que
  la consola/logging es el unico canal disponible aca.

2 tests nuevos (616 en total). Documentado en ARCHITECTURE.md.

- Mitigar colision Sukuna/RIGHT_CLICK y pausa cerca de bordes de pantalla
  ([`b39f009`](https://github.com/josepanz/jarvis-gesture-hud/commit/b39f009a75decde71b14042dc96d84815468b34f))

H-26/V-05 (verificado en camara real, Jose, 2026-09-07: "se confunde con click derecho y no hace
  enseguida"). Causa real: PINCH_RIGHT_CLICK (20px) es mas laxo que JJK_SUKUNA_CONTACT_THRESHOLD
  (15px), asi que un snap real confirma el click derecho (PINCH_CONFIRM_FRAMES=2, ~100ms) antes de
  tener chance de completarse. El pinch "middle" ahora confirma tras RIGHT_CLICK_CONFIRM_FRAMES (6)
  en vez del comun - un snap real sigue cerrando mas alla de la banda 15-20px y nunca llega a
  sostenerse ahi lo suficiente; un click derecho deliberado si.

H-27 (mismo hallazgo: "cerca de Inicio se confunde con el gesto de 2 punos"). both_fists no exigia
  ninguna cercania real entre las 2 manos (solo el gate laxo de "misma persona", 0.55 de la
  diagonal) - una mano activa estirada hacia un borde mas una en reposo en cualquier otra parte
  bastaba. Ahora exige PAUSE_MAX_DISTANCE_FRACTION (0.35), mismo principio que el marco de Gojo.

Ambos mitigan, no eliminan del todo, la ambiguedad geometrica de fondo - documentado en los
  comentarios de config.py junto a cada umbral nuevo.

- Mockear cv2.imshow/waitKey en _AppTestCase - causa real del crash de CI en macOS
  ([`a0ae0ff`](https://github.com/josepanz/jarvis-gesture-hud/commit/a0ae0ff6275098be3c71010f9a9c0e20ff4b3a7e))

Confirmado en Mac real (Intel, macOS 12.7.6, _tkinter recompilado contra Tcl/Tk 8.6.18 para replicar
  fielmente la version que usa actions/setup-python en macos-latest, no la 9.x de Homebrew): la
  hipotesis original de un conflicto por IMPORT de OpenCV/mediapipe vs Tkinter (documentada como sin
  verificar en WORKPLAN 12.1) queda descartada - importar cv2/mediapipe/jarvis.main completo, en
  cualquier orden relativo a tkinter, nunca crashea por si solo.

La causa real es mucho mas puntual: JarvisApp.run() llama a cv2.imshow()/ cv2.waitKey() de verdad en
  cada frame - nunca estuvieron mockeados en _AppTestCase (a diferencia de cv2.VideoCapture). En
  macOS, cv2.imshow() crea una ventana Cocoa real via el backend highgui de OpenCV, que reclama el
  NSApplication del proceso para si mismo; el primer tk.Tk() que el proceso crea despues hereda ese
  estado y crashea en su primer update() (segfault o NSInvalidArgumentException en '-[NSApplication
  macOSVersion]', exit 139/134 segun el punto exacto). Cualquier test que herede de _AppTestCase y
  llame a self.app.run() deja el proceso en ese estado antes de que test_overlay.py/
  test_settings_ui.py toquen Tk por primera vez - por eso ningun repro basado solo en imports lo
  disparaba.

Repro minimo confirmado, sin nada de jarvis ni unittest de por medio: cv2.imshow("x", frame);
  cv2.waitKey(1) tk.Tk().update() # <- crashea aca

Verificado en Mac real: 763 tests, 3 corridas seguidas, cero crashes. Sin cambios en
  .github/workflows/ci.yml ni en src/jarvis/ - era un hueco en el mockeo de hardware de los tests,
  no un problema de invocacion de CI.

Nota aparte, no tocada: test_controls_never_overlap_the_panel sigue siendo flaky en este hardware -
  issue ya documentado (punto 3 de WORKPLAN 12.1), distinto y pre-existente.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Mockear HandSignModel en _AppTestCase - segfault en CI (macOS)
  ([`a372098`](https://github.com/josepanz/jarvis-gesture-hud/commit/a372098f9455b2a428627f12c6dfa1c0e14ecb32))

Cada JarvisApp() construido por _AppTestCase.setUp() (usada por decenas de tests en varios archivos)
  cargaba un onnxruntime.InferenceSession REAL via HandSignTracker -> HandSignModel, sin el mismo
  mockeo que ya tenia HandTracker.__init__ en la linea de arriba - un descuido de cuando Y-02/
  hand-sign-fidelity cableo el tracker en main.py.

Confirmado en CI: crear muchas sesiones ONNX reales seguidas en el mismo proceso terminaba en
  Segmentation fault (exit code 139) a mitad de la suite en macOS - un crash nativo, no un fallo de
  assert. Windows no lo mostro (corrio, solo mas lento de lo necesario). Se agrega
  HandSignModel.__init__ a la lista de mocks ya establecida.

- Mockear ScreenOverlay/SettingsWindow en _AppTestCase - segfault persistia en macOS
  ([`6a815f6`](https://github.com/josepanz/jarvis-gesture-hud/commit/6a815f6b5d74d62899d1319b8c3c71a0f78efafd))

El mock de HandSignModel (commit anterior) no alcanzo: el segfault en CI (macOS) seguia ocurriendo,
  solo que un test mas tarde. Cada JarvisApp() de esta familia de tests construye un ScreenOverlay()
  (tk.Tk() real) + un SettingsWindow real sobre ese mismo root (main.py, TASK-078/081) - ninguno
  mockeado hasta ahora, a diferencia de HandTracker/HandSignModel/cv2/etc. Ningun test de esta
  familia verifica comportamiento real de Tk (solo dispatch de comandos), asi que mockear ambas
  clases enteras es seguro y elimina la creacion/destruccion de tantos roots de Tk reales en un
  mismo proceso - la causa mas probable del crash nativo en el Tcl/Tk de macOS.

- Naruto_u y naruto_ne generaban el icono byte-por-byte identico
  ([`2d61f9e`](https://github.com/josepanz/jarvis-gesture-hud/commit/2d61f9e7a5790d6a4d3f588b651b1e5f7f37d1f3))

Detectado por test_every_icon_is_structurally_distinct_from_every_other en CI (no localmente -
  assets/gesture_icons/ esta gitignoreado, y este repo tenia cacheados naruto_u.png/naruto_ne.png de
  una version anterior de sus specs, de antes de que 9723849 los dejara idénticos; CI arranca sin
  ese cache y lo detecto en el primer run limpio).

naruto_u pasa a glyph "arrow_right" (NARUTO_U -> REDO, adelante/rehacer), mismo criterio que Saru/I
  (glyph = tema de la accion default).

- Pinear onnxruntime en requirements.txt
  ([`c79b321`](https://github.com/josepanz/jarvis-gesture-hud/commit/c79b321277d624cd03e8bd5ae5153dd070f1be0d))

Nunca se agrego cuando se creo hand_sign_model.py (Y-01) - un pip install limpio (CI) rompia la
  cadena de imports de jarvis.main hacia abajo con ModuleNotFoundError, aunque el venv de desarrollo
  local ya lo tenia instalado a mano y nunca lo noto. Pineado a la version instalada localmente
  (1.29.0), mismo criterio que el resto de requirements.txt.

- Precalentar Tk-Aqua antes del primer test real en macOS
  ([`5cbdb51`](https://github.com/josepanz/jarvis-gesture-hud/commit/5cbdb51811dc1aab12eda908f09c78dba9e91811))

Confirmado en CI (macOS, 3 corridas seguidas, siempre en el mismo punto): Segmentation fault ->
  NSException ('-[NSApplication macOSVersion]: unrecognized selector') exactamente en el primer
  tk.Tk() real que crea el proceso completo de tests. Antes de los commits anteriores de esta
  sesion, _AppTestCase creaba muchas ventanas Tk reales ANTES de llegar a este archivo
  (alfabeticamente mas tarde) - eso, sin buscarlo, ya absorbia esta inicializacion. Al sacar esas
  ventanas reales de _AppTestCase (fix del segfault por sesiones ONNX/Tk repetidas), este archivo
  paso a ser el primero en tocar Tk de verdad en toda la corrida.

setUpModule() crea y destruye un root descartable antes de cualquier test real de este archivo -
  mismo mecanismo, pero aislado y con proposito explicito en vez de un efecto colateral de otra
  cosa.

- Resetear el estado de gestos de una mano cuando la mano sale de cuadro
  ([`84dd94b`](https://github.com/josepanz/jarvis-gesture-hud/commit/84dd94b03c671efea62992c4b668fb87f28407b5))

- Revertir EMA_ALPHA a 0.35 y sumar diagnostico de dwell/doble-click/swipe
  ([`3e0ff3c`](https://github.com/josepanz/jarvis-gesture-hud/commit/3e0ff3c93e710b8d14a8dee803838555d5b50d37))

V-04 (hardening-and-polish, verificado en camara real): bajar EMA_ALPHA a 0.25 no arreglo el reporte
  de "puntero impreciso" y sumo latencia perceptible ("tarda en moverse, no se siente natural").
  Revertido a 0.35, el valor previo al cambio del 2026-08-30.

DWELL_CLICK_ENABLED vuelve a su default real (False) tras la prueba en vivo de V-08 - se habia
  forzado a True temporalmente solo para esa verificacion.

Se suma instrumentacion de diagnostico (last_distance/last_velocity/ last_duration_ms en
  SwipeDetector, last_interval_ms en DoubleClickDetector, mas las claves correspondientes en el HUD
  de debug) para leer numeros reales de camara en vez de estimarlos - usada para V-09 y V-10.

- Sellos Naruto de 1 mano corregidos con datos de camara real
  ([`fc74e2a`](https://github.com/josepanz/jarvis-gesture-hud/commit/fc74e2ad7ae4a01da78488182540f4ed1455cbd7))

Verificacion en camara real, sello por sello, con el usuario - de los 8 originales solo Hitsuji se
  acerco a andar bien; el resto necesito correccion real:

- _fingers_crossed reescrito: v1 solo comparaba el orden lateral de las puntas (falso positivo
  60-70% con dedos simplemente juntos, no cruzados). v2 usa interseccion real de segmentos
  (orientacion/producto cruzado). Arregla Tora e Hitsuji. - Uma y Saru REDEFINIDOS por 3ra vez: las
  versiones anteriores pedian aislar el anular (solo o con el medio), biomecanicamente dificil
  (tendones compartidos) - 0% de coincidencia en vivo. Redefinidos a formas que la mano real si pudo
  sostener: Uma = pulgar+indice+meñique extendidos (tipo "rock and roll"); Saru = puño con pulgar
  hacia arriba. - Inu simplificado: solo meñique extendido (el meñique si tiene control
  independiente razonable, a diferencia del anular). - I arreglado: el pulgar "hacia el costado" es
  un movimiento LATERAL, se media con un chequeo VERTICAL (nunca podia detectarlo). Nuevo
  _thumb_offset_from_palm() compara el eje que domina. - NARUTO_SEAL_MISS_TOLERANCE=3: un parpadeo
  de 1 frame a "ningun sello" (ruido de landmark, verificado en vivo) ya no reinicia el hold entero
  - mismo principio que PINCH_CONFIRM_FRAMES del otro lado del problema. - Bug lateral encontrado
  con el fix de I: el umbral original tambien clasificaba a fist_hand() (fixture generica de puño,
  usada en todo el archivo) como NARUTO_I por accidente - subido el umbral con margen. - Iconos y
  leyenda actualizados para las 3 redefiniciones.

496 tests en verde. Las formas corregidas no se re-verificaron en camara por segunda vez en esta
  sesion (a pedido explicito, para seguir con la fase siguiente) - queda pendiente un chequeo en
  vivo de confirmacion.

- Separar assets empaquetados de assets escribibles para el exe portable
  ([`40afcba`](https://github.com/josepanz/jarvis-gesture-hud/commit/40afcba5c53ab9f5b597e969e11fd44ca642eb3f))

H-13: sys._MEIPASS se extrae de nuevo y se borra en cada arranque de un onefile de PyInstaller, asi
  que escribir ahi (iconos generados, modelos descargados en runtime) perdia todo al cerrar la app.
  bundled_assets_dir() queda para lectura de assets empaquetados; writable_assets_dir() resuelve a
  ~/.jarvis-gesture-hud/assets cuando esta congelado, igual que config_store.py para bindings.json.
  Todos los llamadores (hand_tracker, pose_tracker, llm_intent, gesture_icons, log de arranque en
  main.py) escriben o descargan, asi que pasan a la version escribible.

- Sostener un sello ya no completa de paso el hold de pausa
  ([`5531ee9`](https://github.com/josepanz/jarvis-gesture-hud/commit/5531ee94eef63f7c380c31c46a33609def13691d))

Hallazgo de camara real con Jose (2026-09-06, WORKPLAN.md §6, Y-V3): armar Ne (y otros sellos que
  curvan bastante los dedos, ej. Ushi/Saru) satisface de paso _is_fist en las 2 manos - sin
  proteccion, sostenerlo el tiempo suficiente completaba tambien el hold de PAUSA (both_fists,
  PAUSE_HOLD_SECONDS) y disparaba TOGGLE_ACTIVE sin querer.

Mismo mecanismo que la trampa 2 de Y-04 (dwell/swipe): external_seal_in_progress (ya inyectado por
  main.py desde HandSignTracker.hold_seal) ahora tambien suspende el hold de both_fists en
  _process_two_hand_gestures().

- Test_windows_does_not_shell_out rompia en CI no-Windows
  ([`d57bfe5`](https://github.com/josepanz/jarvis-gesture-hud/commit/d57bfe5ae08e65dc409791cc1f85af82ee5fd2b5))

ctypes.windll no existe en absoluto fuera de Windows - patch(..., create=True) sobre el atributo
  ANIDADO user32.LockWorkStation no alcanza si el primer segmento de la ruta (windll) tampoco
  existe. Se patchea windll en si con un MagicMock (create=True), asi la rama de Windows sigue
  verificada en cualquier runner de CI en vez de romper en 2 de las 3 plataformas.

- Usar nombre de temporal unico en la escritura atomica de config_store
  ([`ea34a8f`](https://github.com/josepanz/jarvis-gesture-hud/commit/ea34a8f0e18c23d38c897077c417f495e6f9cec9))

- Validar tipos al cargar bindings persistidos para no romper el arranque
  ([`2ffcec1`](https://github.com/josepanz/jarvis-gesture-hud/commit/2ffcec1faae26ad99e009731d84d1d411069d509))

Causa raiz: config_store.load_bindings() ya pone en cuarentena JSON invalido y errores de I/O, pero
  JSON sintacticamente valido con tipos equivocados (p. ej. gesture_bindings guardado como lista en
  vez de dict) pasaba ese filtro y explotaba mas arriba, en los .update()/ .items() de
  ProfileManager.from_dict() - cuyo propio docstring promete "nunca lanza ante datos malformados",
  promesa que solo era cierta para claves faltantes, no para tipos incorrectos.

- profiles.py: _validated_dict_field() descarta (con log) cualquier campo persistido que no sea un
  dict, cayendo a los defaults de codigo - el perfil "default" sembrado conserva sus valores de
  sensitivity/cooldowns/dwell porque se mergea, nunca se reemplaza. - config_store.py:
  RecursionError y MemoryError se suman a las excepciones que disparan la cuarentena del archivo.

7 tests nuevos (609 en total). Documentado en ARCHITECTURE.md.

### Build System

- Pinear dependencias con techo compatible
  ([`b6d6d3b`](https://github.com/josepanz/jarvis-gesture-hud/commit/b6d6d3b1a7e8b22b939a5acade27e1e28651044e))

### Continuous Integration

- Cachear dependencias de pip
  ([`e9294f8`](https://github.com/josepanz/jarvis-gesture-hud/commit/e9294f8d8ab7661edb125031e421d83368a41dfd))

- Exigir la suite de tests en verde antes de publicar un release
  ([`e64a734`](https://github.com/josepanz/jarvis-gesture-hud/commit/e64a734d718ef46034501c215f29f5cfc8215b8e))

### Documentation

- Actualizar estado, conteo de tests y decisiones de la ronda de endurecimiento
  ([`b11baca`](https://github.com/josepanz/jarvis-gesture-hud/commit/b11baca0927682308ae9caa9f530fda89e9cbc1d))

- Agregar el prompt de ejecucion al WORKPLAN de hand-sign-fidelity
  ([`fd23531`](https://github.com/josepanz/jarvis-gesture-hud/commit/fd23531d5e06753d4c2595ae4d603922e664fec8))

- Agregar referencias visuales reales para los sellos/gestos de workflow 6
  ([`0a7a755`](https://github.com/josepanz/jarvis-gesture-hud/commit/0a7a7550efb93054f8f8a56c7e2105b3a7e4642c))

Fotos/GIFs reales de manos humanas (sin arte de anime, sin IA) para los 8 sellos Naruto de 1 mano,
  los 5 de 2 manos, los 3 gestos JJK y Clap/Korean Heart - ayuda visual para la sesion de
  verificacion en camara. Indice con fuente y nota de fidelidad por gesto en
  naruto_one_hand_seals.md y twohand_jjk_common_gestures.md. Varias tienen marca de agua de banco de
  imagenes (Getty/Shutterstock/Vecteezy) - referencia interna, no para redistribuir. naruto_tori.jpg
  muestra el sello CANONICO del anime (puntas de los dedos tocandose), que no es la forma que el
  codigo detecta hoy (manos separadas en abanico) - usar como referencia de que NO hacer, no de que
  hacer.

- Anotar en la tabla que el alias de H-24 se saco
  ([`139c0f9`](https://github.com/josepanz/jarvis-gesture-hud/commit/139c0f99e2e0ced6afea12462b62d2bdcd27ba22))

- Anotar H-08 como no aplicable (no se toco filter_plausible_hands)
  ([`98c4866`](https://github.com/josepanz/jarvis-gesture-hud/commit/98c4866484e4817a88d9a9d8ff8b4686bdf0fa3c))

- Anotar H-23 pendiente de agrupamiento en la tabla de seguimiento
  ([`67c8800`](https://github.com/josepanz/jarvis-gesture-hud/commit/67c8800a304d8f158b60a6e389ed527a0a2cb3c9))

- Auditoria de NARUTO-HandSignDetection y sellos canonicos reales
  ([`0f49957`](https://github.com/josepanz/jarvis-gesture-hud/commit/0f4995757b9c99b7b785e919799cb5d52f012c3f))

Hallazgo central: los 14 sellos canonicos se hacen con LAS DOS MANOS. Los 8 "sellos de una mano" que
  implementa gestures.py (Tora, Ushi, U, Uma, Hitsuji, Saru, Inu, I) son invencion de este proyecto,
  y NARUTO_TORI esta definido casi al reves (manos separadas en abanico vs. puntas de los dedos
  tocandose). De 13 sellos implementados, 2 son correctos (Ne, Mi). Eso explica de forma directa el
  reporte "ningun sello se reconoce bien": no hay umbral que arregle una forma que nadie hace.

Evidencia medida en esta maquina, no estimada: - su yolox_nano.onnx reconoce sus propias fotos con
  0.82-0.91 - de nuestras 8 formas de una mano, solo 2 dan deteccion (0.91 / 0.47 debil) -
  inferencia 8.1ms promedio / 8.6ms p95 en CPU, modelo de 3.6MB - onnxruntime YA esta instalado en
  el venv (llega con mediapipe)

Se agregan las 14 imagenes canonicas del README de ese repo (MIT) en
  docs/gesture-reference/canonical/ y un README que separa "sello real" de "lo que nuestro codigo
  detecta hoy", para no volver a confundirlos.

Impacto: V-01/V-02 del workflow 6 quedan sin sentido tal como estan escritos.

- Cerrar V-04/V-05/V-08/V-09/V-10 con datos de camara real
  ([`dc52540`](https://github.com/josepanz/jarvis-gesture-hud/commit/dc5254025a54efedca514b8dc6746e4e18faa63c))

Verificacion en vivo (Jose, 2026-09-07): EMA_ALPHA revertido y confirmado, colision
  Sukuna/RIGHT_CLICK confirmada (ya conocida), dwell/doble-click/ swipe con numeros reales via HUD
  de debug. Se documentan 3 hallazgos nuevos sin asignar (H-26/H-27/H-28): latencia extra en Sukuna,
  colision del gesto de pausa cerca de los bordes de pantalla, y el panel de legend sin minimizar ni
  scroll.

- Corregir la medicion citada en el umbral de release de Sukuna
  ([`0728113`](https://github.com/josepanz/jarvis-gesture-hud/commit/07281136739da8a96a57e381006d5e81d49947f9))

- Documentar el crash de CI en macOS sin resolver
  ([`900935a`](https://github.com/josepanz/jarvis-gesture-hud/commit/900935a1691c3b21e151ca452f4a098b2c706833))

Segmentation fault / NSException determinista en la primera vez que el proceso de tests crea un
  tk.Tk() real (siempre el mismo punto, 3 corridas seguidas). 5 causas reales encontradas y
  arregladas en el camino (c79b321, 2d61f9e, 0a8a829, d57bfe5, a372098, 6a815f6), ninguna resolvio
  ESTE crash especifico. Hipotesis sin verificar: conflicto OpenCV/Tkinter por NSApplication en
  macOS-latest de GitHub Actions - necesita separar la invocacion de tests de Tk real a un proceso
  aparte en ci.yml. Pendiente de Jose probando en un Mac real.

- Leyenda e iconos de sellos segun las formas reales de dos manos
  ([`9723849`](https://github.com/josepanz/jarvis-gesture-hud/commit/97238498f9daf8c1b3aad829a84234ced9b80cd7))

Reescribe las 12 descripciones de sello en legend.ENTRIES para describir la forma real de 2 manos
  (sacada de las fotos en docs/gesture-reference/canonical/), no la forma de 1 mano inventada de
  antes (Y-04). Los ICON_SPECS de esos 12 pasan de hands=1 a hands=2 (duplicando el mismo set de
  dedos en ambas manos - el modelo de icono no representa manos entrelazadas, quedan parecidos entre
  si y se distinguen por el glyph, mismo criterio ya aceptado para naruto_ne/naruto_mi). NARUTO_KAI
  ya no tiene fila de leyenda ni icono (Y-04). Snapshot de test_legend.py regenerado - el padding no
  cambio (la fila mas larga sigue siendo la de swipe). Puntero a docs/gesture-reference/canonical/
  agregado al docstring de legend.py.

- Marcar A-01 completada en la tabla de seguimiento
  ([`3a83687`](https://github.com/josepanz/jarvis-gesture-hud/commit/3a83687a33f046de98d6e221be08f25889e46304))

- Marcar A-02 completada en la tabla de seguimiento
  ([`7327c72`](https://github.com/josepanz/jarvis-gesture-hud/commit/7327c72b3fe86fbc9223a7da6d15ebcc445fda02))

- Marcar A-03 completada en la tabla de seguimiento
  ([`5b4ec10`](https://github.com/josepanz/jarvis-gesture-hud/commit/5b4ec106c8dbc8bccdf64742c9df9467b8967a06))

- Marcar A-03b completada en la tabla de seguimiento
  ([`da6124e`](https://github.com/josepanz/jarvis-gesture-hud/commit/da6124ef32082460ce54bb648306b700b08a8b4b))

- Marcar B-01 completada en la tabla de seguimiento
  ([`d326ceb`](https://github.com/josepanz/jarvis-gesture-hud/commit/d326ceb09b73153d5f54d0de381e41a5cb118251))

- Marcar C-01 completada en la tabla de seguimiento
  ([`58edbd5`](https://github.com/josepanz/jarvis-gesture-hud/commit/58edbd5aa37ddefdfd6c9e3c04c3e9a0f55a81eb))

- Marcar C-02 completada en la tabla de seguimiento
  ([`25e46b6`](https://github.com/josepanz/jarvis-gesture-hud/commit/25e46b63a56894980b76d9a6fcbbb36743f1644d))

- Marcar C-03 completada en la tabla de seguimiento
  ([`e49c241`](https://github.com/josepanz/jarvis-gesture-hud/commit/e49c241f63c7352eeaa5efc455d3d631e66a9706))

- Marcar H-01 completada en la tabla de seguimiento
  ([`c15705e`](https://github.com/josepanz/jarvis-gesture-hud/commit/c15705e7ed879215e975f23af8a066466b5876f7))

- Marcar H-02 completada en la tabla de seguimiento
  ([`41e1097`](https://github.com/josepanz/jarvis-gesture-hud/commit/41e10974b42efa5dcd61aa25eacb40a6081bc642))

- Marcar H-03 completada en la tabla de seguimiento
  ([`9517862`](https://github.com/josepanz/jarvis-gesture-hud/commit/9517862d24fa8f0e1f75c759cd9e2dc6bc925449))

- Marcar H-04 completada en la tabla de seguimiento
  ([`d44e57d`](https://github.com/josepanz/jarvis-gesture-hud/commit/d44e57d05d1f9333cf05852ca1942665ac306d50))

- Marcar H-05 completada en la tabla de seguimiento
  ([`2ba46f7`](https://github.com/josepanz/jarvis-gesture-hud/commit/2ba46f7f44308f41aae151d51c02bcdbb808944b))

- Marcar H-06 completada en la tabla de seguimiento
  ([`320d7ef`](https://github.com/josepanz/jarvis-gesture-hud/commit/320d7ef77c73ae922b028eff2945821b6b10c98f))

- Marcar H-07 completada en la tabla de seguimiento
  ([`a98bc2d`](https://github.com/josepanz/jarvis-gesture-hud/commit/a98bc2d2d77587b663b30dfb02d72d76bb68fb41))

- Marcar H-08 completada en la tabla de seguimiento
  ([`352812c`](https://github.com/josepanz/jarvis-gesture-hud/commit/352812c1ecc2d7a94fd1d17a0ae3f9fc996173c1))

- Marcar H-09 completada en la tabla de seguimiento
  ([`b08e728`](https://github.com/josepanz/jarvis-gesture-hud/commit/b08e72803d770e12abd0e5b1b6b7ad29c09c6b22))

- Marcar H-10 completada en la tabla de seguimiento
  ([`174fe3c`](https://github.com/josepanz/jarvis-gesture-hud/commit/174fe3c3adb6c6b5f51fffe7d5e0b8eb571fea9b))

- Marcar H-11 completada en la tabla de seguimiento
  ([`f8894cf`](https://github.com/josepanz/jarvis-gesture-hud/commit/f8894cf67bd0329ef09cecd7a5b776881951faed))

- Marcar H-12 completada en la tabla de seguimiento
  ([`78010c8`](https://github.com/josepanz/jarvis-gesture-hud/commit/78010c8ca1dc586c68060baaffb6c05721875f27))

- Marcar H-13 completada en la tabla de seguimiento
  ([`be153ea`](https://github.com/josepanz/jarvis-gesture-hud/commit/be153ea1c469781a04f99098c3000baa013fc3be))

- Marcar H-14/15/16/17 completada en la tabla de seguimiento
  ([`f74a5a9`](https://github.com/josepanz/jarvis-gesture-hud/commit/f74a5a9bbb22efcfca79c45444d77e321ad4b7e1))

- Marcar H-18 completada en la tabla de seguimiento
  ([`0b6cf4a`](https://github.com/josepanz/jarvis-gesture-hud/commit/0b6cf4ad15ac9e6c1a20464cd5f347f0577618fd))

- Marcar H-19 completada en la tabla de seguimiento
  ([`5a64bee`](https://github.com/josepanz/jarvis-gesture-hud/commit/5a64bee2bdd18646615c104fc8ca4c51926d01a5))

- Marcar H-20 completada en la tabla de seguimiento
  ([`bb4c878`](https://github.com/josepanz/jarvis-gesture-hud/commit/bb4c8781c7e31ecb5a4890d30deb30555d2dcf23))

- Marcar H-21 completada en la tabla de seguimiento
  ([`8e9c3ab`](https://github.com/josepanz/jarvis-gesture-hud/commit/8e9c3abd90a9698e3731df5618fb00961385c30e))

- Marcar H-22 completada en la tabla de seguimiento
  ([`8181bea`](https://github.com/josepanz/jarvis-gesture-hud/commit/8181bea8ec381b00b9ce79745bb83d2848f43874))

- Marcar H-23 completada en la tabla de seguimiento
  ([`54b39d0`](https://github.com/josepanz/jarvis-gesture-hud/commit/54b39d074536d3b7a841a8b97628d9c237ff3b66))

- Marcar H-24 completada en la tabla de seguimiento
  ([`1473a87`](https://github.com/josepanz/jarvis-gesture-hud/commit/1473a87086076bea5ac6861bf21c7661162f08a3))

- Marcar H-25 completada en la tabla de seguimiento
  ([`5c4906c`](https://github.com/josepanz/jarvis-gesture-hud/commit/5c4906cd5d99592efa1b1d800bd5a288ef940fd8))

- Marcar H-26/H-27/H-28 como resueltos
  ([`b231c40`](https://github.com/josepanz/jarvis-gesture-hud/commit/b231c4025b84be78115e1dd0c986743364cb9e86))

Commits b39f009 (H-26/H-27) y a1529b1 (H-28).

- Marcar Y-01 completada en WORKPLAN de hand-sign-fidelity
  ([`c371a20`](https://github.com/josepanz/jarvis-gesture-hud/commit/c371a2037e43202cdafa89fd654b4433e4b9b01d))

- Marcar Y-02 completada en WORKPLAN de hand-sign-fidelity
  ([`4c91fa9`](https://github.com/josepanz/jarvis-gesture-hud/commit/4c91fa921013687d05f3ec6c1ee2e60db4c918ae))

- Marcar Y-03 completada en WORKPLAN de hand-sign-fidelity
  ([`54ba3b4`](https://github.com/josepanz/jarvis-gesture-hud/commit/54ba3b42f656354d05c62969bd521b4eea2ddae9))

- Marcar Y-04 completada en WORKPLAN de hand-sign-fidelity
  ([`f024540`](https://github.com/josepanz/jarvis-gesture-hud/commit/f024540b6bea3596c4172200ba53f6d56170871c))

- Marcar Y-05 completada en WORKPLAN de hand-sign-fidelity
  ([`a34cc20`](https://github.com/josepanz/jarvis-gesture-hud/commit/a34cc200a83c0e27cfe933b90b685fecf7137f33))

- Marcar Y-06 completada en WORKPLAN de hand-sign-fidelity
  ([`7991c3e`](https://github.com/josepanz/jarvis-gesture-hud/commit/7991c3e6b515ca124b7aa19cf083e9b43bcbb07e))

- Marcar Y-07 completada, WORKPLAN de hand-sign-fidelity cerrado
  ([`cdab15c`](https://github.com/josepanz/jarvis-gesture-hud/commit/cdab15cfdbafc73e72067696aeb03599dd18c878))

Los 4 workflows + Y-08 (hallazgo no planeado del Workflow 4) estan completos. README.md actualizado
  (724 -> 749 tests).

- Plan de ejecucion para detectar los sellos reales con el modelo
  ([`efacc83`](https://github.com/josepanz/jarvis-gesture-hud/commit/efacc83f99bda342b606c7ba8d2080a4595f12c5))

Decision de Jose: cablear el modelo YOLOX-Nano (MIT, Kazuhito00) y borrar los sellos de una mano
  inventados. WORKPLAN autocontenido, 7 tareas en 3 workflows mas la verificacion en camara, con
  criterios de aceptacion medidos:

- 14/14 imagenes canonicas se auto-clasifican con score 0.82-0.93 - 8.1ms/frame promedio en CPU,
  modelo de 3.6MB, onnxruntime ya instalado - el frame va SIN espejar: Mi(Snake) cae de 0.82 a 0.70
  espejado - NARUTO_KAI es el unico huerfano (no esta entre los 14 canonicos) - trampas del borrado:
  _fingers_crossed la usa _is_jjk_megumi, y _naruto_hold_seal lo leen los gates de dwell (C-01) y
  swipe (C-03)

V-01 y V-02 del workflow 6 de hardening-and-polish quedan marcados como superados: median la
  fidelidad de formas que no existen.

- Plan de endurecimiento y pulido con auditoria completa del proyecto
  ([`cd1f99b`](https://github.com/josepanz/jarvis-gesture-hud/commit/cd1f99b11399798b40a84b83a86ddd20381d7fa2))

Auditoria de todo el proyecto y plan de trabajo ejecutable en un solo archivo autocontenido
  (openspec/changes/hardening-and-polish/WORKPLAN.md).

Hallazgos: 25 de codigo (3 criticos, 5 altos, 6 medios) + 7 verificaciones

que necesitan camara real. Los 3 criticos, verificados leyendo el codigo:

- Reasignar la fila PINCH_UP en el settings deja el boton del mouse apretado a nivel de SO:
  _dispatch_migrated compara el nombre de accion ya resuelto, no el evento fisico, asi que el gesto
  de soltar el pinch nunca entra a la rama que libera el drag. - Una macro malformada en
  bindings.json mata el loop de camara: build_macro_steps() se evalua como argumento de
  command_bus.dispatch(), o sea fuera de la red de try/except del bus, y run() no protege el for de
  eventos. - Un bindings.json con tipos equivocados impide arrancar la app:
  ProfileManager.from_dict() promete no lanzar ante datos malformados, cierto para claves faltantes
  y falso para tipos incorrectos.

Ademas: en un .exe onefile assets_dir() resuelve a sys._MEIPASS, que PyInstaller re-extrae en cada
  arranque, asi que los iconos se regeneran siempre y cualquier descarga en runtime se pierde al
  cerrar.

Contenido del plan: 8 workflows ordenados por riesgo, cada tarea con contexto, causa raiz,
  verificacion previa obligatoria, cambio propuesto, tests a escribir, criterios de aceptacion y
  mensaje de commit. Incluye la decision modulo por modulo sobre los 16 modulos de core/ que ningun
  codigo de produccion importa: 6 se cablean (cooldown, debounce, bindings por aplicacion, dwell,
  doble click, swipe) y 10 quedan declarados PoC con un test que impide cablearlos por accidente.

- Registrar verificacion parcial de V-03 en camara real
  ([`462c460`](https://github.com/josepanz/jarvis-gesture-hud/commit/462c460843ce36bc07b8246e7ea8e64a46e09d87))

Clap confirmado (dispara KEYBOARD_TOGGLE). Gojo domain, JJK Megumi y corazon coreano NO reprodujeron
  pese a varios intentos guiados - se documenta como "no reproduce" en vez de forzar un cambio de
  umbrales sin datos que lo justifiquen. V-06 y V-07 no se intentaron esta sesion (V-06 sin tiempo,
  V-07 necesita una maquina limpia sin Python).

- Registrar Workflow 4 (verificacion en camara) y Y-08 en el WORKPLAN
  ([`a428732`](https://github.com/josepanz/jarvis-gesture-hud/commit/a428732dc8bb69e94c036e6dfab04228812869f7))

Y-V1..Y-V4 completos con Jose (2026-09-06, DroidCam): los 14 sellos detectan (score real 0.76-0.94
  con forma correcta), umbral 0.7 y hold 1.2s no se ajustan (discriminan bien), costo no se puede
  aislar limpiamente por la varianza propia de DroidCam. Y-V3 encontro una colision real (Ne
  completaba de paso el hold de pausa) - documentada y resuelta en Y-08.

- Verificar H-26/H-27/H-28 en camara real
  ([`4cc5777`](https://github.com/josepanz/jarvis-gesture-hud/commit/4cc57774279d1c9b259a13a4fce564453763d09d))

Confirmado en vivo (Jose, 2026-09-07): snap de Sukuna ya no dispara click derecho, el gesto de pausa
  ya no se confunde cerca de bordes, y el panel de leyenda pagina/colapsa con controles clickeables
  (tras el fix de z-order, commit 57084b5).

### Features

- Bindings de gestos por aplicacion en foco
  ([`4f81ff3`](https://github.com/josepanz/jarvis-gesture-hud/commit/4f81ff3d40cad5674dde2141614b69dd9f6852d3))

_dispatch_bound_event() ahora consume ForegroundApplicationTracker (ya vivo en el loop, cacheado)
  para resolver, en este orden: regla por app del perfil activo (Profile.context_rules) > override
  del perfil > default global > identidad. resolve_contextual_intent() ya existia (pura, testeada) -
  la pieza que faltaba era llamarla.

Con context_rules vacio en todos los perfiles (sin editor propio todavia) el comportamiento es
  byte-identico al de antes mientras nadie defina una regla.

El gate de H-10 (una accion HOLD_REQUIRED no puede aterrizar en un evento sin hold propio) se reusa
  aca: HOLD_REQUIRED_ACTIONS/ HOLD_CAPABLE_EVENTS pasan a publicos en settings_ui.py para que
  main.py los comparta, en vez de duplicar el criterio.

Actualiza el docstring de main.py (desactualizado por A-01/A-02: ya no es cierto que GestureEngine
  use last_*_time a mano) y agrega tests/test_contextual_dispatch.py: no-regresion sin reglas, regla
  de la app en foco gana, regla de otra app no aplica, sin app detectada cae al override del perfil,
  una regla puede apuntar a un atajo custom, y el gate de HOLD_REQUIRED tambien aplica via
  context_rules.

- Detectar los sellos con el modelo cuando hay 2 manos en cuadro
  ([`d88ff68`](https://github.com/josepanz/jarvis-gesture-hud/commit/d88ff68a95647a241da2f5d525904df7b7b3fd55))

- Diagnostico en vivo de HandSignTracker para verificar en camara
  ([`393e9ba`](https://github.com/josepanz/jarvis-gesture-hud/commit/393e9ba61f703552b797cd4815d982b00a3fb525))

HandSignTracker expone last_detection (mejor deteccion cruda del modelo, score real, aunque no
  llegue a min_score ni tenga evento mapeado) y hold_elapsed/hold_needed (progreso del hold en
  curso). main.py los vuelca al HUD de debug (tecla d) como "sign"/"sign_hold" cuando hay tracker
  activo.

Preparacion para el Workflow 4 (WORKPLAN.md §6, verificacion en camara real con Jose) - permite leer
  en vivo el score y el progreso del hold sin depender de que la accion final sea visible.

- Doble click por pinch doble, re-anclado a la posicion del primero
  ([`50d6a2c`](https://github.com/josepanz/jarvis-gesture-hud/commit/50d6a2cf2fccb680ed4311aa7c75f76864261550))

- Dwell-click opcional (apuntar y sostener) sin necesidad de pinch
  ([`b534abf`](https://github.com/josepanz/jarvis-gesture-hud/commit/b534abf9d03f5f073477b66edd9b788220d96447))

- Filtro anatomico de manos via MediaPipe Pose (Fase 3B) + overlay de landmarks (Fase 2)
  ([`64b0511`](https://github.com/josepanz/jarvis-gesture-hud/commit/64b0511ed09a0b43d5d37c537a84cf90d89aad28))

Fase 3B (TASK-060b/060c): - pose_tracker.py: PoseTracker (num_poses=1, mismo patron que
  hand_tracker.py) + filter_hands_by_pose_ownership() - una mano solo se considera del usuario si su
  muñeca esta cerca de la muñeca correspondiente del cuerpo trackeado. Cae al heuristico de TASK-056
  cuando no hay cuerpo trackeado ese frame. - Medido en camara real: PoseLandmarker cuesta
  ~10.4ms/frame, practicamente el mismo costo que HandLandmarker (~10.0ms/frame) - activarlo duplica
  el costo de inferencia por frame. Por eso queda deshabilitado por default
  (config.POSE_HAND_OWNERSHIP_ENABLED), togglable.

Fase 2 (TASK-057): - hand_visualizer.py: overlay toggleable (tecla 'l') de esqueleto + cuadrante +
  distincion mano primaria/otra + etiqueta de gesto activo, cv2 puro sin dependencia nueva.
  GestureEngine expone last_primary_landmarks para la distincion primaria/otra.

Ademas: comentario con las 3 formas de resolver el error de instalacion de llama-cpp-python en
  Windows (limite de ruta MAX_PATH) en requirements-voice.txt.

Tests nuevos (test_pose_tracker.py, test_hand_visualizer.py), 478 tests en verde, verificado en
  camara real (inferencia, fallback sin cuerpo trackeado, boot completo de la app con la
  funcionalidad habilitada y deshabilitada).

- Gestos comunes (Fase 7) - Clap y corazon coreano
  ([`6bce897`](https://github.com/josepanz/jarvis-gesture-hud/commit/6bce8972c6a8ff67558b4739a04ff11c02ec19b9))

TASK-071: CLAP (2 manos, temporal) - segunda instancia de ImpulseDetector sobre la distancia entre
  centros de PALMA (landmarks 0/5/9/13/17, distinto de _hand_center usado por los sellos y del punto
  medio de pellizco del zoom - 3 nociones de "centro de mano" ya en uso). Evento emitido solo si
  ningun otro gesto de 2 manos ya gano - jerarquia, no solapamiento.

TASK-072: KOREAN_HEART (1 mano, estatico + hold) - pulgar cerca del primer nudillo del indice
  (landmark 6), no de su punta, lo que hace que d_thumb_index quede estructuralmente por encima de
  PINCH_CLICK (nunca puede ganar pinch_winner=="index", PINCH_DOWN nunca colisiona por
  construccion). Sostenido 1.0s antes de disparar, mismo mecanismo que LOCK_SESSION/Shaka.

Colision real encontrada y arreglada SIN camara, por el propio test suite: silence_hand() tenia el
  pulgar y el primer nudillo del indice coincidentes por construccion (sin relacion con este gesto)
  y satisfacia igual las 2 condiciones geometricas - se agrego el chequeo de puño cerrado
  (_fingers_curled en los 4 dedos) como discriminador estructural, mismo tipo de hallazgo que el de
  fist_hand()/NARUTO_I en la Fase 4.

TASK-073: dispatch (CLAP->KEYBOARD_TOGGLE "Clapper", KOREAN_HEART-> SCREENSHOT "pose de foto"), 2
  iconos nuevos (glyph clap_burst distinto de snap; primer icono de 1 mano con puño totalmente
  cerrado + glyph corazon), 2 filas de leyenda.

Simplificacion de dispatch sin cambio de comportamiento: run() ruteaba por prefijo NARUTO_/JJK_, que
  CLAP/KOREAN_HEART no llevan - ahora rutea por pertenencia a NARUTO_DEFAULT_BINDINGS (mas simple,
  ya correcto para todo lo existente).

Misma politica de la Fase 6: todo razonado y verificado solo con fixtures sinteticas, pendiente de
  la prueba integral en camara real. 525 tests en verde (+8 sobre la Fase 6).

- Gestos Jujutsu Kaisen (Fase 6) - Gojo, Sukuna, Megumi
  ([`c0cb0cf`](https://github.com/josepanz/jarvis-gesture-hud/commit/c0cb0cffc9f7235de1ae0a2086d7bfeb64fe9dca))

TASK-067: nuevo modulo temporal_gesture.py con ImpulseDetector - primer primitivo TEMPORAL del
  codebase (maquina de 3 estados idle/armed/expired, distingue un snap real de un pinch sostenido
  que eventualmente se suelta).

TASK-068: JJK_GOJO_DOMAIN (2 manos, estatico, Pattern B - angulo pulgar-indice ~90 grados en ambas
  manos + cercania + parte superior del cuadro) y JJK_MEGUMI (1 mano, estatico - familia visual de
  Hitsuji pero con el anular extendido en vez de recogido, discriminador explicito pedido por
  design.md §6.3, estructuralmente imposible de colisionar con Hitsuji).

TASK-069: JJK_SUKUNA (1 mano, temporal) via ImpulseDetector sobre d_thumb_middle. Riesgo de colision
  con RIGHT_CLICK documentado explicitamente como NO resuelto (umbral de contacto mas ajustado que
  el de RIGHT_CLICK, pero un snap real cruza ambos umbrales en el mismo gesto fisico) - pendiente de
  diagnostico en camara real.

TASK-070: dispatch (RIGHT_CLICK/SCREENSHOT/MUTE, reusando acciones ya asignadas - el vocabulario
  fijo de 14 acciones ya estaba agotado por los 13 sellos Naruto), 3 iconos nuevos (glyph "snap"
  nuevo para Sukuna, comunica movimiento en vez de pose estatica), 3 filas de leyenda.

Refactor sin cambio de comportamiento: _naruto_seal/_twohand_seal ahora guardan el evento completo
  (NARUTO_*/JJK_*) en vez de un nombre corto f-string-prefijado, para que el mismo
  hold-state-machine sirva a ambos namespaces sin duplicar logica.

Primera fase donde el usuario pidio explicitamente posponer TODA verificacion en camara real a una
  prueba integral final (en vez de una por fase, como en Fase 4/5) - todo lo de arriba es razonado y
  verificado solo con fixtures sinteticas contra el GestureEngine real, documentado como tal en
  ARCHITECTURE.md. 517 tests en verde (+16 sobre la Fase 5).

- Handsigntracker con debounce y hold sobre el modelo de sellos
  ([`219a9f1`](https://github.com/josepanz/jarvis-gesture-hud/commit/219a9f187fadf897281d50cb4798ad54ce94d8a8))

- Infraestructura de iconos de referencia (Fase 3)
  ([`d99e2ff`](https://github.com/josepanz/jarvis-gesture-hud/commit/d99e2ff8ed831764252839f287c2dccb55c7b67b))

- gesture_icons.py: ICON_SPECS declarativo + ensure_icon()/generate_all_icons() - iconos generados
  con PIL (palma+dedos extendidos/curvados, marca de pinch, badge de accion geometrico sin texto
  para evitar el problema de acentos que ya tiene cv2.putText), cacheados y gitignored bajo
  assets/gesture_icons/. - legend.py: ENTRIES gana icon key por entrada, nuevo
  build_legend_entries(); build_legend_text() se mantiene byte-identico (verificado con test). -
  overlay.py: init_legend(entries, corner, title) renderiza filas de icono+texto via tk.PhotoImage
  nativo (sin PIL.ImageTk); toggle/opacidad/click-through sin cambios.

Verificado renderizando de verdad: 17 iconos distinguibles entre si (hash byte a byte), panel de
  leyenda real capturado con screenshot y leido como imagen. 485 tests en verde.

- Paginar y hacer colapsable el panel de leyenda de gestos
  ([`a1529b1`](https://github.com/josepanz/jarvis-gesture-hud/commit/a1529b1823681bd105200fa9129ba74ee1fbc773))

H-28 (verificado en camara real, Jose, 2026-09-07: "los gestos transparentes ocupan demasiado
  espacio, no son minimizables, y no tienen scroll, ocupan toda la pantalla del lado"). Con las 44
  entradas reales de legend.build_legend_entries(), el panel sin paginar ocupaba toda la mitad de
  pantalla del lado anclado.

El panel entero sigue siendo click-through de punta a punta (no puede tener sus propios widgets
  clickeables sin perder esa propiedad a nivel de HWND), asi que los controles de pagina (circular,
  LEGEND_PAGE_SIZE=12 por pagina) y de colapsar/expandir viven en una ventanita aparte, no
  click-through - mismo patron ya establecido por init_gear_icon(). TOGGLE_LEGEND (mostrar/ ocultar
  el panel entero) queda sin cambios, es un mecanismo distinto y ortogonal a este colapsado parcial.

- Pantalla de configuracion (Fase 8) - persistencia, rebind, atajos y macros
  ([`6313907`](https://github.com/josepanz/jarvis-gesture-hud/commit/6313907968f419d82b16f61fb7a646836bbcb006))

Alcance completo (decision explicita del usuario sobre el MVP): TODO gesto es reasignable, no solo
  los 18 sellos Naruto/JJK/comunes - los 19 gestos "clasicos" de las Fases 1-3 tambien pasan ahora
  por ProfileManager, con identidad como default (sin reasignar nada, comportamiento identico a
  antes de esta fase).

TASK-074: core/config_store.py - JSON generico en disco, atomico, archivo corrupto preservado aparte
  nunca sobreescrito.

TASK-075: Profile gana custom_shortcuts/macros; ProfileManager.to_dict()/ from_dict() puentean al
  schema persistido sin inventar una segunda representacion en memoria.

TASK-076: actions/macro.py - HotkeyCommand/MacroCommand, Commands ordinarios que fluyen por el mismo
  CommandBus. PressKeyCommand.can_execute() ensanchado de {"space","backspace"} a
  pyautogui.KEYBOARD_KEYS completo (superconjunto estricto, sin romper el test existente).

TASK-077/078: Tooltip + icono de engranaje (overlay.py, unica ventana de ese modulo que NO es
  click-through).

TASK-079/080: settings_ui.py - tabla de bindings (37 triggers, sourced de GESTURE_DEFAULT_BINDINGS +
  jarvis.legend.ENTRIES, sin duplicar texto), captura de atajos custom, constructor de macros,
  frases de voz registradas (informativo), ayuda M1/M2/M3.

TASK-081: refactor de dispatch en main.py - _dispatch_naruto_seal() (nombre conservado por
  compatibilidad de tests) ahora resuelve CUALQUIER evento via GESTURE_DEFAULT_BINDINGS antes de
  macro/atajo/_dispatch(); _dispatch_voice_action() y _dispatch() se consolidan (UNDO/REDO/MUTE ya
  no duplicados en 2 lugares). Persistencia cargada al arrancar, guardada de inmediato en cada
  cambio.

2 hallazgos reales durante el propio testing (documentados en ARCHITECTURE.md): un mock wholesale de
  pyautogui rompia silenciosamente PressKeyCommand.can_execute() en tests existentes (corregido
  restaurando KEYBOARD_KEYS real sobre el mock); y event_generate sintetico necesita un update()
  completo previo en un Toplevel recien creado (gotcha de test, no de produccion).

Verificado con Tk real (sin mock) + captura de pantalla real de la ventana de settings y sus 2
  dialogos (screenshots revisados, no solo aserciones). 577 tests en verde (+23 sobre la Fase 7),
  ambos scripts de integracion manual OK (el de integracion en vivo ahora cubre persistencia de
  punta a punta).

- Persistir y editar reglas de gestos por app (A-03b)
  ([`ba4a237`](https://github.com/josepanz/jarvis-gesture-hud/commit/ba4a2371f426861ac510d240839e74eddb6a988d))

Extiende el schema de config_store a context_rules (SCHEMA_VERSION 1 -> 2):
  Profile.to_dict()/_apply_persisted_fields()/_profile_from_dict() ahora (de)serializan {app:
  {evento: accion}} con el mismo patron de validacion de tipos de H-02 (_valid_context_rules(),
  nueva - descarta solo la entrada de app invalida, no el dict entero, mismo criterio que
  _valid_macros()). Un archivo v1 sin la clave sigue cargando igual (context_rules vacio) porque
  _validated_dict_field() ya trata una clave ausente como {} - compatibilidad hacia atras gratis,
  sin rama por version.

Agrega una seccion nueva a SettingsWindow ("Reglas por aplicación en foco") para definir/eliminar
  reglas app+gesto->accion, reusando _rebind_target_options() para la lista de acciones - el mismo
  gate de H-10 (ninguna accion HOLD_REQUIRED sobre un gesto sin hold propio) que ya protege la tabla
  de bindings aplica aca sin duplicar el criterio.

Actualiza el pin de schema_version en test_to_dict_round_trips_through_ from_dict (1 -> 2, cambio
  legitimo de esta tarea) y agrega cobertura nueva en test_profiles.py (compatibilidad v1, tipos
  invalidos anidados, perfil no-default) y test_settings_ui.py (agregar/quitar regla, persistencia
  inmediata, gate de HOLD_REQUIRED en el dialogo).

- Secuencias de sellos como trigger de una accion
  ([`afe4b18`](https://github.com/josepanz/jarvis-gesture-hud/commit/afe4b188255e5281ab4bf93fa65451e40f64fd63))

Copia la IDEA del proyecto original (NARUTO-HandSignDetection, setting/jutsu.csv), no el codigo:
  SequenceTracker (jarvis/hand_sign_sequence.py) mantiene un historial de sellos CONFIRMADOS que se
  limpia si pasan config.NARUTO_SEQUENCE_INTERVAL_SECONDS (2s, mismo valor que sign_interval del
  original) sin ningun sello nuevo, y matchea contra una tabla fija de secuencias exactas (mas
  largas primero, para que una secuencia larga no pierda contra una corta que comparte sufijo). Un
  match consume el historial completo.

3 secuencias representativas decodificadas de jutsu.csv (no las 14 - una de ellas tiene 44 sellos,
  impracticable a mano): JUTSU_BUNSHIN (Hitsuji-Mi-Tora -> Doble click), JUTSU_KAWARIMI
  (Hitsuji-I-Ushi-Inu-Mi -> Deshacer), JUTSU_KATON (Mi-Tora-Saru-I-Uma-Tora, "Bola de Fuego", el
  ejemplo del WORKPLAN -> Zoom +). Cada una es un evento mas en GESTURE_DEFAULT_BINDINGS -
  reasignable por perfil como cualquier otro trigger, con su fila de leyenda e icono propios.

main.py alimenta cada sello confirmado (sign_events) al sequence_tracker antes del dispatch - una
  secuencia completa agrega su propio evento a la misma lista, sin camino de dispatch nuevo.

- Sellos Mizunoe y Gassho, que el modelo ya detecta
  ([`1683272`](https://github.com/josepanz/jarvis-gesture-hud/commit/1683272e55168ee2c11713285c47fd9249adb6dd))

Salian gratis del modelo YOLOX (Y-01): Gassho (manos juntas en oracion) y Mizunoe no son sellos del
  zodiaco, pero el modelo los distingue igual (14/14 imagenes canonicas, Y-01). Se agrega el evento
  (NARUTO_GASSHO/ NARUTO_MIZUNOE en hand_sign_tracker.CLASS_NAME_TO_EVENT), binding default
  (CLOSE_APP/SCROLL_LEFT - los 2 unicos huecos que quedaban en VALID_ACTIONS, CLOSE_APP libre desde
  que Y-04 borro NARUTO_KAI), HOLD_CAPABLE_EVENTS, fila de leyenda e icono. Mismo mecanismo de hold
  que los 12 sellos reales (NARUTO_TWOHAND_HOLD_SECONDS).

CLAP no colisiona con Gassho: verificado en el codigo (no en camara, pendiente Y-V3) que
  ImpulseDetector tiene un estado "expired" explicito - un contacto sostenido mas alla de
  CLAP_MAX_WINDOW_SECONDS (0.4s) nunca dispara al soltarse, ya cubierto por
  test_temporal_gesture.py::test_a_sustained_hold_that_eventually_releases_does_not_fire.

Tests: 731 (antes 729) - 2 tests de dispatch nuevos (Gassho/Mizunoe); test_hand_sign_tracker.py
  cubre las 14 imagenes canonicas ahora (antes 12).

- Sellos Naruto de 1 mano (Fase 4)
  ([`01f171d`](https://github.com/josepanz/jarvis-gesture-hud/commit/01f171dfb84f663de861a19435f3d108faf337b7))

TASK-061/062 - deteccion: - 8 sellos (Tora/Ushi/U/Uma/Saru/Inu/I + Hitsuji) via funciones puras en
  gestures.py, con censo de colision completo contra las 9 chequeos de 1 mano existentes y entre si,
  verificado contra el GestureEngine real (no solo razonado). - Uma y Saru REDEFINIDOS: la
  definicion original de Uma (5 dedos abiertos) colisiona con KEYBOARD_TOGGLE (hallazgo propio, no
  flageado en el diseño); la de Saru (pulgar+meñique) es exactamente la forma de _is_shaka (flag
  explicito del diseño). Ninguno de los 2 cambia el significado de un gesto existente (apply.md
  §15). - Tora/U/Hitsuji comparten la forma base de SCROLL - se distinguen via distancia
  pulgar-indice, separacion indice-medio y un chequeo real de cruce de dedos, sin tocar la condicion
  de SCROLL. - Todos gateados por pinch_winner is None (ningun pinch activo) - descarta colision con
  toda la familia de pinch de una sola vez. - Sostenidos config.NARUTO_SEAL_HOLD_SECONDS antes de
  confirmar (mismo patron que Shaka/LOCK_SESSION) - la gating de HOLD_REQUIRED vive rio arriba, el
  evento no puede existir antes de tiempo.

TASK-063 - dispatch e iconos: - NARUTO_DEFAULT_BINDINGS + JarvisApp._dispatch_naruto_seal(), reusa
  ProfileManager.get_gesture_binding() y _dispatch_voice_action() (mismo camino que la voz). - 8
  iconos nuevos (infra de Fase 3), distinguibles entre si y de los 17 existentes. - 8 filas nuevas
  en la leyenda - las 16 lineas existentes no cambiaron de texto, solo el padding compartido.

495 tests en verde, ambos scripts de integracion manual verificados (incluye un sello de punta a
  punta: deteccion real + hold + dispatch real).

- Sellos Naruto de 2 manos (Fase 5)
  ([`30b8c93`](https://github.com/josepanz/jarvis-gesture-hud/commit/30b8c93df3eee541c4feb04c7517826c627c2d84))

TASK-064/065/066 - Ne, Mi, Tori, Kai, Tatsu:

- Censo de colision actualizado: la superficie crecio de 13 a 21 condiciones desde que Fase 4 agrego
  8 chequeos nuevos de 1 mano (no contemplado en el diseño original). - Proxy grueso a proposito
  (distancia entre centros + curvatura promedio + orientacion) en vez de entrelazado fino de dedos -
  design.md §5.1 ya advertia que MediaPipe no puede verlo de forma confiable entre 2 manos, no es
  una simplificacion mia sin avisar. A pedido explicito del usuario: la geometria real de la foto de
  referencia primero, simplificar solo si falla en camara (igual que Fase 4). - _segments_cross()
  extraido de la v2 de _fingers_crossed (Fase 4) para reusarlo tambien ENTRE las 2 manos (Kai). -
  Kai: manos juntas + indice+medio de ambas cruzados encima (unico sello que "prueba" el entrelazado
  real, via cruce de segmentos). - Tatsu: asimetria de curvatura entre las 2 manos (una envuelve a
  la otra). - Ne/Mi: mismo entrelazado (curvatura media), solo se distinguen por orientacion
  (arriba/abajo) - igual que los sellos reales. - Tori: manos separadas y abiertas ("en abanico"). -
  Mismo mecanismo de sostenido+tolerancia a parpadeos que Fase 4, hold mas largo (1.2s, como
  PAUSE_HOLD_SECONDS) por ser mas complejo de sostener sin querer. - Dispatch/iconos/leyenda reusan
  la infraestructura de TASK-063 tal cual.

501 tests en verde, verificado contra el GestureEngine real (cada fixture dispara solo su propio
  evento, sin colision con gestos de 2 manos existentes). PENDIENTE explicito: ninguno de estos 5
  sellos se verifico en camara real todavia - a pedido del usuario, esa ronda queda para despues.

- Swipe con puño cerrado para atras/adelante y escritorios
  ([`5547406`](https://github.com/josepanz/jarvis-gesture-hud/commit/55474069541d3a21ad001cf5f43e085be7ed19fd))

- Vendorizar el modelo YOLOX de deteccion de sellos (MIT, Kazuhito00)
  ([`a511715`](https://github.com/josepanz/jarvis-gesture-hud/commit/a51171556bc6634d7f2400778862ea4e754007ac))

### Performance Improvements

- Calcular el area de bbox una sola vez por mano al filtrar plausibilidad
  ([`3c9529a`](https://github.com/josepanz/jarvis-gesture-hud/commit/3c9529a4a1cefdf4a738450686a7c42289a964fb))

### Refactoring

- Borrar los sellos de una mano inventados, ya cubiertos por el modelo
  ([`7d45875`](https://github.com/josepanz/jarvis-gesture-hud/commit/7d45875bbb318bb585bc95d913c6619e9c94acca))

Borra las 8 funciones de deteccion geometrica de sellos Naruto de 1 mano
  (_is_naruto_ushi/_uma/_saru/_inu/_i, _index_middle_extended_ring_pinky_curled,
  _thumb_offset_from_palm) y los 5 sellos de 2 manos por geometria (Ne/Mi/Tori/Kai/Tatsu) en
  _process_two_hand_gestures - AUDIT.md midio que 6 de 8 no correspondian a ningun sello real. Los
  12 sellos reales ya los detecta el modelo YOLOX (Y-01/Y-02/Y-03). NARUTO_KAI se borra completo (no
  es uno de los 14 sellos canonicos); su accion default (CLOSE_APP) sigue alcanzable con las 2 manos
  en Shaka. JJK_MEGUMI y JJK_GOJO_DOMAIN quedan intactos (no son sellos Naruto, el modelo no los
  cubre).

Trampa 2 del WORKPLAN: los gates de dwell (C-01) y swipe (C-03) protegian que un sello en formacion
  no completara tambien un dwell/swipe via self._naruto_hold_seal - eso dejo de alcanzar a los 12
  sellos que ahora detecta HandSignTracker FUERA de GestureEngine. Se agrega
  external_seal_in_progress a GestureEngine.process() (inyectado por main.py cada cuadro desde
  hand_sign_tracker.hold_seal) para que ambos gates lo sigan cubriendo.

Tests: 729 (antes 740) - se borraron NarutoOneHandSealTests (6), NarutoTwoHandSealTests (4) y 3
  tests de JJKGestureTests que dependian de fixtures ya borradas; se agregaron 2 tests nuevos para
  la trampa 2 (external_seal_in_progress en dwell y swipe). HandLossStateResetTests y
  HoldRequiredGatingTests (test_naruto_seal_dispatch.py) reescritos contra
  JJK_MEGUMI/HandSignTracker en vez de NARUTO_TORA/NARUTO_I.

- Consolidar los cooldowns de gestos en CooldownRegistry
  ([`5cfb786`](https://github.com/josepanz/jarvis-gesture-hud/commit/5cfb786a93a5971cd039c3953c1d3c2be5a53bbe))

Reemplaza los 5 campos last_*_time ad hoc (click, right_click, screenshot, keyboard_toggle, silence)
  por una sola CooldownRegistry por instancia de GestureEngine, con clock=time.time para preservar
  la semantica exacta que usa process(). Los 5 nombres de accion quedan como constantes de modulo
  (COOLDOWN_*) para que un typo no desactive un cooldown en silencio.

Sin cambio de comportamiento: los 594 tests existentes quedan verdes sin tocar ninguno. Se agrega
  tests/test_gestures_cooldowns.py con cobertura de registro contra config.py, independencia entre
  acciones (no-regresion del bug historico de cooldown compartido) y re-disparo al expirar el
  cooldown.

- Invocar los comandos de bloqueo por subprocess en vez de os.system
  ([`5c1abc8`](https://github.com/josepanz/jarvis-gesture-hud/commit/5c1abc83543bbd928df34d3847d7e0a4d08e85cf))

- Renombrar _dispatch_naruto_seal a lo que realmente hace
  ([`71f0170`](https://github.com/josepanz/jarvis-gesture-hud/commit/71f01708e375f58f8395deca1d2af13247949556))

- Sacar el alias _dispatch_naruto_seal, verificado sin uso real
  ([`bdf04a6`](https://github.com/josepanz/jarvis-gesture-hud/commit/bdf04a6cad0d674e21b8e95c62ba9e3d8d06195a))

- Sincronizar explicitamente el buffer de audio entre hilos
  ([`bf5da43`](https://github.com/josepanz/jarvis-gesture-hud/commit/bf5da43114fbb4e89578071729b71e0495a4d6ae))

- Unificar debounce y tolerancia de fallos en jarvis.core.debounce
  ([`b2d113f`](https://github.com/josepanz/jarvis-gesture-hud/commit/b2d113f002bf968506d730ef519991944c1b884d))

El streak de confirmacion de pinch (self._pinch_streak, un int por dedo) pasa a 4 instancias
  independientes de ConsecutiveFrameDebouncer - una por dedo, para que observe() no comparta racha
  entre ellos.

La tolerancia de fallos de los sellos (Naruto de 1 mano y de 2 manos) es la semantica inversa
  (contar fallos consecutivos para NO revocar un hold, en vez de aciertos consecutivos para
  conceder), asi que no encaja en ConsecutiveFrameDebouncer: se agrega MissToleranceCounter como
  clase hermana en el mismo modulo, y se usa en los dos lugares que llevaban el contador a mano
  (_naruto_miss_streak, _twohand_seal_miss_streak).

_reset_single_hand_state() (H-05) y la rama de perdida de la segunda mano resetean los objetos
  nuevos igual que ya hacian con los campos viejos.

Sin cambio de comportamiento: los 679 tests quedan verdes (672 + 7 nuevos) sin tocar ninguno
  existente. gestures.py no tiene mas contadores de racha a mano.

### Testing

- Pinear el conjunto de modulos PoC no cableados
  ([`2056716`](https://github.com/josepanz/jarvis-gesture-hud/commit/20567163fd0b40a9fe8e746e1397dff844e20b90))

Declara de forma explicita y verificable, en vez de solo grepeable a mano, cuales de los 16 modulos
  "dormidos" de src/jarvis/core/ son prueba de concepto (10) vs. ya cableados
  (cooldown.py/debounce.py/ contextual_bindings.py, A-01/A-02/A-03) vs. con plan propio de cableado
  (double_click.py/swipe.py/dwell.py, workflow 8).

Cada modulo PoC lleva ahora un marcador de una linea al inicio de su docstring ("PoC / no cableado
  (...)"), y tests/test_poc_modules.py (nuevo) verifica por ast que ninguno se importa desde fuera
  de core/ (ni desde otro modulo core/ que no sea el mismo conjunto PoC) - el inverso de
  test_architecture_boundaries.py: pinea lo que NO debe estar cableado, para que cablear algo sea
  decision consciente.

Agrega la seccion "Dormant / PoC modules" a ARCHITECTURE.md con la misma tabla, como respuesta
  rapida a "que de esto esta vivo" sin tener que re-derivarlo de los imports.


## v0.4.0 (2026-08-27)

### Features

- Filtro de manos de fondo/otra persona (TASK-056) y scroll mas estricto
  ([`3acbdb5`](https://github.com/josepanz/jarvis-gesture-hud/commit/3acbdb5311573a8a5064786525e2e477e03617bc))

- filter_plausible_hands()/hands_plausibly_same_person() en gestures.py: descarta manos por debajo
  de MIN_HAND_AREA_FRACTION antes de cualquier logica de gestos, y exige que un par de manos sea
  plausiblemente de la misma persona (centros cerca, medido en camara real) antes de tratarlas como
  un gesto conjunto de 2 manos. - Scroll ahora tambien exige el menique recogido (no solo el
  anular), para no confundirse con otros gestos. - Nuevos tests (BackgroundHandFilterTests,
  pinky-en-scroll) + fixtures de test ajustadas (bbox ya no colapsa a area 0).


## v0.3.1 (2026-08-27)

### Bug Fixes

- Confusion Shaka/puno y pinch demasiado sensible (verificado en camara real)
  ([`8c43d4c`](https://github.com/josepanz/jarvis-gesture-hud/commit/8c43d4c082722e22f289e39acfba2fa6a8abb295))

Diagnosticado con DroidCam en vivo, no adivinado - dos reportes reales de uso:

1. Un puno bloqueaba la sesion. _is_shaka nunca chequeaba el anular. La transicion real de abrir un
  puno sostenido pasa, por un instante, por una forma que ya cumplia _is_shaka (menique "se
  extiende" antes que el resto, pulgar ya arriba, indice/medio todavia curvados) - con el anular
  tambien extendido, cosa que un Shaka real no tiene (se curva). Verificado en vivo antes/despues:
  antes, la transicion sostenia is_shaka=True un tramo visible; despues, solo 3 frames sueltos en
  0.18s, lejos del hold de 1.5s. Fix: exigir anular curvado en _is_shaka tambien.

2. "Todo dispara muy facil". Medidos en camara real: mano relajada llego a 15.5px en indice / 19.2px
  en medio durante movimiento normal, umbral viejo era 30px para practicamente todos los pinch.
  Pinch intencional: mediana 9.6px, bien separado del reposo. Fix doble: (1) umbrales bajados con
  margen sobre los datos medidos (config.py, ver comentario ahi); (2) PINCH_CONFIRM_FRAMES=2 - un
  dedo necesita 2 frames seguidos bajo su umbral antes de poder ganar pinch_winner, absorbe ruido de
  un solo frame sin depender de esta unica medicion para generalizar a otra camara.

Reverificado en vivo end-to-end despues del fix: 5 PINCH_DOWN/4 PINCH_UP limpios siguiendo pellizcos
  deliberados, sin ráfagas ni disparos falsos.

461 tests (17 actualizados para el nuevo requisito de confirmacion de 2 frames, 3 nuevos test
  dedicados, 1 nuevo con la geometria real capturada del bug de Shaka). Regresion completa,
  compilacion y ambos checks de integracion manual verificados.


## v0.3.0 (2026-08-27)

### Features

- Distancia de pinch en 3D usando el z de los landmarks (TASK-055c)
  ([`1142e9a`](https://github.com/josepanz/jarvis-gesture-hud/commit/1142e9a91e474577c9b2134e06878ed4a83c1354))

d_thumb_index/_middle/_ring/_pinky (click, click derecho, captura, zoom, volumen) ahora usan
  _dist3() en vez de _dist() - distancia real 3D en vez de la proyectada en pantalla en 2D.
  d_thumb_pinky_mcp (usado por SILENCE) queda en 2D, no es pinch-family.

z de MediaPipe ya viene normalizado ~a la misma escala que x, asi que reusar `w` para escalarlo es
  consistente con como ya se escala x, sin calibracion extra.

Todos los fixtures sinteticos existentes usan z=0, asi que la formula 3D degrada exacto a la 2D para
  todos ellos - verificado, suite completa sin cambios de comportamiento. Agregado un test nuevo con
  puntos cerca en (x,y) pero lejos en z, confirmado que sin este fix SI se registraba como pinch
  (bug real que esto corrige) y con el fix no.

Pendiente, documentado explicitamente en ARCHITECTURE.md: la re-verificacion de los umbrales PINCH_*
  contra una camara real no se pudo hacer desde este entorno (sin acceso a webcam) - quedan sin
  cambiar en vez de adivinarlos.

457 tests (2 nuevos), regresion completa, compilacion y boot real de la app verificados.


## v0.2.0 (2026-08-27)

### Features

- Suprime los 7 gestos de 1 mano restantes durante gestos de 2 manos (TASK-055b)
  ([`114fb03`](https://github.com/josepanz/jarvis-gesture-hud/commit/114fb036ee59b9a69cb0376c9f66a5f4df5867ad))

Solo LOCK_SESSION y PINCH_DOWN/PINCH_UP estaban protegidos contra un gesto de 2 manos concurrente -
  SILENCE, KEYBOARD_TOGGLE, SCREENSHOT, ZOOM/VOLUMEN de 1 mano, SCROLL y RIGHT_CLICK corrian igual
  sobre la mano "primaria" sin importar que estuviera haciendo la otra mano.

_process_two_hand_gestures ahora tambien devuelve two_hand_active - la condicion geometrica cruda de
  CUALQUIER gesto de 2 manos (shaka/punos/ pinch-zoom/menu meta), no si ya disparo su evento
  (algunos necesitan sostenerse) - y los 7 chequeos quedan gateados por ese flag. LOCK_SESSION y
  PINCH_DOWN mantienen su condicion angosta existente sin tocar, ya era correcta para su colision
  especifica conocida.

Tarea marcada opcional en la spec, se hace ahora porque ademas reduce el trabajo de deteccion de
  colisiones para cada gesto de 2 manos que se agregue despues (sellos Naruto/JJK/comunes), en vez
  de repetirlo por gesto mas adelante.

455 tests (8 nuevos), verificado que los 8 fallan sin el cambio y pasan con el. Regresion completa y
  boot real de la app verificados.


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
