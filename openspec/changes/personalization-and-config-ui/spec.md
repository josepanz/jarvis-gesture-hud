# JARVIS Gesture HUD — Personalization & Config UI — Technical Specification

## 1. Scope

This specification defines the required behavior for the four phases in
`proposal.md`. Every requirement SHALL be treated as normative unless marked
optional/future. Section numbers are stable — code SHOULD reference them as
`spec.md #N`, matching this project's existing convention.

---

# PHASE A — Reference icons per gesture

## 2.1 Icon generation

Each legend entry SHALL have an associated icon, generated procedurally (no
hand-authored binary image assets committed to the repository) and cached on
disk under `jarvis.paths.assets_dir() / "gesture_icons/"`, one PNG per
gesture key, same lazy-download-and-cache pattern as the MediaPipe model in
`hand_tracker.py`.

Icons SHALL be small: 48×48px or smaller, so the panel stays lightweight
("livianas" per the original request).

## 2.2 Icon content

Each icon SHALL visually distinguish itself from every other icon in the set
(no two gestures may render identical icons). A simple stylized hand
glyph (palm outline + marked extended/curled fingers) plus a small action
glyph (e.g. an arrow for scroll, a magnifier for zoom) SHALL satisfy this —
photorealistic rendering is explicitly not required.

## 2.3 Legend integration

The legend panel SHALL show, for every entry, its icon next to its existing
gesture-name/action text, without removing or reformatting the existing text.

Existing legend behavior SHALL be unaffected:

```text
Toggle visibility ('h' / TOGGLE_LEGEND gesture)
Adjust opacity ('+'/'-' / LEGEND_ALPHA_UP/DOWN gesture)
Corner anchoring
Click-through on Windows
```

## 2.4 Deferred: animated reference

Per-gesture animated (GIF) demonstrations are explicitly deferred, not
implemented in this phase. If pursued later, it SHALL be scoped as its own
follow-up change, not silently expanded into this one (`apply.md` §12, no
speculative scope growth).

---

# PHASE B — Naruto hand-seal gestures

## 3.1 Seal roster

The system SHALL recognize at least 5 named, single-hand, static seal poses.
Each seal:

- SHALL be detectable from a single frame's 21 hand landmarks (same
  detection style as existing `gestures.py` pose checks — no temporal
  sequence/multi-frame chaining required for detection itself, though the
  existing confirmation-frame/cooldown pattern used by other gestures MAY
  still apply to avoid single-frame flicker).
- SHALL NOT collide with any existing gesture's detection condition (see
  `design.md` §3.2 for the required collision-avoidance process).
- SHALL be independently assignable to an action (§3.3).

## 3.2 Assignability

Each seal SHALL have a default action binding, AND SHALL be overridable via
the existing `Profile.gesture_bindings` mechanism
(`jarvis.core.profiles.Profile`, `ProfileManager.get_gesture_binding()`),
exactly like any other gesture-to-action override already specified for that
mechanism. No new binding mechanism SHALL be introduced for this phase — see
`design.md` §4 for why this reuse is correct and sufficient here (Phase C
later adds a UI on top of the same mechanism).

## 3.3 Action vocabulary

A seal's bound action SHALL come from the same fixed vocabulary already used
elsewhere in the app: the 11 `Command`-backed gesture actions
(`jarvis.main._MIGRATED_GESTURES`) plus `MUTE`/`UNDO`/`REDO` plus
`KEYBOARD_TOGGLE`/`CLOSE_APP` — i.e. exactly
`jarvis.main._dispatch_voice_action`'s existing input domain. Dispatching a
resolved seal SHALL reuse that same method (or an equivalent one with
identical behavior) rather than duplicating the action-execution logic a
third time (voice already reuses it once).

## 3.4 Safety

A seal bound (by default or by profile override) to a
`HOLD_REQUIRED`/`DESTRUCTIVE`-safety command (per `commands.py`
`CommandMetadata.safety`) SHALL NOT bypass that command's existing safety
gating. No new gesture may silently grant a lower-friction path to a
sensitive action than gestures already have today.

---

# PHASE C — Settings screen

## 4.1 Entry point

A small always-on-top icon (gear) SHALL be shown on screen (native Tkinter
window, same construction family as the existing legend/bubble windows in
`overlay.py`), NOT click-through (it must be clickable, unlike the legend).
Clicking it SHALL open the settings screen.

## 4.2 Bindings table

The settings screen SHALL list every bindable trigger known to the app:

```text
Existing camera gestures (jarvis.legend.ENTRIES' gesture column)
Naruto seals (Phase B)
Voice phrases (jarvis.core.voice_intent_resolver.DEFAULT_PHRASE_BINDINGS
  plus any registered via VoiceIntentResolver.register)
```

For each row, the screen SHALL show: icon (Phase A, where one exists),
trigger name, current bound action, and a tooltip (§4.5) describing what the
trigger does today.

