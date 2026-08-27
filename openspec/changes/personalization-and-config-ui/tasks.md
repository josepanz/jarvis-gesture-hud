# JARVIS Gesture HUD — Personalization & Config UI — Implementation Tasks

## Global execution rule

Same as `multimodal-interaction-core/tasks.md`: tasks MUST be executed
sequentially unless a task explicitly allows parallelism. The agent MUST NOT
implement future tasks automatically. Implement only the requested task and
its explicitly required dependencies. After each task: run relevant tests,
run the full regression suite, verify acceptance criteria, report changed
files, do NOT start the next task automatically. Full protocol:
`multimodal-interaction-core/apply.md` (reused verbatim, not duplicated
here).

Task numbering continues from the prior change's last task, TASK-054.

---

# PHASE A — Reference icons (lowest complexity — do this first)

## TASK-055 — Icon generation module

### Objective

Create `src/jarvis/gesture_icons.py`: declarative `ICON_SPECS`, `ensure_icon(key) -> Path`, `generate_all_icons()`, per `design.md` §2.1–2.2.

### Requirements

- Pillow added to `requirements.txt`.
- Icons generated at ≤48×48px, cached under `jarvis.paths.assets_dir() / "gesture_icons/"`.
- `ensure_icon()` MUST NOT regenerate an icon that already exists on disk.
- Cover every existing `jarvis.legend.ENTRIES` gesture (icon key per entry — see TASK-056).

### Must NOT

- Add `PIL.ImageTk` as a display dependency (display is Tk-native — design.md §2.3).
- Commit hand-authored binary image files to the repo.

### Acceptance criteria

