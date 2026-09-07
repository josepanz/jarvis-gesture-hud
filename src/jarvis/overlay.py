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
# H-28 (`openspec/changes/hardening-and-polish/WORKPLAN.md` §2), confirmado en
# camara real (José, 2026-09-07): con las 44 entradas reales de
# `legend.build_legend_entries()`, el panel sin paginar ocupa toda la mitad
# de pantalla del lado donde esta anclado. 12 filas por pagina es un numero
# razonado (deja el panel a una altura comoda en un monitor 1080p tipico con
# la fuente actual), no medido en camara todavia.
LEGEND_PAGE_SIZE = 12
LEGEND_CONTROLS_BG = "#1c1c28"
LEGEND_CONTROLS_FG = "#e8e8f0"

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

        # H-28: estado de paginado/colapsado del panel (ver init_legend()).
        self._legend_container = None
        self._legend_entries = []
        self._legend_title = None
        self._legend_corner = "top-right"
        self._legend_page = 0
        self._legend_collapsed = False
        self._legend_controls_window = None
        self._legend_page_label = None
        self._legend_collapse_label = None

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
        sin PIL.ImageTk - spec.md #3.1's Must NOT). `icon_path` puede ser
        `None` (H-14: `ensure_icon()` no pudo generar/cachear el icono) - esa
        entrada de leyenda se muestra sin icono en vez de crashear el panel.

        H-28: `entries` completo se guarda y se pagina (LEGEND_PAGE_SIZE por
        pagina) en vez de renderizarse entero de una - con las 44 entradas
        reales, sin paginar el panel ocupa toda la mitad de pantalla del lado
        anclado (hallazgo de camara real, José, 2026-09-07). Los controles de
        pagina/colapso viven en una ventanita SEPARADA y no click-through
        (mismo patron que init_gear_icon) - el panel en si sigue siendo
        click-through de punta a punta, asi que no puede tener sus propios
        widgets clickeables."""
        self._legend_entries = list(entries)
        self._legend_title = title
        self._legend_corner = corner
        self._legend_page = 0
        self._legend_collapsed = False

        self._legend_window = tk.Toplevel(self._root)
        self._legend_window.overrideredirect(True)
        self._legend_window.attributes("-topmost", True)
        self._legend_container = tk.Frame(self._legend_window, bg=LEGEND_BG)
        self._legend_container.pack(padx=14, pady=10)

        self._init_legend_controls()
        self._render_legend()
        self._apply_legend_alpha()

    @property
    def _legend_total_pages(self):
        if not self._legend_entries:
            return 1
        return (len(self._legend_entries) + LEGEND_PAGE_SIZE - 1) // LEGEND_PAGE_SIZE

    def _render_legend(self):
        """Reconstruye el contenido del panel para la pagina/estado de colapso
        actual, y reposiciona ambas ventanas (el panel y sus controles)."""
        if self._legend_container is None:
            return
        for child in self._legend_container.winfo_children():
            child.destroy()
        self._legend_icons = []

        row = 0
        if self._legend_title:
            tk.Label(
                self._legend_container, text=self._legend_title, bg=LEGEND_BG, fg=LEGEND_FG,
                font=("Consolas", 10, "bold"), anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
            row += 1

        if not self._legend_collapsed:
            start = self._legend_page * LEGEND_PAGE_SIZE
            page_entries = self._legend_entries[start : start + LEGEND_PAGE_SIZE]
            # Tk no retiene una referencia propia a PhotoImage - si no la
            # guardamos aca, el garbage collector de Python las destruye y los
            # iconos desaparecen del panel poco despues de crearlo.
            for gesture, action, icon_path in page_entries:
                if icon_path is not None:
                    photo = tk.PhotoImage(file=str(icon_path))
                    self._legend_icons.append(photo)
                    tk.Label(self._legend_container, image=photo, bg=LEGEND_BG).grid(
                        row=row, column=0, sticky="w", padx=(0, 8), pady=2
                    )
                tk.Label(
                    self._legend_container, text=f"{gesture}  →  {action}", bg=LEGEND_BG, fg=LEGEND_FG,
                    font=("Consolas", 10), anchor="w", justify="left",
                ).grid(row=row, column=1, sticky="w", pady=2)
                row += 1

        self._legend_window.update_idletasks()
        _make_click_through(self._legend_window)
        # Los controles se posicionan PRIMERO - _position_legend() necesita
        # conocer su altura real para dejarles franja sin superponerse.
        self._update_legend_controls()
        self._position_legend(self._legend_corner)

    def _position_legend(self, corner):
        # H-28, confirmado en camara real (José, 2026-09-07): superponer los
        # controles al panel no sirve - 2 ventanas "-topmost" no tienen un
        # orden entre si garantizado (`lift()` no alcanzo, los controles
        # quedaban debajo del panel y eran inclickeables). En vez de eso, se
        # reserva una franja SIN superposicion para los controles (mismo
        # lado del panel) y el panel se corre para dejarle lugar - z-order
        # deja de importar porque nunca se tocan.
        win = self._legend_window
        w, h = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        controls_h = 0
        if self._legend_controls_window is not None:
            self._legend_controls_window.update_idletasks()
            controls_h = self._legend_controls_window.winfo_height() + 4
        x = sw - w - LEGEND_MARGIN if "right" in corner else LEGEND_MARGIN
        y = LEGEND_MARGIN + controls_h if "top" in corner else sh - h - LEGEND_MARGIN - controls_h
        win.geometry(f"+{x}+{y}")

    # --- H-28: controles de pagina/colapso (ventana aparte, no click-through,
    # mismo patron que init_gear_icon) -----------------------------------------

    def _init_legend_controls(self):
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        bar = tk.Frame(win, bg=LEGEND_CONTROLS_BG)
        bar.pack(padx=4, pady=2)

        def _label(text, command):
            lbl = tk.Label(
                bar, text=text, bg=LEGEND_CONTROLS_BG, fg=LEGEND_CONTROLS_FG,
                font=("Segoe UI", 10, "bold"), cursor="hand2", padx=6,
            )
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda _event: command())
            return lbl

        _label("◀", self._legend_prev_page)
        self._legend_page_label = tk.Label(
            bar, text="", bg=LEGEND_CONTROLS_BG, fg=LEGEND_CONTROLS_FG, font=("Segoe UI", 9), padx=4,
        )
        self._legend_page_label.pack(side="left")
        _label("▶", self._legend_next_page)
        self._legend_collapse_label = _label("▁", self._legend_toggle_collapsed)

        self._legend_controls_window = win

    def _update_legend_controls(self):
        if self._legend_controls_window is None:
            return
        if self._legend_page_label is not None:
            self._legend_page_label.config(text=f"{self._legend_page + 1}/{self._legend_total_pages}")
        if self._legend_collapse_label is not None:
            self._legend_collapse_label.config(text="▲" if self._legend_collapsed else "▁")
        win = self._legend_controls_window
        win.update_idletasks()
        legend_win = self._legend_window
        # En la franja reservada por _position_legend() (mismo lado que el
        # panel, alineada al mismo borde horizontal) - NUNCA se superpone con
        # el panel, asi que el z-order entre las 2 ventanas topmost deja de
        # importar (ver comentario en _position_legend).
        cw, ch = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x = sw - cw - LEGEND_MARGIN if "right" in self._legend_corner else LEGEND_MARGIN
        y = LEGEND_MARGIN if "top" in self._legend_corner else sh - ch - LEGEND_MARGIN
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        if self._legend_visible:
            win.deiconify()
        else:
            win.withdraw()

    def _legend_prev_page(self):
        self._legend_page = (self._legend_page - 1) % self._legend_total_pages
        self._legend_collapsed = False
        self._render_legend()

    def _legend_next_page(self):
        self._legend_page = (self._legend_page + 1) % self._legend_total_pages
        self._legend_collapsed = False
        self._render_legend()

    def _legend_toggle_collapsed(self):
        self._legend_collapsed = not self._legend_collapsed
        self._render_legend()

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
        # H-28: los controles de pagina/colapso siguen al panel - no tiene
        # sentido dejarlos visibles con TOGGLE_LEGEND apagado.
        if self._legend_controls_window:
            if visible:
                self._legend_controls_window.deiconify()
            else:
                self._legend_controls_window.withdraw()

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
