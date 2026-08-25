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
| **Live integration** of previously-dormant PHASE 3-11 pieces (branch `feature/full-integration-voice-llm`, not yet merged) | Done for what's genuinely low-risk/high-value: Telemetry (always-on, in-memory), `ProfileManager` (sources `smoothing_enabled`, cycle with `p`), `CommandHistory`+`UndoRedoController` (real `z`/`y` undo/redo), a debug HUD overlay (`d`), and `ForegroundApplicationTracker` (cached, feeds telemetry). 424 tests, a new live-integration check script, `GestureEngine` output and a live boot both unchanged. Deliberately still NOT wired: `GestureStateMachine`, generic debounce/cooldown, `ConfidenceFilter` (no real confidence signal to filter — see below), swipe/dwell/double-click gesture bindings, and an `InputProvider`-based loop rewrite — each has a documented reason in `main.py`'s module docstring, not a silent gap |
| Natural-language voice control (STT + local LLM) | Not implemented — deliberately deferred, see Future Work |

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
- **`hud_keyboard.py`** — `HUDKeyboard`: on-screen keyboard layouts (Spanish/numeric/emoji), `draw(frame, cursor)`. Still drawn inside the camera window (unlike the legend, this one is tied to the pinch/cursor interaction happening there). `handle_click(cursor) -> KeyAction | None` no longer executes `pyautogui` itself (OpenSpec TASK-012) — it returns a `KeyAction(kind, value)` describing what was touched (`"key"`/`"text"`/`"layout"`), and `main.py` turns that into a `Command`. Layout switches (123/ABC/EMOJI) stay internal state, no OS side effect, so no `Command` for those.
- **`legend.py`** — content only: `build_legend_text()` builds the multi-line gesture list string. No drawing logic — it used to render on the camera frame via `cv2.addWeighted`; that was removed in favor of a native overlay window (see below).
- **`overlay.py`** — `ScreenOverlay`, built on Tkinter (stdlib, zero new dependencies):
  - `show_bubble(text, x, y)` — a transient translucent toast at any screen position, self-destroys via `after()`.
  - `init_legend(text, corner)` / `set_legend_visible()` / `adjust_legend_alpha()` — a persistent panel anchored to a screen corner, translucent, with runtime opacity control.
  - Both use `_make_click_through(window)`: on Windows this applies `WS_EX_LAYERED | WS_EX_TRANSPARENT` to the real HWND (obtained via `GetParent(winfo_id())`) through `ctypes` — a well-known, dependency-free trick, verified working on this machine (see Decisions). No-op elsewhere.
  - `pump()` is called once per camera frame instead of `mainloop()`, because Tk is not thread-safe and a separate UI thread would race with the camera loop.
- **`gestures.py`** — `GestureEngine`: pure logic, no I/O. `process(hands, w, h, screen_w, screen_h) -> (screen_xy | None, cam_xy | None, events)`. Single-hand gestures always use `hands[0]` and are entirely skipped when `active` is `False` (paused) — in that case `screen_xy` is `None`, so `main.py` neither moves the mouse nor draws the keyboard. The two master, two-hand gestures (`TOGGLE_ACTIVE`, `CLOSE_APP`) are evaluated *before* checking `active`, so pause can always be undone and the app can always be closed.
- **`main.py`** — `JarvisApp`: owns the camera loop, calls `GestureEngine.process`, draws the keyboard/pause banner, handles the keyboard shortcuts (`q`/`h`/`m`/`+`/`-`). `_dispatch()` splits events into the 11 discrete gestures migrated onto `Command`/`CommandBus` (`_dispatch_migrated()`) vs. everything else, still called directly exactly as before this migration.

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
| Index+middle extended, ring curled | Vertical scroll |
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
| Profiles (cursor sensitivity, smoothing, swipe thresholds, dwell, cooldowns, gesture bindings) | `jarvis.core.profiles.ProfileManager` / `Profile` | No — standalone (PHASE 5); `default` profile mirrors `config.py`'s real values |
| Foreground-app detection cache TTL | `jarvis.core.context_tracker.ForegroundApplicationTracker(cache_ttl=0.5)` | No — standalone (PHASE 6) |
| Command history size | `jarvis.core.command_history.CommandHistory(max_size=50)` | No — standalone (PHASE 9) |
| Telemetry history size, optional sink | `jarvis.core.telemetry.TelemetryManager(max_history=500, sink=None)` | No — standalone (PHASE 8) |
| Voice phrase → intent bindings | `jarvis.core.voice_intent_resolver.VoiceIntentResolver(phrase_bindings=...)` | No — standalone (PHASE 11), starts empty unless `DEFAULT_PHRASE_BINDINGS` is opted into |

## Performance baseline

Real measurements taken on the development machine (not estimates), so migrating
onto the `Command`/`CommandBus` architecture could be judged on evidence rather than
assumption:

| Path | Measured | spec.md/design.md budget |
|---|---|---|
| `GestureEngine.process()` (one frame, one hand, worst-case branch coverage) | **~2.65µs/call** (5,000-iteration average) | design.md #25: "gesture event generation: < 1 frame of additional latency" (~16–33ms at 30–60fps) — ~0.01–0.02% of that budget |
| `CommandBus.dispatch()` overhead alone (pyautogui mocked, so only the architecture's own cost is measured) | **~11.8µs/call** (5,000-iteration average) | design.md #25: "local command dispatch: < 20ms target" — ~0.06% of that budget |
| Packaged `.exe`, idle with camera running, no hand in frame | ~260MB RAM, clean log, no crash across 7+ separate manual boot checks (one per phase since PHASE 6) | spec.md #1: "≤ 7% CPU on quad-core" — not independently profiled per-core, but sustained real-time operation across every check is consistent with it |

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
