"""TASK-077/078/079/080 (Fase 8, `openspec/changes/personalization-and-config-ui`,
design.md §5.4/5.5/5.7, spec.md #8.1-8.5): pantalla de configuracion.

`SettingsWindow` es un `Toplevel` sobre el MISMO root de Tk que `overlay.py`
ya posee y bombea cada frame (design.md §5.6: "MUST NOT introduce a second
Tk root") - no bloquea el loop de camara porque nunca corre su propio
`mainloop()`, solo vive dentro del `pump()` ya existente.
"""

import tkinter as tk
from tkinter import ttk

from jarvis.gesture_icons import ensure_icon
from jarvis.llm_intent import VALID_ACTIONS

BG = "#101018"
FG = "#e8e8f0"
ACCENT_BG = "#1c1c28"

# TASK-081/079: los gestos "clasicos" (Fases 1-3, mas SCROLL_LEFT/RIGHT
# agregados junto con el rediseño de scroll) no tienen una relacion 1:1 con
# un icon_key de `gesture_icons.ICON_SPECS` (varios eventos comparten a
# veces un solo icono, ej. PINCH_DOWN/PINCH_UP -> "pinch_click") - este es el
# UNICO puente hand-maintained que hizo falta (no una copia de texto: el
# nombre/tooltip real de cada fila sigue viniendo de `jarvis.legend.ENTRIES`,
# ver `_build_trigger_rows()`). Los sellos/gestos comunes de las Fases 4-7 no
# lo necesitan - su icon_key es siempre `event.lower()`.
_CLASSIC_EVENT_ICON_KEYS = {
    "PINCH_DOWN": "pinch_click",
    "PINCH_UP": "pinch_click",
    "RIGHT_CLICK": "pinch_right_click",
    "SCROLL_UP": "scroll",
    "SCROLL_DOWN": "scroll",
    "SCROLL_LEFT": "scroll",
    "SCROLL_RIGHT": "scroll",
    "ZOOM_IN": "pinch_zoom",
    "ZOOM_OUT": "pinch_zoom",
    "VOLUME_UP": "pinch_volume",
    "VOLUME_DOWN": "pinch_volume",
    "SCREENSHOT": "pinch_screenshot",
    "LOCK_SESSION": "shaka_lock",
    "SILENCE": "silence",
    "KEYBOARD_TOGGLE": "open_palm_keyboard",
    "TOGGLE_ACTIVE": "two_fist_pause",
    "CLOSE_APP": "two_shaka_close",
    "TOGGLE_MIRROR": "key_mirror",
    "TOGGLE_LEGEND": "key_toggle_legend",
    "LEGEND_ALPHA_UP": "key_legend_opacity",
    "LEGEND_ALPHA_DOWN": "key_legend_opacity",
}

M1_M2_M3_HELP_TEXT = (
    "Teclas macro del teclado (M1/M2/M3...): esta app NO puede reconocerlas "
    "como una señal distinta - depende del software del fabricante del "
    "teclado. Si ese software las reenvia como una combinacion de teclas "
    "estandar (ej. Ctrl+Alt+1), remapealas ahi y despues asigná esa "
    "combinacion aca como un atajo custom. Si el teclado las consume antes "
    "de llegar al sistema operativo, esta app nunca las va a ver."
)


