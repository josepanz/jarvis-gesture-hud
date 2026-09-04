"""Overlays nativos de escritorio (Tkinter, stdlib — sin dependencias nuevas):

- Globos translucidos transitorios en la posicion del cursor real, en cualquier
  parte de la pantalla (no solo dentro de la ventana de camara).
- Un panel fijo con el listado de gestos, anclado a una esquina de la pantalla,
  translucido, no-clickeable (click-through nativo en Windows) y con
  transparencia ajustable en caliente.

`pump()` se llama una vez por frame desde el loop principal para procesar el
event-loop de Tk sin bloquear — Tk no es thread-safe, asi que no corre en un
hilo aparte compitiendo con la camara.
"""

import platform
import tkinter as tk

BUBBLE_LIFETIME_MS = 1300
BUBBLE_BG = "#12121a"
BUBBLE_FG = "#f5f5f5"
BUBBLE_ALPHA = 0.82

LEGEND_BG = "#101018"
LEGEND_FG = "#e8e8f0"
LEGEND_MIN_ALPHA = 0.15
LEGEND_MAX_ALPHA = 1.0
LEGEND_MARGIN = 16

# TASK-078 (Fase 8, design.md §5.7): icono de engranaje - abajo a la derecha,
# la esquina que la leyenda (arriba a la derecha por default) no usa.
GEAR_BG = "#101018"
GEAR_FG = "#e8e8f0"
GEAR_MARGIN = 16


def _make_click_through(window):
    """Hace la ventana no-clickeable: los clicks pasan al escritorio de abajo.

    Nativo solo en Windows (WinAPI layered window via ctypes, ya en stdlib).
    En macOS/Linux queda como no-op — la ventana sigue siendo clickeable ahi.
    """
    if platform.system() != "Windows":
        return
    try:
        import ctypes

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    except Exception:
        pass


class ScreenOverlay:
    def __init__(self):
        self._root = tk.Tk()
        self._root.withdraw()

        self._legend_window = None
        self._legend_icons = []
        self._legend_alpha = 0.75
        self._legend_visible = True

        self._gear_window = None

    def pump(self):
        """Procesa el event-loop de Tk (crea/destruye globos vencidos). Llamar cada frame."""
        try:
            self._root.update_idletasks()
            self._root.update()
        except tk.TclError:
            pass

    # --- Globos transitorios --------------------------------------------------

    def show_bubble(self, text, screen_x, screen_y):
        try:
            bubble = tk.Toplevel(self._root)
            bubble.overrideredirect(True)
            bubble.attributes("-topmost", True)
            try:
                bubble.attributes("-alpha", BUBBLE_ALPHA)
            except tk.TclError:
                pass  # el gestor de ventanas no soporta transparencia; se ve opaco igual

            tk.Label(
                bubble, text=text, bg=BUBBLE_BG, fg=BUBBLE_FG,
                font=("Segoe UI", 13, "bold"), padx=18, pady=10,
            ).pack()

            bubble.update_idletasks()
            _make_click_through(bubble)
            bw, bh = bubble.winfo_width(), bubble.winfo_height()
            x = int(screen_x - bw / 2)
            y = int(screen_y - bh - 30)
            bubble.geometry(f"+{max(x, 0)}+{max(y, 0)}")
            bubble.after(BUBBLE_LIFETIME_MS, bubble.destroy)
        except tk.TclError:
            pass

    # --- Panel fijo de gestos ---------------------------------------------------

    def init_legend(self, entries, corner="top-right", title=None):
        """TASK-060 (Fase 3, design.md §3): `entries` es una lista de
        (gesture, action, icon_path) - ver `jarvis.legend.build_legend_entries()`.
        Icono via `tk.PhotoImage(file=...)` (soporte PNG nativo desde Tk 8.6,
        sin PIL.ImageTk - spec.md #3.1's Must NOT)."""
        self._legend_window = tk.Toplevel(self._root)
        self._legend_window.overrideredirect(True)
        self._legend_window.attributes("-topmost", True)

        container = tk.Frame(self._legend_window, bg=LEGEND_BG)
        container.pack(padx=14, pady=10)

        row = 0
        if title:
            tk.Label(
                container, text=title, bg=LEGEND_BG, fg=LEGEND_FG,
                font=("Consolas", 10, "bold"), anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
            row += 1

        # Tk no retiene una referencia propia a PhotoImage - si no la guardamos
        # aca, el garbage collector de Python las destruye y los iconos
        # desaparecen del panel poco despues de crearlo.
        self._legend_icons = []
        for gesture, action, icon_path in entries:
            photo = tk.PhotoImage(file=str(icon_path))
            self._legend_icons.append(photo)
            tk.Label(container, image=photo, bg=LEGEND_BG).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
            tk.Label(
                container, text=f"{gesture}  →  {action}", bg=LEGEND_BG, fg=LEGEND_FG,
                font=("Consolas", 10), anchor="w", justify="left",
            ).grid(row=row, column=1, sticky="w", pady=2)
            row += 1

        self._legend_window.update_idletasks()
        _make_click_through(self._legend_window)
        self._position_legend(corner)
        self._apply_legend_alpha()

    def _position_legend(self, corner):
        win = self._legend_window
        w, h = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x = sw - w - LEGEND_MARGIN if "right" in corner else LEGEND_MARGIN
        y = LEGEND_MARGIN if "top" in corner else sh - h - LEGEND_MARGIN
        win.geometry(f"+{x}+{y}")

    def _apply_legend_alpha(self):
        if not self._legend_window:
            return
        try:
            self._legend_window.attributes("-alpha", self._legend_alpha)
        except tk.TclError:
            pass

    def set_legend_visible(self, visible):
        self._legend_visible = visible
        if not self._legend_window:
            return
        if visible:
            self._legend_window.deiconify()
        else:
            self._legend_window.withdraw()

    def toggle_legend_visible(self):
        self.set_legend_visible(not self._legend_visible)
        return self._legend_visible

    def adjust_legend_alpha(self, delta):
        self._legend_alpha = min(LEGEND_MAX_ALPHA, max(LEGEND_MIN_ALPHA, self._legend_alpha + delta))
        self._apply_legend_alpha()
        return self._legend_alpha

    # --- TASK-078: icono de engranaje (abre el settings screen) ----------------

    def init_gear_icon(self, on_click):
        """A diferencia de TODO lo demas en este modulo, esta ventana NO es
        click-through (spec.md #8.1: hay que poder clickearla) - por eso NO
        se llama `_make_click_through()` aca."""
        self._gear_window = tk.Toplevel(self._root)
        self._gear_window.overrideredirect(True)
        self._gear_window.attributes("-topmost", True)

        label = tk.Label(
            self._gear_window, text="⚙", bg=GEAR_BG, fg=GEAR_FG,
            font=("Segoe UI", 16), width=2, height=1, cursor="hand2",
        )
        label.pack()
        label.bind("<Button-1>", lambda _event: on_click())

        self._gear_window.update_idletasks()
        w, h = self._gear_window.winfo_width(), self._gear_window.winfo_height()
        sw, sh = self._gear_window.winfo_screenwidth(), self._gear_window.winfo_screenheight()
        self._gear_window.geometry(f"+{sw - w - GEAR_MARGIN}+{sh - h - GEAR_MARGIN}")
        self._gear_window.update_idletasks()

    def close(self):
        try:
            self._root.destroy()
        except tk.TclError:
            pass
