# Roadmap — Control por voz en lenguaje natural

> **Archivado.** Documento histórico en español. Resumen vigente (inglés) en la sección "Future work" de [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

No implementado. Documentado como siguiente fase, a implementar solo cuando se confirme.

## Objetivo

Que Jarvis entienda comandos hablados en lenguaje natural ("cerrá esta ventana", "subí el volumen al 50%") captados por micrófono, y los traduzca a acciones del sistema, **sin latencia perceptible y sin depender de la nube**.

## Enfoque propuesto (todo local, bajo costo)

1. **STT (voz→texto) local**: `faster-whisper` (modelo `tiny`/`base`, cuantizado) o `whisper.cpp` — corre en CPU, streaming por bloques cortos (~0.5–1s) para minimizar latencia.
2. **LLM ligero local** para interpretar intención y mapear a una acción concreta (no para conversar libremente): modelo pequeño tipo `Phi-3-mini` o `Llama-3.2-1B/3B` cuantizado (GGUF) vía `llama.cpp`/`ollama`, con un prompt de function-calling restringido al set de acciones ya soportadas por `gestures.py` / `os_native.py`.
3. **Despacho**: el LLM devuelve una acción estructurada (ej. `{"action": "volume_set", "value": 50}`), validada contra un esquema fijo antes de ejecutar — nunca ejecuta texto libre.
4. **Activación**: palabra de activación local ("Jarvis") detectada con un modelo wake-word chico (ej. `openWakeWord`) para no correr STT+LLM todo el tiempo y ahorrar CPU.

## Por qué no ahora

Agrega dependencias pesadas (modelos de cientos de MB, runtime de inferencia) y complejidad de sincronización audio/gesto que no está pedida todavía. Se deja documentado para no perder el diseño, pero se implementa en una fase aparte cuando se confirme.
