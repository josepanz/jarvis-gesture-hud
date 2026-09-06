# WORKPLAN — Sellos reales por modelo (`hand-sign-fidelity`)

> **Auditoría y especificación**: Opus 5 (2026-09-05), sobre la rama
> `feature/pose-ownership-and-visualization` en el commit `0f49957`.
> **Ejecución**: Sonnet, workflow por workflow, en el orden de este archivo.
>
> Este archivo es autocontenido: no hace falta leer la conversación que lo originó,
> ni el repo de referencia. Todo lo que el modelo ejecutor necesita (contexto, causa
> raíz, cambio, trampas, tests, criterios de aceptación y mensaje de commit) está acá.
> La auditoría completa que justifica todo esto está en `AUDIT.md`, al lado.

---

## 0. Cómo usar este archivo

- **Un workflow = una sesión de trabajo = uno o más commits.** No mezclar workflows
  en un mismo commit.
- Cada tarea tiene un ID (`Y-01`, `Y-02`, …). Al terminarla, marcá su casilla en la
  tabla del §8 y escribí en la misma línea el hash del commit.
- **Antes de cambiar código, ejecutá la "Verificación previa" de la tarea.** Los
  números de línea de este documento son del commit `0f49957` y pueden haber corrido.
  Si la verificación previa no reproduce lo descrito, **no toques nada**: anotalo en
  la tabla del §8 con lo que encontraste y seguí con la tarea siguiente.
- Todos los números de rendimiento y de score de este archivo están **medidos en la
  máquina de José**, no estimados. Están puestos para que puedas comparar contra
  ellos, no para que confíes.

---

## 0.1 Protocolo de ejecución y checkpoints

### Dónde para

**Una tarea = un checkpoint.** Al terminar cada tarea:

1. Corré la Definition of Done completa del §1.2.
2. Commiteá con el mensaje indicado en la tarea (uno por tarea, nunca agrupados).
3. Marcá la casilla en la tabla del §8 con el hash (commit `docs:` aparte, como se
   viene haciendo en este proyecto).
4. **Pará y reportá.** No sigas con la tarea siguiente por iniciativa propia.

El reporte de checkpoint son 4 líneas, no un ensayo: qué reproducía el problema
antes, qué cambiaste, cuántos tests hay ahora y si algo quedó raro.

**Excepción**: si una tarea "no reproduce", anotala como tal y seguí sin esperar.

### Cómo se le pide (prompt para copiar y pegar)

```
Leé openspec/changes/hand-sign-fidelity/WORKPLAN.md, secciones §0.1, §1, §2 y la de
la tarea <ID>. Ejecutá SOLO la tarea <ID>.

Contexto: los sellos de una mano que este proyecto implementó son formas inventadas
que no corresponden a ningún sello real; la decisión ya tomada es reemplazarlos por
el modelo YOLOX de C:\workspace\NARUTO-HandSignDetection (MIT, ya clonado local).
El análisis completo está en AUDIT.md, al lado del WORKPLAN.

Reglas:
- Hacé primero la "Verificación previa obligatoria" de la tarea, si la tiene. Si no
  reproduce lo descrito, no toques código: anotalo en §8 y decímelo.
- No re-audites el proyecto ni rediscutas la decisión: el análisis ya está hecho y
  está medido. Si encontrás evidencia de que algo del plan está mal, PARÁ y decilo,
  no improvises un plan nuevo.
- No lances subagentes. La tarea ya trae archivos, líneas y trampas: leé esos.
- Usá `venv\Scripts\python`, NO el `python` del sistema (el global no tiene
  cv2/mediapipe y la suite falla con 47 errores de import ajenos a tu cambio).
- No leas ARCHITECTURE.md completo (son ~1500 líneas): grep a la sección puntual.
- Prestá atención a la sección "Trampas verificadas" de la tarea: están ahí porque
  ya se comprobó que rompen la tarea si se ignoran.
- Al terminar: DoD del §1.2, commit con el mensaje de la tarea, casilla marcada en
  §8 (commit docs: aparte), y pará.
```

Para encadenar varias tareas de un mismo workflow en una sola sesión, cambiá
`SOLO la tarea <ID>` por `las tareas <ID> y <ID>, en ese orden, parando y reportando
entre cada una`.

### Economía de tokens

- **Una sesión nueva por workflow.** Este archivo es autocontenido justamente para
  que la ejecución arranque en frío.
- **Sin subagentes.** El archivo ya trae archivo, línea, causa raíz y trampas.
- **`ARCHITECTURE.md` completo son ~48.000 tokens.** Grep a la sección puntual.

---

## 1. Contexto del proyecto (lo mínimo indispensable)

