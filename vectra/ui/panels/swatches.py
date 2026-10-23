"""Swatches panel: click applies to the active Fill/Stroke (see the tool bar widget)."""

import tkinter as tk

from vectra import settings
from vectra.config import IS_MAC
from vectra.i18n import tr
from vectra.ui.theme import PALETTE, T
from vectra.ui.widgets import FlatButton, Tooltip

COLS = 10
CELL = 24


class SwatchesTab:
    def __init__(self, ed, parent):
        self.ed = ed
        tk.Label(parent, text=tr("swatches_hint"), bg=T["panel"], fg=T["muted"], font=ed.f(8),
                 wraplength=250, justify="left").pack(anchor="w", padx=14, pady=(12, 8))
        self.grid = tk.Frame(parent, bg=T["panel"])
        self.grid.pack(anchor="w", padx=12)
        row = tk.Frame(parent, bg=T["panel"])
        row.pack(fill="x", padx=12, pady=10)
        FlatButton(row, "＋ " + tr("new_swatch"), self.add_current, font=ed.f(9), bg=T["panel2"],
                   padx=8, pady=4).pack(side="left", fill="x", expand=True, padx=(0, 2))
        FlatButton(row, tr("reset_swatches"), self.reset, font=ed.f(9), bg=T["panel2"],
                   padx=8, pady=4).pack(side="left", fill="x", expand=True, padx=(2, 0))
        self.build()

    def colors(self):
        custom = settings.get("swatches")
        return custom if isinstance(custom, list) and custom else list(PALETTE)

    def build(self):
        ed = self.ed
        for w in self.grid.winfo_children():
            w.destroy()
        rbtn = "<Button-2>" if IS_MAC else "<Button-3>"
        none = tk.Canvas(self.grid, width=CELL, height=CELL, bg=T["panel"], highlightthickness=0, cursor="hand2")
        none.create_rectangle(2, 2, CELL - 2, CELL - 2, fill="#ffffff", outline=T["border"])
        none.create_line(3, CELL - 3, CELL - 3, 3, fill=T["danger"], width=2)
        none.grid(row=0, column=0, padx=1, pady=1)
        none.bind("<Button-1>", lambda e: ed.set_focus_color(None))
        Tooltip(none, tr("none"), side="below", font=ed.f(9))
        for i, col in enumerate(self.colors(), start=1):
            cv = tk.Canvas(self.grid, width=CELL, height=CELL, bg=T["panel"], highlightthickness=0, cursor="hand2")
            cv.create_rectangle(2, 2, CELL - 2, CELL - 2, fill=col, outline=T["border"])
            cv.grid(row=i // COLS, column=i % COLS, padx=1, pady=1)
            cv.bind("<Button-1>", lambda e, c=col: ed.set_focus_color(c))
            cv.bind(rbtn, lambda e, c=col: ed.set_color("stroke", c))
            cv.bind("<Double-Button-1>", lambda e, c=col: self.remove(c) if e.state & 0x4 else None)

    def add_current(self):
        col = getattr(self.ed, self.ed.color_focus)
        if not col:
            return
        cols = self.colors()
        if col not in cols:
            cols.append(col)
            settings.set("swatches", cols)
            self.build()

    def remove(self, col):
        cols = [c for c in self.colors() if c != col]
        settings.set("swatches", cols)
        self.build()

    def reset(self):
        settings.set("swatches", None)
        self.build()
