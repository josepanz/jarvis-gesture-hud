# TASKS

> **Archivado.** Documento histórico en español. La versión vigente y consolidada (inglés) está en [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

- [x] `config.py` con umbrales, cooldowns y colores centralizados.
- [x] `os_native.py` — lock/screenshot/volumen multiplataforma.
- [x] `voice.py` — TTS Jarvis en hilo separado + `silence()`.
- [x] `hud_keyboard.py` — layouts es/num/emoji, draw + click.
- [x] `gestures.py` — motor de gestos puro (sin I/O), incluye gesto de silencio.
- [x] `main.py` — loop de cámara y despacho de eventos a los módulos anteriores.
- [x] `run.py` — entry point portable (sin instalar el paquete).
- [x] `legend.py` — contenido del listado de gestos (consumido por el overlay nativo).
- [x] `overlay.py` — globos translúcidos + panel nativo de gestos en una esquina, click-through en Windows, transparencia ajustable.
- [x] Soporte de 2 manos en `hand_tracker.py`/`gestures.py`, con lateralidad corregida según modo espejo.
- [x] Gestos maestros a 2 manos: pausar/reanudar lectura de gestos, cerrar la app.
- [x] Modo espejo conmutable en caliente (tecla `m`) para cámara frontal vs. trasera.
- [x] `build/jarvis.spec` + scripts por SO para PyInstaller (incluye datos de `mediapipe`).
- [x] README, REQUIREMENTS, ROADMAP.
- [x] Build de `Jarvis.exe` con PyInstaller (117MB, onefile) y smoke test: arrancó, cargó modelo y cámara, corrió 10s sin errores en el log, ~260MB de RAM, terminado limpiamente. Hecho en esta misma máquina (con Python instalado) — sigue pendiente una prueba real en una máquina *sin* Python, que requiere acceso a otro equipo.
- [ ] Fase de control por lenguaje natural (ver `../ROADMAP.md`) — no iniciada, deliberadamente fuera de esta fase.
