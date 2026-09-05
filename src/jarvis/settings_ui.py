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

# H-10: el gate de HOLD_REQUIRED (hoy solo LOCK_SESSION) es posicional, no
# estructural (ver ARCHITECTURE.md, "Decisions & rationale") - vive en que
# GestureEngine nunca emite estos eventos antes de sostener su propio hold
# (config.NARUTO_SEAL_HOLD_SECONDS / NARUTO_TWOHAND_HOLD_SECONDS /
# LOCK_HOLD_SECONDS / KOREAN_HEART_HOLD_SECONDS - ver gestures.py). Ofrecer
# LOCK_SESSION como destino de un evento SIN hold propio (ej. PINCH_DOWN,
# instantaneo) rompe esa garantia: el pinch casual bloquearia la sesion sin
# ningun hold. Se filtra aca, en la UI, en vez de resolver esto de forma
# estructural en CommandBus (que requeriria que GestureEvent cargue
# evidencia real de duracion desde GestureEngine hasta el dispatcher - fuera
# de alcance de este fix, ver H-10 en el WORKPLAN de hardening-and-polish).
# Publicos (sin "_") porque A-03 (mismo WORKPLAN, §9) los reusa desde main.py
# para el mismo gate sobre context_rules - una regla por app tampoco puede
# habilitar HOLD_REQUIRED sobre un evento sin hold propio.
HOLD_REQUIRED_ACTIONS = frozenset({"LOCK_SESSION"})
HOLD_CAPABLE_EVENTS = frozenset(
    {
        # sellos Naruto de 1 mano + JJK_MEGUMI: NARUTO_SEAL_HOLD_SECONDS
        "NARUTO_TORA", "NARUTO_USHI", "NARUTO_U", "NARUTO_UMA", "NARUTO_HITSUJI",
        "NARUTO_SARU", "NARUTO_INU", "NARUTO_I", "JJK_MEGUMI",
        # sellos de 2 manos: NARUTO_TWOHAND_HOLD_SECONDS
        "NARUTO_NE", "NARUTO_MI", "NARUTO_TORI", "NARUTO_KAI", "NARUTO_TATSU", "JJK_GOJO_DOMAIN",
        # holds propios
        "KOREAN_HEART", "LOCK_SESSION",
    }
)

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
        self._build_context_rules_section()
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

    def _rebind_target_options(self, event_name):
        """H-10: las acciones HOLD_REQUIRED (LOCK_SESSION) solo se ofrecen en
        filas cuyo gesto de origen ya sostiene su propio hold - ver
        `HOLD_CAPABLE_EVENTS` arriba."""
        actions = VALID_ACTIONS if event_name in HOLD_CAPABLE_EVENTS else VALID_ACTIONS - HOLD_REQUIRED_ACTIONS
        return sorted(actions) + sorted(self._profiles.active.custom_shortcuts) + sorted(
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

        for row_index, (event_name, label, icon_key) in enumerate(_build_trigger_rows(self._default_bindings)):
            icon_path = ensure_icon(icon_key)
            # H-14: ensure_icon() devuelve None si no pudo generar/cachear el
            # icono (fallo de escritura) - la fila se muestra sin icono en vez
            # de crashear la ventana de settings.
            if icon_path is not None:
                photo = tk.PhotoImage(file=str(icon_path))
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
            options = self._rebind_target_options(event_name)
            combo = ttk.Combobox(self._table_frame, textvariable=var, values=options, width=22, state="readonly")
            combo.grid(row=row_index, column=2, padx=(6, 2), pady=2)
            combo.bind("<<ComboboxSelected>>", lambda _e, ev=event_name, v=var: self._on_rebind(ev, v.get()))

    def _on_rebind(self, event_name, new_action):
        self._profiles.active.gesture_bindings[event_name] = new_action
        self._on_change()

    # --- A-03b (WORKPLAN.md §9, `hardening-and-polish`): reglas por app en foco --

    def _build_context_rules_section(self):
        """Editor de `Profile.context_rules` ({app: {evento: accion}}),
        consumido por `main.py._dispatch_bound_event()` desde A-03. Vacio por
        default en todos los perfiles - esta seccion es la unica forma de
        poblarlo, ademas de tocar el perfil por codigo/test."""
        frame = tk.Frame(self._window, bg=ACCENT_BG)
        frame.pack(fill="x", padx=10, pady=(4, 4))

        header = tk.Frame(frame, bg=ACCENT_BG)
        header.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(
            header,
            text="Reglas por aplicación en foco:",
            bg=ACCENT_BG,
            fg=FG,
            font=("Consolas", 9, "bold"),
            anchor="w",
        ).pack(side="left")
        add_btn = tk.Button(header, text="+ Regla", command=self._open_context_rule_dialog)
        add_btn.pack(side="right")
        Tooltip(
            add_btn,
            "Hace que un gesto dispare una acción distinta cuando cierta app está en primer "
            "plano. El nombre de la app se compara literal contra el título de su ventana - "
            "sin reglas, el comportamiento es idéntico al de las filas de arriba.",
        )

        self._context_rules_frame = tk.Frame(frame, bg=ACCENT_BG)
        self._context_rules_frame.pack(fill="x", padx=6, pady=(2, 6))
        self._refresh_context_rules_list()

    def _refresh_context_rules_list(self):
        for child in self._context_rules_frame.winfo_children():
            child.destroy()
        rules = self._profiles.active.context_rules
        if not rules:
            tk.Label(
                self._context_rules_frame,
                text="(ninguna todavía)",
                bg=ACCENT_BG,
                fg="#a0a0b0",
                font=("Consolas", 9),
                anchor="w",
            ).pack(fill="x")
            return
        for app_name in sorted(rules):
            for event_name, action_name in sorted(rules[app_name].items()):
                row = tk.Frame(self._context_rules_frame, bg=ACCENT_BG)
                row.pack(fill="x")
                tk.Label(
                    row,
                    text=f"{app_name}: {event_name} → {action_name}",
                    bg=ACCENT_BG,
                    fg=FG,
                    font=("Consolas", 9),
                    anchor="w",
                ).pack(side="left", fill="x", expand=True)
                tk.Button(
                    row, text="×", command=lambda a=app_name, e=event_name: self._remove_context_rule(a, e)
                ).pack(side="right")

    def _open_context_rule_dialog(self):
        dialog = tk.Toplevel(self._window)
        dialog.title("Nueva regla por app")
        dialog.configure(bg=BG)

        tk.Label(dialog, text="Aplicación (título de ventana, literal):", bg=BG, fg=FG).pack(padx=12, pady=(10, 2))
        app_entry = tk.Entry(dialog, width=40)
        app_entry.pack(padx=12, pady=(0, 8))

        tk.Label(dialog, text="Gesto:", bg=BG, fg=FG).pack(padx=12)
        event_var = tk.StringVar(value=sorted(self._default_bindings)[0])
        event_combo = ttk.Combobox(
            dialog, textvariable=event_var, values=sorted(self._default_bindings), state="readonly", width=30
        )
        event_combo.pack(padx=12, pady=(0, 8))

        tk.Label(dialog, text="Acción:", bg=BG, fg=FG).pack(padx=12)
        action_var = tk.StringVar()
        action_combo = ttk.Combobox(dialog, textvariable=action_var, state="readonly", width=30)
        action_combo.pack(padx=12, pady=(0, 8))

        def _refresh_action_options(*_args):
            # H-10 (mismo gate que `_rebind_target_options` ya aplica a la
            # tabla de arriba): un gesto sin hold propio no ofrece las
            # acciones HOLD_REQUIRED como destino, tampoco aca.
            options = self._rebind_target_options(event_var.get())
            action_combo.configure(values=options)
            if options:
                action_var.set(options[0])

        event_combo.bind("<<ComboboxSelected>>", _refresh_action_options)
        _refresh_action_options()

        def _save():
            app_name = app_entry.get().strip()
            event_name = event_var.get()
            action_name = action_var.get()
            if app_name and event_name and action_name:
                self._profiles.active.context_rules.setdefault(app_name, {})[event_name] = action_name
                self._on_change()
                self._refresh_context_rules_list()
            dialog.destroy()

        tk.Button(dialog, text="Guardar regla", command=_save).pack(pady=(4, 10))

    def _remove_context_rule(self, app_name, event_name):
        rules = self._profiles.active.context_rules
        app_rules = rules.get(app_name)
        if app_rules is not None:
            app_rules.pop(event_name, None)
            if not app_rules:
                rules.pop(app_name, None)
        self._on_change()
        self._refresh_context_rules_list()

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
