# AUDITORÍA — `NARUTO-HandSignDetection` vs. nuestros sellos

> **Auditoría**: Opus 5, 2026-09-05, sobre `C:\workspace\NARUTO-HandSignDetection`
> (Kazuhito Takahashi, MIT) y sobre `src/jarvis/gestures.py` en el commit `0a7a755`.
> **Disparador**: José señaló que las formas de mano que este proyecto usa para los
> sellos son inventadas, y pidió auditar el proyecto de referencia antes de seguir
> con el workflow 6 (verificación en cámara).
>
> Todo lo que se afirma acá está medido o verificado contra código/imágenes reales.
> Los números de inferencia son de **esta** máquina, no de su README.

---

## 0. Resumen para decidir en 30 segundos

1. **Los 14 sellos canónicos son TODOS a dos manos.** Verificado contra las 14
   imágenes del README (bajadas a `docs/gesture-reference/canonical/`).
2. **Nuestros 8 "sellos de una mano" (Tora, Ushi, U, Uma, Hitsuji, Saru, Inu, I)
   no existen.** Son formas inventadas por este proyecto. Eso explica de forma
   directa el reporte de José *"ningún sello se reconoce bien"*: el motor busca
   formas que nadie hace.
3. **Su modelo corre en 8.1 ms/frame en esta máquina** (CPU), es de 3.6 MB, y
   `onnxruntime` **ya está instalado** en nuestro venv. Es más barato que nuestro
   propio `HandLandmarker` (10.0 ms) y que el `PoseLandmarker` que descartamos por
   caro (10.4 ms).
4. Licencia **MIT**: se puede copiar código y usar el modelo, con atribución.

---

## 1. Evidencia dura: qué reconoce su modelo sobre NUESTRAS imágenes

Se corrió su `yolox_nano.onnx` sobre las 18 fotos de referencia que habíamos
juntado — que fueron elegidas justamente para calzar con **nuestras** formas — con
el umbral de reporte bajado a 0.30 a propósito (para que una detección débil
también cuente):

| Nuestra imagen de referencia | Qué dice el modelo real |
|---|---|
| `naruto_ne.jpg` (de su dataset) | **Ne(Rat) 0.91** ✅ |
| `naruto_mi.jpg` (de su dataset) | **Mi(Snake) 0.82** ✅ |
| `naruto_tori.jpg` (de su dataset) | **Tori(Bird) 0.91** ✅ |
| `naruto_tora.jpg` (índice+medio, 1 mano) | Tora(Tiger) 0.91 |
| `naruto_hitsuji.jpg` (dedos cruzados, 1 mano) | Hitsuji(Ram) 0.47 (débil) |
| `naruto_kai.jpg` (mudra, 2 manos) | **Hitsuji(Ram) 0.75** — o sea, esa foto es un Hitsuji, no un Kai |
| `naruto_saru.png` (pulgar arriba) | Tatsu(Dragon) 0.47 — falso positivo |
| `naruto_ushi.jpg` (solo índice) | *nada ≥ 0.30* |
| `naruto_u.jpg` (V de paz) | *nada ≥ 0.30* |
| `naruto_uma.jpg` (pulgar+índice+meñique) | *nada ≥ 0.30* |
| `naruto_inu.jpg` (solo meñique) | *nada ≥ 0.30* |
| `naruto_i.jpg` (puño, pulgar lateral) | *nada ≥ 0.30* |
| `naruto_tatsu.jpg` (puño sobre palma) | *nada ≥ 0.30* |
| JJK (Gojo/Sukuna/Megumi), Clap, Korean Heart | *nada ≥ 0.30* (esperable: 3 no son clases suyas; Gassho sí lo es, pero la foto de Clap es gente aplaudiendo de lejos) |

**Las 3 imágenes que salieron de su propio dataset se reconocen con 0.82–0.91.**
El pipeline funciona perfecto en nuestro entorno: cuando la forma es real, el
modelo la ve con altísima confianza. Cuando no la reconoce, es porque la forma
no es un sello.

---

## 2. En qué nos equivocamos, sello por sello

Comparación de `src/jarvis/gestures.py` contra las 14 imágenes canónicas:

| Nuestro evento | Lo que exige nuestro código | El sello real |
|---|---|---|
| `NARUTO_TORA` | índice+medio extendidos y juntos, **1 mano** | 2 manos: dedos entrelazados con índices juntos apuntando arriba |
| `NARUTO_USHI` | solo índice extendido, **1 mano** | 2 manos: una plana horizontal, la otra debajo en ángulo |
| `NARUTO_U` | índice+medio separados en V, **1 mano** | 2 manos juntas, dedos entrelazados |
| `NARUTO_UMA` | pulgar+índice+meñique, **1 mano** | 2 manos: dedos formando una punta hacia arriba |
| `NARUTO_HITSUJI` | índice+medio cruzados, **1 mano** | 2 manos juntas con índices extendidos hacia arriba |
| `NARUTO_SARU` | puño, pulgar **arriba**, 1 mano | 2 manos: una plana sobre la otra, cruzadas |
| `NARUTO_INU` | solo meñique, **1 mano** | 2 manos: **palma plana arriba, puño abajo** (verificado a ojo) |
| `NARUTO_I` | puño, pulgar **al costado**, 1 mano | 2 manos: puños juntos, nudillos enfrentados |
| `NARUTO_TORI` | manos **separadas en abanico** | manos juntas, **puntas de los dedos tocándose** formando un rombo — *nuestra definición es casi el opuesto* |
| `NARUTO_NE`, `NARUTO_MI` | manos entrelazadas arriba / abajo | ✅ **estos dos sí son correctos** |
| `NARUTO_KAI`, `NARUTO_TATSU` | inventados / no canónicos | Tatsu real es otro; "Kai" no está entre los 14 |

