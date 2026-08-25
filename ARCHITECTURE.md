# Architecture & Status — Jarvis Gesture HUD

Single source of truth for the project's design, current state, decisions, and known
limitations. Supersedes the original Spanish planning docs, which are kept for history
under [`docs/archive-es/`](docs/archive-es/).

## Overview

Jarvis Gesture HUD is a webcam-driven hand-gesture controller for the desktop: pointer,
clicks, drag, scroll, zoom, a floating on-screen keyboard, and OS-level actions (lock
session, screenshot, volume), all offline and cross-platform (Windows/macOS/Linux). It
adds a spoken "Jarvis" voice for feedback, a gesture to interrupt that voice instantly,
support for two hands with master gestures (pause/resume, close app), a native
always-on-top gesture legend, and screen-wide translucent notification bubbles.

The project started from a single-file prototype (kept for reference at
[`docs/original-prototype.md`](docs/original-prototype.md)) and was refactored into a
small modular Python package (`src/jarvis/`), packaged as a portable executable via
PyInstaller.

## Status

All items below are implemented and manually smoke-tested on a real Windows machine
(camera, voice engine, native overlay windows, and the packaged `.exe` were all actually
run, not just written).

| Area | State |
|---|---|
| Core gesture engine (pointer, click/drag, right-click, scroll, zoom, volume, screenshot, lock) | Done |
| Voice feedback (offline TTS, Spanish) + silence gesture | Done — tested: engine finds an installed `es-*` voice and speaks/interrupts correctly |
| Floating virtual keyboard (ES layout, numbers/symbols, emoji) | Done |
| Two-hand tracking + master gestures (pause/resume, close app) | Done — unit-tested with synthetic landmarks |
| Mirror-mode toggle (front vs. rear camera) with handedness correction | Done |
| Native gesture legend (screen-corner overlay, click-through, adjustable opacity) | Done — click-through verified at the WinAPI level on this machine |
| Screen-wide translucent notification bubbles | Done |
| Portable executable (PyInstaller) | Built and smoke-tested (10s run, clean log, ~260MB RAM, no crash) on this machine. **Not yet verified on a machine without Python installed** — see Limitations |
| Natural-language voice control (STT + local LLM) | Not implemented — deliberately deferred, see Future Work |

## Architecture

```
Camera (640x480) -> MediaPipe HandLandmarker -> EMA filter -> GestureEngine -> events
                                                                    |
                    +-----------------------------------------------+----------------------------+
                    v                                v                                            v
              HUDKeyboard (in-frame overlay)   CrossPlatformOS (lock/volume/screenshot)     VoiceJarvis (TTS thread)
                    |                                |                                            |
                    +------------------ pyautogui (mouse/keyboard/scroll) -----------------------+

                                          ScreenOverlay (Tkinter, native desktop windows)
                                          - notification bubbles anywhere on screen
                                          - persistent gesture-legend panel in a screen corner
```

### Modules (`src/jarvis/`)

- **`hand_tracker.py`** — `HandTracker` wraps MediaPipe's **Tasks API** (`HandLandmarker`), not the legacy `mp.solutions` API. Downloads and caches the `.task` model under `assets/`, resolving the path correctly both in dev and inside a PyInstaller `.exe` (`sys._MEIPASS`). `process(frame_rgb, mirrored) -> list[Hand]` returns 0–2 hands, each with `landmarks` and a `handedness` label already corrected for the current mirror mode.
- **`config.py`** — every tunable constant (pinch thresholds, cooldowns, EMA alpha, HUD colors, hold durations, mirror default). Single place to tune behavior without touching logic.
- **`os_native.py`** — `CrossPlatformOS`: static methods `lock_session`, `take_screenshot`, `volume_up/down/mute`. The only module with an `if platform.system() == ...` branch.
- **`voice.py`** — `VoiceJarvis`: a dedicated thread + `queue.Queue` so speaking never blocks the camera loop. `speak(text)` enqueues; `silence()` clears the queue and calls `engine.stop()` to cut off speech immediately.
- **`hud_keyboard.py`** — `HUDKeyboard`: on-screen keyboard layouts (Spanish/numeric/emoji), `draw(frame, cursor)`, `handle_click(cursor) -> key | None`. Still drawn inside the camera window (unlike the legend, this one is tied to the pinch/cursor interaction happening there).
- **`legend.py`** — content only: `build_legend_text()` builds the multi-line gesture list string. No drawing logic — it used to render on the camera frame via `cv2.addWeighted`; that was removed in favor of a native overlay window (see below).
- **`overlay.py`** — `ScreenOverlay`, built on Tkinter (stdlib, zero new dependencies):
  - `show_bubble(text, x, y)` — a transient translucent toast at any screen position, self-destroys via `after()`.
  - `init_legend(text, corner)` / `set_legend_visible()` / `adjust_legend_alpha()` — a persistent panel anchored to a screen corner, translucent, with runtime opacity control.
  - Both use `_make_click_through(window)`: on Windows this applies `WS_EX_LAYERED | WS_EX_TRANSPARENT` to the real HWND (obtained via `GetParent(winfo_id())`) through `ctypes` — a well-known, dependency-free trick, verified working on this machine (see Decisions). No-op elsewhere.
  - `pump()` is called once per camera frame instead of `mainloop()`, because Tk is not thread-safe and a separate UI thread would race with the camera loop.
