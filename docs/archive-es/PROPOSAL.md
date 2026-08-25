# PROPOSAL

> **Archivado.** Documento histórico en español. La versión vigente y consolidada (inglés) está en [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

Refactorizar el prototipo monolítico (`jarvis-camera-sensor-like-holograph.md`) en un proyecto de 6 módulos chicos (`config`, `os_native`, `voice`, `hud_keyboard`, `gestures`, `main`), agregar voz Jarvis offline con gesto de silencio, y dejarlo empaquetable como ejecutable portable vía PyInstaller en las tres plataformas.

Sin dependencias nuevas más allá de `pyttsx3` (TTS offline, ya soportado nativamente en Windows/macOS/Linux sin requerir claves ni internet).

No se toca el mapeo de gestos original salvo agregar uno nuevo (silencio) que no colisiona con los existentes (ver tabla de exclusión mutua en `SPEC.md`).