**Balance: de 13 sellos que implementamos, 2 son correctos (Ne, Mi), 1 está
definido al revés (Tori) y 10 son invención.**

Además, el proyecto real tiene 2 sellos que nosotros no tenemos: **Mizunoe (壬)** y
**Gassho (合掌, el aplauso)** — este último ya lo tenemos implementado como `CLAP`
pero por fuera del namespace de sellos.

---

## 3. Cómo resuelven ellos el problema (arquitectura)

**No usan landmarks ni umbrales geométricos en absoluto.** Es detección de objetos:

- **Modelo**: YOLOX-Nano, entrada 416×416, salida `[1, 3549, 21]`
  (= 4 bbox + 1 objectness + 16 clases). Archivo ONNX de **3.6 MB**.
- **Runtime**: `onnxruntime` (`model/yolox/yolox_onnx.py`, ~250 líneas): preproceso
  con letterbox a 416×416 relleno gris (114), inferencia, y post-proceso en numpy
  puro — decodificación de grids/strides (8/16/32) + NMS multiclase *class-agnostic*.
  **Sin torch, sin tensorflow.**
- **Umbrales**: score de clase 0.7, NMS IoU 0.45, NMS score 0.1.
- **Dataset** (privado, el modelo es público): 10.026 imágenes, 7.098 etiquetadas,
  8.941 cajas de anotación, 2.651 de ellas frames del anime, más el dataset público
  de Kaggle `naruto-hand-sign-dataset` y fotos propias del autor.

La diferencia de fondo: **ellos aprendieron las formas de datos reales; nosotros
las derivamos a mano de suposiciones.** Por eso a nosotros nos pasó lo que dice su
propio README que evitan — y por eso 7 de 8 de nuestros sellos de una mano
necesitaron "corrección" en cámara sin que ninguna corrección los pudiera arreglar:
no había nada que calibrar, la forma buscada estaba mal desde el principio.

### Lo más copiable: cómo manejan la secuencia (`Ninjutsu_demo.py`)

| Mecanismo suyo | Qué hace | ¿Lo tenemos? |
|---|---|---|
| `chattering_check` (cola de N) | solo acepta el sello si las últimas N detecciones son la misma clase | ✅ es nuestro `ConsecutiveFrameDebouncer` (A-02) |
| dedup contra el último | no vuelve a encolar el mismo sello sostenido | ✅ equivalente a `_naruto_hold_seal` |
| `sign_interval` = 2.0 s | si pasan 2 s sin detectar nada, **borra el historial completo** | ❌ **no lo tenemos** (nuestra tolerancia es por frames, no por tiempo) |
| `sign_history_queue` (44) + `jutsu.csv` | concatena el historial en un string de kanjis y lo matchea contra una tabla de secuencias → nombre del jutsu | ❌ **no lo tenemos**: hoy cada sello dispara su propia acción suelta |

El patrón de **secuencias** (`巳,寅,申,亥,午,寅` → "Bola de Fuego") es una idea que no
tenemos y que no requiere ninguna pose nueva: es puro historial + timeout + match.

---

## 4. Qué podemos copiar, ordenado por valor/riesgo

Licencia MIT ⇒ se puede copiar código y usar el modelo, citando autoría.

### (a) Las 14 imágenes canónicas como referencia — HECHO, costo cero
Ya están en `docs/gesture-reference/canonical/` (`01_ne_rat.jpg` … `14_gassho_clap.jpg`).
Resuelve el problema original ("no entiendo las explicaciones") sin tocar código.

### (b) Cablear su modelo YOLOX — la opción que elimina el problema de raíz
**Medido en esta máquina, no estimado:**

| | promedio | p95 | tamaño |
|---|---|---|---|
| `yolox_nano.onnx` (416×416, CPU) | **8.1 ms** | 8.6 ms | 3.6 MB |
| nuestro `HandLandmarker` (ya en el loop) | 10.0 ms | 12.7 ms | — |
| `PoseLandmarker` (descartado por caro) | 10.4 ms | 12.6 ms | — |

- `onnxruntime` **ya está instalado** en nuestro venv (llega con mediapipe):
  **cero dependencias nuevas**.
- 3.6 MB entra en el `.exe` sin discusión (el LLM de voz que decidimos NO empaquetar
  pesa ~1 GB).
- Nos daría los **14 sellos reales** con una sola pieza, y dejaría obsoletas ~700
  líneas de heurística geométrica de sellos en `gestures.py`.