`jarvis-gesture-hud` es un controlador de escritorio por gestos de mano vía webcam
(Python, MediaPipe Tasks API, `pyautogui`, Tkinter para overlays, `pyttsx3` para voz).

Arquitectura: `GestureEngine` (lógica pura, sin I/O) produce eventos string →
`main.py` los resuelve contra los bindings del perfil activo → `Command` →
`CommandBus` → `jarvis.actions.*` → `pyautogui`/`CrossPlatformOS`.

Estado al momento de esta auditoría:

- Rama `feature/pose-ownership-and-visualization`, commit `0f49957`, sin mergear.
- 724 tests automáticos en verde (`python -m unittest discover -s tests`).
- El WORKPLAN de `hardening-and-polish` está **cerrado** salvo su workflow 6
  (verificación en cámara), que quedó bloqueado justamente por lo que resuelve este
  documento.

### 1.1 Convenciones NO negociables

1. **Los commits NUNCA llevan `Co-Authored-By`, ni ninguna referencia a Claude, a un
   modelo o a IA.** Autoría exclusiva de `josepanz`.
2. **Conventional Commits obligatorio**, en español (`fix:` / `feat:` / `perf:` /
   `refactor:` / `test:` / `docs:` / `chore:` / `ci:` / `build:`).
3. **Verificar antes de arreglar.** Si no podés demostrar el comportamiento (test que
   falla, log, medición), no lo toques. Todo umbral nuevo se justifica con un número
   medido o se marca explícitamente como razonado-no-medido.
4. **Todo cambio de comportamiento se documenta en `ARCHITECTURE.md`**, en la sección
   "Decisions & rationale", con causa raíz y cómo se verificó.
5. **Los tests son `unittest` de stdlib, sin dependencias nuevas.**
6. Archivos `tests/manual_*.py` están excluidos del discovery a propósito.

### 1.2 Definition of Done global (aplica a TODA tarea)

```bash
cd C:\workspace\jarvis-gesture-hud
venv\Scripts\python -m py_compile src/jarvis/<archivos tocados>.py
venv\Scripts\python -m unittest discover -s tests            # TODOS en verde
venv\Scripts\python tests/manual_main_integration_check.py   # debe imprimir INTEGRATION OK
venv\Scripts\python tests/manual_live_integration_check.py   # debe terminar sin traceback
```

> **Ojo**: usá `venv\Scripts\python`, NO el `python` del sistema — el intérprete
> global no tiene `cv2`/`mediapipe` y la suite falla con 47 errores de import que no
> tienen nada que ver con tu cambio.

Más: un arranque real de la app (`python run.py`, ~10s, sin mano en cuadro) sin
traceback, para cualquier tarea que toque `main.py`, `gestures.py`, `overlay.py` o
`paths.py`.

Si un test existente se rompe: **no lo ajustes para que pase**. Entendé por qué
primero. En este WORKPLAN varios tests se rompen **a propósito** (borramos los gestos
que pineaban); cada tarea dice explícitamente cuáles y por qué.

---

## 2. Qué se decidió y por qué (resumen de `AUDIT.md`)

**Hallazgo**: los 14 sellos canónicos se hacen **con las dos manos**. Los 8 "sellos de
una mano" que implementa `gestures.py` (Tora, Ushi, U, Uma, Hitsuji, Saru, Inu, I) son
invención de este proyecto, y `NARUTO_TORI` está definido casi al revés. De 13 sellos
implementados, **2 son correctos** (Ne, Mi). Eso explica el reporte de José *"ningún
sello se reconoce bien"*: no hay umbral que arregle una forma que nadie hace.

