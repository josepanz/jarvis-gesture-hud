# WORKPLAN — Endurecimiento y pulido final (`hardening-and-polish`)

> **Auditoría y especificación**: Opus 5 (2026-09-04), sobre la rama
> `feature/pose-ownership-and-visualization` en el commit `2ef30b4`.
> **Ejecución**: Sonnet, workflow por workflow, en el orden de este archivo.
>
> Este archivo es autocontenido: no hace falta leer la conversación que lo originó.
> Todo lo que el modelo ejecutor necesita (contexto, causa raíz, cambio, tests,
> criterios de aceptación, comando de verificación y mensaje de commit) está acá.

---

## 0. Cómo usar este archivo

- **Un workflow = una sesión de trabajo = uno o más commits.** No mezclar workflows en
  un mismo commit.
- Cada tarea tiene un ID (`H-01`, `H-02`, …). Al terminarla, marcá su casilla en la
  tabla del §8 y escribí en la misma línea el hash del commit.
- **Antes de cambiar código, ejecutá la "Verificación previa" de la tarea.** Este
  proyecto tiene historial de backlogs que quedaron viejos: los números de línea de
  este documento son del commit `2ef30b4` y pueden haber corrido. Si la verificación
  previa NO reproduce el problema descrito, **no toques nada**: anotalo en la tabla
  del §8 como "no reproduce" con lo que encontraste, y seguí con la tarea siguiente.
- Los hallazgos marcados **[VERIFICADO A MANO]** los confirmé leyendo el código yo
  mismo, no un agente. Los demás vienen de auditoría delegada y por eso todos traen
  verificación previa obligatoria.

---

## 0.1 Protocolo de ejecución y checkpoints

### Dónde para

**Una tarea = un checkpoint.** Al terminar cada tarea (`H-01`, `A-02`, `C-01`, …):

1. Corré la Definition of Done completa del §1.2.
2. Commiteá con el mensaje indicado en la tarea (uno por tarea, nunca agrupados).
3. Marcá la casilla en la tabla del §12 con el hash.
4. **Pará y reportá.** No sigas con la tarea siguiente por iniciativa propia.

El reporte de checkpoint son 4 líneas, no un ensayo: qué reproducía el problema antes,
qué cambiaste, cuántos tests hay ahora y si algo quedó raro. Si algo no cierra, decilo
en vez de seguir.

**Excepción**: si una tarea "no reproduce" (la verificación previa no muestra el
problema), no la arregles, anotala como tal en §12 con lo que encontraste, y **ahí sí**
seguí con la siguiente sin esperar — no tiene sentido parar por una tarea que no
existía.

### Cómo se le pide (prompt para copiar y pegar)

```
Leé openspec/changes/hardening-and-polish/WORKPLAN.md, secciones §0.1, §1 y la de la
tarea <ID>. Ejecutá SOLO la tarea <ID>.

Reglas:
- Hacé primero la "Verificación previa obligatoria" de la tarea. Si el problema no
  reproduce, no toques código: anotalo en §12 y decímelo.
- No re-audites el proyecto ni busques otros bugs: el análisis ya está hecho en el
  archivo.
- No lances subagentes. La tarea ya tiene los archivos y las líneas: leé esos.
- No leas ARCHITECTURE.md completo (son 1467 líneas): usá grep para la sección puntual
  que necesites.
- Al terminar: DoD del §1.2, commit con el mensaje de la tarea, casilla marcada en §12,
  y pará.
```

Para encadenar varias tareas de un mismo workflow en una sola sesión, cambiá
`SOLO la tarea <ID>` por `las tareas <ID>, <ID> y <ID>, en ese orden, parando y
reportando entre cada una`.

### Economía de tokens (importante)

- **Una sesión nueva por workflow, no por tarea ni por todo.** El contexto de la sesión
  que generó este archivo (auditoría completa, lecturas grandes) no aporta nada a la
  ejecución y se paga en cada mensaje. Este archivo es autocontenido justamente para
  que la ejecución arranque en frío.
- **Sin subagentes.** El archivo ya trae archivo, línea, causa raíz y trampas: no hay
  nada que explorar. Un subagente re-lee todo desde cero y multiplica el costo.
- **`ARCHITECTURE.md` completo son ~48.000 tokens.** Leerlo entero por costumbre es el
  gasto más grande y más evitable de este proyecto. Grep a la sección puntual.
- El commit por tarea es lo que permite tirar el contexto y arrancar limpio: el estado
  del trabajo vive en git y en la tabla del §12, no en la conversación.

---

## 1. Contexto del proyecto (lo mínimo indispensable)

`jarvis-gesture-hud` es un controlador de escritorio por gestos de mano vía webcam
(Python, MediaPipe Tasks API, `pyautogui`, Tkinter para overlays, `pyttsx3` para voz).
Mueve el mouse, hace click/drag/scroll/zoom, teclado virtual en pantalla, acciones de
SO (bloquear sesión, captura, volumen), sellos de Naruto/JJK como gestos, control por
voz opcional (STT `faster-whisper` + LLM local Qwen2.5-1.5B vía `llama-cpp-python`),
y una pantalla de configuración para reasignar cualquier gesto.

Arquitectura: `GestureEngine` (lógica pura, sin I/O) produce eventos string →
`main.py` los resuelve contra los bindings del perfil activo → `Command` →
`CommandBus` → `jarvis.actions.*` → `pyautogui`/`CrossPlatformOS`.

Estado al momento de esta auditoría:

