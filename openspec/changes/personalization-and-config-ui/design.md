# JARVIS Gesture HUD — Personalization & Config UI — Design

## 1. Design objective

Deliver the four phases in `proposal.md` with the smallest real architectural
footprint: reuse `Profile.gesture_bindings`, `CommandBus`, `Command`, and the
existing lazy-model-download pattern (`hand_tracker.py`, `llm_intent.py`)
rather than inventing parallel mechanisms. Only Phase C introduces genuinely
new architecture (persistence), because nothing else needed it before.

---

# 2. PHASE A — Reference icons

## 2.1 New module: `src/jarvis/gesture_icons.py`

```python
ICON_SPECS = {
    "pointer": [...],       # declarative draw ops, see 2.2
    "click_drag": [...],
    ...
}

def ensure_icon(key: str) -> Path:
    """Generates (if missing) and returns the cached PNG path for `key`."""

def generate_all_icons() -> None:
    """Convenience: ensure_icon() for every key in ICON_SPECS. Called once at
    app startup (cheap - each icon is generated at most once, ever, then
    cached under assets/gesture_icons/)."""
```

`ICON_SPECS` keys SHOULD match `jarvis.legend.ENTRIES`' existing gesture
strings closely enough to look up 1:1 — recommend adding a third element
(icon key) to each `ENTRIES` tuple rather than trying to derive one from the
free-text gesture description:

```python
ENTRIES = [
    ("Índice movido", "Puntero", "pointer"),
    ("Pulgar + Índice (pinch)", "Click / Drag", "click_drag"),
    ...
]
```