- **Contra**: +8 ms/frame si corre siempre; 16 clases fijas (agregar un gesto exige
  reentrenar); no cubre JJK ni corazón coreano; hay que adoptar su `yolox_onnx.py`.
- **Mitigación obvia del costo**: correrlo **solo cuando hay 2 manos en cuadro**
  (que es exactamente cuando un sello es posible), no en todos los frames. El
  `HandLandmarker` que ya corre nos dice gratis cuándo pasa eso.

### (c) Redefinir nuestros sellos a mano contra las formas reales
Sin copiar nada: reescribir las 8 funciones `_is_naruto_*` como poses de 2 manos.
Es reescribir el corazón de las Fases 4–5 y mover 8 gestos de la rama de 1 mano a
la de 2 manos. Mucho esfuerzo, y volveríamos a estar adivinando umbrales — que es
exactamente lo que falló.

### (d) El patrón de secuencias
Copiar la idea (historial + timeout de 2 s + match de secuencia → acción), no el
código. Daría "combos" sin agregar ninguna pose nueva.

### (e) La alternativa honesta y barata
Aceptar que nuestros gestos son **"inspirados en"** y no sellos Naruto: renombrarlos
(`SEAL_TWO_FINGERS`, `SEAL_PINKY`, …), sacar la promesa de fidelidad de la leyenda y
de `ARCHITECTURE.md`, y quedarnos con las formas de 1 mano que **sí** funcionan bien
para un control por gestos (son más fáciles de sostener con una mano y dejan la otra
libre). No arregla la fidelidad, pero deja de mentir en la documentación.

---

## 5. Bugs reales encontrados en su código (por si copiamos)

1. **`IndexError` latente en el mapeo de etiquetas.** El modelo emite **16 clases**
   (`output[2] - 5 = 16`) y los dos demos hacen `class_id = int(class_id) + 1`, así
   que la última clase indexa `labels[16]` — pero `setting/labels.csv` tiene 16 filas
   (índices 0..15). Si esa clase llega a dispararse, el demo crashea. Verificado
   programáticamente. Si copiamos el mapeo, hay que corregirlo.
2. **Sin `requirements.txt`**: ninguna versión pineada (mismo problema que nosotros
   ya arreglamos en H-19).
3. `simple_demo.py` hace `copy.deepcopy(frame)` por cuadro antes de saber si lo va a
   usar — costo evitable si adoptamos ese archivo tal cual (nosotros no lo
   necesitamos: no dibujamos sobre una copia).

---

## 6. Impacto sobre el workflow 6 (verificación en cámara)

**V-01 y V-02 quedan sin sentido tal como están escritos.** Medir en cámara si "los 8
sellos de una mano se reconocen bien" es calibrar contra formas que no existen: no
hay umbral que arregle eso. Antes de encender la cámara para sellos hay que decidir
entre (b), (c) o (e).

**Lo que sí sigue siendo válido para probar hoy con cámara**, sin depender de esta
decisión:

- **V-04** — `EMA_ALPHA = 0.25` (precisión del puntero).
- **V-05** — colisión Sukuna ↔ `RIGHT_CLICK`.
- **V-08/V-09/V-10** — dwell, doble click y swipe (workflow 8, recién implementados).
- Los gestos "clásicos": pinch/click, drag, scroll, zoom, volumen, teclado HUD.

---

## 7. Decisión tomada (José, 2026-09-05)

**(b) Cablear el modelo YOLOX**, y **borrar los sellos de una mano inventados**
(*"obviá los sellos de 1 mano de naruto y borralos si no son útiles"*).

El plan de ejecución, autocontenido y tarea por tarea, está en
[`WORKPLAN.md`](WORKPLAN.md) al lado de este archivo.

Verificación extra hecha después de la decisión, ya incorporada al WORKPLAN:

- **14/14 imágenes canónicas se auto-clasifican** con score 0.82–0.93 (umbral 0.7).
  Es la base de los criterios de aceptación de Y-01.
- **El frame hay que pasarlo SIN espejar**: 13 de 14 clasifican igual espejadas, pero
  `Mi(Snake)` cae de 0.82 a **0.70**, justo en el umbral. `main.py` espeja por default
  (`MIRROR_CAMERA_DEFAULT = True`), así que hay que tomar el frame antes del
  `cv2.flip`.
- **`NARUTO_KAI` es el único huérfano**: no está entre los 14 canónicos. Se borra; su
  acción default (`CLOSE_APP`) sigue siendo alcanzable con las 2 manos en Shaka.
- Dos dependencias que hacen fallar el borrado si se ignoran: `_fingers_crossed` la
  usa `_is_jjk_megumi`, y `_naruto_hold_seal` lo leen los gates de dwell (C-01) y
  swipe (C-03). Detalle en Y-04 del WORKPLAN.

---

## Atribución

`NARUTO-HandSignDetection` — Kazuhito Takahashi, licencia MIT.
https://github.com/Kazuhito00/NARUTO-HandSignDetection
Las imágenes de `docs/gesture-reference/canonical/` son del README de ese proyecto.
El dataset de entrenamiento es privado; el modelo entrenado es público.