- **`gestures.py`** — `GestureEngine`: pure logic, no I/O. `process(hands, w, h, screen_w, screen_h) -> (screen_xy | None, cam_xy | None, events)`. Single-hand gestures always use `hands[0]` and are entirely skipped when `active` is `False` (paused) — in that case `screen_xy` is `None`, so `main.py` neither moves the mouse nor draws the keyboard. The two master, two-hand gestures (`TOGGLE_ACTIVE`, `CLOSE_APP`) are evaluated *before* checking `active`, so pause can always be undone and the app can always be closed.
- **`main.py`** — `JarvisApp`: owns the camera loop, calls `GestureEngine.process`, dispatches each event to the relevant module, draws the keyboard/pause banner, and handles the keyboard shortcuts (`q`/`h`/`m`/`+`/`-`).

### Gesture map

| Gesture | Action |
|---|---|
| Index fingertip (landmark 8) moved | Mouse pointer (EMA-smoothed) |
| Pinch thumb(4)+index(8) < 30px | Left click / drag / HUD keyboard key select |
| Pinch thumb(4)+middle(12) < 30px | Right click |
| Index+middle extended, ring curled | Vertical scroll |
| Pinch thumb(4)+ring(16), index extended | Zoom (Ctrl+Scroll) |
| Open palm (index/middle/ring/pinky extended, thumb spread >60px) | Toggle on-screen keyboard |
| Pinch thumb(4)+pinky(20) + vertical movement | Volume up/down |
| Thumb+ring pinch with index and pinky curled | Screenshot |
| Shaka (thumb+pinky extended, index/middle curled) held 1.5s | Lock session |
| Open palm with thumb tucked toward the pinky base | **Voice silence** (interrupts TTS instantly) |
| Both hands closed fists, held 1.2s | **Pause/resume gesture reading** (works even while paused) |
| Both hands in Shaka, held 1.5s | **Close Jarvis** (works even while paused) |

Keyboard shortcuts (camera window focused): `q` quit, `h` toggle legend visibility, `m`
toggle mirror mode, `+`/`-` legend opacity.

### Camera mirroring & handedness

- **Front/selfie** (default, `config.MIRROR_CAMERA_DEFAULT = True`): the frame is flipped
  (`cv2.flip`) before processing — natural for a built-in laptop webcam where the user
  expects a mirror-like view.
- **Rear/external**: not flipped. MediaPipe assumes the input image is already mirrored
  when estimating handedness (Left/Right); when we don't flip, `hand_tracker.py` swaps
  that label so it matches the real hand.
- Toggled at runtime with `m`, no restart needed.
- Single-hand gestures (pinch, open palm, shaka, etc.) only rely on relative landmark
  positions and are unaffected by mirroring. Handedness only matters for two-hand
  gestures that need to know *which* hand is which — the two implemented so far
  (both-fists, both-shaka) don't need that distinction, since they just check that both
  detected hands independently satisfy the same per-hand condition.

### Voice (Jarvis)

- Engine: `pyttsx3` (offline, no network).
- Language: picks an installed `es-*` voice if present, falls back to the system default.
  Verified on this machine: it correctly selected "Microsoft Sabina — Spanish (Mexico)"
  over the installed English voice.
- Non-blocking: a queue drained by a dedicated thread, so speaking never affects the
  camera frame rate.
- The silence gesture clears the queue and calls `engine.stop()` — an interrupt, not a
  permanent mute; the next queued phrase (if any) is dropped too, since the gesture is
  meant to shut Jarvis up right now.

### Native OS integration

- **Lock**: Windows `ctypes.windll.user32.LockWorkStation()` · macOS `CGSession -suspend`
  · Linux `xdg-screensaver lock || gnome-screensaver-command -l || loginctl lock-session`.
- **Volume/Mute**: OS media keys via `pyautogui.press(...)` — identical call on all three
  platforms.
- **Screenshot**: `pyautogui.screenshot()`, saved to `captures/` with a timestamp.

### Visual feedback