class Tooltip:
    """~25 lineas, patron estandar de Tkinter (design.md §5.5) - sin
    dependencia nueva."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None):
        if self._tip is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = tk.Toplevel(self.widget)
        self._tip.overrideredirect(True)
        self._tip.attributes("-topmost", True)
        self._tip.geometry(f"+{x}+{y}")
        tk.Label(
            self._tip, text=self.text, bg="#2a2a3a", fg=FG, font=("Segoe UI", 9),
            padx=8, pady=4, justify="left", wraplength=320,
        ).pack()

    def _hide(self, _event=None):
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


def canonicalize_shortcut(state, keysym):
    """TASK-080 (design.md §5.4): normaliza `event.state`/`event.keysym` de
    un `<KeyPress>` en un string `ctrl+alt+t`-style, orden fijo de
    modificadores. Funcion pura (recibe los 2 campos, no el Event de Tk
    entero) para poder testearla sin un event loop real."""
    parts = []
    if state & 0x0004:
        parts.append("ctrl")
    if state & 0x20000 or state & 0x0008:  # 0x20000: Alt en Windows; 0x0008: Mod1/Alt en X11
        parts.append("alt")
    if state & 0x0001:
        parts.append("shift")
    base = (keysym or "").lower()
    if base not in ("control_l", "control_r", "alt_l", "alt_r", "shift_l", "shift_r"):
        parts.append(base)
    return "+".join(parts)


def _event_icon_key(event_name):
    return _CLASSIC_EVENT_ICON_KEYS.get(event_name, event_name.lower())


def _build_trigger_rows(default_bindings):
    """Una fila por cada trigger de `GESTURE_DEFAULT_BINDINGS` (spec.md
    #8.2: "every bindable trigger known to the app") - el nombre/tooltip
    real viene de `jarvis.legend.ENTRIES`, cruzado por icon_key (ninguna
    copia de texto nueva); si un evento no tiene fila de leyenda (no debería
    pasar, todo evento real tiene una), cae a mostrar el nombre crudo."""
    from jarvis.legend import ENTRIES as LEGEND_ENTRIES

    text_by_icon_key = {icon_key: gesture for gesture, _action, icon_key in LEGEND_ENTRIES}
    rows = []
    for event_name in default_bindings:
        icon_key = _event_icon_key(event_name)
        label = text_by_icon_key.get(icon_key, event_name)
        rows.append((event_name, label, icon_key))
    return sorted(rows, key=lambda row: row[0])


class SettingsWindow:
    def __init__(self, root, profiles, default_bindings, voice_intent_resolver=None, on_change=None):
        self._root = root
        self._profiles = profiles
        self._default_bindings = default_bindings
        self._voice_intent_resolver = voice_intent_resolver
        self._on_change = on_change or (lambda: None)
        self._window = None
        self._icon_refs = []  # Tk no retiene PhotoImage propias - ver overlay.py
        self._row_vars = {}

    def open(self):
        if self._window is not None and self._window.winfo_exists():
            self._window.deiconify()
            self._window.lift()
            return
        self._build()

    def _build(self):
        self._window = tk.Toplevel(self._root)
        self._window.title("Configuración — Jarvis")
        self._window.configure(bg=BG)
        self._window.geometry("760x560")

        self._build_shortcut_macro_bar()
        self._build_bindings_table()
        self._build_voice_phrases_section()
        self._build_m1_m2_m3_help()

    # --- TASK-080: crear atajos/macros reusables --------------------------------

    def _build_shortcut_macro_bar(self):
        bar = tk.Frame(self._window, bg=BG)
        bar.pack(fill="x", padx=10, pady=(10, 4))

        new_shortcut_btn = tk.Button(bar, text="+ Atajo custom", command=self._open_shortcut_capture_dialog)
        new_shortcut_btn.pack(side="left", padx=(0, 6))
        Tooltip(new_shortcut_btn, "Crea un atajo de teclado nuevo (ej. Ctrl+Alt+T) para asignar a cualquier fila.")

        new_macro_btn = tk.Button(bar, text="+ Macro", command=self._open_macro_builder_dialog)
        new_macro_btn.pack(side="left")
        Tooltip(new_macro_btn, "Crea una secuencia de teclas/texto/espera para asignar a cualquier fila.")

    def _open_shortcut_capture_dialog(self):
        dialog = tk.Toplevel(self._window)
        dialog.title("Nuevo atajo")
        dialog.configure(bg=BG)

        combo_var = tk.StringVar(value="(presioná una combinación)")
        tk.Label(dialog, textvariable=combo_var, bg=BG, fg=FG, font=("Consolas", 12), padx=12, pady=8).pack()
        name_entry = tk.Entry(dialog)
        name_entry.insert(0, "MI_ATAJO")
        name_entry.pack(padx=12, pady=(0, 8))

        captured = {"combo": None}

        def _on_key(event):
            combo = canonicalize_shortcut(event.state, event.keysym)
            captured["combo"] = combo
            combo_var.set(combo)

        dialog.bind("<KeyPress>", _on_key)
        dialog.focus_set()

        def _save():
            if captured["combo"]:
                name = name_entry.get().strip() or "MI_ATAJO"
                self._profiles.active.custom_shortcuts[name] = captured["combo"]
                self._on_change()
                self._refresh_bindings_table()
            dialog.destroy()

        tk.Button(dialog, text="Guardar", command=_save).pack(pady=(0, 10))

    def _open_macro_builder_dialog(self):
        dialog = tk.Toplevel(self._window)
        dialog.title("Nueva macro")
        dialog.configure(bg=BG)

        name_entry = tk.Entry(dialog)
        name_entry.insert(0, "saludo")
        name_entry.pack(padx=12, pady=(10, 4))

        steps_listbox = tk.Listbox(dialog, width=40)
        steps_listbox.pack(padx=12, pady=4)
        steps = []

        def _add_step(kind, prompt_default):
            value_entry_win = tk.Toplevel(dialog)
            value_entry_win.title(kind)
            entry = tk.Entry(value_entry_win)
            entry.insert(0, prompt_default)
            entry.pack(padx=10, pady=10)

            def _confirm():
                raw = entry.get()
                value = int(raw) if kind == "wait-ms" else raw
                steps.append({"kind": kind, "value": value})
                steps_listbox.insert("end", f"{kind}: {value}")
                value_entry_win.destroy()

            tk.Button(value_entry_win, text="Agregar", command=_confirm).pack(pady=(0, 10))

        btn_bar = tk.Frame(dialog, bg=BG)
        btn_bar.pack(pady=4)
        tk.Button(btn_bar, text="+ Tecla", command=lambda: _add_step("press-key", "enter")).pack(side="left", padx=2)
        tk.Button(btn_bar, text="+ Texto", command=lambda: _add_step("type-text", "hola")).pack(side="left", padx=2)
        tk.Button(btn_bar, text="+ Espera (ms)", command=lambda: _add_step("wait-ms", "300")).pack(side="left", padx=2)

        def _save():
            if steps:
                name = f"MACRO:{name_entry.get().strip() or 'sin_nombre'}"
                self._profiles.active.macros[name] = steps
                self._on_change()
                self._refresh_bindings_table()
            dialog.destroy()

        tk.Button(dialog, text="Guardar macro", command=_save).pack(pady=(4, 10))

    # --- TASK-079: tabla de bindings ---------------------------------------------

    def _rebind_target_options(self):
        return sorted(VALID_ACTIONS) + sorted(self._profiles.active.custom_shortcuts) + sorted(
            self._profiles.active.macros
        )

    def _build_bindings_table(self):
        container = tk.Frame(self._window, bg=BG)
        container.pack(fill="both", expand=True, padx=10, pady=4)

        canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self._table_frame = tk.Frame(canvas, bg=BG)
        self._table_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._table_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._refresh_bindings_table()

    def _refresh_bindings_table(self):
        for child in self._table_frame.winfo_children():
            child.destroy()
        self._icon_refs.clear()
        self._row_vars.clear()

        options = self._rebind_target_options()
        for row_index, (event_name, label, icon_key) in enumerate(_build_trigger_rows(self._default_bindings)):
            photo = tk.PhotoImage(file=str(ensure_icon(icon_key)))
            self._icon_refs.append(photo)
            tk.Label(self._table_frame, image=photo, bg=BG).grid(row=row_index, column=0, padx=(2, 6), pady=2)

            name_label = tk.Label(
                self._table_frame, text=label, bg=BG, fg=FG, font=("Consolas", 10), anchor="w", width=40
            )
            name_label.grid(row=row_index, column=1, sticky="w")
            Tooltip(name_label, f"Evento: {event_name}")

            current = self._profiles.get_gesture_binding(event_name, global_bindings=self._default_bindings)
            var = tk.StringVar(value=current)
            self._row_vars[event_name] = var
            combo = ttk.Combobox(self._table_frame, textvariable=var, values=options, width=22, state="readonly")
            combo.grid(row=row_index, column=2, padx=(6, 2), pady=2)
            combo.bind("<<ComboboxSelected>>", lambda _e, ev=event_name, v=var: self._on_rebind(ev, v.get()))

    def _on_rebind(self, event_name, new_action):
        self._profiles.active.gesture_bindings[event_name] = new_action
        self._on_change()

    # --- TASK-079: frases de voz registradas (solo informativo) ------------------

    def _build_voice_phrases_section(self):
        if self._voice_intent_resolver is None:
            return
        phrases = self._voice_intent_resolver.phrase_bindings
        if not phrases:
            return
        frame = tk.Frame(self._window, bg=ACCENT_BG)
        frame.pack(fill="x", padx=10, pady=(4, 4))
        tk.Label(
            frame, text="Frases de voz registradas (solo informativo):", bg=ACCENT_BG, fg=FG,
            font=("Consolas", 9, "bold"), anchor="w",
        ).pack(fill="x", padx=6, pady=(4, 0))
        for phrase, action in sorted(phrases.items()):
            tk.Label(
                frame, text=f'"{phrase}" → {action}', bg=ACCENT_BG, fg=FG, font=("Consolas", 9), anchor="w"
            ).pack(fill="x", padx=12)

    # --- TASK-080: ayuda M1/M2/M3 -------------------------------------------------

    def _build_m1_m2_m3_help(self):
        tk.Label(
            self._window, text=M1_M2_M3_HELP_TEXT, bg=BG, fg="#a0a0b0", font=("Segoe UI", 8),
            wraplength=610, justify="left", anchor="w",
        ).pack(fill="x", padx=10, pady=(4, 10))