- Unit tests (no display needed): `ensure_icon()` produces a valid PNG of the expected size; a second call does not rewrite the file (mtime unchanged, or a call-count spy on the draw path shows it wasn't invoked twice); every `ICON_SPECS` key is visually distinguishable from every other by construction (e.g. assert no two specs are structurally identical).

---

## TASK-056 — Legend entries gain an icon key

### Objective

Extend `jarvis.legend.ENTRIES` with a third element (icon key) per entry; add `build_legend_entries()` returning the full tuples. Keep `build_legend_text()` working unchanged.

### Requirements

Per `design.md` §2.1. Every entry gets an icon key that exists in `gesture_icons.ICON_SPECS` (TASK-055).

### Must NOT

- Remove or reformat `build_legend_text()` — anything still calling it must keep working.

### Acceptance criteria

- Test: every `ENTRIES` icon key resolves via `gesture_icons.ensure_icon()` without raising.
- Test: `build_legend_text()` output is byte-identical to before this task (regression).

---

## TASK-057 — Legend panel renders icon + text rows

### Objective

`overlay.ScreenOverlay.init_legend(entries, corner)` renders one icon+text row per entry (design.md §2.4), replacing the single pre-formatted `Label`. `main.py` calls `build_legend_entries()` instead of `build_legend_text()`.

### Requirements

- Existing legend behavior unchanged: toggle visibility, opacity adjustment, corner anchoring, click-through on Windows (manual verification, per design.md §2.5 — this file has no automated Tk tests today and this task does not need to add real-window automation, only preserve behavior).

### Must NOT

- Start a second `Tk()` root.
- Change the legend's toggle/opacity keyboard bindings.

### Acceptance criteria

- Manual smoke test on Windows: legend shows icons, `h` still toggles it, `+`/`-` still change opacity, panel still click-through.
- Full existing test suite still green (nothing in `tests/` constructs `ScreenOverlay` today, so this is a compile/import-safety check plus the manual smoke test).

---

# PHASE B — Naruto hand-seal gestures (moderate complexity)

## TASK-058 — Collision-avoidance census and roster finalization

### Objective

Execute `design.md` §3.2's required process: enumerate every existing gesture check in `gestures.py`, propose final landmark thresholds for the 5-seal roster (`design.md` §3.1), adjust/rename/drop any seal that collides.

### Must produce

A short written note (in the task report, per `apply.md` §27) listing the final roster with one line of geometric definition each, and confirmation no collision was found (or what was changed to resolve one).

### Must NOT

- Modify any existing gesture's detection logic.

### Acceptance criteria

- The written roster note exists in the task report.
- No code changes in this task beyond the note (this is an analysis task feeding TASK-059).

---

## TASK-059 — Seal detectors and engine wiring

### Objective

Implement `is_naruto_<name>(landmarks) -> bool` for the roster finalized in TASK-058, wired into `GestureEngine.process()`, emitting `NARUTO_<NAME>` events.

### Requirements

Per `design.md` §3.3, `spec.md` #3.1.

### Must NOT

- Change any existing gesture's event name or trigger condition.

### Acceptance criteria

- One positive synthetic-landmark test per seal.
- One negative test per seal against every existing gesture fixture (no false positive) and vice versa — `design.md` §3.2's process, made permanent as tests.
- Full existing `GestureEngine` regression suite still green.

---

## TASK-060 — Seal-to-action dispatch and icons

### Objective

Wire `NARUTO_<NAME>` events to actions via `Profile.gesture_bindings`, reusing `_dispatch_voice_action` (`design.md` §3.3, `spec.md` #3.2–3.4). Add an icon per seal (extends TASK-055's `ICON_SPECS`, reuse — not a new icon system).

### Requirements

- `NARUTO_SEAL_DEFAULT_BINDINGS` dict with a sensible default per seal, documented in the task report.
- A seal bound to a `HOLD_REQUIRED`/`DESTRUCTIVE` command must not bypass that command's existing gating (`spec.md` #3.4) — verify by test (e.g. bind a seal to `LOCK_SESSION` and confirm the existing hold/confirmation behavior still applies, not an instant unguarded execution).

### Must NOT

- Duplicate the action-execution logic that already exists for voice.

### Acceptance criteria

- Test: default binding dispatches the right `Command`.
- Test: a `Profile` override changes the dispatched action.
- Test: an unbound seal (no default, no override) is a safe no-op.
- Live-integration check (extend `tests/manual_live_integration_check.py`) exercising one seal end-to-end, same pattern as the existing voice-dispatch checks.

---

# PHASE C — Settings screen (highest complexity — do this after A and B)

## TASK-061 — Persistence layer

### Objective

`src/jarvis/core/config_store.py`: `load_bindings()`/`save_bindings()`, JSON schema per `design.md` §5.2, atomic write, corrupt-file-preserved-not-clobbered handling (`spec.md` #4.6).

### Must NOT

- Touch `jarvis.paths.assets_dir()` — this is user-edited state, not a downloaded/generated asset (`spec.md` #4.6).
- Ever raise out of `load_bindings()` for a missing/corrupt file.

### Acceptance criteria

- Tests: round-trip save→load; missing file → `{}`/defaults, no exception; corrupt JSON → old file preserved under a `.bak-*` name, defaults returned, no exception; concurrent-crash-safety is satisfied by construction (temp file + `os.replace`), not required to be tested by inducing an actual crash.

---

## TASK-062 — ProfileManager (de)serialization

### Objective

Bridge `config_store`'s schema to `Profile`/`ProfileManager` construction — `to_dict()`/`from_dict()` (or equivalent adapter functions), per `design.md` §5.2.

### Must NOT

- Introduce a second in-memory representation of a profile alongside the existing `Profile` dataclass (`apply.md` §14).

### Acceptance criteria

- Round-trip test: construct a `Profile` with bindings, `to_dict()`, `from_dict()`, assert equality.
- Existing `test_profiles.py` suite still green, unchanged behavior for anything not touching (de)serialization.

---

## TASK-063 — HotkeyCommand and MacroCommand

### Objective

`src/jarvis/actions/macro.py`: `HotkeyCommand(combo)`, `MacroCommand(steps)`, per `design.md` §5.3, `spec.md` #4.4.1–4.4.2.

### Requirements

- Both are real `Command` subclasses, flow through `CommandBus` unchanged.
- `MacroCommand`'s `metadata.safety` is at least as strict as its strictest step (`spec.md` #4.4.2) — implement and test this explicitly, it's a safety requirement, not a nice-to-have.

### Must NOT

- Add a new dependency for hotkey execution (`pyautogui.hotkey()` already covers it — `design.md` §5.3).

### Acceptance criteria

- Test: `HotkeyCommand("ctrl+alt+t").execute()` calls `pyautogui.hotkey("ctrl", "alt", "t")` (mocked).
- Test: `MacroCommand` runs steps in order, including a `wait-ms` step producing a measurable (mocked `time.sleep`) delay.
- Test: a macro containing a `HOLD_REQUIRED` step reports `HOLD_REQUIRED` (or stricter) as its own safety, never `SAFE`.
- Test: `CommandBus.dispatch(MacroCommand(...))` records one `CommandHistory` entry (not one per step) — confirm this is the intended granularity before asserting it (implementer's call, documented in the report if it differs).

---

## TASK-064 — Tooltip helper

### Objective

`Tooltip` class in `src/jarvis/settings_ui.py`, per `design.md` §5.5.

### Acceptance criteria

- Manual verification only (real Tk widget) — no automated test required for this task; note this explicitly in the report rather than skipping silently.

---

## TASK-065 — Gear icon window

### Objective

A small, always-on-top, clickable (NOT click-through) gear icon window, per `design.md` §5.7, opening the settings screen on click.

### Must NOT

- Overlap the existing legend panel's default corner.
- Apply `_make_click_through()` to this window (it must remain clickable, unlike the legend/bubbles).

### Acceptance criteria

- Manual smoke test: icon visible, clickable, opens settings window, doesn't block the camera loop.

---

## TASK-066 — Settings screen: bindings table

### Objective

`SettingsWindow` lists every bindable trigger (gestures, seals, voice phrases) with icon, name, current action, tooltip — per `spec.md` #4.2.

### Requirements

Source the trigger list from `jarvis.legend.ENTRIES`, the Phase B seal roster, and `VoiceIntentResolver`'s registered phrases — do not hand-maintain a fourth duplicate list.

### Acceptance criteria

- Manual smoke test: table shows all triggers with correct current bindings on open.

---

## TASK-067 — Settings screen: rebind, custom shortcut capture, macro builder

### Objective

Implement rebinding a row to any fixed-vocabulary action, custom-shortcut capture (`design.md` §5.4), and the macro step builder (`spec.md` #4.4.2), all inside `SettingsWindow`.

### Requirements

- Shortcut capture only while the dedicated input has focus (no global hook, no new dependency — `spec.md` non-goals).
- The M1/M2/M3 limitation and workaround (`spec.md` #4.4.3, `design.md` §6.3) is shown as help text/tooltip near the shortcut-capture control.

### Must NOT

- Add `pynput`/`keyboard` or any global-hotkey dependency.

### Acceptance criteria

- Manual smoke test: rebind a row, capture a shortcut, build a 2-step macro, all visibly reflected in the UI before saving.

---

## TASK-068 — Wire persistence into the live app

### Objective

Settings changes call `config_store.save_bindings()`; app startup calls `config_store.load_bindings()` and applies it to `ProfileManager` before the camera loop starts; gesture/seal/voice dispatch all resolve through the now-possibly-overridden bindings.

### Requirements

Per `spec.md` #4.3, #4.6.

### Acceptance criteria

- Integration test (extend `tests/manual_live_integration_check.py`): rebind an action via the settings API (not necessarily clicking real UI — calling the underlying save/apply functions is sufficient), restart `JarvisApp` construction, confirm the new binding is active.
- Full regression suite still green.
- Real app boot still succeeds (existing discipline for every phase in this project).

---

# PHASE D — Voice model download icon (do this last — depends on Phase C)

## TASK-069 — Voice model download row

### Objective

Add the row/button described in `spec.md` §5, `design.md` §7 to `SettingsWindow`.

### Requirements

- Tooltip discloses size, purpose, and the separate `requirements-voice.txt` install step, before any download starts (`spec.md` #5.2).
- Dependency check via `importlib.util.find_spec`, never a real import just to check (`spec.md` #5.3 step 1).
- Download runs on a background thread; UI updates are scheduled back onto the Tk thread (`design.md` §7.2) — never touch a Tk widget from the download thread directly.
- Idempotent: already-downloaded state is detected and shown without re-downloading (`spec.md` #5.4).

### Must NOT

- Attempt `pip install` at runtime.
- Block the settings window or camera loop during download.

### Acceptance criteria

- Test: dependency-missing path shows guidance, does not start a download (mocked `find_spec`).
- Test: dependency-present path starts a background download calling the existing model-path-ensuring function (mocked network call — no real 1GB download in CI).
- Test: already-downloaded path reports ready state without invoking the download.
- Manual smoke test (optional, requires `requirements-voice.txt` installed): a real download completes and the state updates to ready.