- **Native gesture legend**: a real, borderless, always-on-top OS window (Tkinter
  `Toplevel`) anchored to a screen corner — no longer drawn on the camera frame.
  Translucent (`-alpha`), click-through on Windows (doesn't block clicks to whatever is
  behind it), opacity adjustable with `+`/`-`, visibility toggled with `h`.
- **Screen-wide translucent bubbles**: firing a discrete event (lock, screenshot,
  silence, keyboard toggle, volume, zoom, right-click, pause/resume, close) shows a
  translucent toast at the current on-screen cursor position — anywhere on the desktop,
  not just inside the camera window — that self-destroys after ~1.3s. Click/drag/scroll
  are deliberately excluded: they fire many times per second and would flood the screen
  with toasts instead of helping.

### Packaging

`build/jarvis.spec` (PyInstaller, onefile) bundles `mediapipe`'s data files and the
downloaded `hand_landmarker.task` model, plus `pyttsx3` driver hidden-imports for all
three platforms. `build/build_windows.ps1` / `build_macos.sh` / `build_linux.sh` are
per-OS convenience wrappers (PyInstaller builds natively for the host OS — there's no
cross-compilation). Built and smoke-tested on this machine: `Jarvis.exe`, 117MB, ran 10s
with a clean log and ~260MB RAM before being terminated.

## Requirements (traceability)

### Functional

| ID | Requirement |
|----|-----------|
| FR-1 | Move the pointer with the index fingertip (landmark 8), EMA-smoothed. |
| FR-2 | Left click / drag via pinch thumb(4)+index(8) < 30px. |
| FR-3 | Right click via pinch thumb(4)+middle(12) < 30px. |
| FR-4 | Vertical scroll with index+middle extended. |
| FR-5 | Zoom (Ctrl+Scroll) via pinch thumb(4)+ring(16). |
| FR-6 | Toggle on-screen keyboard with an open palm (4 fingers extended, thumb spread). |
| FR-7 | Multilingual virtual keyboard: Spanish (ñ, accents), symbols, emoji. |
| FR-8 | Volume control (up/down/mute) via pinch thumb+pinky + vertical movement. |
| FR-9 | Screenshot via thumb+ring pinch, index/pinky curled. |
| FR-10 | Lock session via Shaka gesture (thumb+pinky extended) held > 1.5s. |
| FR-11 | Offline Jarvis voice announces in Spanish: startup, lock, screenshot, keyboard toggle. |
| FR-12 | Silence gesture (open hand, thumb tucked toward pinky) interrupts voice instantly. |
| FR-13 | Gesture legend as a native, screen-corner-anchored window (not drawn in the camera window). Translucent, click-through, runtime-adjustable opacity (`+`/`-`), visibility toggle (`h`). |
| FR-14 | Screen-wide translucent bubble on a discrete action (lock, screenshot, silence, keyboard, volume, zoom, right-click, pause/resume, close), auto-dismissing after ~1.3s. |
| FR-15 | Detect up to 2 simultaneous hands, with handedness (Left/Right) corrected for mirror mode. |
| FR-16 | Two-hand master gesture: both fists held 1.2s toggles gesture reading on/off (also pauses the pointer; the toggle and close gestures still work while paused). |
| FR-17 | Two-hand master gesture: both hands in Shaka held 1.5s closes the application. |
| FR-18 | Runtime-togglable mirror mode (`m`) — front (mirrored) vs. rear/external (not mirrored) camera, no restart. |

### Non-functional

| ID | Requirement |
|----|-----------|
| NFR-1 | ≤ 7% CPU on a quad-core, ≤ 30ms gesture-to-action latency. |
| NFR-2 | Minimal dependencies: `opencv-python`, `mediapipe`, `pyautogui`, `numpy`, `pyttsx3`. |
| NFR-3 | Cross-platform: Windows, macOS, Linux — no OS-specific branches outside `os_native.py`. |
| NFR-4 | Packageable as a portable executable (PyInstaller), no Python install required on the target machine. |
| NFR-5 | All processing is local — no network calls, no telemetry. |

### Out of scope (this phase)

- Natural-language microphone control via a local LLM (see Future Work below).
- Multi-user support (two hands for a single user *are* supported, see FR-15).
- UI-based gesture customization (today, tuned by editing `src/jarvis/config.py`).

## Decisions & rationale

- **Modular refactor over the monolithic prototype.** The original single-file script
  (`jarvis-camera-sensor-like-holograph.md`) worked but mixed gesture detection with I/O
  side effects (mouse, voice, OS calls) in one class, making it impossible to test
  gesture logic without a real camera. Splitting `GestureEngine` (pure) from dispatch in
  `main.py` keeps the same per-frame workload (no extra layers) while making gestures
  testable with synthetic landmarks — used throughout this project to verify the
  two-hand master gestures without a webcam.