- Rama `feature/pose-ownership-and-visualization`, commit `2ef30b4`, **sin mergear**
  (PR #2 abierto).
- 594 tests automáticos en verde (`python -m unittest discover -s tests`), 59 archivos
  en `tests/`.
- Fases 1–8 del roadmap implementadas. Documentación viva en `ARCHITECTURE.md`
  (fuente de verdad, en inglés); propuestas OpenSpec en `openspec/changes/`.

### 1.1 Convenciones NO negociables

Estas reglas vienen del historial real del proyecto. Romperlas es peor que no hacer la
tarea.

1. **Los commits NUNCA llevan `Co-Authored-By`, ni ninguna referencia a Claude, a un
   modelo o a IA.** Autoría exclusiva de `josepanz`.
2. **Conventional Commits obligatorio**, en español, porque `python-semantic-release`
   lee los prefijos en `main`: `fix:` / `feat:` / `perf:` / `refactor:` / `test:` /
   `docs:` / `chore:` / `ci:` / `build:`.
3. **Verificar antes de arreglar.** La disciplina central de este proyecto es
   root-cause con datos reales, no adivinanza: si no podés demostrar el bug (test que
   falla, log, medición), no lo "arregles". Todo umbral nuevo se justifica con un
   número medido o se marca explícitamente como razonado-no-medido.
4. **No cablear los módulos dormidos de `src/jarvis/core/`.** `GestureStateMachine`,
   el debounce/cooldown genérico, los detectores de swipe/dwell/double-click y un loop
   basado en `InputProvider` están construidos y testeados a propósito **sin** estar
   conectados al loop de cámara. Cada uno tiene el "por qué no" en su docstring.
   Conectarlos cambia latencia y feel ya probados: fuera de alcance acá.
5. **Todo cambio de comportamiento se documenta en `ARCHITECTURE.md`**, en la sección
   "Decisions & rationale", con causa raíz y cómo se verificó — no solo qué se cambió.
6. **`GestureEngine` es la línea base correcta** salvo bug demostrado. No refactorizarlo
   por gusto estético.
7. **Los tests son `unittest` de stdlib, sin dependencias nuevas.** Los fixtures de
   gestos son landmarks sintéticos; ese estilo se mantiene.
8. Archivos `tests/manual_*.py` están excluidos del discovery a propósito (construyen
   `VoiceJarvis`/`ScreenOverlay`/ventanas Tk reales). Se corren a mano.

### 1.2 Definition of Done global (aplica a TODA tarea)

Ninguna tarea está terminada hasta que todo esto pase:

```bash
cd C:\workspace\jarvis-gesture-hud
python -m py_compile src/jarvis/<archivos tocados>.py
python -m unittest discover -s tests            # 594+ tests, TODOS en verde
python tests/manual_main_integration_check.py   # debe imprimir INTEGRATION OK
python tests/manual_live_integration_check.py   # debe terminar sin traceback
```

Más: un arranque real de la app (`python run.py`, ~10s, sin mano en cuadro) sin
traceback en el log, para cualquier tarea que toque `main.py`, `gestures.py`,
`overlay.py` o `paths.py`.

Si un test existente se rompe: **no lo ajustes para que pase**. Entendé por qué se
rompió primero. Si el test estaba pineando comportamiento correcto, tu cambio está
mal. Si el test pineaba un valor que legítimamente cambió (p. ej. un umbral), actualizá
el pin y decilo en el commit.

---

## 2. Inventario de hallazgos

Severidad: **CRÍTICO** = crashea la app o deja el SO en mal estado · **ALTO** = pérdida
de funcionalidad o riesgo de seguridad real · **MEDIO** = bug con workaround ·
**BAJO/ESTILO** = calidad.

| ID | Sev | Área | Síntoma en una línea |
|---|---|---|---|
| H-01 | CRÍTICO | dispatch | Una macro malformada en disco mata el loop de cámara entero |
| H-02 | CRÍTICO | persistencia | Un `bindings.json` corrupto impide arrancar la app, sin salida |
| H-09 | CRÍTICO | dispatch | Reasignar la fila `PINCH_UP` deja el botón del mouse apretado a nivel de SO |
| H-03 | ALTO | red/assets | Descargas de modelo sin checksum ni escritura atómica: un parcial se reusa para siempre |
| H-05 | ALTO | gestos | El estado de gestos de 1 mano no se resetea si la mano sale de cuadro → `LOCK_SESSION` instantáneo al volver |
| H-10 | ALTO | seguridad | El settings deja mapear `LOCK_SESSION` a un gesto instantáneo, evadiendo el hold de 1.5s |
| H-13 | ALTO | packaging | En el `.exe` onefile los assets viven en `_MEIPASS`: se regeneran/pierden en cada arranque |
| H-18 | ALTO | CI/CD | `release.yml` y `ci.yml` corren en paralelo: se puede publicar un release sin tests verdes |
| H-04 | MEDIO | arranque | Fallo de red en el primer arranque = traceback crudo, sin mensaje útil |
| H-06 | MEDIO | gestos | "Pinch fantasma" del anular gana la prioridad sin disparar nada y se come el volumen |
| H-11 | MEDIO | undo/redo | La pila de redo nunca se invalida al ejecutar un comando nuevo |
| H-12 | MEDIO | recursos | Salir con el micrófono grabando no cierra el stream de audio |
| H-14 | MEDIO | arranque | `ensure_icon()` sin manejo de error: un fallo de escritura crashea el arranque |
| H-15 | MEDIO | assets | Escritura de iconos no atómica (inconsistente con `config_store`) |
| H-19 | MEDIO | deps | `requirements.txt` sin ningún pin, con historial real de rotura por `mediapipe` |
| H-07 | BAJO | docs/config | Comentario de umbral cita el ruido del dedo equivocado |
| H-08 | ESTILO | perf | Recomputación redundante de bbox por cuadro |
| H-16 | BAJO | packaging | `jarvis.spec` no pre-genera ni empaqueta los iconos |
| H-17 | BAJO | dead code | `generate_all_icons()` sin uso fuera de tests |
| H-20 | BAJO | CI | Sin cache de pip: reinstala mediapipe/opencv en cada corrida |
| H-21 | ESTILO | seguridad | `os.system()` con strings en vez de `subprocess` con lista |
| H-22 | BAJO | threads | `_frames` de `voice_capture` sin sincronización explícita |
| H-23 | ESTILO | persistencia | Nombre de archivo temporal fijo en la escritura atómica |
| H-24 | BAJO | claridad | `_dispatch_naruto_seal()` ya no despacha solo sellos |
| H-25 | BAJO | docs | `ARCHITECTURE.md` y `README.md` citan conteos de tests viejos |

**Descartados explícitamente (auditados y NO son bugs — no los "arregles"):**

- El flag `self._llm_resolving` **no** tiene race: tanto el `True` como el `False` se
  escriben en el hilo principal; el hilo de fondo solo toca la `queue.Queue`.
- `_resolve_llm_intent_async` **sí** captura `Exception` y la reenvía por la cola.
- La frontera de confianza del LLM **sí** es real: `llm_intent.py` valida contra
  `VALID_ACTIONS` y nunca pasa texto libre a `pyautogui`/shell.
- **No hay llamadas a Tk desde hilos de fondo.** Todo Tk sale del hilo del loop de
  cámara vía `pump()`.
- `MacroCommand` y `LockSessionCommand` no son reversibles, así que no existe el
  problema de "deshacer una macro a medias".
- No hay path traversal alcanzable desde `bindings.json`, ni dead config en
  `config.py`, ni division-by-zero en los cálculos geométricos.
- El patrón de mock-total de `pyautogui.KEYBOARD_KEYS` ya está resuelto en todos los
  tests donde importa; no existe un equivalente sin restaurar para `cv2`/`mediapipe`/`tkinter`.

---

## 3. WORKFLOW 1 — Nada puede crashear la app (CRÍTICO, hacer primero)

**Objetivo**: después de este workflow, ni un archivo de configuración corrupto ni una
macro malformada ni un fallo de red pueden matar la app o dejarla sin arrancar.

**Por qué primero**: son los únicos hallazgos que producen pérdida total de
funcionalidad, y dos de ellos se disparan con datos que el propio usuario puede generar
usando la pantalla de configuración.

---

### H-01 · CRÍTICO · Una macro malformada mata el loop de cámara

**[VERIFICADO A MANO]**

**Archivos**: `src/jarvis/main.py` (~líneas 616–632, 700–715), `src/jarvis/actions/macro.py`
(~líneas 50–63), `src/jarvis/core/profiles.py` (`_apply_persisted_fields`).

**Síntoma**: con una macro inválida guardada en `~/.jarvis-gesture-hud/bindings.json`,
hacer el gesto que la dispara cierra la aplicación entera (cámara incluida) con un
traceback.

**Causa raíz**: en `_dispatch_macro_or_shortcut()`, la construcción de los pasos ocurre
**como argumento** de la llamada al bus:

```python
self.command_bus.dispatch(MacroCommand(action_name, build_macro_steps(macro_steps)))
```

`build_macro_step()` lanza `ValueError` para cualquier paso con un `"kind"` que no
reconoce. Como se evalúa *antes* de entrar a `CommandBus.dispatch()`, la red de
try/except del bus (que sí protege todo lo demás) nunca la ve. La excepción sube por
`_dispatch_naruto_seal()` hasta el `for event in events:` de `run()`, que no tiene
try/except, y mata el proceso.

Agravante: `ProfileManager.from_dict()` carga las macros del disco **sin validar la
forma de los pasos**, así que un `bindings.json` editado a mano, corrupto o de un
esquema futuro produce exactamente esto.

**Verificación previa obligatoria** — escribí primero un test que falle:

```python
# tests/test_dispatch_error_isolation.py (nuevo)
# Con una macro cuyo paso tiene kind="no-existe", _dispatch_naruto_seal NO debe
# propagar la excepción. Hoy propaga: el test debe fallar antes del fix.
app.profiles.active.macros["MACRO:rota"] = [{"kind": "no-existe"}]
app.profiles.active.gesture_bindings["NARUTO_TORA"] = "MACRO:rota"
app._dispatch_naruto_seal("NARUTO_TORA")   # hoy: ValueError
```

Reusá el `_AppTestCase` de `tests/test_naruto_seal_dispatch.py` (ya aísla
`config_store.load_bindings`/`save_bindings` a un directorio temporal — importalo, no
lo reimplementes).

**Cambio**:

1. En `_dispatch_macro_or_shortcut()`, construí los pasos **dentro** de un try/except
   antes de despachar, y ante fallo mostrá feedback al usuario en vez de propagar:
   usá `self.feedback.notify(...)` con el canal `("hud",)`, igual que hace
   `_handle_voice_result` para el caso "todavía estoy pensando".
2. Defensa en profundidad: envolvé el `for event in events:` de `run()` en un
   try/except por evento, que registre el error (`logging`) y siga con el evento
   siguiente. Un gesto que falla no puede tumbar los demás ni la cámara.
3. Validá la forma de los pasos al **cargar** (`profiles.py`), descartando macros
   inválidas con un log en vez de aceptarlas: un binding roto es preferible a un
   arranque roto.

**Tests a agregar** (archivo nuevo `tests/test_dispatch_error_isolation.py`):

- Una macro con `kind` desconocido → no lanza, y el usuario recibe feedback.
- Una macro cuyos pasos no son una lista (p. ej. un string) → no lanza.
- Un paso válido después de uno inválido → la macro inválida no rompe el despacho de
  un gesto posterior normal (p. ej. `PINCH_DOWN` sigue funcionando).
- Una macro válida sigue ejecutándose exactamente igual que antes (no-regresión).

**Criterios de aceptación**: los 4 tests nuevos en verde; los 594 existentes sin
tocar; `manual_main_integration_check.py` en OK.

**Commit**: `fix: aislar fallos de macro/atajo para que no tumben el loop de camara`

---

### H-02 · CRÍTICO · Un `bindings.json` corrupto impide arrancar

**[VERIFICADO A MANO]** (`core/profiles.py:206-217`)

**Archivos**: `src/jarvis/core/profiles.py` (`_apply_persisted_fields`,
`_profile_from_dict`), `src/jarvis/core/config_store.py` (`load_bindings`).

**Síntoma**: si `~/.jarvis-gesture-hud/bindings.json` tiene tipos inesperados, la app
no arranca más y la única salida es borrar el archivo a mano — algo que el usuario
final no sabe que existe.

**Causa raíz**: `config_store.load_bindings()` se protege de JSON inválido y de errores
de I/O (renombra el archivo corrupto a `.bak-<timestamp>` y devuelve `{}` — ese
mecanismo está bien y hay que preservarlo), pero **JSON sintácticamente válido con
tipos equivocados pasa el filtro** y explota más arriba:

```python
profile.macros.update({name: list(steps) for name, steps in (data.get("macros") or {}).items()})
```

Si `macros` es un string → `AttributeError: 'str' object has no attribute 'items'`.
Si `steps` es un número → `TypeError: 'int' object is not iterable`. Si `profiles` no
es un dict → falla antes. `ProfileManager.from_dict()` promete en su docstring que
"nunca lanza ante datos malformados": hoy esa promesa es falsa para tipos incorrectos,
solo es cierta para claves faltantes.

Secundario (misma tarea): `load_bindings()` no captura `RecursionError` (JSON
patológicamente anidado) ni `MemoryError` (archivo gigante), así que esos dos casos
tampoco caen en la ruta de cuarentena.

**Verificación previa obligatoria**:

```python
# Debe lanzar hoy (y no lanzar después del fix):
ProfileManager.from_dict({"schema_version": 1, "profiles": {"default": {"macros": "no-soy-un-dict"}}})
ProfileManager.from_dict({"schema_version": 1, "profiles": {"default": {"macros": {"m": 42}}}})
ProfileManager.from_dict({"schema_version": 1, "profiles": "tampoco-soy-un-dict"})
ProfileManager.from_dict({"profiles": {"default": {"gesture_bindings": ["lista", "no", "dict"]}}})
```

**Cambio**: en `profiles.py`, validá el tipo de cada campo persistido antes de
aplicarlo y descartá (con log) lo que no encaje, cayendo a los defaults de código —
que es exactamente lo que el docstring ya promete. Mantené el merge sobre el perfil
`"default"` ya sembrado (no lo reemplaces: sus valores de sensibilidad/cooldowns/dwell
nunca vienen del disco y tienen que sobrevivir a la carga). En `config_store.py`,
agregá `RecursionError` y `MemoryError` a las excepciones que disparan la cuarentena
del archivo.

**Tests a agregar** en `tests/test_profiles.py` y `tests/test_config_store.py`:

- Los 4 casos de la verificación previa: no lanzan y devuelven un `ProfileManager`
  con los defaults de código intactos.
- Un `bindings.json` con tipos mixtos (una macro válida y una inválida) conserva la
  válida y descarta la inválida.
- Regresión explícita: los valores no persistidos del perfil `default`
  (`sensitivity`/`cooldowns`/`dwell`) siguen siendo los de código después de un
  `from_dict()` con datos parciales.

**Criterios de aceptación**: `ProfileManager.from_dict()` no lanza para **ningún**
input JSON-válido; el archivo corrupto sigue quedando en cuarentena, nunca
sobrescrito en silencio.

**Commit**: `fix: validar tipos al cargar bindings persistidos para no romper el arranque`

---

### H-03 · ALTO · Descargas de modelo sin checksum ni escritura atómica

**Archivos**: `src/jarvis/hand_tracker.py` (~29–34), `src/jarvis/pose_tracker.py`
(~34–39), `src/jarvis/llm_intent.py` (~70–75, `_ensure_model_path`).

**Síntoma**: si la descarga del modelo se corta (wifi, cierre de la app, disco lleno),
queda un archivo parcial con el nombre final. En el arranque siguiente el código lo
encuentra, asume que está completo, y lo pasa a un parser nativo (MediaPipe /
`llama.cpp`) — que falla de forma opaca, o peor, con un crash nativo. El único
workaround es borrar el archivo a mano.

**Riesgo adicional**: no hay verificación de integridad (hash) de ningún modelo
descargado. En un proyecto offline y personal esto no es un vector de ataque
realista, pero **sí** es la diferencia entre "archivo corrupto detectado" y "el parser
nativo se come basura". El valor real acá es robustez, no defensa contra un atacante.

**Verificación previa obligatoria**: simulá el parcial. Truncá a la mitad el
`hand_landmarker.task` de `assets/` (copialo antes) y arrancá la app: confirmá que el
error es opaco/crash y no un mensaje útil con re-descarga.

**Cambio** (un helper compartido, no tres implementaciones):

1. Descargá siempre a `<destino>.part` y hacé `os.replace()` al terminar — el mismo
   patrón atómico que `config_store.py` ya usa bien. Así un parcial nunca ocupa el
   nombre final.
2. Verificá el tamaño esperado cuando el servidor lo informa (`Content-Length`), y si
   no coincide, borrá el `.part` y reportá un error accionable.
3. Donde tengas un hash conocido y estable del artefacto, verificalo; donde no, dejá
   escrito en el docstring que la comprobación es solo de tamaño y por qué.
4. Poné el helper en `src/jarvis/paths.py` (o un módulo nuevo `downloads.py`) y usalo
   desde los tres llamadores. **No dupliques**: el proyecto ya extrajo `paths.py`
   justamente para no duplicar esta clase de lógica.

**Tests a agregar** (`tests/test_model_download.py`, nuevo): con `urlretrieve`/HTTP
mockeado — descarga exitosa deja el archivo final y ningún `.part`; descarga
interrumpida (excepción a mitad) **no** deja archivo con el nombre final; tamaño
inconsistente con `Content-Length` es rechazado; un archivo final ya existente no se
vuelve a descargar.

**Commit**: `fix: descarga atomica y verificada de los modelos para no reusar parciales`

---

### H-04 · MEDIO · Fallo de red en el primer arranque = traceback crudo

**Archivos**: `src/jarvis/main.py` (~268–275, construcción de `HandTracker`/`PoseTracker`).

**Cambio**: envolvé la inicialización en try/except y, ante fallo, mostrá un mensaje
accionable ("no se pudo descargar/cargar el modelo de manos; revisá la conexión — el
archivo va a `assets/`") por `logging` y por burbuja del overlay si el overlay ya
existe, y salí con un código de error limpio en vez de un traceback. Cuidado con el
orden: el overlay puede no estar construido todavía; el mensaje por consola tiene que
funcionar igual.

**Test**: en `tests/test_main_startup.py` (nuevo), con `HandTracker.__init__`
mockeado para lanzar, `JarvisApp()` reporta el error de forma controlada.

**Commit**: `fix: mensaje accionable si falla la carga del modelo al arrancar`

---

## 4. WORKFLOW 2 — Bugs de dispatch y rebinding

**Objetivo**: que reasignar un gesto en la pantalla de configuración no pueda dejar el
sistema operativo en mal estado ni evadir un gate de seguridad.

**Contexto necesario**: en la Fase 8 se generalizó el despacho — `_dispatch_naruto_seal()`
(nombre histórico, ver H-24) resuelve **todo** evento contra
`GESTURE_DEFAULT_BINDINGS` + los overrides del perfil, y recién después llama a
`_dispatch()`. Esa generalización es correcta y deseada, pero dejó dos huecos.

---

### H-09 · CRÍTICO · Reasignar `PINCH_UP` deja el botón del mouse apretado

**[VERIFICADO A MANO]** (`main.py:357-374` recibe el nombre **ya resuelto** que
`main.py:634-652` produjo)

**Síntoma**: el usuario reasigna la fila `PINCH_UP` en la pantalla de configuración a
cualquier otra acción. A partir de ahí, el primer pinch presiona el botón izquierdo del
mouse y **nunca lo suelta**: el escritorio queda arrastrando, fuera del control de la
app. Solo se arregla cerrando Jarvis (o ni eso, si el botón queda lógicamente apretado).

**Causa raíz**: la máquina de estados del drag vive en `_dispatch_migrated()` y se
apoya en comparar el string recibido:

```python
elif gesture_type == "PINCH_UP":
    if self.is_dragging:
        self.command_bus.dispatch(MouseButtonCommand(pressed=False))
        self.is_dragging = False
```

Pero lo que llega ahí es el **nombre de acción resuelto**, no el evento físico crudo:
`_dispatch_naruto_seal()` resuelve el binding y llama `self._dispatch(action_name, ...)`.
Si `PINCH_UP` está reasignado, el gesto físico de soltar el pinch nunca entra por esa
rama: `MouseButtonCommand(pressed=False)` no se despacha y `self.is_dragging` queda en
`True` para siempre.

**Verificación previa obligatoria**:

```python
app.profiles.active.gesture_bindings["PINCH_UP"] = "SCREENSHOT"
app._dispatch_naruto_seal("PINCH_DOWN", cam_xy=(10, 10), screen_xy=(500, 400))
assert app.is_dragging is True
app._dispatch_naruto_seal("PINCH_UP", cam_xy=(10, 10), screen_xy=(500, 400))
assert app.is_dragging is False   # hoy FALLA: sigue en True, el mouse quedó apretado
```

**Cambio**: el ciclo de vida del drag tiene que gobernarse por el **evento físico**,
antes de la resolución del binding. Opción recomendada: manejar el par
`PINCH_DOWN`/`PINCH_UP` en `_dispatch_naruto_seal()` (o en el loop de `run()`) sobre el
evento crudo — soltar el botón siempre que llegue un `PINCH_UP` físico y `is_dragging`
sea `True` — y recién después resolver el binding para la acción que el usuario haya
elegido. Es decir: la limpieza del drag es un invariante del sistema, no una acción
reasignable.

Cuidá dos cosas que ya funcionan y no deben romperse: el `PINCH_DOWN` sobre el teclado
virtual **no** arranca un drag (hay un test que lo pinea), y el `TOGGLE_ACTIVE` hace su
propia limpieza de drag.

**Tests a agregar** en `tests/test_naruto_seal_dispatch.py`:

- El caso de la verificación previa, en ambas direcciones (`PINCH_UP` reasignado,
  `PINCH_DOWN` reasignado).
- Con ambos reasignados, `is_dragging` nunca queda en `True` tras un ciclo completo.
- No-regresión: sin reasignaciones, el drag se comporta exactamente igual que hoy;
  el click sobre el teclado virtual sigue sin arrancar drag.

**Commit**: `fix: la limpieza del drag ya no depende del binding de PINCH_UP`

---

### H-10 · ALTO · El rebinding evade el hold de 1.5s de `LOCK_SESSION`

**Archivos**: `src/jarvis/settings_ui.py` (`_rebind_target_options`, ~253–296),
`src/jarvis/actions/system.py` (`LockSessionCommand`, ~111–116),
`src/jarvis/core/command_bus.py`.

**Síntoma**: la pantalla de configuración ofrece `LOCK_SESSION` como destino de
**cualquier** fila, incluida `PINCH_DOWN` (instantáneo). Con ese rebind, un pinch
casual bloquea la sesión sin ningún hold — perdiendo trabajo sin confirmación.

**Causa raíz**: el gate de `HOLD_REQUIRED` es **posicional, no estructural**. Vive
dentro de `GestureEngine` (que solo emite `LOCK_SESSION` después de 1.5s de Shaka
sostenido) y `LockSessionCommand` documenta en su propio docstring que asume ese hold
"aplicado aguas arriba". `CommandBus` recibe `HOLD_REQUIRED` y **no lo verifica**
(a diferencia de `DESTRUCTIVE`, que rechaza de plano). La suposición solo se sostiene
mientras el binding sea el default.

**Verificación previa obligatoria**: abrí el combo de la fila `PINCH_DOWN` en la
pantalla de configuración (o inspeccioná `_rebind_target_options()` para esa fila) y
confirmá que `LOCK_SESSION` aparece como opción.

**Cambio** — elegí **una** de estas dos, no las dos:

- **(A) Estructural, preferida**: hacé que el evento cargue la evidencia del hold.
  El `GestureEvent` ya tiene `duration_ms`; usalo. `CommandBus` (o el dispatcher)
  rechaza un `HOLD_REQUIRED` cuyo evento de origen no declare un hold suficiente, y
  emite feedback explicando por qué. Cierra el hueco para cualquier acción
  `HOLD_REQUIRED` futura, no solo para el lock.
- **(B) Mínima**: filtrá `_rebind_target_options()` para que las acciones
  `HOLD_REQUIRED` solo se ofrezcan en filas cuyo gesto de origen tenga hold propio
  (los sellos con `NARUTO_SEAL_HOLD_SECONDS`, los de dos manos, Shaka). Más barato,
  pero deja el gate dependiendo de la UI.

Si elegís (B), dejá escrito en `ARCHITECTURE.md` que el gate sigue siendo posicional y
por qué se aceptó.

**Tests**: en `tests/test_settings_ui.py`, que la fila `PINCH_DOWN` no ofrezca
`LOCK_SESSION`; y/o en `tests/test_command_bus.py`, que un `HOLD_REQUIRED` sin
evidencia de hold sea rechazado con `status="REJECTED"` (no `ERROR`) y feedback.

**Commit**: `fix: el rebinding ya no puede evadir el hold de las acciones HOLD_REQUIRED`

---

### H-11 · MEDIO · La pila de redo nunca se invalida

**Archivos**: `src/jarvis/core/undo_redo.py` (~20–57),
`src/jarvis/core/command_history.py` (~67–85), `src/jarvis/main.py` (`_on_command_result`).

**Síntoma**: deshacé un `VolumeUp` (`z`), hacé después una acción nueva y no
relacionada (un zoom), y presioná redo (`y`): re-ejecuta el `VolumeUp` viejo. Todo
sistema de undo/redo invalida la pila de redo al ejecutar una acción nueva; este no.

**Cambio**: al registrar un comando genuinamente nuevo (no originado en un
undo/redo), limpiá `_redo_stack`. El punto natural es
`JarvisApp._on_command_result()`, que ya llama a `CommandHistory.record()`. Necesitás
distinguir un dispatch nuevo de uno originado por undo/redo — un flag en el
controlador durante su propia ejecución alcanza; hacelo explícito, no implícito.

**Tests** en `tests/test_undo_redo.py`: ejecutar → undo → ejecutar otro → redo no hace
nada (y lo reporta); y no-regresión: ejecutar → undo → redo inmediato sigue
funcionando igual que hoy.

**Commit**: `fix: invalidar la pila de redo al ejecutar un comando nuevo`

---

### H-12 · MEDIO · Salir grabando deja el micrófono abierto

**Archivos**: `src/jarvis/main.py` (~749–751, bloque de shutdown de `run()`),
`src/jarvis/voice_capture.py` (~52–78).

**Síntoma**: `v` para grabar y `q` para salir sin volver a apretar `v` deja el
`sounddevice.InputStream` abierto: el micrófono queda tomado más allá de la vida de la
app.

**Cambio**: en el shutdown de `run()`, antes de `self.overlay.close()`, cerrá el
listener de voz si existe y está grabando. Hacelo defensivo (try/except y chequeo de
`None`): el listener es opcional — las dependencias de voz no están instaladas siempre —
y un fallo al cerrar no puede impedir que la app termine.

**Test** en `tests/test_main_shutdown.py` (nuevo): con `VoiceListener` mockeado y
grabando, el shutdown llama a su `stop()`; con el listener en `None`, el shutdown no
lanza.

**Commit**: `fix: cerrar el stream de microfono al salir de la app`

---

## 5. WORKFLOW 3 — Bugs del motor de gestos

**Aviso importante**: este workflow toca `GestureEngine`, el corazón probado del
proyecto. Cada cambio va con su test de regresión de landmarks sintéticos, y la suite
completa tiene que quedar verde. Si un fixture existente empieza a fallar, **el fixture
probablemente tenía razón**: entendé por qué antes de tocarlo.

---

### H-05 · ALTO · El estado de gestos de una mano no se resetea al perder la mano

**[VERIFICADO A MANO]** (`gestures.py:648-650`)

**Síntoma**: sostenés Shaka apuntando a bloquear la sesión, la mano sale un instante de
cuadro (oclusión, borde de la cámara — cosa habitual con webcam), volvés todavía en
Shaka, y `LOCK_SESSION` dispara **al instante**, sin el hold de 1.5s. Lo mismo, en
espejo, para los sellos de Naruto/JJK, el corazón coreano, y el scroll (una
`scroll_baseline` vieja produce un scroll grande e involuntario al reaparecer).

**Causa raíz**: `process()` retorna temprano **antes** de tocar cualquier estado de una
mano:

```python
if not self.active or not hands:
    self.last_primary_landmarks = None
    return None, None, events
```

`lock_start_time`, `_naruto_hold_start`/`_naruto_hold_seal`,
`_korean_heart_hold_start`, `scroll_baseline`, `prev_zoom_y`, `prev_pinky_y`,
`was_pinching`/`was_right_pinching` y `_pinch_streak` conservan sus valores viejos. Con
`lock_start_time` rancio, `now - self.lock_start_time` ya supera el umbral en el primer
cuadro de vuelta.

Es una **asimetría real, no una decisión de diseño**: la ruta de dos manos
(`pause_hold_start`, `close_hold_start`, `_twohand_seal_hold_*`) sí resetea
correctamente cuando `len(hands) != 2`. Nada en `ARCHITECTURE.md` documenta la
diferencia. Y ningún test ejercita el escenario "mano desaparece y reaparece".

**Verificación previa obligatoria** — test que falle primero:

```python
# Shaka sostenido → mano fuera de cuadro > LOCK_HOLD_SECONDS → misma Shaka de vuelta.
# Esperado: NO dispara LOCK_SESSION en el primer cuadro de vuelta. Hoy: dispara.
```

Usá el patrón de fixtures de `tests/test_gesture_engine_regression.py` y su forma de
manipular el tiempo (mirá cómo lo hacen los tests de hold existentes; no metas
`time.sleep` real).

**Cambio**: resetear el estado de una mano dentro de esa rama de salida temprana,
igual que ya hace la ruta de dos manos. Extraé un `_reset_single_hand_state()` y
llamalo ahí — así el conjunto de variables a resetear queda en **un** lugar y un gesto
futuro no se olvida de sumarse.

Ojo con la interacción con `NARUTO_SEAL_MISS_TOLERANCE=3`: esa tolerancia existe para
sobrevivir el parpadeo de clasificación **con la mano presente**. "No hay mano" no es
un parpadeo de clasificación: reseteá de una. Si decidís aplicar la tolerancia también
a cuadros sin mano, justificalo con datos.

**Tests a agregar** en `tests/test_gesture_engine_regression.py` (clase nueva, p. ej.
`HandLossStateResetTests`):

- Shaka → sin manos por más que el hold → Shaka: no dispara `LOCK_SESSION` en el primer
  cuadro de vuelta; sí dispara si se completa un hold nuevo entero.
- Lo mismo para un sello de una mano (elegí uno, p. ej. `NARUTO_TORA`) y para
  `KOREAN_HEART`.
- Forma de scroll → sin manos → misma forma: la baseline se recaptura y no hay evento
  de scroll espurio en el primer cuadro.
- Pausa (`active=False`) en medio de un hold → reanudar: el hold arranca de cero.
- No-regresión: un hold continuo normal sigue disparando igual que hoy.

**Commit**: `fix: resetear el estado de gestos de una mano cuando la mano sale de cuadro`

---

### H-06 · MEDIO · "Pinch fantasma" del anular se come el volumen

**Archivos**: `src/jarvis/gestures.py` (~689–767, resolución de `pinch_winner`),
`src/jarvis/config.py` (constantes `PINCH_*`).

**Síntoma**: en un gesto de volumen (pulgar+meñique), a veces no pasa nada: el evento
`VOLUME_UP`/`VOLUME_DOWN` se pierde en algunos cuadros.

**Causa raíz**: el umbral con el que el anular **compite** por `pinch_winner` es
`max(PINCH_SCREENSHOT, PINCH_ZOOM) = 25`, pero el anular solo **dispara** algo con
`d_thumb_ring < 20` (captura, con los dedos recogidos) o `< 25` con el índice extendido
(zoom). En la banda 20–25px sin índice extendido, el anular puede ganar la competencia
—por tener simplemente la distancia más chica que el meñique, cuyo umbral es 28— y
**no disparar nada**, suprimiendo el evento legítimo del meñique en ese cuadro.

Ejemplo numérico verificado: `d_thumb_ring=20.5`, `d_thumb_pinky=21.0` → ambos
"activos", gana el anular, ni captura (necesita <20) ni zoom (necesita índice
extendido) se cumplen → cero eventos en ese cuadro.

Es una colisión nueva, distinta de las dos ya documentadas en `ARCHITECTURE.md`.

**Verificación previa obligatoria**: fixture sintético con esas distancias, confirmando
que hoy no sale ningún evento y que el gesto de volumen sí debería salir.

**Cambio**: que el anular compita solo con el umbral **realmente alcanzable** para la
pose actual — `PINCH_SCREENSHOT` cuando el índice está recogido, `PINCH_ZOOM` solo
cuando está extendido — en vez del `max()` a ciegas. Principio general: una familia de
pinch no puede ganar la prioridad con un umbral más laxo que el que necesita para
disparar.

Revisá si el mismo razonamiento aplica a otra familia (el mecanismo del `max()` puede
estar repetido). Si aplica, arreglá las dos en el mismo commit y decilo.

**Tests** en `tests/test_gesture_engine_regression.py`: el caso de la banda 20–25px con
índice recogido produce el evento de volumen; captura y zoom siguen disparando en sus
condiciones propias (no-regresión); ningún cuadro produce dos familias de pinch a la vez.

**Commit**: `fix: el anular ya no gana prioridad de pinch con un umbral que no puede disparar`

---

### H-07 · BAJO · Comentario de umbral cita el dedo equivocado

**Archivo**: `src/jarvis/config.py` (~92, `JJK_SUKUNA_RELEASE_THRESHOLD`).

El comentario justifica los 55px citando el ruido de mano relajada del **meñique**
(~51px), pero el `ImpulseDetector` de Sukuna se alimenta de `d_thumb_middle` — dedo
**medio**, cuyo ruido medido está documentado en el mismo archivo como ~19.2px. El
umbral sigue siendo seguro; lo que está mal es la justificación, y puede engañar a un
re-tuneo futuro haciéndole creer que el margen es más chico de lo que es.

**Cambio**: corregir el comentario para citar la medición del dedo medio. Sin cambio
funcional. **No toques el valor** sin datos de cámara real (ver V-05).

**Commit**: `docs: corregir la medicion citada en el umbral de release de Sukuna`

---

### H-08 · ESTILO · Recomputación redundante por cuadro

**Archivo**: `src/jarvis/gestures.py` (~331–333, `filter_plausible_hands`).

`_bbox_area_fraction()` se calcula dos veces por mano (una para filtrar, otra como
clave de ordenamiento). Con `MAX_HANDS=2` el costo es despreciable. Hacelo en una sola
pasada solo si estás tocando esa función por otra razón; **no** abras un commit propio
para esto.

---

## 6. WORKFLOW 4 — Empaquetado y assets

**Objetivo**: que el `.exe` portable se comporte como el modo desarrollo.

---

### H-13 · ALTO · En el `.exe` onefile los assets se pierden en cada arranque

**[VERIFICADO A MANO]** (`paths.py:12-16`)

**Síntoma**: el `.exe` regenera los 30+ iconos de gestos en **cada** arranque (arranque
más lento sin razón), y cualquier archivo que la app descargue en runtime se pierde al
cerrar. Para el control por voz esto sería fatal: el modelo LLM de ~1GB se
re-descargaría cada vez. Hoy no explota porque la voz no está empaquetada en el `.exe`
— pero es una bomba de tiempo para el día que sí lo esté.

**Causa raíz**:

```python
def assets_dir():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"
```

`sys._MEIPASS` en un build **onefile** es un directorio temporal que PyInstaller
extrae de nuevo en cada lanzamiento y limpia al salir. Sirve perfecto para leer
assets **empaquetados** (el `hand_landmarker.task`, que sí va dentro del bundle) y es
el lugar equivocado para **escribir** cualquier cosa que deba persistir.

**Cambio**: separá los dos conceptos, que hoy están fusionados en una función:

- `bundled_assets_dir()` → `_MEIPASS` cuando está congelado (solo lectura: modelos
  empaquetados).
- `writable_assets_dir()` → un directorio del usuario que persiste, del mismo orden que
  el que ya usa `config_store.py` (`~/.jarvis-gesture-hud/`), tanto congelado como en
  desarrollo.

Los lectores de assets empaquetados usan la primera; los que **generan o descargan**
(iconos, modelo LLM, modelos descargados en runtime) usan la segunda. En desarrollo,
mantené el comportamiento actual (`assets/` junto al repo) para no romper el flujo de
trabajo ni los tests — o, si unificás, actualizá `.gitignore` y decilo en el commit.

**Cuidado**: `assets_dir()` tiene varios llamadores (`hand_tracker`, `pose_tracker`,
`llm_intent`, `gesture_icons`). Grepealos todos y clasificá cada uno como lector-de-
bundle o escritor **antes** de cambiar nada. Un llamador mal clasificado rompe el
arranque.

**Tests** en `tests/test_paths.py` (nuevo o existente): con `sys.frozen`/`sys._MEIPASS`
simulados, la ruta de bundle apunta a `_MEIPASS` y la escribible **no**; en
desarrollo, ambas resuelven como hoy.

**Verificación adicional**: build real del `.exe` y confirmar que el segundo arranque
no regenera iconos (medí el tiempo de arranque o mirá el log).

**Commit**: `fix: separar assets empaquetados de assets escribibles para el exe portable`

---

### H-14 + H-15 + H-16 + H-17 · Robustez de la generación de iconos

**Archivos**: `src/jarvis/gesture_icons.py` (`ensure_icon`, `generate_all_icons`),
`build/jarvis.spec`.

Un solo commit para los cuatro:

- **H-14 (MEDIO)**: `ensure_icon()` no maneja errores alrededor de `mkdir()`/`save()`.
  Un fallo de escritura (permisos, disco lleno, directorio de solo lectura) crashea el
  arranque, porque `JarvisApp.__init__` → `build_legend_entries()` lo llama sin red.
  **Cambio**: try/except; ante fallo, log y degradación elegante (entrada de leyenda sin
  icono). La leyenda es una ayuda visual: nunca puede impedir arrancar.
- **H-15 (MEDIO)**: la escritura no es atómica (`exists()` y después `Image.save(path)`
  directo al destino). Dos procesos, o un `save()` interrumpido, dejan un PNG parcial
  cacheado para siempre. **Cambio**: temp + `os.replace()`, el mismo patrón de
  `config_store.py`. Consistencia interna: el proyecto ya tiene el patrón correcto en
  otro módulo.
- **H-16 (BAJO)**: `jarvis.spec` no pre-genera ni empaqueta los iconos. Con H-13
  resuelto es menos grave, pero pre-generarlos en el build ahorra el trabajo en el
  primer arranque. Opcional: hacelo solo si H-13 quedó cerrado.
- **H-17 (BAJO)**: `generate_all_icons()` no se usa fuera de los tests. Si H-16 la
  aprovecha, dejala y documentá el uso. Si no, borrala o marcala explícitamente como
  utilitaria de build/test.

**Tests**: `ensure_icon()` con `save` mockeado para lanzar → no propaga y devuelve algo
usable; una escritura interrumpida no deja el archivo final (mismo estilo de test que
H-03).

**Commit**: `fix: generacion de iconos atomica y tolerante a fallos de escritura`

---

## 7. WORKFLOW 5 — CI/CD, dependencias y limpieza

---

### H-18 · ALTO · Se puede publicar un release sin tests verdes

**Archivos**: `.github/workflows/release.yml`, `.github/workflows/ci.yml`.

Ambos workflows disparan en push a `main` de forma **independiente**, sin gate entre
ellos. `release.yml` puede calcular la versión, taggear, publicar el GitHub Release y
adjuntar binarios mientras `ci.yml` todavía corre — o incluso si `ci.yml` falla.

**Cambio**: que el release dependa de los tests. Dos formas: correr la suite como job
previo dentro de `release.yml` con `needs:`, o usar `workflow_run` para que el release
se dispare solo al completarse CI con éxito. Preferí la primera (una sola fuente de
verdad, menos indirección).

**Verificación**: `act` local si está disponible, o un push a una rama de prueba con el
trigger temporalmente ampliado. **No pruebes esto en `main`** — publicaría un release.

**Commit**: `ci: exigir la suite de tests en verde antes de publicar un release`

---

### H-19 · MEDIO · `requirements.txt` sin ningún pin

**Archivos**: `requirements.txt`, `requirements-voice.txt`.

`requirements.txt` lista nombres desnudos (`opencv-python`, `mediapipe`, `pyautogui`,
`numpy`, `pyttsx3`, `Pillow`). Este proyecto **ya se rompió** exactamente así:
`mediapipe` 0.10.30 eliminó la API `mp.solutions` de los wheels de Windows y obligó a
reescribir `hand_tracker.py` sobre la Tasks API. Nada impide que el próximo `pip
install -r requirements.txt` traiga una versión que vuelva a romper — ni que el `.exe`
portable se construya con dependencias transitivas distintas en cada build.

**Cambio**: pineá con techo compatible (`mediapipe>=0.10.35,<0.11`, y el equivalente
para el resto), usando **las versiones que hoy están instaladas y verificadas** en el
entorno de desarrollo. Sacalas de `pip freeze` del venv del proyecto — no inventes
números. Anotá arriba del archivo por qué existe el techo (una línea, citando el caso
`mp.solutions`).

Para `requirements-voice.txt`, mantené los pisos `>=` que ya tiene y agregá techos con
el mismo criterio. Conservá intacto el bloque de notas sobre `MAX_PATH` de Windows: es
información ganada con dolor.

**Verificación**: `pip install -r requirements.txt` en un venv limpio + suite completa
verde con esas versiones exactas.

**Commit**: `build: pinear dependencias con techo compatible`

---

### H-20 · BAJO · Sin cache de pip en CI

Agregá `cache: 'pip'` a `actions/setup-python` en ambos workflows. `mediapipe` y
`opencv-python` son pesados y hoy se reinstalan desde cero en cada corrida y cada leg
de la matriz. Aprovechá para verificar que las acciones estén pineadas por versión
(`actions/checkout@v4`, no `@main`).

**Commit**: `ci: cachear dependencias de pip`

---

### H-21 · ESTILO · `os.system()` en las ramas de macOS/Linux

**Archivo**: `src/jarvis/os_native.py` (~24–29).

`lock_session()` usa `os.system()` con strings de comando hardcodeados. **No es una
vulnerabilidad**: ningún input del usuario llega ahí, verificado. Pero `os.system()`
pasa por el shell, no da control de errores y no permite distinguir "el comando no
existe" de "el comando falló" — que es justamente lo que la cadena de fallback de Linux
(`xdg-screensaver || gnome-screensaver-command || loginctl`) necesita saber.

**Cambio**: migrar a `subprocess.run([...])` con lista de argumentos y `shell=False`,
manejando la cadena de fallback en Python (probar cada uno, mirar el código de retorno)
en vez de delegarla al `||` del shell. Beneficio real: en Linux la app puede reportar
"no encontré ningún mecanismo de bloqueo" en vez de fallar en silencio.

**Cuidado**: no hay máquina macOS/Linux para probar esto. Testeá con `subprocess.run`
mockeado por plataforma, igual que hace hoy `tests/test_os_native.py`, y **no** cambies
qué comandos se ejecutan — solo cómo se invocan. Marcá en el commit que la ruta
macOS/Linux queda verificada solo por test con mock.

**Commit**: `refactor: invocar los comandos de bloqueo por subprocess en vez de os.system`

---

### H-22 · BAJO · `_frames` sin sincronización explícita

**Archivo**: `src/jarvis/voice_capture.py` (~63–64 vs 71–77).

El callback de audio de `sounddevice` (hilo propio de la librería) hace `append` a
`self._frames` mientras el hilo de transcripción lo lee/vacía. El `append`/`list` de
CPython es atómico por el GIL, así que en la práctica no corrompe — pero el patrón es
frágil y depende de un detalle de implementación del intérprete.

**Cambio**: usá una `queue.Queue` (el mismo mecanismo que el resto del proyecto ya usa
para cruzar hilos) o un `threading.Lock` explícito. Documentá cuál y por qué.

**Commit**: `refactor: sincronizar explicitamente el buffer de audio entre hilos`

---

### H-23 · ESTILO · Nombre de archivo temporal fijo en la escritura atómica

**Archivo**: `src/jarvis/core/config_store.py` (~52–55).

La escritura atómica usa un nombre de temporal fijo. Dos instancias de Jarvis
escribiendo a la vez se pisarían el temporal. Escenario poco probable (una sola app de
escritorio), arreglo trivial: incluí el PID o usá `tempfile.mkstemp()` en el mismo
directorio. Agrupalo con otro commit de `config_store.py` si toca; no abras uno propio.

---

### H-24 · BAJO · `_dispatch_naruto_seal()` ya no despacha solo sellos

**Archivo**: `src/jarvis/main.py` (~634).

Desde la Fase 8 resuelve el binding de **todo** evento que la app puede producir (37+),
no solo los sellos de Naruto. El nombre se conservó a propósito por compatibilidad con
los tests existentes. Ahora que hay una tanda de trabajo abierta, es el momento de
renombrarlo a algo honesto (`_dispatch_bound_event` o `_resolve_and_dispatch`).

**Cambio**: renombrar, actualizar todos los llamadores y los tests que lo invocan por
nombre, y **dejar un alias** `_dispatch_naruto_seal = _dispatch_bound_event` si algún
test de terceros o script manual lo usa (grepealo antes: `tests/`, `openspec/`,
`ARCHITECTURE.md`). Commit `refactor:`, sin cambio de comportamiento — la suite
completa tiene que quedar idéntica.

**Commit**: `refactor: renombrar _dispatch_naruto_seal a lo que realmente hace`

---

### H-25 · BAJO · Documentación con conteos de tests viejos

**Archivos**: `ARCHITECTURE.md`, `README.md`.

Ambos citan conteos históricos (422/441/496 según la sección) cuando hoy son 594. Los
números por fase **dentro de la sección Status son historia legítima** y no hay que
reescribirlos; lo que hay que corregir son las afirmaciones en presente: la sección
Development de `ARCHITECTURE.md` ("422 tests") y la línea final de `README.md`
("422 tests").

Dos afirmaciones que además ya son **falsas**, encontradas en esta auditoría:

- `ARCHITECTURE.md` dice que `Intent` "no se construye en ningún punto del pipeline
  vivo" (`core/intents.py` y la entrada de Decisions correspondiente). Es falso desde
  que se cableó la voz: `core/voice_intent_resolver.py` y `llm_intent.py` **ambos**
  construyen `Intent` y esos objetos llegan al despacho real. Corregí las dos
  ubicaciones.
- `core/profiles.py` (~línea 49) tiene un comentario que remite a
  `main.py._dispatch_gesture_event()`, un método que **no existe** (el real se llama
  `_dispatch_naruto_seal`). Si H-24 ya renombró el método, este comentario queda
  correcto por accidente: verificá cuál de los dos nombres quedó y dejá el comentario
  apuntando al real.

Hacelo **al final de todos los workflows**, en un commit `docs:` único, junto con las
entradas nuevas de "Decisions & rationale" de todo lo que se arregló. Así el número
queda correcto una sola vez.

**Commit**: `docs: actualizar estado, conteo de tests y decisiones de la ronda de endurecimiento`

---

## 8. WORKFLOW 6 — Verificación en cámara real (REQUIERE A JOSÉ)

**Esto no lo puede hacer un modelo solo.** Necesita a José frente a la cámara haciendo
gestos, capturando landmarks reales y midiendo. Va **después** de los workflows 1–5,
para no mezclar "arreglar bugs de código" con "corregir umbrales contra datos reales".

**Protocolo establecido** (el que funcionó en la Fase 4, 2026-08-27 — seguilo, no
improvises):

1. Un gesto por vez. Nunca varios en la misma sesión sin cerrar el anterior.
2. Loguear landmarks crudos: deltas tip/pip por dedo y las distancias derivadas. Medir,
   no adivinar.
3. Comparar contra los umbrales **actuales** de `gestures.py`/`config.py` — releelos
   primero, cambiaron desde la última sesión.
4. Verificación de N segundos con pausas, para distinguir "no dispara" de "dispara
   intermitente".
5. Cada umbral que se cambie queda documentado con el número medido y la fecha.

| ID | Qué verificar | Por qué está pendiente |
|---|---|---|
| V-01 | Los 8 sellos Naruto de una mano (Tora, Ushi, U, Uma, Hitsuji, Saru, Inu, I) | José reportó "ningún sello se reconoce bien" en uso real. Uma/Saru/Inu se redefinieron por 3ª vez y **nunca se re-verificaron en vivo** después de esa redefinición; Ushi y U nunca se probaron limpiamente |
| V-02 | Los 5 sellos de dos manos (Ne, Mi, Tori, Kai, Tatsu) | **Los 5 umbrales son razonados, no medidos.** Nunca vieron una cámara. Dado que 7 de 8 sellos de una mano necesitaron corrección real pese a pasar la verificación sintética, tratalos como primer borrador |
| V-03 | JJK (Gojo, Sukuna, Megumi) + Clap + corazón coreano | Fases 6 y 7 se implementaron con verificación sintética únicamente, por decisión explícita de José ("las verificaciones las hacemos en la fase final") |
| V-04 | `EMA_ALPHA = 0.25` (bajado de 0.35 el 2026-08-30) | Cambiado por el reporte "mouse muy impreciso", **razonado, no medido**. Confirmar que mejora la precisión percibida o revertir |
| V-05 | Colisión Sukuna ↔ `RIGHT_CLICK` | Declarada conocida y **deliberadamente no resuelta** en el código: el contacto de Sukuna (15px) es más ajustado que el de `RIGHT_CLICK` (20px), así que un snap real cruza primero el umbral del click derecho. Solo un snap humano real puede decidir el arreglo |
| V-06 | Colisión residual con Shaka/Screenshot | Se arregló el caso específico pinch-click vs Shaka (falta de chequeo de distancia pulgar-índice). El "todo dispara screenshot" que queda es **hipótesis sin confirmar**: `SCREENSHOT` es la acción default de 3 sellos distintos (`NARUTO_TORA`, `JJK_SUKUNA`, `KOREAN_HEART`), así que puede ser síntoma de V-01 y no causa propia. Se resuelve **después** de V-01 |
| V-07 | El `.exe` portable en una máquina sin Python | Se buildeó y probó solo en la máquina de desarrollo, que tiene Python instalado. Necesita otra máquina física o virtual |

**Orden recomendado**: V-01 primero (es el bloqueante y el que puede explicar V-06),
después V-03 y V-04 (rápidos, una sesión), después V-02 (el más largo: 5 gestos de dos
manos con umbrales sin medir), y V-05/V-06 al final con los datos de los anteriores.
V-07 es independiente y puede ir cuando haya máquina.

---

## 9. WORKFLOW 7 — Unificar la arquitectura: qué se cablea y qué queda como PoC

**Contexto**: `src/jarvis/core/` tiene **16 módulos que ningún código de producción
importa** — solo sus propios tests. Se construyeron para tachar tareas de un checklist
de OpenSpec cuyo `spec.md` asumía otra arquitectura (un clasificador que emite varios
gestos candidatos con confianza por cuadro; `GestureEngine` es un detector booleano de
umbrales). Verificado con grep de referencias reales desde `src/`, no con la doc.

**Decisión tomada** (Opus, 2026-09-04), con el criterio: *se cablea solo lo que el
código de producción ya reimplementó a mano, porque ahí la abstracción demostró que
hacía falta.* Todo lo demás queda como prueba de concepto, declarado como tal — no se
borra, pero deja de ser ambiguo.

| Módulo | Decisión | Razón |
|---|---|---|
| `cooldown.py` | **CABLEAR** (A-01) | `GestureEngine` tiene 5 timers `last_*_time` ad hoc dispersos; esa dispersión ya produjo un bug real (el cooldown compartido entre `PINCH_DOWN` y `RIGHT_CLICK` que se comía clicks legítimos) |
| `debounce.py` | **CABLEAR** (A-02) | `PINCH_CONFIRM_FRAMES` es debounce hecho a mano, y `NARUTO_SEAL_MISS_TOLERANCE` es su espejo (histéresis). Dos reimplementaciones manuales del mismo concepto |
| `contextual_bindings.py` | **CABLEAR** (A-03) | `ForegroundApplicationTracker` ya está vivo y cacheado; falta solo consumirlo. Habilita una feature real ("este gesto significa otra cosa en Photoshop") sin cambiar ningún gesto |
| `context.py` | **PoC** | `resolve_contextual_intent()` toma strings, no un `Context`. Construir el dataclass sería ceremonia sin función — el mismo anti-patrón que el proyecto ya rechazó para `Intent` |
| `gesture_state_machine.py`, `conflict_resolver.py` | **PoC** | Asumen un clasificador con candidatos y confianza que no existe ni está planeado. Sin entrada real que consumir |
| `input_provider.py` + los 3 providers | **PoC** | Abstracción para una reescritura del loop que nadie pidió. La convergencia real (cámara/teclado/voz → misma acción) **ya está lograda** vía `Command`/`CommandBus` |
| `intent_resolution.py` | **PoC** | Duplica el mapeo acción→`Command` que `main.py._dispatch()` ya hace y que funciona |
| `hud_state_machine.py` | **PoC** | Segundo modelo de HUD; el simple (`overlay.py`/`legend.py`) está vivo. Dos modelos conviviendo es peor que uno |
| `double_click.py`, `swipe.py`, `dwell.py` | **CABLEAR** (workflow 8, §10) | Decisión revisada por José: son features que faltan en la arquitectura. El doble click no es un extra — **hoy no se puede abrir un archivo del escritorio con gestos**, que es un agujero funcional, no una comodidad |
| `undo_feedback.py` | **PoC (superado)** | `main.py._trigger_undo()` ya lo hace **mejor**: etiquetas en español por burbuja del overlay, contra el `"UNDO VolumeUp: OK"` en inglés dibujado sobre el frame de cámara que ofrece este módulo. Cablearlo sería un retroceso de UX |

**Orden**: este workflow va **después de los workflows 1–5** (A-01/A-02 tocan
`GestureEngine`, A-03 toca la misma región de `main.py` que H-09 y H-24). Es
independiente del workflow 6 (cámara).

**Regla que aplica a los tres cableados**: son refactors **sin cambio de
comportamiento**. El criterio de aceptación es que la suite completa quede verde **sin
tocar un solo test existente**. Si un test existente falla, tu refactor cambió
comportamiento: revertí y entendé qué.

---

### A-01 · Consolidar los cooldowns ad hoc en `CooldownRegistry`

**Archivos**: `src/jarvis/gestures.py` (~375–379 el estado, ~730–743 y ~917–939 los
usos), `src/jarvis/core/cooldown.py`, `src/jarvis/config.py` (~46–50).

**Situación actual**: 5 campos de estado (`last_click_time`, `last_right_click_time`,
`last_screenshot_time`, `last_toggle_time`, `last_silence_time`) con 5 constantes
(`CLICK_COOLDOWN=0.3`, `RIGHT_CLICK_COOLDOWN=0.4`, `KEYBOARD_TOGGLE_COOLDOWN=1.0`,
`SCREENSHOT_COOLDOWN=1.5`, `SILENCE_COOLDOWN=0.8`) y el patrón
`if now - self.last_X_time > config.X_COOLDOWN:` repetido en cada rama.

**Cambio**: una sola `CooldownRegistry` en `GestureEngine.__init__`, registrando cada
acción con **exactamente** su valor actual, y reemplazar cada chequeo por
`self.cooldowns.try_fire("<accion>")`.

**Cuatro trampas concretas, verificadas leyendo `cooldown.py` — no las descubras a
golpes**:

1. **`CooldownRegistry` usa `time.monotonic` por defecto; `GestureEngine` usa
   `time.time()`** (el `now` de `process()`). Pasá `clock=time.time` al construirla,
   para preservar la semántica exacta y para que los tests que hoy manipulan el tiempo
   sigan funcionando igual. `monotonic` sería *mejor* (inmune a cambios de reloj del
   sistema), pero eso es un cambio de comportamiento: anotalo como follow-up, **no lo
   metas de contrabando** en este refactor.
2. **`try_fire()` chequea Y registra en la misma llamada.** Llamala **solo en el punto
   donde el evento realmente se dispara**, nunca como pre-chequeo de una rama que
   después podría no disparar — si no, el cooldown queda armado por un evento que nunca
   ocurrió. Revisá cada uno de los 5 usos: hoy algunos chequean primero y registran
   después de decidir.
3. **Diferencia de borde `>` vs `>=`**: el código actual dispara con
   `now - last > COOLDOWN` (estricto); `try_fire()` bloquea con `< cooldown`, o sea
   dispara con `>=`. En el instante exacto de igualdad el comportamiento difiere. Es
   irrelevante en la práctica, pero si un test pinea el borde exacto, esa es la causa —
   no ajustes el test sin entenderlo.
4. **`try_fire()` con una acción no registrada nunca bloquea** (devuelve `True`
   siempre). Un typo en el nombre de la acción no falla ruidosamente: **desactiva el
   cooldown en silencio**. Definí los 5 nombres como constantes de módulo y usá esas
   constantes en los dos lados, nunca strings literales sueltos.

**Tests a agregar** en `tests/test_gestures_cooldowns.py` (nuevo): cada una de las 5
acciones respeta su duración propia (una no bloquea a otra — regresión explícita del
bug histórico del cooldown compartido); un nombre de acción no registrado se detecta
(test que recorra las constantes y confirme que todas están registradas en el registro).

**Criterio de aceptación**: los 594 tests existentes verdes **sin modificar ninguno**.
`GestureEngine` no tiene más campos `last_*_time`.

**Commit**: `refactor: consolidar los cooldowns de gestos en CooldownRegistry`

---

### A-02 · Unificar el debounce y la tolerancia de fallos

**Archivos**: `src/jarvis/gestures.py` (~385, 697–708 el streak de pinch; ~399/403,
860–878 y ~613–619 la tolerancia de fallos), `src/jarvis/core/debounce.py`,
`src/jarvis/config.py` (~32, ~75).

**Situación actual**: dos mecanismos hechos a mano que son la misma idea vista desde
los dos lados.

- `self._pinch_streak = {"index": 0, "middle": 0, "ring": 0, "pinky": 0}` con
  `min(count+1, PINCH_CONFIRM_FRAMES)` → "no dispares antes de N cuadros consecutivos".
- `self._naruto_miss_streak` y `self._twohand_seal_miss_streak` con
  `NARUTO_SEAL_MISS_TOLERANCE=3` → "no tires el progreso de un hold por N cuadros de
  parpadeo".

**Cambio, en dos partes — y la segunda parte es honestidad sobre los límites del módulo
existente**:

1. **El streak de pinch encaja exacto** en `ConsecutiveFrameDebouncer`: es
   level-triggered y se resetea con `None` o con una clave distinta, igual que el
   código a mano. Usá **una instancia por dedo** (4 instancias, un dict
   `{"index": ConsecutiveFrameDebouncer(config.PINCH_CONFIRM_FRAMES), ...}`), llamando
   `observe(nombre_del_dedo)` cuando ese dedo está bajo su umbral y `observe(None)`
   cuando no. **No** intentes meter los 4 dedos en un solo debouncer: `observe()`
   resetea la racha cuando cambia la clave, así que un solo objeto haría que los dedos
   se pisen entre sí.
2. **La tolerancia de fallos NO encaja** en `ConsecutiveFrameDebouncer`: ese módulo
   cuenta *aciertos consecutivos para conceder*, y acá hace falta contar *fallos
   consecutivos para no revocar*. Son semánticas inversas. En vez de forzarlo (que es
   como se rompen los refactors), **agregá una clase hermana en el mismo
   `debounce.py`** — p. ej. `MissToleranceCounter(tolerance)` con
   `observe(matched) -> bool` ("¿sigue vivo el progreso?") — y usala en los dos lugares
   que hoy llevan el contador a mano. El objetivo del workflow es que los dos
   mecanismos vivan juntos y con nombre, no que uno se disfrace del otro.

**Cuidado con la interacción con H-05**: si H-05 ya está hecho, el reset de estado al
perder la mano tiene que resetear también estos objetos nuevos
(`debouncer.reset()` / el contador de tolerancia). Agregalos al
`_reset_single_hand_state()` que H-05 creó. Si H-05 no está hecho todavía, **hacelo
primero**: este refactor sin ese reset empeora el bug.

**Tests a agregar** en `tests/test_debounce.py` (extender) y
`tests/test_gesture_engine_regression.py`: `MissToleranceCounter` con sus casos de
borde (0 fallos, exactamente `tolerance` fallos, `tolerance+1`); los 4 dedos mantienen
rachas independientes (un pinch de índice no acredita cuadros al del medio); un hold de
sello sobrevive 3 cuadros de parpadeo y muere al 4º (comportamiento actual, pineado).

**Criterio de aceptación**: los 594 existentes verdes sin modificar ninguno.
`gestures.py` no tiene más contadores de racha a mano.

**Commit**: `refactor: unificar debounce y tolerancia de fallos en jarvis.core.debounce`

---

### A-03 · Cablear bindings por aplicación (`contextual_bindings.py`)

**Archivos**: `src/jarvis/main.py` (la resolución de binding en
`_dispatch_naruto_seal`/`_dispatch_bound_event` tras H-24),
`src/jarvis/core/contextual_bindings.py`, `src/jarvis/core/profiles.py`
(`Profile.context_rules`, que ya existe y está validado pero nadie lee).

**Qué habilita**: que un mismo gesto haga cosas distintas según la app en foco, sin
cambiar ningún gesto. `ForegroundApplicationTracker` **ya está vivo** en el loop
(cacheado, `cache_ttl=0.5`, alimentando telemetría), así que la pieza que falta es solo
consumir su salida.

**La función a usar ya existe y es pura**:

```python
resolve_contextual_intent(gesture_type, active_application, bindings_by_app, global_bindings=None)
# bindings_by_app: {app: {gesture_type: intent_name}}   ← esto es Profile.context_rules
# devuelve el nombre de acción, o None; nunca lanza
```

**Cambio**: en el punto único donde hoy se resuelve el binding, la precedencia pasa a
ser, explícitamente y en este orden:

1. regla por aplicación del perfil activo (`profile.context_rules[app][event]`)
2. override del perfil (`profile.gesture_bindings[event]`)
3. default global (`GESTURE_DEFAULT_BINDINGS[event]`)
4. identidad (el propio nombre del evento)

**Preservación de comportamiento, que es lo que hace este cambio seguro**:
`context_rules` arranca **vacío** en todos los perfiles, y con el dict vacío
`resolve_contextual_intent()` devuelve `None` y cae al paso 2 — o sea, comportamiento
byte-idéntico al actual mientras nadie defina una regla. Documentalo así en el commit.

**Trampas**:

- `Profile.context_rules` **no se persiste** hoy (`config_store` guarda solo
  `gesture_bindings`/`custom_shortcuts`/`macros`, a propósito). No lo agregues al
  esquema en esta tarea: dejá el cableado de resolución primero, y persistencia + UI
  como tarea aparte (ver A-03b). Un cambio de esquema arrastra migración y versionado.
- El nombre de app que devuelve `ForegroundApplicationTracker` es el **título de la
  ventana en crudo**, dependiente del SO y de la app; no es un identificador estable.
  No inventes normalización sofisticada: hacé el match como esté documentado en
  `context_tracker.py` y dejá escrito que el matcheo es literal, para que quien defina
  reglas sepa contra qué.
- Sigue valiendo lo de H-10: una regla por app **no puede** habilitar una acción
  `HOLD_REQUIRED` sobre un gesto sin hold. Si H-10 se resolvió por la vía (A)
  estructural, esto ya está cubierto; si se resolvió por la vía (B) de UI, agregá el
  mismo filtro acá.

**Tests a agregar** en `tests/test_naruto_seal_dispatch.py` o archivo nuevo
`tests/test_contextual_dispatch.py`: sin reglas, la resolución es idéntica a la actual
(no-regresión, el test más importante); con una regla para la app en foco, gana la
regla; con una regla para **otra** app, no aplica; con el tracker devolviendo `None`
(sin app detectada), cae al comportamiento global; una regla que apunta a una macro o a
un atajo custom también funciona (pasa por el mismo `_dispatch_macro_or_shortcut`).

**Commit**: `feat: bindings de gestos por aplicacion en foco`

---

### A-03b · (Opcional, solo si A-03 quedó cerrado) Persistir y editar las reglas por app

Extender el esquema de `config_store` a `context_rules` (subiendo `SCHEMA_VERSION` y
manejando la lectura de un archivo v1 sin ese campo) y agregar a `SettingsWindow` una
sección para definir "app + gesto → acción". Tarea de producto, no de deuda: hacela
solo si José la pide. Si la hacés, la validación de tipos de H-02 tiene que cubrir el
campo nuevo.

---

### B-01 · Declarar el conjunto PoC de forma explícita y verificable

**Problema**: hoy "qué está vivo y qué no" solo se puede saber grepeando referencias.
Eso ya costó tiempo en esta auditoría, y la documentación se desincronizó en silencio
(ver los dos casos de doc obsoleta en H-25). El proyecto **ya resolvió esta misma clase
de problema** con `tests/test_architecture_boundaries.py`, que pinea con un test qué
módulos pueden ramificar en `platform.system()`. Aplicá el mismo patrón.

**Cambio**:

1. Un test nuevo (`tests/test_poc_modules.py`) con la lista explícita de módulos PoC de
   la tabla de arriba, que falle si alguno **empieza** a ser importado desde
   `src/jarvis/` fuera de `core/` (o desde `main.py`) sin actualizar la lista. Es el
   inverso del test de boundaries: pinea lo que **no** debe estar cableado, para que
   cablear algo sea una decisión consciente y no un accidente.
2. Un encabezado uniforme de una línea al inicio del docstring de cada módulo PoC:
   `PoC / no cableado (ver openspec/changes/hardening-and-polish/WORKPLAN.md §9).`
   Los docstrings ya explican el "por qué no" caso por caso — no los reescribas, solo
   agregá el marcador para que sea grepeable.
3. Una tabla en `ARCHITECTURE.md` (sección nueva "Dormant / PoC modules") con las mismas
   dos columnas de la tabla de §9: módulo y decisión. Es la respuesta a "qué de esto
   está vivo" sin tener que grepear.

**Criterio de aceptación**: `grep -rn "PoC / no cableado" src/` lista exactamente los
módulos de la tabla; el test nuevo falla si se importa uno desde código vivo.

**Commit**: `test: pinear el conjunto de modulos PoC no cableados`

---

## 10. WORKFLOW 8 — Gestos que faltan: dwell, doble click y swipe

**Contexto y por qué se hace**: los tres detectores existen, están testeados y no están
cableados. La justificación original era "ninguna acción de esta app mapea a esto" —
cierta cuando se escribió, pero circular: no hay acción porque no hay gesto y no hay
gesto porque no hay acción. José cortó el círculo. El doble click además tapa un agujero
funcional real: **sin él no se puede abrir un archivo ni una carpeta con gestos.**

**Orden**: después del workflow 7 (C-02 toca los cooldowns que A-01 consolida; hacerlo
antes obliga a tocar dos veces el mismo código). Cada gesto termina en el workflow 6 con
verificación en cámara — sin eso, este workflow no está cerrado, solo escrito.

**Lo que aplica a los tres, y este proyecto ya aprendió a golpes**: un gesto nuevo no
es solo un detector. Es censo de colisiones contra las **17 comprobaciones de una mano
× 2 manos + 4 de dos manos** que ya existen, entrada en `legend.ENTRIES` (con su 3er
elemento de icono), entrada en `ICON_SPECS`, snapshot de `tests/test_legend.py`
regenerado, entrada en `GESTURE_DEFAULT_BINDINGS` para que sea reasignable desde el
settings, y su fila en `_CLASSIC_EVENT_ICON_KEYS` si comparte icono. Si te salteás uno,
la suite te lo dice — pero mejor tenerlo presente desde el principio.

---

### C-01 · Dwell-click: click sin pinch (el de mayor valor real)

**Módulo**: `src/jarvis/core/dwell.py` — ya trae `DwellDetector.update(x, y,
confidence, min_confidence) -> progress` **y** `draw_dwell_progress(frame, center,
progress)`, un anillo de progreso en cv2 ya implementado. No hay que escribir ni el
detector ni el feedback visual.

**Por qué este primero**: ataca directamente un dolor que José reportó en uso real —
que el pinch de click se confunde con Shaka y que el puntero es impreciso. Dwell
significa "apuntá y quedate quieto": no necesita ninguna forma de mano nueva, así que
**no agrega superficie de colisión de poses**. Es la mejor relación valor/riesgo de los
tres.

**Diseño**:

- Apuntar el detector al índice en coordenadas **normalizadas** (el módulo trabaja en
  ese espacio: `DEFAULT_MAX_TARGET_DISTANCE=0.05` es fracción del cuadro, no píxeles).
  El `draw_dwell_progress()` en cambio se dibuja con `cam_xy` (coordenadas del frame).
  No mezcles los dos espacios: es el error obvio acá.
- **Opt-in, apagado por defecto**: `config.DWELL_CLICK_ENABLED = False`. Con dwell
  siempre activo, dejar la mano quieta apoyada en el escritorio clickea cosas solo.
  Esto no es conservadurismo: es que el gesto no tiene forma propia, así que su único
  gate es la quietud.
- Acción: click izquierdo. Emití un evento nuevo `DWELL_CLICK` y bindealo a la acción
  de click en `GESTURE_DEFAULT_BINDINGS`, no llames a `pyautogui` directo — así entra
  por el mismo `Command`/`CommandBus`/historial que todo lo demás y es reasignable.

**Colisión crítica, que es la razón por la que esta tarea puede salir mal**:
`DEFAULT_DURATION_MS = 600` es **exactamente** `config.NARUTO_SEAL_HOLD_SECONDS = 0.6`.
Sostener cualquier sello de una mano durante su hold completaría también el dwell y
dispararía dos acciones con un solo gesto. Dos medidas, las dos necesarias:

1. Suspender el dwell cuando haya cualquier otro candidato activo: `pinch_winner is not
   None`, un hold de sello en progreso, `two_hand_active`, o la app en pausa. Llamá
   `detector.reset()` en esos casos, no solo ignores el resultado — si no, el progreso
   sigue acumulando por debajo.
2. Duración propia más larga que el hold de los sellos: `config.DWELL_DURATION_MS = 900`
   como punto de partida (razonado, no medido — marcalo así). El número final sale de
   la cámara: tiene que ser cómodo de completar a propósito e incómodo de completar sin
   querer.

**Tests** (`tests/test_gesture_engine_regression.py`, clase nueva `DwellClickTests`):
con el flag apagado nunca aparece `DWELL_CLICK` (no-regresión: es el estado por
defecto, así que **toda la suite existente tiene que quedar idéntica**); con el flag
encendido y el índice quieto, aparece una sola vez al completar; moverse más que
`cancel_distance` reinicia el progreso; sosteniendo un sello no aparece `DWELL_CLICK`
aunque pase el tiempo; en pausa tampoco; después de disparar, no vuelve a disparar sin
mover y volver a quedarse quieto.

**Commit**: `feat: dwell-click opcional (apuntar y sostener) sin necesidad de pinch`

---

### C-02 · Doble click — y por qué el camino obvio es el equivocado

**Módulo**: `src/jarvis/core/double_click.py` — `DoubleClickDetector.register_click()`
devuelve `"single"` o `"double"`. Es solo un clasificador: no retiene nada por sí mismo.

**El problema real, que hay que entender antes de escribir una línea**. Hoy
`PINCH_DOWN` → `mouseDown` y `PINCH_UP` → `mouseUp`: eso ya es un click de SO real. Dos
en sucesión rápida deberían ser un doble click nativo. No lo son, por **dos** razones
independientes:

1. `config.CLICK_COOLDOWN = 0.3` (300ms) bloquea el segundo `PINCH_DOWN`. Windows usa
   ~500ms de intervalo de doble click, así que solo queda una ventana de ~200ms donde
   el segundo click pasa el cooldown y todavía cuenta como doble. Inalcanzable a
   propósito.
2. Windows exige que los dos clicks caigan dentro de un rectángulo chico
   (`SM_CXDOUBLECLK`, ~4px por defecto). Con un puntero movido por la mano y suavizado
   por EMA, **el puntero se corre entre los dos pinches** — y el propio movimiento de
   volver a pinzar mueve el landmark del índice. Aun arreglando el cooldown, el SO
   probablemente no los emparejaría.

**Dos diseños posibles. Elegí el segundo:**

- **Retener el primer click** 450ms para ver si llega otro, y disparar `doubleClick()`
  si llegó. Es lo que sugiere el docstring del módulo, y **es la opción equivocada**:
  agrega 450ms de latencia a la interacción más usada de toda la app. Descartada.
- **Re-anclar el segundo click** (recomendada): el primer click sale inmediato, como
  hoy, sin ningún cambio de latencia. Si `register_click()` dice `"double"` en el
  segundo, entonces (a) se permite pasar el cooldown esa única vez y (b) el segundo
  click se emite **en las coordenadas de pantalla del primero**, no en las actuales.
  Los dos clicks caen así en el mismo punto y dentro del intervalo, y el SO los empareja
  como doble click nativo. Costo de latencia: cero.

**Implementación de la opción elegida**:

- Guardá la posición de pantalla del primer click al dispararlo.
- Al detectar el segundo como `"double"`: `MouseMoveCommand(primera_xy)` y después el
  par `MouseButtonCommand(True)`/`MouseButtonCommand(False)` — reusando los Commands
  que ya existen. **No agregues un `DoubleClickCommand`** que envíe dos clicks más: el
  primero ya salió, mandarías tres.
- El bypass del cooldown es **una sola vez** y solo para el segundo click de un par
  reconocido. Si A-01 ya está hecho, esto es una llamada explícita al registro; si no,
  es una excepción en el chequeo a mano. Por eso este workflow va después del 7.
- Aprovechá `DoubleClickDetector` también para el feedback: una burbuja "doble click"
  distingue visualmente los dos casos, que es información útil cuando algo no funciona.
- Registrá el click en `register_click()` en el `PINCH_UP` (click completo), como dice
  el docstring del módulo — no en el `PINCH_DOWN`.

**Ojo con `clock`**: el detector usa `time.monotonic` por defecto y `GestureEngine`
usa `time.time()`. Misma trampa que A-01: inyectá `clock=time.time` si el dwell/doble
click viven dentro del engine, o mantené el detector en `main.py` con su reloj propio y
sé explícito sobre cuál elegiste.

**Tests** (`tests/test_gesture_engine_regression.py` + `tests/test_naruto_seal_dispatch.py`):
dos pinches dentro del intervalo producen dos clicks, el segundo en las coordenadas del
primero; dos pinches separados por más que el intervalo producen dos clicks normales,
cada uno en su posición; **un click simple no se duplica nunca** (el criterio de
aceptación del TASK-019 original); tres pinches rápidos son un par + un simple, no un
triple; el bypass del cooldown no se acumula (no habilita una ráfaga).

**Commit**: `feat: doble click por pinch doble, re-anclado a la posicion del primero`

---

### C-03 · Swipe: el de más riesgo, hacelo último

**Módulo**: `src/jarvis/core/swipe.py` — `SwipeDetector.update(x, y, timestamp)`
devuelve `"SWIPE_LEFT"/"RIGHT"/"UP"/"DOWN"` o `None`, en espacio normalizado, con
reinicio automático de su propia ventana.

**El riesgo, dicho claro**: si le das el índice sin ningún gate de pose, **cualquier
movimiento rápido del puntero dispara un swipe**. Eso rompe el uso normal de la app. El
detector no tiene la culpa: le falta el gate, que es justamente lo que nadie definió
cuando se escribió el módulo.

**Diseño**:

- **Gate de pose: puño cerrado, una sola mano.** Es la forma que queda libre en una
  superficie ya saturada: `_is_fist()` hoy solo participa en gestos de dos manos
  (`both_fists`, ancla del meta-menú) y en dos sellos que se distinguen por la
  **dirección del pulgar** (`NARUTO_SARU` pulgar arriba, `NARUTO_I` pulgar al costado).
  Un puño con el pulgar recogido, moviéndose rápido, con una sola mano, no colisiona con
  nada — pero **verificalo con el censo, no me creas**: corré cada fixture existente
  contra el detector nuevo y confirmá que ninguna produce `SWIPE_*`.
- Gates adicionales: `not two_hand_active`, `pinch_winner is None`, y ningún hold de
  sello en progreso. Y `reset()` del detector cuando la pose se pierde, o una ventana a
  medio abrir sobrevive a un cambio de gesto.
- **Acciones: reusá `HotkeyCommand`** (Fase 8) — no hace falta ningún Command nuevo.
  `SWIPE_LEFT`/`SWIPE_RIGHT` → `alt+left`/`alt+right` (atrás/adelante: funciona en
  navegadores y en el explorador de archivos). **`SWIPE_UP`/`SWIPE_DOWN` se detectan
  pero quedan SIN binding por defecto**, disponibles para que el usuario los asigne
  desde el settings: un swipe vertical con el puño es menos natural que uno horizontal,
  y no hay ninguna acción obviamente correcta para ellos. Mejor dejarlos libres que
  comprometerlos con un default malo — y ya son reasignables por el mecanismo de la
  Fase 8, así que no cuesta nada. Los 4 van igual a `GESTURE_DEFAULT_BINDINGS` (los
  verticales con identidad, que es un no-op seguro) para que aparezcan como filas en la
  tabla del settings.

**Swipe contra scroll — la distinción que NO hay que borrar.** Los dos tienen 4
direcciones y los dos deciden el eje por `abs(dx)` vs `abs(dy)`, así que la tentación de
unificarlos o de bindear swipe a scroll va a aparecer. No lo hagas:

- **Scroll** es *continuo y sostenido*: pose de índice+medio, dirección por
  desplazamiento respecto de una baseline, dispara cuadro a cuadro mientras se sostiene.
  Mueve **contenido**.
- **Swipe** es *discreto y de una sola vez*: pose de puño, exige distancia **y**
  velocidad dentro de una ventana de 600ms, dispara una vez y cierra la ventana.
  Ejecuta un **comando de navegación**.

Bindear swipe a scroll sería redundante y encima peor (una sola unidad de scroll por
gesto, contra el sostenido que ya funciona bien). El valor del swipe es exactamente lo
que el scroll no puede hacer. Colisión de detección no hay — la pose del scroll no es un
puño — pero el costo de que el usuario tenga que recordar dos gestos de 4 direcciones es
real: la leyenda tiene que decir "mover contenido" contra "navegar", no repetir
"izquierda/derecha/arriba/abajo" dos veces.
- Los 4 eventos van a `GESTURE_DEFAULT_BINDINGS` y a la leyenda con sus iconos (el
  badge de flecha ya existe en `ICON_SPECS` para los eventos de scroll: reusá el patrón).

**Tests**: cada dirección con un movimiento sintético que cumple distancia y velocidad;
un movimiento largo pero lento **no** dispara (criterio explícito del spec original);
un movimiento rápido sin la pose de puño no dispara; ninguna fixture existente produce
`SWIPE_*` (censo de colisiones, el test más importante de esta tarea); perder la pose a
mitad de la ventana la cancela.

**Commit**: `feat: swipe con puño cerrado para atras/adelante y escritorios`

---

### C-04 · Verificación en cámara de los tres (va al workflow 6)

Sumá estas filas a la tabla del workflow 6 — sin esto, C-01/C-02/C-03 están escritos,
no terminados:

| ID | Qué medir |
|---|---|
| V-08 | **Dwell**: cuántos ms son cómodos a propósito e incómodos sin querer. Empezá en 900 y ajustá con el dato. Confirmar que sostener un sello no lo completa |
| V-09 | **Doble click**: intervalo real entre dos pinches deliberados de José (¿entra en los 450ms del default?) y cuánto se corre el puntero entre ambos — el número que justifica el re-anclaje |
| V-10 | **Swipe**: distancia y velocidad reales de un swipe con puño (los defaults 0.15 / 0.5 son razonados, no medidos) y confirmar que el movimiento normal del puntero nunca los alcanza |

---

## 11. Fuera de alcance (NO hacer en esta tanda)

- **Cablear los módulos PoC de `core/`** listados como tal en la tabla de §9:
  `gesture_state_machine`, `conflict_resolver`, el loop basado en `InputProvider`,
  `intent_resolution`, `hud_state_machine`, `context.py` y `undo_feedback`. Conectarlos
  cambia latencia y feel ya probados, o duplica algo que ya funciona. Lo que **sí** se
  cablea está especificado en §9 (A-01/A-02/A-03) y §10 (C-01/C-02/C-03) — esas dos
  listas son cerradas: no agregues otros módulos por iniciativa propia.
- **Wake word** para la voz (hoy es push-to-talk con `v`, decisión deliberada).
- **Empaquetar las dependencias de voz y el modelo de ~1GB en el `.exe`** (límite de
  alcance explícito).
- **Reescribir `GestureEngine`** o migrarlo a un clasificador con confianza. Es la
  línea base correcta salvo bug demostrado.
- **Mergear el PR #2 / borrar ramas viejas.** Decisión de José, no de un modelo.
- **Cambiar umbrales de gestos sin datos de cámara real** (ver §8). La única excepción
  son los umbrales que están mal *estructuralmente*, no mal *numéricamente* — como
  H-06, donde el problema es qué umbral se usa para competir, no cuánto vale.

---

## 12. Tabla de seguimiento

Marcá la casilla y anotá el hash al cerrar cada tarea. Si una tarea "no reproduce",
escribilo con lo que encontraste en vez de borrarla.

### Workflow 1 — Nada puede crashear (CRÍTICO)

- [ ] H-01 macro malformada no tumba el loop · commit: ______
- [ ] H-02 bindings.json corrupto no impide arrancar · commit: ______
- [ ] H-03 descarga atómica y verificada de modelos · commit: ______
- [ ] H-04 mensaje accionable si falla la carga del modelo · commit: ______

### Workflow 2 — Dispatch y rebinding

- [ ] H-09 el drag no depende del binding de PINCH_UP · commit: ______
- [ ] H-10 el rebinding no evade HOLD_REQUIRED · commit: ______
- [ ] H-11 invalidar la pila de redo · commit: ______
- [ ] H-12 cerrar el micrófono al salir · commit: ______

### Workflow 3 — Motor de gestos

- [ ] H-05 resetear estado de una mano al perder la mano · commit: ______
- [ ] H-06 pinch fantasma del anular · commit: ______
- [ ] H-07 comentario del umbral de Sukuna · commit: ______
- [ ] H-08 (opcional, solo si tocás esa función) bbox redundante

### Workflow 4 — Empaquetado y assets

- [ ] H-13 separar assets empaquetados de escribibles · commit: ______
- [ ] H-14/15/16/17 generación de iconos robusta y atómica · commit: ______

### Workflow 5 — CI/CD, dependencias y limpieza

- [ ] H-18 gate de tests antes del release · commit: ______
- [ ] H-19 pinear dependencias · commit: ______
- [ ] H-20 cache de pip en CI · commit: ______
- [ ] H-21 subprocess en vez de os.system · commit: ______
- [ ] H-22 sincronizar el buffer de audio · commit: ______
- [ ] H-23 (agrupar) temp único en config_store
- [ ] H-24 renombrar `_dispatch_naruto_seal` · commit: ______
- [ ] H-25 actualizar docs + entradas de Decisions · commit: ______ ← **último de todos**

### Workflow 7 — Unificación de arquitectura (después de 1–5)

- [ ] A-01 cooldowns en `CooldownRegistry` · commit: ______
- [ ] A-02 debounce + tolerancia de fallos unificados (**requiere H-05 hecho**) · commit: ______
- [ ] A-03 bindings por aplicación en foco (**requiere H-09 y H-24 hechos**) · commit: ______
- [ ] A-03b (opcional, solo si José lo pide) persistir y editar reglas por app
- [ ] B-01 pinear el conjunto PoC con un test · commit: ______

### Workflow 8 — Gestos que faltan (después del 7)

- [ ] C-01 dwell-click opcional · commit: ______
- [ ] C-02 doble click re-anclado (**requiere A-01 hecho**) · commit: ______
- [ ] C-03 swipe con puño (hacelo último: mayor riesgo de colisión) · commit: ______

### Workflow 6 — Cámara real (requiere a José)

- [ ] V-01 sellos Naruto de una mano (bloqueante)
- [ ] V-02 sellos Naruto de dos manos
- [ ] V-03 JJK + Clap + corazón coreano
- [ ] V-04 confirmar o revertir EMA_ALPHA 0.25
- [ ] V-05 colisión Sukuna ↔ RIGHT_CLICK
- [ ] V-06 colisión residual Shaka/Screenshot (después de V-01)
- [ ] V-07 `.exe` portable en máquina limpia
- [ ] V-08 duración cómoda del dwell (después de C-01)
- [ ] V-09 intervalo y deriva del puntero entre dos pinches (después de C-02)
- [ ] V-10 distancia y velocidad reales de un swipe (después de C-03)

---

## 13. Estado final esperado

Al cerrar los workflows 1–5:

- Ningún input de disco, de red o de la pantalla de configuración puede crashear la app
  ni dejar el SO en mal estado.
- El `.exe` portable se comporta igual que el modo desarrollo respecto a assets.
- No se puede publicar un release sin tests verdes, y las dependencias son
  reproducibles.
- La suite pasa de 594 a ~630+ tests, con cobertura nueva en las áreas que hoy no
  tienen ninguna: pérdida y reaparición de la mano, carga de configuración malformada,
  descargas interrumpidas, y el ciclo de vida del drag bajo rebinding.

Y al cerrar el workflow 7:

- Los cooldowns y el debounce dejan de estar reimplementados a mano dentro de
  `GestureEngine`: viven en un solo lugar con nombre, que es lo que evita que vuelva a
  aparecer un bug de la familia del cooldown compartido.
- Los gestos pueden significar cosas distintas según la app en foco, sin que ningún
  gesto cambie, y con comportamiento byte-idéntico al actual mientras no haya reglas
  definidas.
- Deja de haber ambigüedad sobre qué de `core/` está vivo: 6 módulos se cablearon (3 en
  el workflow 7 + los 3 detectores del workflow 8), 10 quedan declarados PoC con un test
  que impide cablearlos por accidente.

Y al cerrar el workflow 8:

- **Se puede abrir un archivo o una carpeta con gestos**, que hoy es imposible.
- Hay una forma de clickear que no depende del pinch, para cuando el pinch se confunde
  con Shaka o el puntero está impreciso.
- Atrás/adelante y cambio de escritorio salen con un gesto, reusando la infraestructura
  de atajos de la Fase 8 sin agregar ningún `Command` nuevo.

Lo que **no** cierra sin cámara: la precisión real de reconocimiento de los sellos. Ese
es el workflow 6 y es el único que necesita a José presente.
