# Requirements

> **Archivado.** Documento histórico en español. La versión vigente y consolidada (inglés) está en [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Funcionales

| ID | Requisito |
|----|-----------|
| FR-1 | Mover el puntero con el índice (landmark 8), suavizado por EMA. |
| FR-2 | Click izquierdo / drag con pinch pulgar(4)+índice(8) < 30px. |
| FR-3 | Click derecho con pinch pulgar(4)+medio(12) < 30px. |
| FR-4 | Scroll vertical con índice+medio extendidos. |
| FR-5 | Zoom (Ctrl+Scroll) con pinch pulgar(4)+anular(16). |
| FR-6 | Toggle de teclado HUD con palma abierta (4 dedos extendidos, pulgar separado). |
| FR-7 | Teclado virtual multilingüe: español (ñ, acentos), símbolos, emojis. |
| FR-8 | Control de volumen (subir/bajar/mute) con pinch pulgar+meñique + movimiento vertical. |
| FR-9 | Captura de pantalla con gesto pulgar+anular pinch, índice/meñique recogidos. |
| FR-10 | Bloqueo de sesión con gesto Shaka (pulgar+meñique extendidos) sostenido > 1.5s. |
| FR-11 | Voz Jarvis (offline) anuncia en español: inicio, bloqueo, captura, toggle de teclado. |
| FR-12 | Gesto de silencio (mano abierta, pulgar recogido hacia el meñique) interrumpe la voz al instante. |
| FR-13 | Panel con la lista de gestos, como ventana nativa de Windows anclada a una esquina de la pantalla (no dibujado dentro de la ventana de cámara). Translúcido, no-clickeable (click-through), con transparencia ajustable en caliente (`+`/`-`) y toggle de visibilidad (`h`). |
| FR-14 | Globo translúcido sobre toda la pantalla (no solo la ventana de cámara) al disparar una acción discreta (bloqueo, captura, silencio, teclado, volumen, zoom, click derecho, pausa/reanudación, cierre), con auto-desaparición ~1.3s. |
| FR-15 | Detección de hasta 2 manos simultáneas, con lateralidad (Left/Right) corregida según si la cámara está en modo espejo o no. |
| FR-16 | Gesto maestro a 2 manos: 2 puños juntos sostenidos 1.2s activa/desactiva la lectura de gestos (pausa también el puntero; el gesto de pausa/reanudación y el de cierre siguen funcionando estando en pausa). |
| FR-17 | Gesto maestro a 2 manos: ambas manos en Shaka sostenidas 1.5s cierra la aplicación. |
| FR-18 | Modo espejo conmutable en caliente (tecla `m`) — cámara frontal (espejada) vs. trasera/externa (sin espejar), sin reiniciar la app. |

## No funcionales

| ID | Requisito |
|----|-----------|
| NFR-1 | ≤ 7% CPU en quad-core, ≤ 30ms de latencia de gesto. |
| NFR-2 | Dependencias mínimas: `opencv-python`, `mediapipe`, `pyautogui`, `numpy`, `pyttsx3`. |
| NFR-3 | Multiplataforma: Windows, macOS, Linux — sin ramas de código específicas fuera de `os_native.py`. |
| NFR-4 | Empaquetable como ejecutable portable (PyInstaller) sin instalar Python en el equipo destino. |
| NFR-5 | Todo el procesamiento es local — sin llamadas de red, sin telemetría. |

## Fuera de alcance (esta fase)

- Reconocimiento de lenguaje natural por micrófono y control por LLM (ver [`ROADMAP.md`](ROADMAP.md)).
- Soporte multi-usuario (2 manos sí están soportadas, ver FR-15).
- Personalización de gestos vía UI (hoy se ajustan en `src/jarvis/config.py`).