- **Migrated off `mp.solutions` to the MediaPipe Tasks API.** Google removed the legacy
  `mp.solutions.hands` API from Windows wheels starting at mediapipe 0.10.30 (confirmed
  on this machine — `dir(mp)` no longer exposes `solutions` even at 0.10.35). `hand_tracker.py`
  wraps `HandLandmarker` instead, which requires downloading a `.task` model file once
  (cached under `assets/`, and resolved correctly inside a frozen `.exe` via `sys._MEIPASS`).
- **Fixed two direction bugs while re-implementing scroll/zoom.** The original script
  compared a camera-frame pixel coordinate against a screen-resolution coordinate to
  decide scroll/zoom direction — meaningless once the two use different scales. The
  rewrite uses frame-to-frame vertical deltas (same technique already used for volume),
  which is both correct and consistent across all three "move to change something"
  gestures.
- **Master gestures reuse existing per-hand checks, applied twice.** Rather than
  inventing new pose logic for "both hands," `_is_fist`/`_is_shaka` are the same
  functions used for single-hand gestures, just evaluated once per detected hand. This
  keeps the two-hand feature cheap and consistent with the rest of the engine, and
  avoids needing handedness at all for the two gestures implemented so far.
- **Legend moved out of the camera frame into a native OS window.** Drawing it on the
  cv2 frame (the original approach) meant Hershey-font `cv2.putText` couldn't render
  accents or ñ properly, and it was invisible if the camera window wasn't focused or
  visible. A Tkinter `Toplevel` is a real desktop window: renders full Unicode, can sit
  in a fixed screen corner regardless of the camera window's state, and can be made
  translucent and click-through.
- **Click-through implemented for Windows specifically, not a generic cross-platform
  abstraction.** True click-through overlays are OS-specific (Windows layered windows vs.
  macOS `ignoresMouseEvents` vs. Linux compositor support, which isn't guaranteed at
  all). Building a lowest-common-denominator abstraction across all three would either
  add heavy platform-specific dependencies (e.g., `pyobjc` for macOS) or promise
  behavior Linux can't reliably deliver. Since the actual development and testing
  happened on Windows, the WinAPI trick (`ctypes` + `SetWindowLongW`) was implemented
  and *verified* there (see Status), while other platforms get a documented best-effort
  fallback instead of a false guarantee.
- **Bubbles exclude click/drag/scroll events on purpose.** These fire many times a
  second during normal use; a bubble per event would spam the screen and hurt
  performance (each bubble is a real Tk window). Only discrete, rare events get a
  bubble.
- **Natural-language voice control deferred, not attempted.** It would add heavy
  dependencies (STT + LLM runtime, hundreds of MB of models) and real-time audio/gesture
  synchronization complexity that wasn't requested for this phase. Documented in detail
  below so the design isn't lost, but implemented only when explicitly requested.

## Known limitations

- **Click-through is only guaranteed on Windows.** On macOS/Linux, the legend and bubble
  windows still render but may capture mouse clicks meant for whatever is behind them —
  best-effort, not verified.
- **Tkinter's `-alpha` window transparency depends on the window manager.** Confirmed
  working on this Windows machine; on some Linux compositors it may render fully opaque
  instead of translucent.
- **The portable `.exe` was built and smoke-tested on this development machine, which
  has Python installed.** It ran cleanly for a short session, but a true "clean machine"
  validation (no Python, no dev tools) still needs to happen on a separate physical or
  virtual machine — that's outside what this environment can do.
- **`cv2.putText` (Hershey fonts) cannot render accented characters or `ñ` reliably.**
  This only affects the on-screen virtual keyboard glyphs now (Spanish `ñ`/accents),
  since the legend moved to a Tkinter window that renders Unicode correctly.
- **No automated test suite.** Verification so far is manual smoke-testing (voice,
  overlay, packaging) plus ad hoc unit checks of `GestureEngine` with synthetic
  landmarks, run interactively rather than committed as a test file.

## Future work

See [`docs/archive-es/ROADMAP.md`](docs/archive-es/ROADMAP.md) for the full original
write-up (Spanish). Summary: natural-language voice control via microphone, entirely
local — `faster-whisper`/`whisper.cpp` for speech-to-text, a small local LLM
(`Phi-3-mini` or `Llama-3.2-1B/3B` quantized, via `llama.cpp`/`ollama`) restricted to a
fixed function-calling schema over the actions already implemented in `gestures.py` /
`os_native.py`, and a lightweight local wake-word model so STT+LLM don't run
continuously. Not started — deliberately deferred until requested.
