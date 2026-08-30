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

A second, larger refactor is in progress under an OpenSpec change proposal
(`openspec/changes/multimodal-interaction-core/`) evolving the app from "gesture
string in, pyautogui call out" into a `GestureEvent -> Command -> CommandBus`
architecture, migrated one task at a time with tests and regression checks at each
step (see that folder's `tasks.md` for live progress, and Architecture below for
what's actually wired in today vs. still direct).

## Status

All items below are implemented and manually smoke-tested on a real Windows machine
(camera, voice engine, native overlay windows, and the packaged `.exe` were all actually
run, not just written).

| Area | State |
|---|---|
| Core gesture engine (pointer, click/drag, right-click, scroll, zoom, volume, screenshot, lock) | Done |
| Voice feedback (offline TTS, Spanish) + silence gesture | Done — tested: engine finds an installed `es-*` voice and speaks/interrupts correctly |
| Floating virtual keyboard (ES layout, numbers/symbols, emoji) | Done |
| Two-hand tracking + master gestures (pause/resume, close app, pinch-zoom, secondary-action menu) | Done — unit-tested with synthetic landmarks; testing this way is what caught the Shaka double-fire bug described in Decisions |
| Mirror-mode toggle (front vs. rear camera) with handedness correction | Done |
| Native gesture legend (screen-corner overlay, click-through, adjustable opacity) | Done — click-through verified at the WinAPI level on this machine |
| Screen-wide translucent notification bubbles | Done |
| Portable executable (PyInstaller) | Built and smoke-tested (10s run, clean log, ~260MB RAM, no crash) on this machine. **Not yet verified on a machine without Python installed** — see Limitations |
| `Command`/`CommandBus`/`FeedbackManager` foundation (OpenSpec PHASE 1) | Done — 78 unit tests, plus a real integration check against the live `VoiceJarvis`/`ScreenOverlay` instances |
| Mouse/click/drag/scroll/zoom/keyboard-HUD/system-actions migrated onto `Command`/`CommandBus` (OpenSpec PHASE 2) | Done — 109 unit tests total, a mocked full-pipeline integration check, a live app boot, and a measured ~5µs/dispatch overhead (~0.3ms/s at 60fps against a 30ms latency budget) |
| Gesture state machine, debounce, confidence filter, cooldown registry, smoothing toggle, double-click/swipe/dwell detectors, conflict resolver (OpenSpec PHASE 3/4) | Built and unit-tested (177 tests total) as standalone `core/` utilities. **Deliberately not wired into the live `GestureEngine`/camera loop** — see Decisions below. Only exception: the smoothing on/off toggle, a small, default-preserving change made directly to `GestureEngine` |
| Profiles, Context Engine, HUD state machine + feedback rendering (OpenSpec PHASE 5/6/7) | Built and unit-tested (246 tests total) as standalone `core/` utilities, same "not wired into the live loop" discipline as PHASE 3/4. One live-OS addition: `CrossPlatformOS.foreground_window_title()` (Windows/macOS/Linux), tested with each platform's OS call mocked |
| Telemetry: TelemetryManager + performance/gesture/command metrics + debug HUD (OpenSpec PHASE 8) | Built and unit-tested (299 tests total), same standalone/not-wired-in discipline. `TelemetryManager.record()` is a synchronous, lightweight in-memory append (spec.md #34's "lightweight enough" clause); an optional `sink` runs on a background thread so real I/O, if ever configured, can't block the caller |
| Undo/Redo: CommandHistory + UndoRedoController + undo feedback (OpenSpec PHASE 9) | Built and unit-tested (345 tests total). `VolumeUpCommand`/`VolumeDownCommand`/`CanvasZoomCommand` made genuinely reversible (the one exception to "not wired into live code" — these are real, small, additive changes to already-shipped Phase 2 commands, all existing tests re-verified green) |
| InputProvider + Gesture/Keyboard/Voice implementations (OpenSpec PHASE 10) | Built and unit-tested (363 tests total), same standalone/not-wired-in discipline. All three reuse `GestureEvent` as a shared event type instead of a separate `InputEvent` model — see Decisions |
| VoiceIntentResolver + intent convergence (OpenSpec PHASE 11) | Built and unit-tested (377 tests total). `VoiceIntentResolver` takes already-transcribed text only — no microphone/STT anywhere, matching ROADMAP.md's standing deferral. A real end-to-end test drives gesture-, keyboard-, and voice-sourced intents through the same `IntentCommandResolver` and `CommandBus` to the same `LockSessionCommand`, proving source-agnostic convergence rather than just asserting it |
| Quality: regression suite, performance baseline, error isolation, docs, architecture audit (OpenSpec PHASE 12 — final phase) | Done. **422 tests total, all passing.** Comprehensive, previously-nonexistent `GestureEngine` regression suite (see Decisions) and `HandTracker` handedness tests. Real measured performance baseline (below). All 4 error-isolation claims verified as named tests. Architecture audit found and fixed 2 real doc inaccuracies (see Decisions) and added a permanent import-boundary test |
| **Live integration** of previously-dormant PHASE 3-11 pieces (branch `feature/full-integration-voice-llm`, not yet merged) | Done for what's genuinely low-risk/high-value: Telemetry (always-on, in-memory), `ProfileManager` (sources `smoothing_enabled`, cycle with `p`), `CommandHistory`+`UndoRedoController` (real `z`/`y` undo/redo), a debug HUD overlay (`d`), and `ForegroundApplicationTracker` (cached, feeds telemetry). A new live-integration check script, `GestureEngine` output and a live boot both unchanged. Deliberately still NOT wired: `GestureStateMachine`, generic debounce/cooldown, swipe/dwell/double-click gesture bindings, and an `InputProvider`-based loop rewrite — each has a documented reason in `main.py`'s module docstring, not a silent gap |
| Natural-language voice control (STT + local LLM), same branch | Done — push-to-talk (`v` toggles recording, no real key-up in the per-frame `cv2.waitKey` polling model). `jarvis.voice_capture.VoiceListener` records via `sounddevice` and transcribes via `faster-whisper` ("base" model, offline). Text is resolved first by the existing `VoiceIntentResolver` (free phrase match), falling back to `jarvis.llm_intent.LLMIntentResolver` — a local Qwen2.5-1.5B-Instruct GGUF model via `llama-cpp-python`, constrained to a fixed, validated action vocabulary (never trusts free-form LLM text). `ConfidenceFilter` (built in PHASE 5, previously unused for lack of a real confidence signal) is now genuinely wired: faster-whisper's own `1 - no_speech_prob` gates low-confidence transcriptions before the LLM is even called. `faster-whisper`/`llama-cpp-python`/`sounddevice` are optional (`requirements-voice.txt`, lazy-imported) — the base app and its test suite run without them installed. 441 tests total, plus a real dispatch check in the live-integration script. **Not bundled into the PyInstaller release `.exe`** — deliberate scope boundary, see Known limitations |

## Architecture

```
Camera (640x480) -> MediaPipe HandLandmarker -> EMA filter -> GestureEngine -> events (strings)
                                                                    |
                                                                    v
                                              JarvisApp._dispatch() / _dispatch_migrated()
                                                                    |
                        +-------------------------------------------+-------------------------------+
                        v                                                                             v
              11 discrete gestures + continuous mouse-move                          NOT YET migrated (no PHASE 2 task
              (click/drag/right-click/scroll/zoom/                                  names them): pause/resume, close app,
              keyboard-HUD/volume/mute/screenshot/lock)                             silence, keyboard-HUD toggle, mirror,
                        |                                                            legend visibility/opacity
                        v                                                                             |
              GestureEvent (discrete only, spec.md #15) -> Command                                    v
                        |                                                          direct calls, same as before this
                        v                                                          migration (VoiceJarvis / ScreenOverlay /
                  CommandBus.dispatch()                                            pyautogui.mouseUp for the drag-cleanup case)
                        |
          +-------------+-------------+
          v                           v
  jarvis.actions.* (mouse/       on_result hook
  keyboard/system) ->                 |
  pyautogui / CrossPlatformOS         v
                              FeedbackManager.notify()
                                      |
                          +-----------+-----------+
                          v                       v
                  ScreenOverlay (HUD)       VoiceJarvis (TTS)
```

### Modules (`src/jarvis/`)

- **`hand_tracker.py`** — `HandTracker` wraps MediaPipe's **Tasks API** (`HandLandmarker`), not the legacy `mp.solutions` API. Downloads and caches the `.task` model under `assets/`, resolving the path correctly both in dev and inside a PyInstaller `.exe` (`sys._MEIPASS`). `process(frame_rgb, mirrored) -> list[Hand]` returns 0–2 hands, each with `landmarks` and a `handedness` label already corrected for the current mirror mode.
- **`config.py`** — every tunable constant (pinch thresholds, cooldowns, EMA alpha, HUD colors, hold durations, mirror default). Single place to tune behavior without touching logic.
- **`os_native.py`** — `CrossPlatformOS`: static methods `lock_session`, `take_screenshot`, `volume_up/down/mute`, `foreground_window_title`. The only module branching on `platform.system()` for **OS actions**. (`overlay.py` separately branches on `platform.system()` for its own, unrelated Windows-only click-through rendering trick — a distinct HUD-only concern, not an OS action — see its entry below. TASK-054's architecture audit found this and corrected this line, which previously overstated "the only module" without that qualifier; a regression test now pins both as the only two allowed.)
- **`voice.py`** — `VoiceJarvis`: a dedicated thread + `queue.Queue` so speaking never blocks the camera loop. `speak(text)` enqueues; `silence()` clears the queue and calls `engine.stop()` to cut off speech immediately.
- **`paths.py`** — `assets_dir()`: shared path resolution for downloaded model assets (dev path vs. `sys._MEIPASS` inside a PyInstaller `.exe`), extracted from `hand_tracker.py` so `llm_intent.py` reuses the same logic instead of duplicating it.
- **`voice_capture.py`** — `VoiceListener`: real microphone capture (`sounddevice`, lazy-imported) + STT (`faster-whisper`, lazy-imported, model `"base"`). `start()`/`stop()` toggle recording; transcription runs on a background thread so it never blocks the camera loop; `poll_result()` is non-blocking and delivers `(kind, text, confidence)`, with `confidence` sourced from faster-whisper's own `1 - no_speech_prob`.
- **`llm_intent.py`** — `LLMIntentResolver`: local LLM (`llama-cpp-python`, lazy-imported) fallback for voice commands `VoiceIntentResolver`'s phrase matching doesn't catch. Downloads/caches a Qwen2.5-1.5B-Instruct GGUF model via `paths.assets_dir()`. `VALID_ACTIONS` is the fixed, validated output vocabulary — the model's raw text is never trusted directly, only strict `{"action": "NAME"}` JSON matching that set.
- **`hud_keyboard.py`** — `HUDKeyboard`: on-screen keyboard layouts (Spanish/numeric/emoji), `draw(frame, cursor)`. Still drawn inside the camera window (unlike the legend, this one is tied to the pinch/cursor interaction happening there). `handle_click(cursor) -> KeyAction | None` no longer executes `pyautogui` itself (OpenSpec TASK-012) — it returns a `KeyAction(kind, value)` describing what was touched (`"key"`/`"text"`/`"layout"`), and `main.py` turns that into a `Command`. Layout switches (123/ABC/EMOJI) stay internal state, no OS side effect, so no `Command` for those.
- **`legend.py`** — content only: `build_legend_text()` builds the multi-line gesture list string. No drawing logic — it used to render on the camera frame via `cv2.addWeighted`; that was removed in favor of a native overlay window (see below).
- **`overlay.py`** — `ScreenOverlay`, built on Tkinter (stdlib, zero new dependencies):
  - `show_bubble(text, x, y)` — a transient translucent toast at any screen position, self-destroys via `after()`.
  - `init_legend(text, corner)` / `set_legend_visible()` / `adjust_legend_alpha()` — a persistent panel anchored to a screen corner, translucent, with runtime opacity control.
  - Both use `_make_click_through(window)`: on Windows this applies `WS_EX_LAYERED | WS_EX_TRANSPARENT` to the real HWND (obtained via `GetParent(winfo_id())`) through `ctypes` — a well-known, dependency-free trick, verified working on this machine (see Decisions). No-op elsewhere.
  - `pump()` is called once per camera frame instead of `mainloop()`, because Tk is not thread-safe and a separate UI thread would race with the camera loop.
- **`gestures.py`** — `GestureEngine`: pure logic, no I/O. `process(hands, w, h, screen_w, screen_h) -> (screen_xy | None, cam_xy | None, events)`. Single-hand gestures always use `hands[0]` and are entirely skipped when `active` is `False` (paused) — in that case `screen_xy` is `None`, so `main.py` neither moves the mouse nor draws the keyboard. The two master, two-hand gestures (`TOGGLE_ACTIVE`, `CLOSE_APP`) are evaluated *before* checking `active`, so pause can always be undone and the app can always be closed.
- **`main.py`** — `JarvisApp`: owns the camera loop, calls `GestureEngine.process`, draws the keyboard/pause banner, handles the keyboard shortcuts (`q`/`h`/`m`/`+`/`-`/`z`/`y`/`p`/`d`/`v`). `_dispatch()` splits events into the 11 discrete gestures migrated onto `Command`/`CommandBus` (`_dispatch_migrated()`) vs. everything else, still called directly exactly as before this migration. `_handle_voice_result()`/`_dispatch_voice_action()` route push-to-talk transcriptions through `VoiceIntentResolver` then `LLMIntentResolver` into the same `Command`/`CommandBus` path gestures use.

### `src/jarvis/core/` — OpenSpec foundation (PHASE 1)

- **`events.py`** — `GestureEvent`: frozen, validated dataclass per spec.md #2.1 (`gesture_type`, `hand`, `confidence` in [0,1], `position`, `velocity`, `duration_ms`, `timestamp`, `source`, `state` restricted to the 8 documented values, `metadata`, auto-generated `id`).
- **`intents.py`** — `Intent`: frozen, validated dataclass per spec.md #2.2 (`name`, `source`, `confidence`, `timestamp`, `context`, `parameters`, `metadata`). Built and tested, but **not constructed anywhere in the live dispatch path yet** — see Decisions below for why.
- **`commands.py`** — `Command` (ABC: `metadata` property, `can_execute()`, `execute()`, optional `undo()`/`redo()`), `CommandMetadata` (name + safety level, one of `SAFE`/`CONFIRM_REQUIRED`/`HOLD_REQUIRED`/`DESTRUCTIVE`), `CommandResult` (`success`, `status` restricted to `EXECUTED`/`REJECTED`/`ERROR` with cross-field consistency validation, `message`, `duration_ms`, `error`, `metadata`, with `.ok()`/`.rejected()`/`.failed()` factories).
- **`command_bus.py`** — `CommandBus.dispatch(command) -> CommandResult`: validate -> reject `DESTRUCTIVE` outright (spec.md #27) -> `can_execute()` -> `execute()` -> result, every step guarded so a bad command can never crash the caller. Logs via stdlib `logging`; fills in `duration_ms` if the command didn't report one; optional `on_result(command, result)` hook for feedback/telemetry, itself exception-guarded.
- **`feedback.py`** — `FeedbackManager`: adapter over the *existing* `VoiceJarvis`/`ScreenOverlay` (doesn't reimplement TTS or the HUD), channels `hud`/`tts`/`sound`/`silent` per spec.md #30, per-channel enable/disable, never raises.

### `src/jarvis/actions/` — concrete Commands (PHASE 2)

- **`mouse.py`** — `MouseMoveCommand`, `MouseButtonCommand(pressed)`, `RightClickCommand`, `ScrollCommand(amount)`, `CanvasZoomCommand(amount)` (Ctrl+Scroll — canvas/viewport zoom, not object scaling, see Decisions). Each wraps the exact `pyautogui` call `main.py` used to make directly.
- **`keyboard.py`** — `PressKeyCommand(key_name)`, `TypeTextCommand(text)` — what `HUDKeyboard.handle_click()` used to call directly.
- **`system.py`** — `VolumeUpCommand`, `VolumeDownCommand`, `MuteCommand`, `ScreenshotCommand`, `LockSessionCommand`, wrapping `CrossPlatformOS`. Safety per spec.md #27's own examples: `SAFE` for volume/mute/screenshot, `HOLD_REQUIRED` for lock (the 1.5s Shaka hold that already gated it is unchanged — this declares that fact, doesn't add new gating).

### Gesture map

| Gesture | Action |
|---|---|
| Index fingertip (landmark 8) moved | Mouse pointer (EMA-smoothed) |
| Pinch thumb(4)+index(8) < 30px | Left click / drag / HUD keyboard key select |
| Pinch thumb(4)+middle(12) < 30px | Right click |
| Index+middle extended, ring+pinky curled | Vertical scroll |
| Pinch thumb(4)+ring(16), index extended | Zoom (Ctrl+Scroll) |
| Open palm (index/middle/ring/pinky extended, thumb spread >60px) | Toggle on-screen keyboard |
| Pinch thumb(4)+pinky(20) + vertical movement | Volume up/down |
| Thumb+ring pinch with index and pinky curled | Screenshot |
| Shaka (thumb+pinky extended, index/middle curled) held 1.5s | Lock session |
| Open palm with thumb tucked toward the pinky base | **Voice silence** (interrupts TTS instantly) |
| Both hands closed fists, held 1.2s | **Pause/resume gesture reading** (works even while paused) |
| Both hands in Shaka, held 1.5s | **Close Jarvis** (works even while paused) |
| Both hands pinching (thumb+index), spread apart / brought together | **Canvas zoom** (Ctrl+Scroll) — same action as the single-hand zoom, just a more natural two-hand trigger. Does **not** scale the selected object in a design app; that already works today via a normal single-hand drag on the app's own resize handle. |
| One hand closed fist (anchor, either hand) + the other showing 1/2/3/4 fingers, held 0.6s | Secondary menu: 1 = toggle gesture legend, 2 = toggle mirror mode, 3 = legend more opaque, 4 = legend more transparent — the same four actions already bound to `h`/`m`/`+`/`-`, now also reachable without touching the keyboard. Debounced: won't repeat while the pose is held, needs to be released and re-formed. |
| Naruto seal Tora (index+middle together, thumb crossed close), held 0.6s | Screenshot (default binding, profile-overridable) |
| Naruto seal Ushi (index only, thumb tucked), held 0.6s | Undo |
| Naruto seal U/Hare (index+middle spread apart, thumb tucked), held 0.6s | Redo |
| Naruto seal Uma/Horse — redefined a 3rd time, real-camera verified (thumb+index+pinky extended, middle+ring curled), held 0.6s | Zoom in |
| Naruto seal Hitsuji/Ram (index+middle genuinely crossed — segment-intersection check), held 0.6s | Mute |
| Naruto seal Saru/Monkey — redefined a 3rd time, real-camera verified (fist, thumb pointing up), held 0.6s | Toggle on-screen keyboard |
| Naruto seal Inu/Dog — redefined, real-camera verified (pinky extended alone), held 0.6s | Volume down |
| Naruto seal I/Boar (fist, thumb extended to the side — lateral offset check), held 0.6s | Lock session (`HOLD_REQUIRED` — the hold above already satisfies it) |
| Naruto seal Ne/Rat — two-hand (hands clasped close, partially folded, pointing up), held 1.2s | Zoom out |
| Naruto seal Mi/Snake — two-hand (same as Ne, pointing down), held 1.2s | Scroll down |
| Naruto seal Tori/Bird — two-hand (hands fanned apart, both open), held 1.2s | Scroll up |
| Naruto seal Kai/Release — two-hand (clasped, index+middle of both hands crossed), held 1.2s | Close Jarvis |
| Naruto seal Tatsu/Dragon — two-hand (clasped, one fist + one open hand), held 1.2s | Volume up |
| JJK Gojo — Domain Expansion — two-hand (both hands' thumb→index vectors ~90° apart, hands close together, held up in the upper frame), held 1.2s | Right click |
| JJK Sukuna — finger snap (thumb+middle drop below contact then rise above release within 0.35s — `ImpulseDetector`, TEMPORAL, no hold) | Screenshot |
| JJK Megumi — shadow summon (index+middle crossed, **ring extended** — the explicit discriminator vs. Hitsuji, which requires ring curled), held 0.6s | Mute |
| Clap — two-hand (both hands' palm centers drop below contact then rise above release within 0.4s — `ImpulseDetector`, TEMPORAL, no hold) | Toggle on-screen keyboard ("Clapper" pun) |
| Korean finger heart — one-hand (fist, thumb near the index's first joint — **not** its tip, which stays `PINCH_CLICK`'s territory), held 1.0s | Screenshot (classic photo pose) |

Keyboard shortcuts (camera window focused): `q` quit, `h` toggle legend visibility, `m`
toggle mirror mode, `+`/`-` legend opacity, `l` toggle hand/landmark visualization
overlay (TASK-057, off by default).

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
| FR-19 | Two-hand pinch gesture (both hands thumb+index pinched, distance between them changing) triggers canvas zoom (Ctrl+Scroll) — not object scaling. |
| FR-20 | Secondary-action gesture menu: one hand as a closed-fist anchor (either hand) + the other hand showing 1–4 fingers, held 0.6s, mirrors the `h`/`m`/`+`/`-` keyboard shortcuts (legend visibility, mirror mode, legend opacity) as gestures. |

### Non-functional

| ID | Requirement |
|----|-----------|
| NFR-1 | ≤ 7% CPU on a quad-core, ≤ 30ms gesture-to-action latency. |
| NFR-2 | Minimal dependencies: `opencv-python`, `mediapipe`, `pyautogui`, `numpy`, `pyttsx3`. |
| NFR-3 | Cross-platform: Windows, macOS, Linux — OS-specific branches contained to `os_native.py` (OS actions) and `overlay.py` (its own Windows-only click-through rendering trick), nowhere else — pinned by `tests/test_architecture_boundaries.py`. |
| NFR-4 | Packageable as a portable executable (PyInstaller), no Python install required on the target machine. |
| NFR-5 | All processing is local — no network calls except the one-time `hand_landmarker.task` model download. `jarvis.core.telemetry.TelemetryManager` exists (PHASE 8) but is local-only by construction and not wired into the live app — see spec.md #35, honored either way. |

### Out of scope (this phase)

- Natural-language microphone control via a local LLM (see Future Work below).
- Multi-user support (two hands for a single user *are* supported, see FR-15).
- UI-based gesture customization (today, tuned by editing `src/jarvis/config.py`).

## Configuration reference

Every tunable value in the project, and where it lives:

| What | Where | Wired into the live app? |
|---|---|---|
| Pinch thresholds, cooldowns, EMA alpha, HUD colors, mirror default, master/meta gesture hold durations | `src/jarvis/config.py` | Yes — read directly by `GestureEngine`/`HUDKeyboard`/`legend.py` |
| Smoothing on/off | `GestureEngine(smoothing_enabled=...)` constructor param | Yes, if passed explicitly — `main.py` currently constructs `GestureEngine()` with the default (`True`, identical to pre-PHASE-3 behavior) |
| Confirmation-frame count (debounce) | `jarvis.core.debounce.ConsecutiveFrameDebouncer(confirmation_frames=3)` | No — standalone (PHASE 3) |
| Minimum confidence threshold | `jarvis.core.confidence.ConfidenceFilter(minimum_confidence=0.70)` | No — standalone (PHASE 3) |
| Per-action cooldowns (generic registry) | `jarvis.core.cooldown.CooldownRegistry(cooldowns={...})` | No — standalone (PHASE 3); `GestureEngine`'s own cooldowns in `config.py` are separate and already live |
| Double-click interval, swipe distance/velocity/duration, dwell duration/cancel-distance | `jarvis.core.{double_click,swipe,dwell}.py` constructors | No — standalone (PHASE 4) |
| Profiles (cursor sensitivity, smoothing, swipe thresholds, dwell, cooldowns, gesture bindings) | `jarvis.core.profiles.ProfileManager` / `Profile` | Partially — `main.py` reads `smoothing_enabled` from the active profile and cycles profiles with `p` (PHASE 5, wired on `feature/full-integration-voice-llm`); `default` mirrors `config.py`'s real values, no other profile is registered by default |
| Foreground-app detection cache TTL | `jarvis.core.context_tracker.ForegroundApplicationTracker(cache_ttl=0.5)` | Yes — polled every frame in `main.py`, feeds telemetry (PHASE 6, wired on `feature/full-integration-voice-llm`) |
| Command history size | `jarvis.core.command_history.CommandHistory(max_size=50)` | Yes — every discrete command dispatch is recorded; `z`/`y` undo/redo (PHASE 9, wired on `feature/full-integration-voice-llm`) |
| Telemetry history size, optional sink | `jarvis.core.telemetry.TelemetryManager(max_history=500, sink=None)` | Yes — FPS/frame time, gesture and command outcomes recorded every frame (PHASE 8, wired on `feature/full-integration-voice-llm`) |
| Voice phrase → intent bindings | `jarvis.core.voice_intent_resolver.VoiceIntentResolver(phrase_bindings=...)` | Yes — `main.py` constructs it with `DEFAULT_PHRASE_BINDINGS`, tried before the LLM fallback on every push-to-talk result (PHASE 11, wired on `feature/full-integration-voice-llm`) |
| LLM action vocabulary, model choice | `jarvis.llm_intent.VALID_ACTIONS` / `LLMIntentResolver(model_path=...)` | Yes — fallback when no phrase matches (`feature/full-integration-voice-llm`) |
| Voice confidence threshold | `jarvis.main.JarvisApp` constructs `ConfidenceFilter(minimum_confidence=_VOICE_MIN_CONFIDENCE)` (`0.5`) | Yes — gates on faster-whisper's own confidence before resolving intent (`feature/full-integration-voice-llm`) |

## Performance baseline

Real measurements taken on the development machine (not estimates), so migrating
onto the `Command`/`CommandBus` architecture could be judged on evidence rather than
assumption:

| Path | Measured | spec.md/design.md budget |
|---|---|---|
| `GestureEngine.process()` (one frame, one hand, worst-case branch coverage) | **~2.65µs/call** (5,000-iteration average) | design.md #25: "gesture event generation: < 1 frame of additional latency" (~16–33ms at 30–60fps) — ~0.01–0.02% of that budget |
| `CommandBus.dispatch()` overhead alone (pyautogui mocked, so only the architecture's own cost is measured) | **~11.8µs/call** (5,000-iteration average) | design.md #25: "local command dispatch: < 20ms target" — ~0.06% of that budget |
| Packaged `.exe`, idle with camera running, no hand in frame | ~260MB RAM, clean log, no crash across 7+ separate manual boot checks (one per phase since PHASE 6) | spec.md #1: "≤ 7% CPU on quad-core" — not independently profiled per-core, but sustained real-time operation across every check is consistent with it |
| `HandLandmarker.process()` (real camera frame, real inference — the existing per-frame cost, not new) | **~10.0ms/frame average, ~12.7ms p95** | (baseline for the row below, not previously measured on its own) |
| `PoseLandmarker.process()` (TASK-060c, lite variant, real camera frame — new, opt-in) | **~10.4ms/frame average, ~12.6ms p95** — roughly doubles combined per-frame vision-inference cost when enabled | design.md #25's ~16–33ms/frame budget — significant enough that this ships disabled by default (`config.POSE_HAND_OWNERSHIP_ENABLED`), see Decisions |

There is no meaningful "before" to compare against beyond "zero abstraction
overhead by definition" (the original monolithic prototype called `pyautogui`
directly) — the real question PHASE 2's migration raised was whether inserting
`Command`/`CommandBus` between detection and `pyautogui` would be *perceptible*.
Both measured overheads are microseconds against millisecond-to-tens-of-millisecond
budgets, so the answer is no.

## Development

- **Run the tests**: `python -m unittest discover -s tests -v` (stdlib `unittest`,
  zero new test dependencies, 422 tests, ~0.8s total including the handful that
  construct a real `HandLandmarker`). One file is
  deliberately excluded from discovery — `tests/manual_main_integration_check.py`
  (constructs a real `VoiceJarvis`/`ScreenOverlay`) — run it directly:
  `python tests/manual_main_integration_check.py`.
- **Adding a new OpenSpec task's module**: follow the pattern established since
  PHASE 1 — a frozen, validated `@dataclass` for data models (see
  `jarvis.core.events.GestureEvent`); a module docstring citing the task number and
  the relevant `spec.md`/`design.md`/`apply.md` section with a short quote; and, if
  the module isn't wired into the live camera loop, an explicit one-or-two-sentence
  "why not" (the standing reason: `jarvis.gestures.GestureEngine` and
  `jarvis.main.JarvisApp` are the working, tested baseline — design.md #5.1 treats
  existing behavior as correct unless a specific bug is found, so new
  infrastructure earns its way into the live loop deliberately, not by default).
- **Before calling a task done**: compile (`python -m py_compile ...`), run the
  full suite, re-run the one-line `GestureEngine` regression smoke check that's
  been used since PHASE 2 (construct a flat-hand fixture, confirm
  `screen_xy == (336, 189)` and `events == ["PINCH_DOWN"]`), and boot the real app
  briefly (`python run.py`, no hand in frame, confirm no traceback in the log).
- **OpenSpec docs**: `openspec/changes/multimodal-interaction-core/{proposal,spec,
  design,tasks,apply}.md`. `tasks.md` is the live checklist — check boxes off as
  work lands, and where the source doc gave no acceptance criteria, add a short,
  clearly-labeled implementer-added list rather than leaving it unverifiable.

### Releases

Versioning and releases are automated with
[python-semantic-release](https://python-semantic-release.readthedocs.io/), driven
by [Conventional Commits](https://www.conventionalcommits.org/) on `main`
(`.github/workflows/release.yml`):

1. Every commit merged to `main` MUST use a Conventional Commits prefix —
   `feat:` (minor bump), `fix:`/`perf:` (patch bump), or
   `docs:`/`refactor:`/`test:`/`chore:`/`build:`/`ci:`/`style:` (no bump, but still
   included in the changelog). This is a **process change starting on this
   branch** — commits before it don't follow this convention and semantic-release
   only looks forward from the last tag, so that's fine.
2. On push to `main`, the `release` job computes the next version from those
   commit prefixes, updates `src/jarvis/__init__.py:__version__` and
   `pyproject.toml:project.version`, appends `CHANGELOG.md`, and creates a git tag
   + GitHub Release — only if there's something releasable (a `feat`/`fix`/`perf`
   commit since the last tag).
3. If a release was created, `build-binaries` builds `Jarvis.exe`/`Jarvis`
   natively on `windows-latest`/`macos-latest`/`ubuntu-latest` (PyInstaller can't
   cross-compile — see `build/build_*.sh`/`.ps1`) and attaches each as a downloadable
   asset on that GitHub Release.
4. **Known gap, stated plainly rather than overclaimed**: the macOS and Linux
   binaries are unsigned. macOS Gatekeeper will refuse to run an unsigned binary
   downloaded from the internet without the user right-clicking → Open (or
   `xattr -d com.apple.quarantine`) the first time — there's no Apple Developer
   certificate available to sign/notarize it properly. Linux binaries typically
   need `chmod +x` after download. Windows is the only platform this project has
   actually run the packaged `.exe` on and verified (see Status) — the CI build for
   the other two platforms has not yet been triggered for real (this workflow is
   new, on an unmerged branch, as of this writing) and should be treated as
   unverified until a release actually runs it.
5. `pip install pyinstaller` happens fresh inside each CI job — no local machine
   dependency, unlike the manual `build/build_*.ps1`/`.sh` scripts.

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
- **Two-hand pinch reinterpreted as canvas zoom, not object scaling.** A generic "resize
  the selected object" gesture isn't achievable across arbitrary apps (Photoshop,
  Illustrator, AutoCAD, Canva) without knowing where that app's resize handle is on
  screen — and dragging that handle is exactly what the existing single-hand
  pinch+drag already does, no new gesture needed. What a two-hand pinch *can* honestly
  and universally do is trigger the same Ctrl+Scroll canvas zoom the single-hand zoom
  gesture already sends, just with a more natural "spread your hands apart" motion. Kept
  the same `ZOOM_IN`/`ZOOM_OUT` events and dispatch code — no new action, just a second
  way to trigger it.
- **The secondary-action menu is handedness-agnostic on purpose.** It would have been
  possible to assign "left hand = anchor, right hand = selector," using the handedness
  correction already built for mirror mode. Instead, either hand can be the fist anchor —
  simpler, avoids depending on handedness classification confidence at all, and keeps
  the property (documented earlier) that no *currently implemented* gesture actually
  needs to know left from right.
- **Added a "primary hand" continuity heuristic when picking `hands[0]`.** Building the
  two-hand features surfaced a latent issue: with two hands in frame, MediaPipe doesn't
  guarantee `hand_landmarks` stays in the same order across frames, so blindly using
  `hands[0]` for single-hand gestures could make the pointer jump between hands.
  `GestureEngine._pick_primary()` now picks whichever detected hand is closest to last
  frame's index-fingertip position, so a resting second hand doesn't steal or jitter the
  pointer.
- **Found and fixed a real double-fire bug while testing the close-app gesture.** Holding
  both hands in Shaka to close the app also happened to satisfy the single-hand Shaka
  condition on whichever hand `_pick_primary` treated as active, firing `LOCK_SESSION`
  in the same frame as `CLOSE_APP`. Fixed by suppressing the single-hand lock check while
  `both_shaka` is true — caught via synthetic-landmark unit testing, not observed live.
- **`GestureEvent` is constructed for the migrated discrete gestures; `Intent` is not
  constructed anywhere yet, despite TASK-006's flow diagram naming both.** Without a
  real IntentEngine (not a foundation task — no task creates one) to consume it, an
  `Intent` built at each of the 11 dispatch sites would be created and immediately
  discarded, which is ceremony without function and contradicts "Implementation MUST
  be minimal." The `gesture_type -> Command` mapping in `main.py._dispatch_migrated()`
  *is* the intent-resolution logic today, just not reified as a separate object.
  Reconsider once a real `IntentEngine`/`ContextEngine` exists to read `Intent.context`
  meaningfully (Phase 6) — at that point promoting this to real `Intent` construction
  is a small, mechanical change.
- **Continuous mouse movement skips `GestureEvent` entirely and goes straight to
  `MouseMoveCommand`**, per spec.md #15 ("Continuous signals MUST NOT be forced
  through the same execution model as discrete gestures"). Measured overhead of the
  `Command`/`CommandBus` layer itself: ~5µs per dispatch (10k-iteration
  microbenchmark, pyautogui mocked out so only the architecture's own cost is
  measured) — at 60fps that's ~0.3ms of added latency per second of video, against a
  30ms per-gesture budget. Not perceptible.
- **`CommandBus` blocks `DESTRUCTIVE` commands outright but doesn't gate
  `CONFIRM_REQUIRED`/`HOLD_REQUIRED`.** No confirmation-prompt or hold-tracking
  mechanism exists anywhere in the app (HUD, voice, or otherwise), so building one
  now would be speculative. `LockSessionCommand` declares `HOLD_REQUIRED` as
  documentation of the fact that `GestureEngine` already enforces a 1.5s hold before
  ever emitting `LOCK_SESSION` — the bus doesn't (yet) enforce this itself.
- **Only the 11 gesture strings + continuous mouse-move named across TASK-006–013
  were migrated.** Two-hand master gestures (pause/resume, close), the silence
  gesture, keyboard-HUD visibility toggle, mirror toggle, and legend
  visibility/opacity are not named in any PHASE 2 task and were deliberately left
  calling `VoiceJarvis`/`ScreenOverlay`/`pyautogui` directly, unchanged — including
  one spot (`TOGGLE_ACTIVE`'s drag-cleanup) that now sits inconsistently next to a
  `MouseButtonCommand` used everywhere else for the same `mouseUp()` call. Flagged
  rather than silently fixed, since it's outside every currently-scoped task.
- **`FeedbackManager` failure-and-success messages for migrated actions live in
  `main.py._on_command_result()`, wired via `CommandBus`'s `on_result` hook** (built
  in TASK-004 anticipating exactly this). Only the actions that already had a
  bubble/voice line before this migration keep one — `MouseMove`/`MouseButton`/
  `Scroll`/`PressKey`/`TypeText` stay silent, matching pre-migration behavior exactly.
  System-action (`LockSession`/`Screenshot`/`VolumeUp`/`VolumeDown`) *failures* now
  produce feedback too — new behavior, required explicitly by TASK-013's acceptance
  criteria (the old code had no error handling around these calls at all: an
  exception would have crashed the whole camera loop, which `CommandBus` now
  prevents structurally).
- **PHASE 3/4's gesture-quality infrastructure (state machine, debounce, confidence
  filtering, cooldown registry, double-click/swipe/dwell detectors, conflict
  resolver) is built and thoroughly unit-tested, but deliberately not wired into
  `GestureEngine` or the live camera loop.** These tasks largely assume a
  classifier producing multiple, confidence-scored *candidate* gestures per frame
  (spec.md's own example: "PINCH 0.92, POINT 0.81") — `GestureEngine` is a
  threshold/boolean if-elif detector, structurally different, and has been treated
  as the correct, working baseline throughout this project (design.md #5.1:
  "current behavior is correct unless a specific bug is identified"). Wiring any of
  these in would change real, already-shipped latency or interaction feel (e.g.
  debounce delays every click by N frames; double-click detection must hold back
  the first click to see if a second follows) without a concrete request to do so.
  Each new module's docstring states this explicitly and explains why. The one
  exception is the smoothing on/off toggle (TASK-018): small, additive, defaults
  to the exact prior behavior, safe to land directly in `GestureEngine`.
- **PHASE 5/6/7 (profiles, context, HUD) follows the exact same "built, tested,
  not wired in" discipline as PHASE 3/4, for the same reason: none of it is
  mechanically safe to attach to the live camera loop without a concrete decision
  this session didn't have grounds to make on its own.** `ProfileManager`'s
  `default` profile is seeded from today's real `jarvis.config` constants
  specifically so that *if* something later reads through it, switching to
  `"default"` is defined to be a no-op — but `GestureEngine` doesn't read from it
  yet. `ContextualHudRenderer`/`HUDStateMachine` are a second, richer HUD model
  that coexists with, but doesn't replace, the simpler working one
  (`jarvis.overlay`/`jarvis.legend`) actually used by `main.py`.
- **`CrossPlatformOS.foreground_window_title()` is the one PHASE 5/6/7 piece that
  does touch live OS state**, added to `os_native.py` specifically to preserve
  this project's existing rule that only one module branches on
  `platform.system()`. Best-effort by design (returns `None` on any failure,
  including on an unsupported platform) — tested with each OS path mocked, since
  actually querying the real foreground window during an automated test run isn't
  meaningful (the answer is "whatever's focused when the test happens to run").
- **A few HUD-state and reticle-color choices are extensions beyond the literal
  spec text**, flagged in the affected modules' own docstrings rather than
  silently invented: `HUDStateMachine` places `PAUSED` (a state spec.md #31 lists
  but never diagrams a transition for) next to `IDLE`/`TRACKING`, matching this
  app's own existing pause/resume gesture; `draw_dwell_reticle()`'s
  idle/targeting/confirming/selected colors satisfy spec.md #33's "visually
  distinguish" requirement without the spec dictating actual colors.
- **Volume undo is a best-effort symmetric nudge, not an exact restore.** spec.md
  #28's own example ("Volume: 80→90, undo: 90→80") implies querying an absolute
  OS volume level, which this project has never done — `CrossPlatformOS` only
  presses relative media keys. `VolumeUpCommand.undo()` therefore presses
  volume-down once rather than recalling and restoring an exact prior value.
  `CanvasZoomCommand`, by contrast, undoes exactly (scrolling `-amount` truly is
  the mathematical inverse of scrolling `amount`) — the two commands only look
  symmetric on the surface; documented explicitly in both docstrings so this
  isn't a silently-overstated guarantee (spec.md #28: "MUST NOT pretend an
  action is reversible when it cannot safely restore the previous state").
  "HUD state" and "settings changes" (PHASE 9's other two reversibility
  candidates) have no existing Command to attach undo to at all — no task in
  PHASE 2 ever wrapped a HUD-visibility toggle or a settings change as a
  Command, so there's nothing there yet, not a gap in this phase's work.
- **PHASE 10's three InputProviders reuse `GestureEvent` as their shared output
  type, instead of building the separate `InputEvent` model design.md #3's
  suggested folder listing names (`core/events/{gesture_event, input_event}`).**
  `GestureEvent.gesture_type` doubles as a general "what happened" tag (e.g.
  `"KEY_PRESS"` for a keystroke), and every camera-specific field on it
  (hand/position/velocity/duration_ms) was already optional from TASK-001 -
  building a second, near-identical dataclass for this would have duplicated it
  for no functional gain. `GestureInputProvider` needed one adjustment to fit the
  uniform zero-arg `poll()` contract: camera input genuinely needs a new frame
  each cycle, so frame acquisition is injected via a `frame_source` callable at
  construction rather than a method argument.
- **PHASE 12's architecture audit (TASK-054) found and fixed two real
  documentation inaccuracies, not just confirmed a clean bill of health.** This
  file previously claimed `os_native.py` was "the only module" branching on
  `platform.system()` and that NFR-5 meant "no telemetry" — both were true when
  first written but silently went stale as later phases added `overlay.py`'s own
  platform check and PHASE 8's (unwired, local-only) `TelemetryManager`. Corrected
  above, and `tests/test_architecture_boundaries.py` now pins the actual, intended
  set of platform-branching modules (two, not one) so this can't silently drift
  again without a test failing.
- **PHASE 12's comprehensive `GestureEngine` regression suite (TASK-050) is the
  first PERMANENT, automated test of most of this project's gesture vocabulary.**
  Click/drag, right-click, scroll, zoom, volume, screenshot, lock, silence, and all
  four two-hand master/meta gestures had only ever been verified ad hoc (throwaway
  manual checks during PHASE 3/4 development) before this. Writing real,
  isolated-per-gesture synthetic landmark fixtures caught the same class of bug
  that's recurred throughout this project's history: a fixture's "move this
  fingertip far away so it doesn't interfere" placement can accidentally satisfy
  the *other* direction of a tip-vs-pip "extended" check, misfiring `SILENCE` or
  `KEYBOARD_TOGGLE`. Fixed by making unrelated fingers genuinely curled
  (`tip.y > pip.y`) rather than merely distant, and by moving a pinched pair's
  thumb *together with* the finger being tested (not leaving the thumb static)
  when the test needs that finger to travel far enough to produce a directional
  delta signal.
- **Natural-language voice control (STT + LLM) is now implemented** on
  `feature/full-integration-voice-llm` (merged) — see Status and Known limitations
  for what shipped and what's still open (wake word, exe bundling).
- **Pinch-family gestures could fire together on a fist with only thumb+index
  deployed — real bug, reported from actual use, fixed (`openspec/changes/
  personalization-and-config-ui`, TASK-055).** `gestures.py` computed each
  pinch-family distance (click, right-click, screenshot, zoom, volume)
  independently, with no check that only one was meant. In a natural fist with
  just thumb+index pinching, the curled middle/ring/pinky fingertips land close
  enough to the thumb's resting point to also satisfy another pinch family's own
  threshold — confirmed by reverting the fix and reproducing `['SCREENSHOT',
  'PINCH_DOWN']` firing together from a single synthetic fixture (not assumed).
  Fixed by resolving one winner per frame — the pinch family with the smallest
  thumb-to-fingertip distance — before any branch is allowed to fire; every
  other candidate is suppressed that frame. Discovered along the way: `PINCH_DOWN`
  and `RIGHT_CLICK` share `self.last_click_time` for their cooldowns, and
  `PINCH_DOWN`'s branch runs first each frame, so it was already accidentally
  masking that specific pair from co-firing — `SCREENSHOT` (its own independent
  cooldown) was the pairing that actually reproduced the bug.
- **`PINCH_DOWN`/`RIGHT_CLICK` sharing one cooldown timer was itself a second,
  separate real bug — fixed too.** Not the same-frame ambiguity above (already
  closed by the fix): a *genuine, unambiguous* right-click done shortly after a
  genuine left-click (or vice versa) got silently swallowed, because whichever
  fired first reset the shared `last_click_time` the other one's cooldown check
  read from. Confirmed both directions by reverting and reproducing (a clean
  right-click immediately after a clean left-click produced no `RIGHT_CLICK`
  event, and the symmetric case likewise dropped `PINCH_DOWN`). Fixed with a
  second, independent `last_right_click_time`.
- **The 7 single-hand checks that had no two-hand suppression now do
  (TASK-055b, `openspec/changes/personalization-and-config-ui`).** Only
  `LOCK_SESSION` and `PINCH_DOWN`/`PINCH_UP` were ever gated against a
  concurrent two-hand gesture — `SILENCE`, `KEYBOARD_TOGGLE`, `SCREENSHOT`,
  single-hand `ZOOM_IN`/`ZOOM_OUT`, `VOLUME_UP`/`VOLUME_DOWN`,
  `SCROLL_UP`/`SCROLL_DOWN`, and `RIGHT_CLICK` ran unconditionally on the
  primary hand regardless of what the other hand was doing. `_process_two_hand_
  gestures` now also returns a general `two_hand_active` flag (the raw
  geometric OR of `both_shaka`/`both_fists`/`both_pinching`/"one hand is a fist
  and the other isn't" — not whether a two-hand event actually fired, since
  some require a hold to confirm), and all 7 are gated by it. `LOCK_SESSION`'s
  and `PINCH_DOWN`'s existing, narrower suppression conditions were left
  untouched (they were already correct for their specific known collision, no
  need to broaden them). This was optional per the task's own spec — done now
  because it also reduces the collision-avoidance burden for every future
  two-hand gesture this project adds (Naruto/JJK/common gestures), rather than
  re-litigating it per gesture later.
- **Pinch-family distances now use the landmark's `z` coordinate (TASK-055c,
  `openspec/changes/personalization-and-config-ui`) — real 3D distance, not
  just the 2D screen-projected one.** `d_thumb_index`/`_middle`/`_ring`/`_pinky`
  (click, right-click, screenshot, zoom, volume) now go through a new
  `_dist3()` alongside the existing `_dist()` (kept for everything else, e.g.
  `SILENCE`'s thumb-to-MCP check, which isn't pinch-family). Two points close
  on screen but far apart in depth are no longer treated as touching. Every
  existing synthetic fixture uses `z=0`, so the 3D formula degrades exactly to
  the 2D one for all of them (verified — full suite unchanged). **Real-camera
  threshold re-verification (`config.py`'s `PINCH_*` constants) was NOT done
  as part of this task** — this environment initially had no webcam access,
  so the thresholds were left numerically unchanged at first. **Update: real
  camera access (DroidCam) became available shortly after** — see the next
  two entries for what that made possible.
- **Real-camera diagnosis (DroidCam, 2026-08-27) of two reports from actual
  use: Shaka/fist confusion (a fist locked the session) and "everything
  fires too easily."** Both root-caused with live landmark data, not guessed:
  - *Shaka/fist confusion*: `_is_shaka` never checked the ring finger. Live
    capture showed the natural motion of opening a held fist passes, for a
    few frames, through a pose that already satisfied `_is_shaka` (pinky
    reading "extended" before the other fingers catch up, thumb already
    tip-up, index/middle still curled) — with the ring finger extended too,
    which a real Shaka/hang-loose sign doesn't have (it curls). Fixed by
    requiring the ring finger curled in `_is_shaka` too — verified live
    before/after: before, the transition sustained `is_shaka=True` for a
    visible stretch; after, only 3 scattered, non-consecutive frames spanning
    0.18s (nowhere near `LOCK_HOLD_SECONDS=1.5`). Pinned as a permanent
    regression test built from the actual captured geometry.
  - *"Everything fires too easily"*: measured real thumb-to-fingertip
    distances with the hand relaxed (not intentionally pinching) vs.
    intentionally pinching. A relaxed hand's index dipped to 15.5px and
    middle to 19.2px during ordinary movement — already under the old 30px
    thresholds — while an intentional pinch's median was 9.6px. The old
    thresholds (25–30px, nearly identical across all 5 pinch families) sat
    too close to relaxed-hand noise, especially for click/right-click.
    Fixed two ways: (1) thresholds lowered with a safety margin from the
    measured data (`PINCH_CLICK` 30→18, `PINCH_RIGHT_CLICK` 30→20,
    `PINCH_SCREENSHOT` 25→20, `PINCH_ZOOM` 30→25, `PINCH_VOLUME` 30→28); (2) a
    new `PINCH_CONFIRM_FRAMES=2` requirement — a pinch-family finger must be
    under its threshold for 2 consecutive frames before it's allowed to win
    `pinch_winner`, absorbing single-frame noise regardless of exact
    threshold values (generalizes better than threshold-tuning alone, which
    is inherently specific to this one camera/session's measurements).
    Verified live end-to-end afterward: 5 clean `PINCH_DOWN`/4 `PINCH_UP`
    matching deliberate pinches, 1 genuine `RIGHT_CLICK`, 2 `KEYBOARD_TOGGLE`
    from open-palm — no misfiring, no rapid-fire duplicates.
- **TASK-056 (`openspec/changes/personalization-and-config-ui`) — background /
  other-person hand filtering.** `GestureEngine.process()` now runs
  `filter_plausible_hands()` (new, `gestures.py`) once per frame, before any
  gesture logic: discards hands whose 21-landmark bounding-box area (fraction
  of the frame) is below `config.MIN_HAND_AREA_FRACTION`, keeps the 2 largest
  if more remain. Separately, `_process_two_hand_gestures()` now also
  requires `hands_plausibly_same_person()` (new) — both hands' bbox centers
  within `config.TWO_HAND_MAX_CENTER_DISTANCE_FRACTION` of the frame
  diagonal — before treating a 2-hand pair as one joint gesture; if not, each
  hand stays individually eligible as the single primary hand (only the
  *joint* 2-hand interpretation is rejected, not the hands themselves).
  Thresholds measured live (DroidCam, 2026-08-27, normal desk-webcam
  distance): a real single/either hand's bbox area fraction ranged
  0.0028–0.0126; `MIN_HAND_AREA_FRACTION=0.0015` sits comfortably below that
  (a background hand meaningfully farther from the camera falls off much
  faster, since bbox area scales with the square of distance). The same
  user's 2 hands' center-distance fraction, in normal desk use (not
  necessarily posed together), ranged 0.384–0.398 of the frame diagonal;
  `TWO_HAND_MAX_CENTER_DISTANCE_FRACTION=0.55` leaves comfortable margin
  above that so the user's own spread-apart hands are never rejected.
  **Explicit limitation, not silently solved:** this is a bounding-box-size
  and rough-proximity heuristic, not person re-identification or depth
  sensing — a second person standing close to the user, at a similar
  distance from the camera, with a similarly-sized hand nearby, is NOT
  reliably filtered by this (Phase 3B's `PoseLandmarker`-based anatomical
  wrist-ownership check, not yet implemented, is the stronger fix for that
  case — see `openspec/changes/personalization-and-config-ui/design.md`
  §3B). Verified live end-to-end afterward: 236 frames over 8s with a real
  hand in frame, 0 frames where the filter incorrectly dropped it (pointer
  stayed non-`None` throughout).
- **Scroll gesture tightened (same session as TASK-056, ad hoc per user
  report): now also requires the pinky curled, not just the ring finger.**
  Previously `index.y < pip.y and middle.y < pip.y and ring.y > pip.y` was
  enough — a hand with the pinky still extended could satisfy it. Now also
  requires `pinky.y > pts[18].y`, matching the user's explicit description
  ("el resto de los dedos" — ring AND pinky — curled, not just ring), same
  disambiguation reasoning as the earlier Shaka/fist fix.
- **Phase 3B (TASK-060b/060c) — MediaPipe Pose-based anatomical hand-ownership
  filter.** New `src/jarvis/pose_tracker.py` (`PoseTracker`, mirrors
  `hand_tracker.py`'s structure, `num_poses=1` deliberately — see its
  docstring), plus `filter_hands_by_pose_ownership()`: a detected hand is only
  kept if its wrist (landmark 0) is within `config.POSE_MAX_WRIST_DISTANCE_FRACTION`
  of the frame diagonal from the tracked body's left- or right-wrist landmark
  (indices 15/16 of MediaPipe's 33-point BlazePose topology). Wired into
  `main.py`'s `run()`, right after `HandTracker.process()`: when a body is
  confidently tracked, its result narrows `hands` before they reach
  `GestureEngine.process()` (which still runs TASK-056's bbox-area filter
  underneath — augments, doesn't replace); when no body is tracked that
  frame, `filter_hands_by_pose_ownership()` returns `None` and `hands` is
  left untouched, falling back to TASK-056's heuristic exactly as before —
  verified live (8s, real camera, no body in the frame's close-up
  hand/desk framing): 0 exceptions, hand tracking/pointer behavior
  unchanged throughout the whole run.
  - **Performance measurement (`spec.md` #3B.3), real camera, this
    development machine:** `PoseLandmarker` (lite variant) costs **~10.4ms/
    frame average, ~12.6ms p95** — measured back-to-back with
    `HandLandmarker`'s own **~10.0ms/frame average, ~12.7ms p95** on the same
    hardware/frames. Running both every frame roughly **doubles** per-frame
    vision-inference cost (~20ms combined) against design.md #25's "< 1 frame
    of additional latency" budget (~16–33ms at 30–60fps) — a real, non-trivial
    cost, not negligible.
  - **Decision: disabled by default** (`config.POSE_HAND_OWNERSHIP_ENABLED =
    False`), togglable via that constant — not "clearly bad" (TASK-056's
    heuristic keeps working standalone with zero regression), but doubling
    inference cost is significant enough that shipping it opt-in, honestly
    documented with real numbers, is the responsible default per design.md
    §3B.3's own guidance for a borderline-not-catastrophic cost.
  - **Explicit limitations, not silently solved:** (1) `POSE_MAX_WRIST_DISTANCE_FRACTION`
    (0.08) is a *reasoned* default (2 different models agreeing on the same
    physical wrist point should be very close), **not measured against real
    full-body camera data** — this session's camera framing (hand/desk
    close-up) never had a full body in view, so the wrist-agreement distance
    and the "hand correctly kept when a body IS tracked" path were verified
    only via `tests/test_pose_tracker.py`'s deterministic unit tests, not live
    end-to-end. (2) Same residual gap Phase 1 §1.2 already documented for a
    second person at a *similar* distance — Pose ownership fixes the "hand
    not attached to any tracked body" case, not "two people, each anatomically
    holding up their own hand, close together" (only 1 body is tracked,
    `num_poses=1`, by design — see §3B.1's own rationale).
- **Phase 2 (TASK-057) — toggleable hand/landmark visualization overlay.**
  New `src/jarvis/hand_visualizer.py`: `HAND_CONNECTIONS` (standard 21-point
  hand topology, declared locally — not from the removed `mp.solutions`, same
  reasoning as `hand_tracker.py`'s own docstring), `hand_connection_segments()`/
  `bounding_quadrant()` (pure, unit-tested against synthetic landmark sets),
  and `draw_hand_overlay()` (plain `cv2` drawing, zero new dependency):
  skeleton lines + landmark dots + a bounding-quadrant rectangle per detected
  hand, primary hand in `config.HAND_OVERLAY_PRIMARY_COLOR` (green) vs. any
  other detected hand in `config.HAND_OVERLAY_OTHER_COLOR` (dim gray) — primary
  determined by object identity against `GestureEngine.last_primary_landmarks`
  (new attribute, set every `process()` call, `None` when paused/no hands) —
  and the last-fired gesture name labeled next to the primary hand. New key
  **`l`** toggles it (off by default); reuses the existing `events[-1] if
  events else None` convention the debug HUD already uses for "current
  gesture." Doesn't change any gesture-detection behavior (full regression
  suite green with the toggle both on and off, since the draw call only runs
  after `GestureEngine.process()` has already produced its result). **Visual
  correctness verified by actually rendering it**: a real camera session had
  no hand in frame during this task (this environment's camera framing), so
  correctness was confirmed by rendering `draw_hand_overlay()` onto a frame
  with realistic synthetic 2-hand landmark data (proportioned like a real
  open hand) and reading the resulting PNG back as an image — skeleton
  connects correctly end-to-end (thumb/index/middle/ring/pinky + palm base),
  primary hand renders green with its bounding quadrant and the
  `PINCH_DOWN` label positioned above it, the other hand renders dim gray
  with no label, exactly as designed.
- **Phase 3 (TASK-058/059/060) — procedural reference-icon infrastructure.**
  New `src/jarvis/gesture_icons.py`: `ICON_SPECS` (declarative — finger
  extended/curled sets per hand, optional pinch-contact marker, optional
  small action-glyph badge), `ensure_icon(key) -> Path` (lazy-generate-and-
  cache under `assets_dir()/gesture_icons/`, same pattern as the MediaPipe
  model downloads — gitignored, nothing hand-authored committed), and
  `generate_all_icons()`. Drawn with `PIL.Image`/`PIL.ImageDraw` (new
  dependency: Pillow, added to `requirements.txt`) — a stylized palm +
  5-finger skeleton (bold/dark for extended, thin/gray for curled), a red dot
  marking pinch contact when relevant, and a small geometric action badge
  (arrow/lock/mute/zoom/camera/keyboard/pause/close — no text, to sidestep
  the same accented-character font problem `cv2.putText` already has,
  documented below). Keyboard-only legend entries (no hand involved) get a
  plain keycap glyph with the literal key letter instead (ASCII only: Q/H/M/
  +-, no accents needed there). All 17 existing legend entries covered; every
  icon's raw PNG bytes verified pairwise-distinct (`tests/test_gesture_icons.py`).
  - `jarvis.legend.ENTRIES` gained a 3rd tuple element (icon key) per entry;
    new `build_legend_entries()` resolves it through `ensure_icon()`.
    `build_legend_text()` kept unchanged — verified byte-identical output
    before/after (`tests/test_legend.py`).
  - `overlay.ScreenOverlay.init_legend()` signature changed from a single
    pre-formatted `text` string to `(entries, corner, title=None)`: each
    entry renders as an icon `Label` + a text `Label` in a grid row, native
    `tk.PhotoImage(file=...)` (PNG support built into Tk 8.6+) — no
    `PIL.ImageTk`, per spec.md #3.1's explicit Must NOT. `PhotoImage`
    instances are kept alive in `self._legend_icons` (Tk does not hold its
    own reference — without this, Python's GC would collect them and the
    icons would blank out shortly after the panel is created, a known Tk
    gotcha). Toggle/opacity/click-through bindings unchanged (`_toggle_legend_visible`/
    `adjust_legend_alpha`/`_make_click_through` untouched).
  - **Verified by actually rendering it**, same discipline as the hand
    overlay above: constructed a real `ScreenOverlay`, called
    `init_legend(build_legend_entries(), title=TITLE)` for real, screenshotted
    the live screen region, and read the image back — icons, colors, and text
    rows all render correctly against the translucent panel background, title
    at top, exactly as designed.
- **Phase 4 (TASK-061/062/063) — one-hand Naruto seals.** Full collision
  census against the complete 9-check single-hand surface (`design.md` §1.4)
  plus every other new seal, verified against the REAL `GestureEngine` (not
  just reasoned about) — every one of the 8 seal fixtures produces
  `[f"NARUTO_{name}"]` and nothing else after its hold, and every existing
  fixture (pinch/scroll/zoom/volume/screenshot/shaka/fist/silence/open-palm,
  including the fist-opening-transition regression from the earlier
  Shaka fix) produces zero `NARUTO_*` events (`tests/test_gesture_engine_regression.py::NarutoOneHandSealTests`).
  - **`Saru` (Monkey) — REDEFINED, per design.md's own explicit flag.** The
    original definition ("thumb+pinky extended, rest curled") is EXACTLY
    `_is_shaka`'s shape — reusing it would silently change what an existing
    gesture (`LOCK_SESSION`/`CLOSE_APP`) means, forbidden by `apply.md` §15.
    Redefined to thumb+ring extended, index/middle/pinky curled — unused by
    anything else, verified.
  - **`Uma` (Horse) — REDEFINED, a collision design.md itself did NOT flag,
    found during this task's own census (same kind of gap-catching this
    project has done before — see the earlier collision-surface undercount
    and the shared-cooldown bug).** The original definition ("all 5 fingers
    extended and spread, thumb out") is a STRICT SUBSET of `KEYBOARD_TOGGLE`'s
    existing condition (open palm + thumb spread >60px) — any hand shaped
    like the original Uma would ALSO satisfy `KEYBOARD_TOGGLE`, firing both.
    Redefined to index+middle+ring extended, pinky curled, thumb extended to
    the side — distinct curl signature, verified.
  - **Tora/U/Hitsuji share the same base finger-curl shape as SCROLL**
    (index+middle extended, ring+pinky curled) — per design.md's own
    description of Tora. Distinguished from SCROLL and from each other
    entirely via conditions ALREADY computed in `process()`, without
    touching SCROLL's existing condition at all: thumb distance to index
    `<=40px` (Tora/U/Hitsuji) vs. SCROLL's existing, unchanged `>40px`
    (mutually exclusive, no dead zone, no shared code path); index-middle
    tip distance `<30px` ("together" → Tora) vs. `>50px` ("spread/peace-sign"
    → U); a genuine finger-crossing check (`_fingers_crossed` — compares tip
    x-order against MCP x-order, not just "close together") → Hitsuji. A
    30–50px index-middle gap is a deliberate dead zone: fires neither, safer
    than guessing.
  - **All 8 seals additionally gated on `pinch_winner is None`** (no
    pinch-family condition currently winning) **and `not two_hand_active`.**
    This is a blanket rule, not per-seal tuning — it structurally rules out
    any collision with the 5 pinch-family gestures regardless of a specific
    seal's exact thumb geometry (if a seal's thumb ever gets close enough to
    a fingertip to register as a pinch, the pinch wins that frame and the
    seal simply doesn't fire — never both).
  - **`I` (Boar) — accepted, documented limitation, not a collision to
    resolve.** `_is_fist()` doesn't check the thumb, so `I`'s shape (fist +
    thumb out) also reads as `_is_fist()==True` for the two-hand
    `fists[0] != fists[1]` meta-menu discrimination. With 2 hands in frame
    and the other hand NOT a fist, this arms the meta-menu's anchor mode in
    the background — it does not fire any action by itself (still needs a
    separate, deliberate 1–4-finger hold on the other hand). Judged
    acceptable: a dormant background state, not a silently-wrong executed
    action — the exact line `apply.md`/this project's collision policy
    actually cares about.
  - **Hold-then-confirm timing, same pattern as `LOCK_SESSION`/`_is_shaka`:**
    a new `config.NARUTO_SEAL_HOLD_SECONDS=0.6` (same order as
    `META_HOLD_SECONDS`) — a seal must be held continuously before its event
    fires; releasing it (even to a shape that matches no seal) resets the
    timer from zero, verified (`test_releasing_the_seal_before_the_hold_resets_it`).
    **This is what satisfies "a seal bound to a `HOLD_REQUIRED` command
    doesn't bypass its gating" (TASK-063):** the gating lives entirely
    upstream, inside `GestureEngine` — a `NARUTO_*` event is structurally
    incapable of existing before its hold completes, so no dispatch-layer
    code could ever bypass it even if it tried. Verified end-to-end
    (`tests/test_naruto_seal_dispatch.py::HoldRequiredGatingTests` +
    `manual_live_integration_check.py`, both using the real default binding
    `NARUTO_I` → `LockSession`, which is genuinely `HOLD_REQUIRED`).
  - **Dispatch (TASK-063):** `main.py`'s `NARUTO_DEFAULT_BINDINGS` dict +
    `JarvisApp._dispatch_naruto_seal()`, reusing `ProfileManager.get_gesture_binding()`
    (already built for TASK-024, untouched) for "profile override > default
    > None" precedence, and reusing `_dispatch_voice_action()` (the same
    fixed-vocabulary path voice already uses) for the actual dispatch — a
    seal and the equivalent voice command produce identical feedback/history
    behavior by construction, not by parallel implementation. An unbound
    seal (`get_gesture_binding` returns `None`) is a safe no-op, verified.
    Default bindings: Tora→Screenshot, Ushi→Undo, U→Redo, Uma→ZoomIn,
    Hitsuji→Mute, Saru→KeyboardToggle, Inu→VolumeDown, I→LockSession.
  - **Icons:** 8 new `ICON_SPECS` entries (Phase 3 infra), all pairwise
    byte-distinct from each other and from the 17 existing icons (verified),
    plus one new legend row per seal — the 16 pre-existing legend lines
    changed ONLY in padding width (a longer new line widened the shared
    `ljust`), never in their own text (verified, updated snapshot in
    `tests/test_legend.py`).
  - **Update — real-camera verification session (2026-08-27), one seal at a
    time, with the user's real hand.** Synthetic-fixture verification (above)
    proved the code was internally consistent and collision-free; it did NOT
    prove a real hand could actually produce these shapes the way the
    fixtures assumed. It couldn't — of the 8 seals, only Hitsuji's base shape
    came close on the first real attempt. Root-caused per seal (raw
    per-finger tip/pip deltas and derived distances logged live, not
    guessed):
    - **`_fingers_crossed` (v1) false-positived ~60–70% of the time** on a
      genuine Tora attempt (index+middle simply held together, not crossed)
      — it only compared the LATERAL ORDER of the two tips against their
      MCPs' order, which flips easily from ordinary landmark noise when tips
      are close together. **Fixed (v2):** real 2D line-segment intersection
      (orientation/cross-product test) between each finger's full MCP→tip
      segment — a structurally stronger signal that a genuine cross requires.
    - **Uma (v2: "index+middle+ring extended, pinky curled") and Saru (v2:
      "thumb+ring extended") both scored 0% on a genuine attempt** — both
      required isolating the ring finger independently of its neighbors,
      which is physiologically hard (middle/ring/pinky share tendons; most
      people cannot curl/extend the ring finger alone without dragging
      adjacent fingers). The real hand naturally produced thumb+index+pinky
      extended (middle+ring curled — an "I-love-you"/"rock-on"-style shape)
      when attempting Uma, and a fully-open hand when attempting Saru.
      **Redefined a 3rd time, informed by what the real hand could actually
      do:** Uma → thumb+index+pinky extended, middle+ring curled (verified
      achievable). Saru → closed fist with the thumb pointing UP (not
      isolating any single finger — distinguished from `I` below by thumb
      DIRECTION, not by which fingers curl).
    - **Inu (v1: "ring+pinky extended together") also scored 0%** — same
      ring-isolation problem; the real hand stayed fully closed. **Redefined:**
      pinky extended alone (pinky has meaningfully more independent tendon
      control than ring, confirmed by every capture where it moved
      independently while ring did not).
    - **`I` (Boar) scored ~0% on its own thumb condition** for a different
      reason: the original check reused the same VERTICAL curl test as every
      other finger (`tip.y < pip.y`), but "thumb extended outward to the
      side" is a LATERAL motion — a vertical check structurally cannot see
      it (thumb read as "curled" ~97% of the time even while held clearly
      out to the side). **Fixed:** new `_thumb_offset_from_palm()` compares
      the thumb tip's horizontal vs. vertical offset from the palm-center
      landmark (9) and requires the lateral component to dominate — the same
      helper now also drives Saru's "thumb up" (vertical component
      dominates instead).
    - **New shared mechanism: `config.NARUTO_SEAL_MISS_TOLERANCE=3`.** Even
      holding a correct shape deliberately, live classification flickers to
      "no seal" for an occasional single frame (landmark noise, not a real
      pose change) — confirmed live. Without tolerance, ANY flicker fully
      reset the 0.6s hold, making it near-impossible to complete in
      practice. Same principle as `PINCH_CONFIRM_FRAMES` (TASK-055/1.5),
      applied to the opposite side of the problem: not losing an in-progress
      confirmation, rather than not granting one too early.
    - **A real, subtler bug the fix for `I` surfaced and caught before
      shipping:** the existing `fist_hand()` regression fixture (used
      throughout this whole test file for two-hand scenarios) has its thumb
      resting a plausible-but-arbitrary distance to the side — with `I`'s
      original 0.06 lateral threshold, that ordinary fixture ALSO read as
      `NARUTO_I` when passed as a single hand. Raised the threshold to 0.15
      (verified against `fist_hand()`'s own offset) so a relaxed fist's
      incidental thumb position can't be mistaken for a deliberate sideways
      extension; `I`'s own fixture (built for a clearly deliberate lateral
      thumb) still clears the new threshold comfortably.
    - **Icons and legend updated to match** every redefinition (Uma/Saru/Inu
      geometry, `I`'s clarified "costado" wording) — regenerated, re-verified
      pairwise-distinct.
    - **Scope of this pass:** re-verified via updated unit tests (496 total,
      green) and the same root-cause-from-real-data discipline as every fix
      in this project. The FIXED detectors were **not** re-run against the
      camera a second time in this session (explicit user choice — "documenta
      y sigue" — to move on rather than spend another live round); a
      follow-up live check of Tora/Hitsuji/Uma/Saru/Inu/`I` specifically is
      recommended before considering Phase 4 fully closed. Ushi and U were
      not cleanly re-attempted live either (the session moved on before a
      clean take) — their designs were left unchanged since the underlying
      shapes (index alone; index+middle spread) are anatomically ordinary,
      but they carry the same "not confirmed after this pass" caveat.
- **Phase 5 (TASK-064/065/066) — two-hand Naruto seals (Ne, Mi, Tori, Kai,
  Tatsu).** The user provided a reference photo of the real traditional
  seals (all genuinely two-hand, fine finger-interlacing) and explicitly
  chose **"real geometry first, simplify only if it fails live"** over
  starting from a simplified proxy. design.md §5.1 itself already flags
  that MediaPipe's 21 landmarks per hand can't reliably resolve fine
  inter-hand finger interlacing (occlusion) and explicitly permits a coarser
  proxy (hand-center distance + average finger curl + relative orientation)
  as long as it's documented and the seal stays visually recognizable — that
  permission is what's implemented here, not an unprompted simplification.
  - **Collision surface is larger than design.md described**, because it
    was written before Phase 4 added 8 new single-hand checks: a new
    two-hand gesture must now avoid colliding with **17** single-hand checks
    (9 original + 8 Naruto one-hand seals) × 2 hands, plus the **4** existing
    two-hand-specific checks (`both_shaka`/`both_fists`/`both_pinching`/meta-menu)
    = 21 conditions total, not the 13 the original document counted.
  - **New shared primitives** (`gestures.py`): `_segments_cross()` (factored
    out of the one-hand `_fingers_crossed` fix so it can also compare
    segments ACROSS the two hands, for Kai), `_curl_ratio()` (fraction of
    the 4 non-thumb fingers reading extended — the "how folded/interlaced"
    proxy), `_hand_center()`/`_hands_distance()`, `_hand_points_up()`/`_hand_points_down()`.
  - **Geometric definitions** (all evaluated inside `_process_two_hand_gestures`,
    excluded whenever `both_shaka`/`both_fists`/`both_pinching` already
    matched — hierarchy, not overlap, per the user's own standing principle
    for this project):
    - `Kai` — both hands' centers clasped-close AND both hands' index+middle
      extended AND a real segment-cross between the two hands' index or
      middle fingers (reuses the same geometric intersection test as the
      one-hand Hitsuji fix, applied cross-hand). Checked first (most
      specific).
    - `Tatsu` — clasped-close AND a large curl-count asymmetry between the
      two hands (one much more curled than the other — a coarse proxy for
      "one hand wraps/layers over the other").
    - `Ne` — clasped-close AND both hands' curl ratio in a "partially
      folded" middle band (neither a fist nor fully open — the interlacing
      proxy) AND both hands' average fingertip position above the wrist
      ("pointing up").
    - `Mi` — identical to `Ne` except both hands point DOWN instead — the
      ONLY difference between the two, matching the real seals (design.md
      §5.1: "distinguish from Ne by orientation... not finger shape alone").
    - `Tori` — hands at a MEDIUM distance (further apart than the clasped
      seals, not as far as an unrelated two-hand gesture) AND both hands'
      curl ratio high (open/spread, not folded) — "fanned open" per the
      reference photo.
  - **Same hold-then-confirm + miss-tolerance mechanism as Phase 4**, new
    dedicated state (`self._twohand_seal_hold_name/_start/_miss_streak`) and
    a longer `config.NARUTO_TWOHAND_HOLD_SECONDS=1.2` (matches the existing
    `PAUSE_HOLD_SECONDS` two-hand precedent — longer than the one-hand
    seals' 0.6s, since a two-hand pose is more complex/error-prone to hold
    by accident).
  - **Verified against the real `GestureEngine`** (synthetic fixtures, same
    discipline as every seal in this project): each of the 5 fixtures fires
    exactly its own `NARUTO_<NAME>` event and nothing else; none of the
    existing two-hand fixtures (`both_fists`/`both_shaka`/meta-menu) leak a
    seal event, and none of the 5 new fixtures leak an existing two-hand
    event (`tests/test_gesture_engine_regression.py::NarutoTwoHandSealTests`).
  - **Dispatch/icons/legend**, same TASK-063 mechanism reused as-is
    (`_dispatch_naruto_seal` already dispatches by the `NARUTO_` prefix
    regardless of 1- or 2-hand origin — no new dispatch code needed).
    Defaults: Ne→ZoomOut, Mi→ScrollDown, Tori→ScrollUp, Kai→CloseApp
    ("Release" — a deliberate thematic fit), Tatsu→VolumeUp. 5 new
    `hands: 2` icons (Phase 3 infra already supported this), all pairwise
    byte-distinct from the existing 25.
  - **Honest limitation, explicitly not yet closed:** unlike Phase 4, **none
    of these 5 seals have been verified against a real hand on camera yet**
    — this pass ends at synthetic-fixture verification, by the user's own
    explicit choice ("saltamos a la fase 5, luego realizaremos la prueba
    integral nuevamente" — skip to Phase 5, do the real-camera pass together
    afterward). All 5 geometric thresholds
    (`NARUTO_TWOHAND_CLASP_MAX_DISTANCE_FRACTION=0.20`,
    `NARUTO_TWOHAND_FAN_MIN/MAX_DISTANCE_FRACTION=0.20/0.42`, the 0.2–0.8
    curl-ratio "interlaced" band, the 0.75 "open" threshold for Tori, the
    ≥2 curl-count asymmetry for Tatsu) are REASONED, not measured — given
    Phase 4's experience (7 of 8 one-hand seals needed real correction
    despite passing synthetic verification first), these should be treated
    as a first draft pending the same live-camera correction cycle, not a
    finished result.
- **Phase 6 (TASK-067/068/069/070) — Jujutsu Kaisen gestures (Gojo Domain
  Expansion, Sukuna's snap, Megumi).** First phase in the project where the
  user opted OUT of the per-phase live-camera correction cycle used for
  Phases 4/5 — explicit instruction was to defer ALL remaining verification
  to one combined "prueba integral" pass covering Phases 4/5/6 together, and
  to keep implementing code in the meantime. Everything below is REASONED
  and synthetic-fixture-verified only; nothing here has touched a real
  camera yet.
  - **`temporal_gesture.py` (new module) — `ImpulseDetector`**, the first
    TEMPORAL/multi-frame primitive in this codebase (every existing gesture
    is either single-frame state or a simple hold-timer). A 3-state machine
    (`idle` → `armed` → fires and returns to `idle`, OR `armed` → `expired`
    if the window elapses while still in contact → `idle` only once the
    tracked distance finally rises above `release_threshold`, WITHOUT
    firing). The 3rd state is what makes a long sustained pinch that
    eventually releases NOT count as an impulse — a naive 2-state version
    (armed/idle only) was drafted first and found, by reasoning through the
    exact sequence, to spuriously refire once the sustained hold finally
    let go; the 3-state version was written specifically to close that hole,
    and `tests/test_temporal_gesture.py` pins all 4 of TASK-067's acceptance
    criteria including that exact scenario. Reused as-is for Sukuna here and
    intended for Clap in Phase 7 (design.md explicitly forbids a second,
    parallel implementation).
  - **`JJK_SUKUNA` (one-hand, temporal)** — `ImpulseDetector` tracking
    `d_thumb_middle` (the same distance `RIGHT_CLICK` already computes),
    contact/release/window reasoned at 15px/55px/0.35s (tighter contact than
    `PINCH_RIGHT_CLICK`'s 20px — a snap is a decisive full touch, not a
    casual pinch; release comfortably above the ~51px relaxed-hand noise
    ceiling measured for Phase 4/TASK-056). Fed unconditionally every frame
    (not gated behind `pinch_winner`/`two_hand_active` like the static
    seals) because the detector needs the real distance every frame to track
    its own state machine correctly — gating it would starve it of frames
    mid-gesture. **Known, deliberately UNRESOLVED collision risk:** because
    Sukuna's contact threshold (15px) is tighter than `RIGHT_CLICK`'s
    (20px), a real snap's approach necessarily crosses `RIGHT_CLICK`'s
    looser threshold first — if held there for `PINCH_CONFIRM_FRAMES`
    consecutive frames, `RIGHT_CLICK` could fire on the same physical
    motion that later completes as `JJK_SUKUNA`. This is flagged in code
    (`gestures.py`, next to the `update()` call) rather than silently
    "solved" by an unverified threshold tweak — it's exactly the kind of
    thing Phase 4's real-camera pass caught and this one explicitly can't,
    yet. `tests/test_gesture_engine_regression.py::JJKGestureTests` does
    confirm the synthetic discrimination TASK-069 asks for (a fast
    contact→release sequence fires `JJK_SUKUNA` not `RIGHT_CLICK`; a
    2-frame-confirmed sustained pinch fires `RIGHT_CLICK` and, even after
    being rewound past Sukuna's window and finally released, never fires
    `JJK_SUKUNA`) — synthetic fixtures necessarily can't exercise the timing
    ambiguity of a *real*, noisy, human snap.
  - **`JJK_GOJO_DOMAIN` (two-hand, static, taxonomy Pattern B per design.md
    §1.5)** — new `_thumb_index_angle_deg()` primitive (dot product between
    each hand's thumb MCP→tip and index MCP→tip vectors) checked against
    ~90°±35° for BOTH hands, AND the two hands' centers within
    `JJK_GOJO_MAX_DISTANCE_FRACTION=0.30` of the frame diagonal (looser than
    the Naruto seals' 0.20 "clasped" threshold — Gojo's frame doesn't
    require the hands to actually touch), AND both wrists' average y above
    (numerically below, image coordinates) `JJK_GOJO_MAX_AVG_WRIST_Y=0.55`
    (upper half of frame, approximating "held up near the face"). The
    condition is genuinely BETWEEN the two hands (relative angle + relative
    position), never two independently-classified single-hand shapes —
    confirmed staying Pattern B per TASK-068's explicit ask. Checked LAST in
    the two-hand elif chain (after Kai/Tatsu/Ne/Mi/Tori) since it's a
    structurally distinct geometric family (vector angle, not
    distance/curl-ratio) and doesn't need to compete for priority with them.
  - **`JJK_MEGUMI` (one-hand, static)** — same visual family as Hitsuji
    (index+middle genuinely crossed, via the existing `_segments_cross`
    primitive) but with the ring finger EXTENDED instead of curled — the
    exact discriminator design.md §6.3 asked for, made structurally
    impossible to collide with Hitsuji (Hitsuji's own base-shape check
    requires ring curled) rather than relying on a threshold.
    `tests/test_gesture_engine_regression.py::JJKGestureTests::test_megumi_is_geometrically_distinguished_from_hitsuji_by_the_ring_finger`
    builds both fixtures from the literal same coordinates except that one
    finger, to pin exactly that.
  - **Event naming refactor (no behavior change):** `_naruto_seal` and
    `_twohand_seal` now hold the FULL event string (`"NARUTO_KAI"`,
    `"JJK_MEGUMI"`, `"JJK_GOJO_DOMAIN"`) instead of a bare name later
    f-string-prefixed with `NARUTO_` — needed so the same
    hold-then-confirm-then-miss-tolerance state machine could serve both the
    `NARUTO_` and `JJK_` namespaces without duplicating it. `main.py`'s
    dispatch loop now checks `event.startswith("NARUTO_") or
    event.startswith("JJK_")` before routing to `_dispatch_naruto_seal`
    (kept that name — it already only ever cared about the prefix
    generically, never NARUTO-specific logic).
  - **Dispatch defaults exhaust the fixed action vocabulary.**
    `llm_intent.VALID_ACTIONS` has exactly 14 actions, and the 13 Naruto
    seals from Phases 4/5 already claim 13 of them — only `RIGHT_CLICK`
    remained free. `JJK_GOJO_DOMAIN` takes it (Gojo, the most prominent of
    the 3, gets the one genuinely free slot); `JJK_SUKUNA`→`SCREENSHOT`
    (reused from Tora — "snap" a picture) and `JJK_MEGUMI`→`MUTE` (reused
    from Hitsuji — shadow/stealth theme) deliberately REUSE an already-bound
    action. This isn't a bug: `ProfileManager.get_gesture_binding()` already
    treats every binding as independently overridable per profile, so two
    physical gestures defaulting to the same command is equivalent to two
    keyboard shortcuts for the same action, not a collision.
  - **Icons**: `jjk_sukuna` is the first icon to use a NEW glyph (`snap` —
    four short radiating lines, a small motion/spark cue) instead of a
    static pose glyph, per TASK-070's explicit ask that Sukuna's icon
    communicate motion, not just shape (it reuses `pinch_right_click`'s
    exact hand shape — thumb+middle touching — and is differentiated
    ONLY by that glyph, intentionally, since Sukuna genuinely IS that
    pinch, just fast). `jjk_gojo_domain`/`jjk_megumi` are visually distinct
    by extended-finger-set alone (new combinations not used by any prior
    icon), no glyph needed. All 32 icons confirmed pairwise byte-distinct
    (`tests/test_gesture_icons.py`).
  - **Honest limitation, explicitly not yet closed:** none of Gojo/Sukuna/
    Megumi have touched a real camera. Beyond the usual "thresholds are
    reasoned not measured" caveat already carried over from Phase 5, Sukuna
    specifically carries a KNOWN, undiagnosed collision risk against
    `RIGHT_CLICK` (see above) that can only really be resolved by watching
    what a real snap's landmark sequence actually does frame-by-frame —
    exactly the kind of failure Phase 4's real-camera pass caught 7 times
    out of 8 and this phase, by explicit user choice, hasn't attempted yet.
    Deferred to the combined Phase 4+5+6 "prueba integral" live-camera pass.
- **Phase 7 (TASK-071/072/073) — common gestures (Clap, Korean finger
  heart).** Same "keep coding, defer all verification" instruction as Phase
  6 — everything below is reasoned and synthetic-fixture-verified only.
  - **`CLAP` (two-hand, temporal, taxonomy Pattern D per design.md §1.5)** —
    a SECOND `ImpulseDetector` instance (the first reusable-primitive payoff:
    design.md explicitly forbids a parallel reimplementation) tracking the
    distance between the two hands' PALM centers (average of landmarks
    0/5/9/13/17 — a new `_palm_center()`/`_palm_centers_distance()` pair,
    deliberately distinct from `_hand_center()`/`_hands_distance()`, which
    average all 21 landmarks for the Naruto/JJK two-hand seals, and from the
    pinch-point average the two-hand pinch-zoom uses — 3 different "hand
    center" notions, each already owned by a different existing gesture).
    Thresholds reasoned as fractions of the frame diagonal, same unit as the
    Naruto two-hand seals: contact 0.12 (tighter than their 0.20 "clasped"
    proximity — a clap is actual near-contact, not just "brought together"),
    release 0.30, window 0.4s. Fed unconditionally every frame (same reason
    as Sukuna — the detector needs real distance every frame); the `CLAP`
    event itself is gated behind the full two-hand hierarchy (`_twohand_seal
    is None` and none of `both_shaka`/`both_fists`/`both_pinching`) so it
    never collides with an already-recognized two-hand gesture, and folded
    into `two_hand_active` like every other two-hand event. The
    `clap_hand()` test fixture was deliberately built with all 4 non-thumb
    fingers uniformly extended (`curl_ratio=1.0`, outside the 0.2–0.8
    "interlaced" band Ne/Mi/Kai/Tatsu depend on) specifically so that NO
    distance between two such hands accidentally satisfies an existing
    two-hand gesture — confirmed by a dedicated test
    (`test_clap_hand_pair_never_matches_an_existing_two_hand_gesture`) across
    contact/release/near-miss distances, not assumed.
  - **`KOREAN_HEART` (one-hand, static + hold-confirmation)** — thumb tip
    close to the index's PIP (landmark 6, the first joint), explicitly NOT
    close to its tip (landmark 8, `PINCH_CLICK`'s own metric) — the
    structural distinction is what makes `d_thumb_index >= PINCH_CLICK` true
    by construction for this shape, so `pinch_winner` can never resolve to
    `"index"` for it and `PINCH_DOWN` can never fire for it, at any point
    during the hold — not just "unlikely below some tuned threshold." Held
    `KOREAN_HEART_HOLD_SECONDS=1.0` before firing (same mechanism as
    `LOCK_SESSION`/Shaka), so a fast touch-and-release of the *real*
    `PINCH_CLICK` shape stays exclusively `PINCH_DOWN`/`PINCH_UP` — it's
    geometrically a different shape from the start, not a race against the
    clock.
    - **Real collision found and fixed WITHOUT a camera, by the test suite
      itself** (same discipline as Phase 4's `fist_hand()`/`NARUTO_I`
      incident): the first draft of `korean_heart_shape` didn't check finger
      curl at all, and `tests/test_gesture_engine_regression.py`'s
      "existing fixtures don't leak a new event" census caught that
      `silence_hand()` — whose thumb (landmark 4) and index PIP (landmark
      6) are coincidentally placed at the exact same point by that
      fixture's own construction, unrelated to Korean Heart — satisfied
      both of Korean Heart's conditions after being held. **Fixed** by
      requiring `_fingers_curled(pts, 8, 12, 16, 20)` too (Korean Heart is a
      closed fist with only the thumb crossing; `SILENCE` requires all 4
      fingers extended) — a structural exclusion, not a threshold nudge,
      matching how every other near-collision in this project has been
      resolved once found.
  - **Dispatch mechanism simplified, no behavior change**: `main.py`'s
    `run()` loop used to route by `event.startswith("NARUTO_") or
    event.startswith("JJK_")`; `CLAP`/`KOREAN_HEART` carry neither prefix
    (they're not "seals"), so the check became `event in
    NARUTO_DEFAULT_BINDINGS` instead — simpler (a plain membership test) and
    already correct for every existing key, since every event
    `GestureEngine` can emit through this path has always had exactly one
    entry in that dict. `_dispatch_naruto_seal` itself didn't change; its
    docstring was updated to stop implying prefix-awareness it never
    actually had.
  - **Dispatch defaults, thematic reuse (fixed 14-action vocabulary long
    since exhausted, see Phase 6):** `CLAP`→`KEYBOARD_TOGGLE` (the "Clapper"
    — clap to turn something on/off — reused from Saru) and
    `KOREAN_HEART`→`SCREENSHOT` (the finger heart is a classic photo pose —
    reused from Tora/Sukuna).
  - **Icons**: `clap` reuses `naruto_tori`'s exact hand shape (both hands
    fully open) on purpose — Clap and Tori are visually identical as static
    poses, since the icon model can't represent motion or inter-hand
    distance — differentiated ONLY by a NEW glyph (`clap_burst`: 6 short
    lines radiating from a filled center dot, denser than Sukuna's `snap`
    glyph, deliberately distinct from it too — same "this is an impulse"
    language, different silhouette). `korean_heart` is the first one-hand
    icon with an empty extended-set (a plain closed fist, thumb marked via
    the existing pinch-marker mechanism at its curled position) plus a new
    `heart` glyph. All 34 icons confirmed pairwise byte-distinct
    (`tests/test_gesture_icons.py`).
  - **Honest limitation, explicitly not yet closed:** neither gesture has
    touched a real camera. Deferred, along with Phases 4/5/6, to the
    combined "prueba integral" live-camera pass.

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
- **STT+LLM voice control needs its optional dependencies and a ~1GB model
  download on first use.** `pip install -r requirements-voice.txt`, then
  `jarvis.llm_intent._ensure_model_path()` downloads the Qwen2.5-1.5B-Instruct
  GGUF into `assets/` the first time `LLMIntentResolver.resolve()` actually
  runs (same pattern as the MediaPipe model) — not bundled in the portable
  `.exe`, so a release build has no voice control out of the box.
- **No wake word.** Voice listening is push-to-talk (`v` toggles recording) —
  deliberate, to avoid the extra always-on model/dependency (`openWakeWord`)
  a wake-word implementation would need.

## Future work

See [`docs/archive-es/ROADMAP.md`](docs/archive-es/ROADMAP.md) for the full original
write-up (Spanish) — natural-language voice control is now implemented (see Status,
`jarvis.voice_capture`/`jarvis.llm_intent`). Still open: a local wake-word model so
STT doesn't need a manual key press, and bundling the voice dependencies/model into
the packaged `.exe` release.
