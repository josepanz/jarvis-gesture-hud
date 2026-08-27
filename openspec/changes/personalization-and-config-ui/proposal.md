# JARVIS Gesture HUD — Personalization & Config UI

## 1. Summary

This change adds four user-requested capabilities to the existing, shipped application:

```text
A. Lightweight reference icons per gesture (legend + future config screen)
B. Naruto-style hand-seal gestures, assignable to actions
C. A settings screen (gear icon) with tooltips to bind gestures/keys/macros
   to actions, including custom shortcuts and M1/M2/M3-style macro keys
D. A "download voice model" icon inside the settings screen
```

This is an ADDITIVE change. It follows the same incremental philosophy as
`openspec/changes/multimodal-interaction-core/`: the existing application is
the baseline, nothing existing SHALL be silently removed or renamed, and every
phase SHALL leave the application runnable.

This proposal reuses `multimodal-interaction-core/apply.md` as its execution
protocol — the rules there (one task at a time, stop after each task, test
before/after, no speculative dependencies, report format) apply verbatim to
this change too. It is not duplicated here.

---

## 2. Ordering rationale (menor a mayor)

The user explicitly asked for phases ordered from lowest to highest
complexity/effort/token-cost/dependencies. That evaluation, done against the
CURRENT codebase (not in the abstract):

| Phase | What | Complexity | New deps | Why this position |
|---|---|---|---|---|
| **A** | Reference icons per gesture | Low | +Pillow (icon generation only) | Purely additive display feature. `legend.py`'s `ENTRIES` list already separates gesture/action data from rendering — this only adds a third field and one new rendering path. No interaction with the gesture/command pipeline at all. |
| **B** | Naruto hand-seal gestures | Moderate | None | New pure-Python landmark geometry (same style as existing `_is_shaka`/pinch detectors in `gestures.py`) plus tests. Its "assignable to actions" requirement is satisfied by wiring the already-built-but-dormant `Profile.gesture_bindings` (PHASE 5 of the prior change) into live dispatch — reuse, not new architecture. |
| **C** | Settings screen (gear icon, tooltips, bindings, custom shortcuts, macros) | High | None (if scoped as specified below) | The only phase that needs genuinely new architecture: a persistence layer (today `ProfileManager` is in-memory only — nothing in this project has ever been saved to disk), a real settings UI, and a `MacroCommand`. Reused carefully, no new dependency is actually required — see §7 of `design.md`. This is the largest phase by file count, test count, and design decisions that need to be gotten right. |
| **D** | "Download voice model" icon | Low (but gated) | None | Small in isolation — one icon/row, one background download, reusing `jarvis.llm_intent._ensure_model_path()` almost as-is. It is ordered LAST not because it is hard, but because the user's own request makes it conditional on C ("si se decide poner pantalla de menú principal o solo icono, agregar un icono también...") — it needs a place to live. |

Recommended execution order: **A → B → C → D**. Each phase SHOULD be
implemented, tested, and reported on independently (per `apply.md` §26 — stop
after each task, do not auto-continue), because the phases are only loosely
coupled (D depends on C; B depends on nothing new from A; A depends on
nothing).

---

## 3. Goals

The system SHALL, across the four phases:

1. Show a small reference icon next to every gesture entry in the existing
   legend panel, without breaking its current toggle/opacity/click-through
   behavior.
2. Recognize at least 5 additional, single-hand, static gesture poses
   inspired by Naruto hand seals, each independently assignable to any
   action already in the app's fixed action vocabulary.
3. Provide a settings screen, reachable from a gear icon, where a user can:
   - see every bindable trigger (gesture, Naruto seal, voice phrase) with an
     icon, name, and tooltip;
   - reassign it to a different action from the existing vocabulary;
   - define a custom keyboard shortcut as an action;
   - define a multi-step macro as an action;
   - persist these choices across restarts.
4. Provide a way, from that same settings screen, to download the optional
   voice model on demand, with size and purpose disclosed in a tooltip
   before the user commits to the download.

## 4. Non-goals (all four phases)

The following SHALL NOT be part of this change:

- Recognizing the full, authentic 12-seal Naruto sequence system (multi-seal
  chains, two-hand seals). Scoped to single-hand static poses — see
  `design.md` §3 for the explicit reasoning.
- Defining brand-new CAMERA gesture shapes through the settings UI (a
  gesture-recording/training pipeline). The settings UI lets a user REBIND
  existing triggers (gestures, seals, voice phrases) to actions — it does not
  let them invent a new hand pose from the UI.
- Native support for vendor-specific keyboard macro keys (M1/M2/M3) as a
  distinct OS-level signal. See `design.md` §6.3 for why, and the documented
  workaround (rebind the physical key in the keyboard's own vendor software
  to send an unused key combo, then bind that combo here).
- Actually running `pip install` at runtime to fetch the voice dependencies.
  Phase D only downloads the model file; missing Python packages are
  reported to the user with an instruction, never auto-installed.
- Global (OS-wide, unfocused-window) hotkey capture. Custom shortcuts are
  captured only while the settings window has keyboard focus.
- Animated GIF generation from gesture names. Explicitly deferred — see
  `design.md` §2.4.

---

## 5. Compatibility requirement

Same as the prior change (`multimodal-interaction-core/proposal.md` §11):

```text
Old functionality
+
New capability
=
Same existing behavior
+
New capability
```

No phase is complete if an existing supported capability (legend
toggle/opacity, existing gesture set, existing keyboard shortcuts, voice
control, undo/redo, profiles, telemetry) is silently broken.