This is a backward-compatible extension (adds a field, doesn't remove one) —
`build_legend_text()` keeps working unchanged for anything still consuming
it; add a new `build_legend_entries()` that returns the full tuples
(icon-aware callers use this one, per `spec.md` #2.3).

## 2.2 Drawing approach

Use `PIL.Image` (`"L"` or `"RGBA"` mode, small canvas e.g. 48×48) +
`PIL.ImageDraw` primitives (`line`, `ellipse`, `polygon`) to draw a stylized
hand: a rounded palm shape, 5 finger stubs, each independently
extended/curled per the icon's spec, plus a small overlay glyph for the
resulting action (e.g. a circular arrow for scroll/zoom, a speaker for
volume). This is the same level of visual fidelity as a simple pictogram —
enough to be recognizable at a glance, not a realistic hand.

`ICON_SPECS[key]` SHOULD be a small declarative structure (e.g. a bitmask of
which fingers are extended + an optional glyph name) rather than raw
per-pixel draw calls duplicated per icon, so adding an icon for Phase B's
seals is a short entry, not a new function.

## 2.3 Display (no `PIL.ImageTk` needed)

`tkinter.PhotoImage(file=str(png_path))` reads PNG/GIF natively since Tk 8.6
(bundled with the Python versions this project already requires — no new
runtime dependency for DISPLAY). Only GENERATING the PNG needs Pillow. This
avoids `ImageTk`, which has occasionally fragile Tk-linking behavior across
platforms/PyInstaller builds — worth avoiding when a simpler native path
exists.

## 2.4 `overlay.py` change

`init_legend(text, corner)` SHALL become `init_legend(entries, corner)`
where `entries` is a list of `(icon_path_or_None, gesture_text, action_text)`
— the panel becomes a vertical stack of small `Frame(icon Label + text
Label)` rows instead of one big `Label` with a pre-formatted string. Keep
the same `Toplevel`/`overrideredirect`/`click-through`/alpha logic
unchanged; only the interior layout changes.

`main.py`'s `self.overlay.init_legend(build_legend_text())` becomes
`self.overlay.init_legend(build_legend_entries())`.

## 2.5 Testing

`overlay.py` has never had automated tests (real Tkinter windows, previously
only manually smoke-tested — see `ARCHITECTURE.md` Known limitations). Keep
that boundary: put all TESTABLE logic in `gesture_icons.py` (pure
generation, no Tk) and `legend.py`'s `build_legend_entries()` (pure data),
both fully unit-testable without a display. `overlay.py`'s row-layout change
stays manually verified, consistent with how the rest of that file is
validated today.

## 2.6 Deferred: GIFs

Tk can technically cycle GIF frames natively (`PhotoImage(format="gif -index
N")` + `.after()`), so an animated version wouldn't need a new dependency
either — but "a GIF generated from the gesture's text" isn't a well-defined
transformation, and authoring real per-gesture animations is a much bigger
asset-creation effort than a static pictogram. Ship static icons first; if
the user wants animated ones after seeing static icons in place, that's a
small, well-scoped follow-up (swap `ensure_icon` for
`ensure_icon_frames()` returning N frames instead of 1).

---

# 3. PHASE B — Naruto hand seals

## 3.1 Roster (starting proposal — MUST be validated per §3.2 before final commit)

Real Naruto jutsu seals are mostly two-handed (fingers interlaced), and
several are visually close to each other. Recreating all 12 authentically
would mean two-hand fine-grained finger-interlacing detection — high
false-positive risk, and direct collision risk with the two existing
two-hand master gestures (fist-pause, Shaka-close). This phase deliberately
scopes to single-hand, static, INSPIRED-BY poses instead — document this
plainly (proposal.md already does) so nobody expects the full authentic set.

Starting candidates (5), each a `NARUTO_<NAME>` gesture type:

```text
NARUTO_TORA  (Tiger) — index + middle fingers extended together (touching),
             ring + pinky curled, thumb crossed over the palm.
NARUTO_UMA   (Horse) — all 5 fingers extended and spread evenly (distinct
             from the existing SILENCE pose, which requires the thumb tucked
             toward the pinky specifically).
NARUTO_INU   (Dog)   — ring + pinky extended together, index + middle
             curled, thumb resting on the curled fingers.
NARUTO_I     (Boar)  — closed fist with the thumb extended outward to the
             side (not tucked in, not up).
NARUTO_SARU  (Monkey)— thumb + pinky extended, index/middle/ring curled
             (visually close to Shaka, which today is TWO-HAND-only for
             CLOSE_APP — verify no single-hand Shaka-shaped check exists
             elsewhere before finalizing this one; if it does, rename/drop).
```

## 3.2 Required collision-avoidance process (normative — spec.md #3.1)

Before finalizing thresholds, the implementing agent MUST:

1. Enumerate every existing single-hand and two-hand pose check in
   `gestures.py` (pinch variants, palm/silence, fist, Shaka) — same census
   `ARCHITECTURE.md`'s "Gesture map" table already documents.
2. For each new `NARUTO_*` check, write a synthetic-landmark test proving it
   does NOT also satisfy any existing gesture's condition, and vice versa
   (existing gesture fixtures must not accidentally satisfy a new seal's
   condition either) — same discipline already used for the
   `GestureEngine` regression suite (`tests/test_gesture_engine_regression.py`,
   see `ARCHITECTURE.md` Decisions for the exact bug class this guards
   against: a "far away" finger isn't the same as a genuinely curled one).
3. If a collision is found, adjust the geometric threshold or drop/rename
   that seal from the roster rather than special-casing detection order
   (order-dependent detection is a known source of flakiness this project
   has avoided elsewhere).

## 3.3 Wiring

New module `src/jarvis/naruto_seals.py` (or a new section in `gestures.py`,
implementer's choice) exposing one function per seal,
`is_naruto_<name>(landmarks) -> bool`, called from `GestureEngine.process()`
alongside existing single-hand checks, emitting a `NARUTO_<NAME>` event
string exactly like existing gesture types.

`main.py` gains:

```python
NARUTO_SEAL_DEFAULT_BINDINGS = {
    "NARUTO_TORA": "SCREENSHOT",
    "NARUTO_UMA":  "VOLUME_UP",
    ...  # implementer's reasonable default choices, documented in the task report
}

def _dispatch_naruto_seal(self, seal_name):
    action = self.profiles.get_gesture_binding(seal_name, NARUTO_SEAL_DEFAULT_BINDINGS)
    if action:
        self._dispatch_voice_action(action)  # exact reuse — see spec.md #3.3
```

This is the THIRD caller of the fixed-action-vocabulary dispatch path
(gesture-migrated actions call it directly today via `_dispatch_migrated`;
voice via `_dispatch_voice_action`; this adds seals) — confirms the
vocabulary/dispatch design introduced for voice already generalizes, no new
abstraction needed.

## 3.4 Icons

Each `NARUTO_*` seal gets an entry in Phase A's `ICON_SPECS` too (reuse, not
a parallel icon system) — the settings screen (Phase C) lists seals exactly
like any other bindable trigger, icon included.

---

# 4. Why Phase B doesn't need Phase C

`Profile.gesture_bindings` is a plain `dict[str, str]` already validated by
`Profile.__post_init__`. "Assignable to options" (the user's own wording) is
satisfied by constructing a `Profile` with a `gesture_bindings` override —
today that requires editing Python (constructing a `Profile(...)` — there is
no persistence or UI yet). That's a real, if code-level, form of
assignability, consistent with how every other profile override already
works pre-Phase-C. Phase C's settings screen later becomes a GUI on top of
the exact same mechanism — it does not replace it.

---

# 5. PHASE C — Settings screen

## 5.1 New modules

```text
src/jarvis/settings_ui.py     — SettingsWindow (Tkinter Toplevel), Tooltip helper
src/jarvis/core/config_store.py — load_bindings()/save_bindings(), JSON on disk
src/jarvis/actions/macro.py   — MacroCommand, HotkeyCommand
```

## 5.2 `config_store.py`

```python
CONFIG_DIR = Path.home() / ".jarvis-gesture-hud"
CONFIG_FILE = CONFIG_DIR / "bindings.json"

def load_bindings() -> dict:
    """Returns {} (defaults apply) on missing/corrupt file. On corrupt file,
    renames it aside (bindings.json.bak-<timestamp>) instead of overwriting -
    spec.md #4.6's "never silently clobber" requirement. Never raises."""

def save_bindings(data: dict) -> None:
    """Writes atomically (write to a temp file in the same dir, then
    os.replace()) so a crash mid-write can't corrupt the previous good
    file."""
```

Schema (versioned from day one, so a future format change doesn't need a
second migration mechanism per `apply.md` §14):

```json
{
  "schema_version": 1,
  "profiles": {
    "default": {
      "gesture_bindings": {"NARUTO_TORA": "SCREENSHOT"},
      "custom_shortcuts": {"MY_SHORTCUT": "ctrl+alt+t"},
      "macros": {
        "MACRO:greeting": [
          {"kind": "type-text", "value": "hola"},
          {"kind": "wait-ms", "value": 300},
          {"kind": "press-key", "value": "enter"}
        ]
      }
    }
  }
}
```

`ProfileManager` gains `to_dict()`/`from_dict()` (or a small adapter
function outside the class, implementer's choice) bridging this schema to
existing `Profile` construction — do not invent a second, competing
in-memory representation (`apply.md` §14).

## 5.3 `MacroCommand` / `HotkeyCommand`

```python
class HotkeyCommand(Command):
    def __init__(self, combo: str):  # "ctrl+alt+t"
        self._parts = combo.split("+")
    def execute(self):
        try:
            pyautogui.hotkey(*self._parts)
            return CommandResult.ok()
        except Exception as exc:
            return CommandResult.failed(error=str(exc))

class MacroCommand(Command):
    def __init__(self, steps: list[Command | WaitStep]):
        self._steps = steps
    @property
    def metadata(self):
        # safety = the strictest safety level among self._steps - spec.md #4.4.2
        ...
    def execute(self):
        for step in self._steps:
            ...  # run each step; a WaitStep just time.sleep()s
        return CommandResult.ok()
```

Both are ordinary `Command`s — they flow through the existing `CommandBus`,
get recorded in `CommandHistory`, and get feedback via `FeedbackManager`
exactly like every other action already does. No new execution layer.

`pyautogui.hotkey()` already supports arbitrary key combinations — confirmed
no new dependency is needed for EXECUTING a custom shortcut or a macro's key
steps.

## 5.4 Capturing a shortcut (no new dependency)

Bind `<KeyPress>` on a dedicated, focused `Entry`/label inside the settings
window. Canonicalize `event.state`/`event.keysym` into `ctrl`/`alt`/
`shift`/the base key, in a fixed modifier order, join with `+`. This only
needs to work while that widget has focus — global (unfocused-window) hotkey
capture is explicitly out of scope (`proposal.md` non-goals), so no
`pynput`/`keyboard` dependency is needed here either.

## 5.5 Tooltip helper

```python
class Tooltip:
    def __init__(self, widget, text):
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
    def _show(self, event):
        self._tip = tk.Toplevel(...)  # overrideredirect, small Label, positioned near cursor
    def _hide(self, event):
        self._tip.destroy()
```

Standard, well-known ~25-line Tkinter pattern. No new dependency.

## 5.6 Non-blocking

`SettingsWindow` is a `Toplevel` on the SAME `Tk` root `overlay.py` already
owns and pumps every frame (`ScreenOverlay._root`) — it does not start a
second `Tk()`/mainloop (Tkinter does not support multiple `Tk()` instances
reliably in one process). `ScreenOverlay` gains a way to construct/reveal it
(e.g. `ScreenOverlay.open_settings(on_save)` or the settings module takes
`overlay._root` directly) — implementer's choice, but MUST NOT introduce a
second Tk root.

## 5.7 Gear icon

A small always-on-top, NOT-click-through `Toplevel` (reuse
`ScreenOverlay`'s window-creation pattern minus the `_make_click_through`
call), positioned in a screen corner not already used by the legend, with a
simple `⚙` character/glyph as its content (no new asset needed — Tk can
render the Unicode gear glyph directly in a `Label`, same as this project
already renders emoji in bubble text like `"🔒 Bloqueando sesión"`).

---

# 6. Dependency and feasibility notes

## 6.1 Pillow (Phase A only)

`Pillow` is added to `requirements.txt` (not `requirements-voice.txt` — it's
needed for the base app's legend, not an optional heavy feature). It is a
common, pure-C-extension-with-prebuilt-wheels package with wheels for every
platform/Python version this project targets — low risk to add.

## 6.2 Phase C's "no new dependency" claim

Re-verify at implementation time: `tkinter.ttk` (Combobox/Treeview) ships
with the Python stdlib on Windows/macOS/most Linux distributions with the
official python.org installer; on some minimal Linux distros `python3-tk`
is a separate OS package — this is an EXISTING constraint (the whole app
already depends on `tkinter` for `overlay.py`), not a new one introduced by
this phase.

## 6.3 M1/M2/M3 macro keys — feasibility

Gaming keyboards' dedicated macro keys are typically one of:

```text
(a) Remapped by vendor software (Razer Synapse, Logitech G HUB, Corsair
    iCUE, ...) to send an ordinary keycode/combo chosen in that software -
    reaches this app like any other keypress. WORKS with this feature.
(b) Consumed entirely by the vendor software/driver and never surfaces as a
    standard OS keystroke at all. DOES NOT reach Python. NOT fixable from
    this app without vendor-specific SDK integration (out of scope - would
    be a new, brand-specific dependency per keyboard vendor, explicitly the
    kind of speculative dependency `apply.md` §12 rules out).
```

This app can only ever see case (a). The settings screen's help text SHALL
say so plainly (spec.md #4.4.3) rather than implying blanket "M1/M2/M3
support" that would fail silently for case (b) users.

---

# 7. PHASE D — Voice model download icon

## 7.1 Placement

A new row inside `SettingsWindow` (Phase C), not a fifth always-on-top
corner window — keeps screen clutter down, and matches
`proposal.md`'s "smallest footprint that satisfies the request" framing.

## 7.2 Implementation

```python
def _check_voice_deps_available() -> bool:
    import importlib.util
    return all(
        importlib.util.find_spec(mod) is not None
        for mod in ("faster_whisper", "llama_cpp", "sounddevice")
    )

def _start_voice_model_download(on_progress, on_done):
    def _run():
        try:
            path = jarvis.llm_intent._ensure_model_path()  # or a progress-aware variant
            on_done(success=True, path=path)
        except Exception as exc:
            on_done(success=False, error=str(exc))
    threading.Thread(target=_run, daemon=True).start()
```

`urllib.request.urlretrieve(url, path, reporthook=...)` already supports a
progress callback `(block_num, block_size, total_size)` — wire it to update
a label/progress bar via `overlay._root.after(0, ...)` (Tkinter calls must
happen on the main/Tk thread, not the download thread — schedule the UI
update instead of touching widgets directly from the background thread).

## 7.3 Idempotency

`_ensure_model_path()` already no-ops (returns the existing path without
re-downloading) if the file exists — Phase D's UI just needs to check this
before showing a "download" vs. "already downloaded" state, per spec.md #5.4.
