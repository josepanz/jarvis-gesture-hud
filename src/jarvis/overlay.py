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
        self._legend_alpha = 0.75
        self._legend_visible = True

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

    def init_legend(self, text, corner="top-right"):
        self._legend_window = tk.Toplevel(self._root)
        self._legend_window.overrideredirect(True)
        self._legend_window.attributes("-topmost", True)

        tk.Label(
            self._legend_window, text=text, justify="left", anchor="w",
            bg=LEGEND_BG, fg=LEGEND_FG, font=("Consolas", 10), padx=14, pady=10,
        ).pack()

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

    def close(self):
        try:
            self._root.destroy()
        except tk.TclError:
            pass