## 4.3 Rebinding

The user SHALL be able to change a row's bound action to any value in the
fixed action vocabulary (spec.md #3.3), OR to one of:

- a custom keyboard shortcut (§4.4);
- a previously-defined macro (§4.4).

A rebind SHALL take effect for the remainder of the session immediately and
SHALL be persisted (§4.6) so it survives a restart.

## 4.4 Custom shortcuts and macros

### 4.4.1 Custom shortcut

The screen SHALL provide a way to capture a keyboard combination (e.g.
`ctrl+alt+t`) by listening for key events while a dedicated input has
keyboard focus. The captured combination SHALL be stored as a normalized
string (lowercase, `+`-joined, deterministic modifier order — e.g.
`ctrl+alt+shift+t`) and executed via a new `HotkeyCommand` wrapping
`pyautogui.hotkey(*parts)`.

### 4.4.2 Macro

The screen SHALL provide a way to compose an ordered list of steps, each
step being one of:

```text
press-key   (reuses PressKeyCommand)
type-text   (reuses TypeTextCommand)
wait-ms     (a pause between steps, new, no OS side effect)
```

A saved macro SHALL be exposed as a named action addable to the fixed
vocabulary (namespaced, e.g. `MACRO:<name>`) and executed via a new
`MacroCommand` that runs its steps in order through the same `CommandBus`
each step would otherwise go through individually. A macro's declared safety
level (`commands.py` `CommandMetadata.safety`) SHALL be at least as strict as
the strictest step it contains — a macro MUST NOT be able to launder a
`DESTRUCTIVE`/`HOLD_REQUIRED` step into a `SAFE`-looking macro.

### 4.4.3 Physical macro keys (M1/M2/M3…)

The app SHALL NOT claim to natively recognize a physical "M1" or similar
vendor macro key as a distinct signal — see `design.md` §6.3. The settings
screen's help text/tooltip for shortcut capture SHALL state this limitation
explicitly and SHALL describe the workaround (remap the physical key, in the
keyboard's own vendor software, to an unused standard key combination; bind
that combination here).

## 4.5 Tooltips

Every interactive element in the settings screen (rows, buttons, inputs)
SHALL have a tooltip shown on hover, explaining what it does in plain
language. No element SHALL rely on an icon or label alone to convey a
destructive or non-obvious action.

## 4.6 Persistence

Bindings (including custom shortcuts and macros) SHALL be persisted to a
per-user JSON file outside the repository/install directory (a user-config
directory, NOT `jarvis.paths.assets_dir()` — that path is for
downloaded/generated read-mostly assets, not user-edited state). Persistence
SHALL:

- load automatically on next app start, restoring the previous session's
  bindings;
- fail gracefully on a missing or corrupt file (fall back to defaults, log
  the problem, never crash app startup);
- never silently overwrite the file with an empty/default state as a result
  of a load failure (a corrupt file SHOULD be preserved/renamed aside, not
  clobbered, so the user's customization isn't destroyed by a bug).

## 4.7 Non-blocking

Opening and using the settings screen SHALL NOT freeze or measurably stall
the camera loop / `overlay.pump()` cadence, consistent with `design.md` §19
of the prior change ("HUD code MUST NOT become the source of truth for
business logic" / must stay non-blocking).

---

# PHASE D — Voice model download icon

## 5.1 Location

The download control SHALL live inside the settings screen (Phase C) as a
row/button — not as a fourth always-on-top corner icon — unless a future
request explicitly asks for a standalone icon (see `proposal.md`'s
non-goals: no scope growth beyond what's asked).

## 5.2 Disclosure

Its tooltip SHALL state, before any download starts:

- the approximate download size (`~1GB`, matching the actual
  `Qwen2.5-1.5B-Instruct` Q4_K_M GGUF referenced by
  `jarvis.llm_intent.MODEL_URL`);
- what the download is for (local voice-command understanding, offline, no
  cloud calls);
- that it additionally requires `requirements-voice.txt` to be installed
  separately (this control does not install Python packages).

## 5.3 Behavior

Clicking it SHALL:

1. Check (via `importlib.util.find_spec`, not a real import) whether
   `faster_whisper`, `llama_cpp`, and `sounddevice` are importable. If not,
   show guidance to run `pip install -r requirements-voice.txt` and take no
   further action.
2. If present, run `jarvis.llm_intent._ensure_model_path()` (or an
   equivalent using the same URL/cache path) on a background thread, so the
   settings screen and camera loop remain responsive.
3. Report progress (a percentage or a simple "downloading…" state is
   sufficient — exact UI is an implementation decision, not a normative
   requirement) and a final ready/error state.

## 5.4 Idempotency

If the model file already exists at the cached path, clicking SHALL report
"already downloaded" / ready state without re-downloading.