**Decisión de José (2026-09-05)**: cablear el modelo YOLOX-Nano de
[NARUTO-HandSignDetection](https://github.com/Kazuhito00/NARUTO-HandSignDetection)
(MIT, Kazuhito Takahashi), y **borrar los sellos de una mano inventados**.

**Por qué es viable** (todo medido en esta máquina):

| | valor |
|---|---|
| Inferencia, frame 640×480, CPU | **8.1 ms** promedio, 8.6 ms p95 |
| Inferencia, imagen 1200×784 | 9.7 ms promedio |
| Nuestro `HandLandmarker` (ya corre cada frame) | 10.0 ms promedio |
| `PoseLandmarker` (descartado por caro en TASK-060c) | 10.4 ms promedio |
| Tamaño del modelo | 3.6 MB |
| `onnxruntime` en el venv | **ya instalado** (llega con mediapipe) |
| Auto-clasificación de las 14 imágenes canónicas | **14/14 con score 0.82–0.93** |

El modelo es **más barato que lo que ya corremos**, y encima sólo va a correr cuando
haya 2 manos en cuadro (única situación en la que un sello es posible).

### Mapeo clase del modelo → evento nuestro

El modelo emite 16 clases; `setting/labels.csv` del repo original las nombra.
El demo original hace `class_id + 1` para indexar esa tabla.

| clase (+1) | nombre en labels.csv | evento nuestro |
|---|---|---|
| 1 | `Ne(Rat)` | `NARUTO_NE` |
| 2 | `Ushi(Ox)` | `NARUTO_USHI` |
| 3 | `Tora(Tiger)` | `NARUTO_TORA` |
| 4 | `U(Hare)` | `NARUTO_U` |
| 5 | `Tatsu(Dragon)` | `NARUTO_TATSU` |
| 6 | `Mi(Snake)` | `NARUTO_MI` |
| 7 | `Uma(Horse)` | `NARUTO_UMA` |
| 8 | `Hitsuji(Ram)` | `NARUTO_HITSUJI` |
| 9 | `Saru(Monkey)` | `NARUTO_SARU` |
| 10 | `Tori(Bird)` | `NARUTO_TORI` |
| 11 | `Inu(Dog)` | `NARUTO_INU` |
| 12 | `I(Boar)` | `NARUTO_I` |
| 13 | `Gassho` | *(nuevo, Y-06)* |
| 14 | `Unknown` | ignorar |
| 15 | `Mizunoe` | *(nuevo, Y-06)* |

**12 de nuestros 13 sellos mapean 1:1.** El único huérfano es **`NARUTO_KAI`**, que no
está entre los 14 canónicos (no es un signo del zodíaco) — se borra (ver Y-04).

---

## 3. WORKFLOW 1 — Traer el modelo (fundación, no cambia comportamiento)

**Objetivo**: tener el modelo cargable y probado dentro del proyecto, sin que la app
lo use todavía. Al terminar este workflow el comportamiento de la app es
**byte-idéntico** al de hoy.

---

### Y-01 · Vendorizar el modelo y el wrapper ONNX

**Fuente**: `C:\workspace\NARUTO-HandSignDetection` (clonado localmente, MIT).

**Qué traer**:

1. **El modelo**: copiar `model/yolox/yolox_nano.onnx` (3.6 MB) a
   `assets/hand_sign_yolox_nano.onnx` y **commitearlo**.
   - *Por qué commitearlo y no descargarlo*: son 3.6 MB (el `.gitignore` sólo excluye
     `assets/*.task`, así que un `.onnx` se commitea normal), hace que el `.exe`
     portable sea self-contained, y evita agregar un modo de falla de red para un
     archivo tan chico. Los modelos que SÍ se descargan (`hand_landmarker.task`, el
     GGUF de voz) pesan órdenes de magnitud más.
2. **El wrapper**: portar `model/yolox/yolox_onnx.py` (~250 líneas) a
   `src/jarvis/hand_sign_model.py`.
   - Es numpy puro + `onnxruntime`: preproceso letterbox a 416×416 con relleno gris
     (114), inferencia, y post-proceso (decodificación de grids/strides 8/16/32 + NMS
     multiclase class-agnostic). **Sin torch, sin tensorflow.**
   - Traducir los comentarios al español, como el resto de `src/jarvis/`.
   - **Dejar la atribución MIT en el docstring del módulo** (autor, repo, licencia).
3. **Atribución**: crear `THIRD-PARTY-NOTICES.md` en la raíz con el texto de la
   licencia MIT de `C:\workspace\NARUTO-HandSignDetection\LICENSE` (Copyright (c) 2020
   KazuhitoTakahashi) y una línea diciendo qué archivos derivan de ahí.

**Trampas verificadas**:

- **`IndexError` latente en el mapeo de etiquetas** (bug real del proyecto original):
  el modelo emite **16 clases** (`output shape [1, 3549, 21]` → `21 - 5 = 16`) y el
  demo hace `class_id + 1`, así que la última clase indexaría `labels[16]` — pero
  `labels.csv` tiene 16 filas (índices 0..15). **No copies ese mapeo tal cual**: usá
  una tupla/dict propio de 16 entradas indexado por `class_id` sin offset, con la
  clase sobrante mapeada a `None`.
- **No copies `simple_demo.py`**: hace `copy.deepcopy(frame)` por cuadro antes de
  saber si lo va a usar. No lo necesitamos (no dibujamos sobre una copia).
- El wrapper original tiene `providers=['CUDAExecutionProvider', 'CPUExecutionProvider']`
  por default. Dejalo así (cae a CPU solo si no hay CUDA), pero **medí en CPU**.

**Verificación previa obligatoria**:

```bash
venv\Scripts\python -c "import onnxruntime; print(onnxruntime.__version__)"
```
Debe imprimir una versión, no fallar. Si falla, `onnxruntime` no está instalado y
esta tarea cambia de forma (habría que agregarlo a `requirements.txt`) — anotalo.

**Tests a agregar** (`tests/test_hand_sign_model.py`, nuevo):

- El modelo carga y expone la forma de entrada esperada (`[1, 3, 416, 416]`).
- **Las 14 imágenes canónicas de `docs/gesture-reference/canonical/` se
  auto-clasifican**, cada una como su propio sello, con score ≥ 0.7. Este es el test
  central: es la verificación con datos reales que este proyecto exige, y ya se sabe
  que pasa — medido: 14/14, scores 0.82–0.93.
- Un frame de ruido aleatorio no produce ninguna detección ≥ 0.7 (verificado: 0
  detecciones).
- El mapeo de clases no puede lanzar `IndexError` para ninguna clase 0..15.

**Criterios de aceptación**: los tests nuevos en verde; los 724 existentes sin tocar;
la app arranca igual (nadie usa el modelo todavía).

**Commit**: `feat: vendorizar el modelo YOLOX de deteccion de sellos (MIT, Kazuhito00)`

---

### Y-02 · `HandSignTracker`: la política de la app sobre el modelo

**Archivo nuevo**: `src/jarvis/hand_sign_tracker.py` (paralelo a `hand_tracker.py` y
`pose_tracker.py`).

Envuelve `hand_sign_model.py` con lo que la app necesita, sin tocar `main.py`
todavía. Responsabilidades:

1. **Cargar el modelo desde `bundled_assets_dir()`** (H-13: assets empaquetados =
   sólo lectura; `writable_assets_dir()` es para lo que se descarga o genera —
   este modelo va commiteado, así que es *bundled*).
2. **Mapear clase → evento** con la tabla del §2.
3. **Debounce**: reusar `jarvis.core.debounce.ConsecutiveFrameDebouncer` (A-02), NO
   reimplementar. El proyecto original usa el mismo patrón (`chattering_check`).
4. **Hold**: un sello sólo emite su evento tras sostenerse
   `config.NARUTO_TWOHAND_HOLD_SECONDS`. **Esto no es opcional**: ver la trampa de
   HOLD_REQUIRED abajo.
5. **Dedup**: mientras el mismo sello siga sostenido, no repetir el evento (mismo
   comportamiento que `_naruto_hold_seal` tiene hoy).
6. Exponer `hold_seal` (el sello sostenido ahora, o `None`) para que los gates de
   dwell y swipe sigan funcionando (ver trampa abajo).

**Trampas verificadas**:

- **El frame va SIN espejar.** `main.py` espeja el frame cuando `self.mirrored`
  (default `True`). Medido: 13 de las 14 imágenes canónicas clasifican igual
  espejadas, pero **`Mi(Snake)` cae de 0.82 a 0.70** — justo en el umbral. El frame
  sin espejar existe en `run()` antes del `cv2.flip`: usá ese.
- **HOLD_REQUIRED (H-10)**: `NARUTO_I → LOCK_SESSION` es el binding por default, y la
  garantía de que un lock no se dispara sin hold es **posicional**: vive en que
  `GestureEngine` nunca emite el evento antes de cumplir el hold. `settings_ui.py`
  lista los eventos de sello en `HOLD_CAPABLE_EVENTS`. Si el tracker nuevo emite sin
  hold, se rompe ese gate de seguridad **en silencio**.
- **`config.NARUTO_SEAL_HOLD_SECONDS` (0.6) queda sin uso** una vez que no hay sellos
  de una mano: todos los sellos pasan a ser de dos manos y usan
  `NARUTO_TWOHAND_HOLD_SECONDS` (1.2). No borres la constante en esta tarea (la usa
  todavía el código viejo); se resuelve en Y-04.

**Tests a agregar** (`tests/test_hand_sign_tracker.py`, nuevo):

- Con el modelo mockeado: una detección suelta no emite (falta debounce); N
  detecciones seguidas de la misma clase + el hold cumplido sí emiten, una sola vez.
- Sostener el mismo sello no repite el evento; cambiar de sello reinicia el hold.
- Una clase sin evento mapeado (`Unknown`) nunca emite nada.
- Detecciones por debajo del umbral de score se descartan antes del debounce.
- Con las 14 imágenes reales: cada una produce su evento tras el hold.

**Criterios de aceptación**: el tracker funciona aislado; `main.py` sigue sin
importarlo; los 724 tests existentes intactos.

**Commit**: `feat: HandSignTracker con debounce y hold sobre el modelo de sellos`

---

## 4. WORKFLOW 2 — Cablear y borrar la geometría inventada

**Objetivo**: que los sellos pasen a detectarse por el modelo, y que desaparezca el
código que buscaba formas que nadie hace.

**Por qué en este orden**: Y-03 deja los dos caminos coexistiendo detrás de un flag
(reversible en una línea); recién Y-04 borra el viejo, ya con el nuevo funcionando.

---

### Y-03 · Cablear el tracker en el loop de cámara

**Archivo**: `src/jarvis/main.py` (`JarvisApp.__init__` y `run()`).

**Cambio**:

1. `config.HAND_SIGN_MODEL_ENABLED = True` (nuevo). A diferencia de
   `POSE_HAND_OWNERSHIP_ENABLED` (que quedó en `False` por costo), éste va en `True`:
   es más barato que el `HandLandmarker` que ya corre, y es la única forma de que los
   sellos funcionen.
2. Construir `HandSignTracker` en `__init__` sólo si el flag está activo, con el mismo
   try/except que H-04 le puso a `HandTracker` (un fallo de carga del modelo no puede
   terminar en un traceback crudo).
3. En `run()`, **llamar al tracker sólo cuando `len(hands) == 2`**. Ése es el gate de
   costo: un sello canónico siempre usa las dos manos, así que en el uso normal (una
   mano, puntero/click) el modelo ni se ejecuta. `hands` ya viene del `HandTracker`
   que corre igual.
4. Los eventos que emite el tracker entran por **el mismo `for event in events:`** que
   ya existe, con su try/except por evento (H-01). No inventes un camino nuevo de
   dispatch: los nombres de evento son los mismos de siempre, así que bindings,
   perfiles persistidos, leyenda y settings siguen funcionando sin migración.

**Trampa**: pasá el frame **sin espejar** (ver Y-02).

**Verificación previa obligatoria**: medí el costo real antes y después con el HUD de
debug (tecla `d`, muestra FPS). Anotá los FPS con una mano en cuadro (el modelo no
debería correr) y con dos (debería correr). Si con dos manos los FPS caen más de lo
que explican 8 ms, algo está corriendo de más.

**Tests** (`tests/test_hand_sign_dispatch.py`, nuevo): con el tracker mockeado,
un evento de sello llega a `_dispatch_bound_event` y dispara la acción bindeada; con
una sola mano en cuadro el tracker **no se invoca**.

**Commit**: `feat: detectar los sellos con el modelo cuando hay 2 manos en cuadro`

---

### Y-04 · Borrar los sellos de una mano inventados

**Archivo**: `src/jarvis/gestures.py`.

Esto es lo que José pidió explícitamente: *"obviá los sellos de 1 mano de naruto y
borralos si no son útiles"*. No son útiles: `AUDIT.md` demuestra que 6 de 8 no
corresponden a ningún sello real.

**Qué se borra**:

- Las funciones `_is_naruto_ushi`, `_is_naruto_uma`, `_is_naruto_saru`,
  `_is_naruto_inu`, `_is_naruto_i`, `_index_middle_extended_ring_pinky_curled`,
  `_thumb_offset_from_palm`.
- El bloque de detección de sellos de una mano dentro de `process()` (hoy ~líneas
  877–936), **salvo la rama de `JJK_MEGUMI`** (ver trampa).
- El bloque de sellos de dos manos por geometría dentro de
  `_process_two_hand_gestures()` (Ne/Mi/Tori/Kai/Tatsu/Gojo) — **salvo
  `JJK_GOJO_DOMAIN`**, que no es un sello Naruto y el modelo no cubre.
- El evento **`NARUTO_KAI`** completo (no está entre los 14 canónicos): su entrada en
  `GESTURE_DEFAULT_BINDINGS`, su fila de leyenda, su icono y su fila de settings. No
  se pierde funcionalidad: su acción default era `CLOSE_APP`, que sigue siendo
  alcanzable con las 2 manos en Shaka sostenidas.
- `config.NARUTO_SEAL_HOLD_SECONDS` y las constantes de geometría de sellos que queden
  sin uso (`NARUTO_TWOHAND_CLASP_MAX_DISTANCE_FRACTION`,
  `NARUTO_TWOHAND_FAN_MIN/MAX_DISTANCE_FRACTION`) — **verificá con grep** cuáles
  quedaron realmente huérfanas antes de borrar cada una.

**Trampas verificadas** (éstas son las que hacen fallar la tarea si se ignoran):

1. **`_fingers_crossed` NO se borra**: la usa `_is_jjk_megumi` (`gestures.py:309`).
   JJK Megumi es un gesto de una mano que **no** es un sello Naruto y que el modelo no
   cubre — se queda tal cual está.
2. **`_naruto_hold_seal` NO desaparece**: lo leen los gates de **dwell** (C-01,
   `gestures.py:1079`) y **swipe** (C-03, `gestures.py:1061`), ambos implementados
   hace días. Si lo borrás, esos dos gates quedan siempre-falsos **en silencio** y
   vuelve la colisión que C-01/C-03 justamente arreglaron. Opciones: (a) que
   `GestureEngine` lea el `hold_seal` del tracker nuevo, o (b) que `main.py` se lo
   inyecte cada frame. Elegí una y dejala explícita en el código, no implícita.
3. **`_is_fist` NO se borra**: lo usan el menú meta de 2 manos, `both_fists` y el gate
   de swipe (C-03).

**Tests que se rompen a propósito** (borralos o adaptalos, y decilo en el commit):

- `tests/test_gesture_engine_regression.py`: `NarutoOneHandSealTests` (clase entera),
  los fixtures `naruto_*_hand()` y `NARUTO_SEAL_FIXTURES`, el helper `hold_naruto()`,
  y las partes de `NarutoTwoHandSealTests` que ya no aplican.
- `HandLossStateResetTests` usa `naruto_tora_hand()` — hay que rehacer ese caso con
  otro gesto sostenido (p. ej. `KOREAN_HEART`, que sigue existiendo).
- `DwellClickTests.test_holding_a_seal_never_completes_dwell` (C-01) y
  `SwipeTests.test_no_existing_fixture_ever_produces_a_swipe` (C-03) usan esos mismos
  fixtures. **Estos dos NO se borran**: son la protección de la trampa 2 de arriba.
  Reescribilos contra el mecanismo nuevo de `hold_seal`.
- `tests/test_naruto_seal_dispatch.py::HoldRequiredGatingTests` usa `naruto_i_hand()`
  para probar el pipeline completo de HOLD_REQUIRED. Rehacelo con el tracker nuevo:
  es el test que protege que un pinch casual no bloquee la sesión.

**Criterios de aceptación**: `grep -rn "_is_naruto_" src/` no devuelve nada; la suite
queda verde con menos tests que antes (es esperado: se borraron gestos), y el conteo
nuevo queda anotado en el commit.

**Commit**: `refactor: borrar los sellos de una mano inventados, ya cubiertos por el modelo`

---

### Y-05 · Leyenda, iconos y settings a las formas reales

**Archivos**: `src/jarvis/legend.py`, `src/jarvis/gesture_icons.py`,
`src/jarvis/settings_ui.py`, `tests/test_legend.py`.

Hoy la leyenda describe formas de una mano que ya no existen ("Sello Inu (solo
meñique)", "Sello Saru (puño, pulgar arriba)", …) y los iconos dibujan esas mismas
formas inventadas. Todo eso pasa a describir el sello real, de dos manos.

**Cambio**:

1. Reescribir las descripciones de `legend.ENTRIES` para los 12 sellos, en términos de
   las dos manos. Las formas reales están fotografiadas en
   `docs/gesture-reference/canonical/` — **mirá las imágenes, no inventes la
   descripción**.
2. Los `ICON_SPECS` de los 12 sellos pasan a `"hands": 2`. El modelo de iconos no
   representa manos entrelazadas, así que varios van a quedar parecidos entre sí:
   está bien, se distinguen por el glyph, igual que ya pasa con `naruto_ne`/`naruto_mi`.
3. Regenerar el snapshot de `tests/test_legend.py` (`_EXPECTED_TEXT`) — el padding
   `ljust` cambia si cambia la fila más larga.
4. Agregar en la leyenda o en el README un puntero a
   `docs/gesture-reference/canonical/`, que es la referencia visual buena.

**Commit**: `docs: leyenda e iconos de sellos segun las formas reales de dos manos`

---

## 5. WORKFLOW 3 — Lo que el modelo regala (opcional, decidir después de la cámara)

---

### Y-06 · Mizunoe y Gassho como eventos nuevos

El modelo detecta 2 sellos que hoy no tenemos: **Mizunoe (壬)** y **Gassho (合掌**, las
manos juntas en oración). Salen gratis: ya están en el modelo, sólo falta el evento,
el binding default, la fila de leyenda y el icono.

**Ojo con `CLAP`**: ya tenemos un evento `CLAP` (dos manos, `ImpulseDetector`,
**movimiento** de acercar y separar). Gassho es una **pose estática** de manos juntas.
Son cosas distintas: no los unifiques, y cuidá que un Gassho sostenido no dispare
también un `CLAP` (el detector de impulso necesita el movimiento, así que en principio
no colisiona — **verificalo en cámara antes de darlo por hecho**).

**Commit**: `feat: sellos Mizunoe y Gassho, que el modelo ya detecta`

---

### Y-07 · Secuencias de sellos → una acción

El proyecto original tiene una idea que nosotros no: una **secuencia** de sellos
dispara una acción (`巳,寅,申,亥,午,寅` → "Bola de Fuego"), con un historial que se
limpia solo si pasan 2 s sin detectar nada (`sign_interval`), y match exacto contra
una tabla (`jutsu.csv`).

Copiar **la idea**, no el código: historial + timeout + match de secuencia → acción.
Da "combos" sin agregar ninguna pose nueva, y encaja con el sistema de bindings que ya
existe (una secuencia es simplemente otro trigger reasignable).

**No lo hagas antes de la cámara**: primero hay que saber que un sello suelto se
detecta bien y cuánto tarda; una secuencia de 6 sellos multiplica cualquier problema
de detección por 6.

**Commit**: `feat: secuencias de sellos como trigger de una accion`

---

### Y-08 · Fix: sostener un sello no debe completar de paso el hold de pausa

**No estaba planeada** - hallazgo real del Workflow 4 (Y-V3, verificación en cámara
con José, 2026-09-06): armar Ne (y en general cualquier sello que curve bastante
los dedos de las 2 manos, ej. Ushi/Saru) satisface de paso `_is_fist` en ambas
manos. Sin protección, sostenerlo lo suficiente completaba TAMBIÉN el hold de
`both_fists` (`PAUSE_HOLD_SECONDS`, `gestures.py`) y disparaba `TOGGLE_ACTIVE`
sin querer - se vio en vivo dos veces armando Ne.

**Causa raíz**: el modelo (Y-01/Y-02/Y-03) corre y acumula su propio hold en
`main.py`, completamente aparte de `_process_two_hand_gestures()` - nunca hereda
la jerarquía que sí protege a `JJK_GOJO_DOMAIN`, que sigue viviendo adentro de
esa función.

**Fix**: `external_seal_in_progress` (el mismo mecanismo que la trampa 2 de Y-04,
ya inyectado por `main.py` desde `HandSignTracker.hold_seal`) ahora también
suspende el hold de `both_fists` en `_process_two_hand_gestures()`, no solo los
gates de dwell/swipe.

**Commit**: `fix: sostener un sello ya no completa de paso el hold de pausa` · `5531ee9`

---

## 6. WORKFLOW 4 — Verificación en cámara (REQUIERE A JOSÉ)

Reemplaza a **V-01 y V-02** del WORKPLAN de `hardening-and-polish`, que quedaron sin
sentido (medían la fidelidad de formas inventadas).

**Protocolo**: un sello por vez, con las imágenes de
`docs/gesture-reference/canonical/` a la vista para copiar la forma.

| ID | Qué medir |
|---|---|
| Y-V1 | Los 12 sellos, uno por uno: ¿se detectan? ¿con qué score? ¿cuánto tardan en confirmar? |
| Y-V2 | Costo real: FPS con 1 mano (modelo apagado) vs. 2 manos (modelo corriendo) |
| Y-V3 | Falsos positivos: hacer los gestos clásicos de 2 manos (pausa, cerrar, zoom) y confirmar que no disparan sellos |
| Y-V4 | El umbral 0.7 y el hold de 1.2 s: ¿son cómodos, o hay que ajustarlos con el dato real? |

Las demás verificaciones pendientes del workflow 6 viejo (**V-04** EMA_ALPHA, **V-05**
colisión Sukuna, **V-08/V-09/V-10** dwell/doble click/swipe) **no dependen de este
WORKPLAN** y se pueden hacer en cualquier momento.

---

## 7. Fuera de alcance (NO hacer en esta tanda)

- **Reentrenar el modelo** o ampliar sus clases. Son 16 fijas; agregar un gesto propio
  exige un dataset y un pipeline de entrenamiento que este proyecto no tiene.
- **Reemplazar el `HandLandmarker` por el modelo.** El puntero, el pinch, el scroll y
  todo lo continuo siguen viniendo de landmarks: el modelo detecta *sellos*, no da
  posición de dedos.
- **Migrar los gestos JJK ni el corazón coreano.** No están entre las 16 clases; se
  quedan geométricos, tal como están.
- **Tocar el `CLAP` existente** (ver Y-06).
- **Mergear el PR #2 ni borrar ramas.** Decisión de José.

---

## 8. Tabla de seguimiento

### Workflow 1 — Traer el modelo (no cambia comportamiento)

- [x] Y-01 vendorizar modelo + wrapper ONNX · commit: a511715
- [x] Y-02 `HandSignTracker` con debounce y hold · commit: 219a9f1

### Workflow 2 — Cablear y borrar lo inventado

- [x] Y-03 cablear en el loop, gate de 2 manos (**requiere Y-02**) · commit: d88ff68
- [x] Y-04 borrar los sellos de una mano (**requiere Y-03**) · commit: 7d45875
- [x] Y-05 leyenda, iconos y settings a las formas reales · commit: 9723849

### Workflow 3 — Lo que el modelo regala (opcional, después de la cámara)

- [x] Y-06 Mizunoe y Gassho · commit: 1683272
- [ ] Y-07 secuencias de sellos · commit: ______
- [x] Y-08 fix colisión sello/pausa (no planeada, hallazgo Y-V3) · commit: 5531ee9

### Workflow 4 — Cámara real (requiere a José)

- [x] Y-V1 los 12 sellos, uno por uno
- [x] Y-V2 costo real con 1 vs. 2 manos
- [x] Y-V3 falsos positivos contra los gestos clásicos de 2 manos
- [x] Y-V4 ajuste del umbral (0.7) y del hold (1.2 s) con datos reales

#### Resultados (verificado en cámara real, José, 2026-09-06)

Cámara DroidCam (fuente de FPS inestable de por sí, ver Y-V2). Debug HUD
instrumentado para esta sesión con `sign`/`sign_hold` (clase+score crudo y
progreso del hold en vivo) - ver `hand_sign_tracker.HandSignTracker.last_detection`/
`hold_elapsed`/`hold_needed` y `main.py` (telemetry del HUD), commit `393e9ba`.

**Y-V1 — score real por sello** (los 14, con forma correcta):

| Sello | Score | Disparó |
|---|---|---|
| Tora | 0.83 | sí (captura real guardada en `captures/`) |
| Ushi | 0.89 | sí |
| U | 0.87 | sí |
| Uma | 0.94 | sí |
| Hitsuji | 0.78 | sí (el más ajustado del zodíaco) |
| Saru | 0.86 | sí |
| Inu | 0.79 | sí (pasó umbral, confirmado por score) |
| I (Boar) | — | sí (bloqueó la sesión real - LOCK_SESSION) |
| Ne | 0.84 | sí |
| Mi | 0.89-0.90 | sí |
| Tori | 0.87 | sí |
| Tatsu | 0.82 | sí (necesitó reintento - la primera forma no llegó a 0.7) |
| Mizunoe | 0.76 | sí (pasó umbral) |
| Gassho | 0.43 -> 0.91 | sí, recién tras corregir postura (cerró la app real - CLOSE_APP) |

Rango real con forma correcta: **0.76-0.94**. Confirma el rango medido en
Y-01 con las fotos estáticas (0.82-0.93) - la cámara en vivo no lo empeora
de forma relevante.

**Y-V2 — costo real**: FPS con 1 mano ~21-33, con 2 manos ~16-22 (mismo
rango de variación con o sin el modelo corriendo - la varianza de DroidCam
domina la medición, no se puede aislar limpiamente el costo de ~8ms que ya
midió Y-01 con este instrumento). No contradice la medición de Y-01; no la
reemplaza tampoco.

**Y-V3 — falso positivo real encontrado**: armar Ne (manos juntas cerca de
la cara) pasa, en el camino, por una forma que se lee como "2 puños
juntos" - si se sostiene ese tránsito más de `PAUSE_HOLD_SECONDS` (1.2s),
dispara `TOGGLE_ACTIVE` (pausa) sin querer, dos veces en esta sesión. No es
un sello inventado disparando solo (los 14 sellos en sí no dieron ningún
falso positivo cruzado), pero sí una colisión real entre el gate de 2 manos
"clásico" (`gestures.py`, `_is_fist`/`both_fists`) y el sello detectado por
el modelo - **causa raíz**: el modelo corre y acumula hold en main.py
completamente aparte de `_process_two_hand_gestures()`, así que nunca hereda
la jerarquía que sí protege a JJK_GOJO_DOMAIN (que sigue viviendo adentro de
esa función). Fix: ver Y-08 más abajo.

**Y-V4 — umbral y hold**: **no se ajustan**. 0.7 discrimina bien (Gassho mal
hecho: 0.43, filtrado correctamente; bien hecho: 0.91) y 1.2s se sintió
cómodo en el uso real, sin quejas.

---

## 9. Estado final esperado

- Los sellos que la app detecta son **los reales**, verificados contra las fotos del
  dataset que entrenó al modelo — no formas derivadas de suposiciones.
- Desaparece la clase de bug que originó todo esto: ya no hay umbrales geométricos de
  sellos que calibrar, así que no hay nada que "no se reconozca bien" por estar
  buscando la forma equivocada.
- El costo por frame **baja** en el caso común (una mano: el modelo no corre) y sube
  ~8 ms sólo cuando hay dos manos en cuadro.
- `gestures.py` pierde toda la geometría de sellos y se queda con lo que sí le
  corresponde: puntero, pinches, scroll, zoom, volumen y los gestos que el modelo no
  cubre (JJK, corazón coreano, clap, shaka).
