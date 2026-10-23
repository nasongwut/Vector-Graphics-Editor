"""Helpers shared by the side-panel tabs."""

import tkinter as tk

from vectra.ui.theme import T


class Section:
    """Collapsible panel section with a ▾ title row (click to fold)."""

    def __init__(self, parent, ed, title):
        self.ed = ed
        self.frame = tk.Frame(parent, bg=T["panel"])
        head = tk.Frame(self.frame, bg=T["panel"], cursor="hand2")
        head.pack(fill="x", padx=12, pady=(10, 4))
        self.arrow = tk.Label(head, text="▾", bg=T["panel"], fg=T["muted"], font=ed.f(9))
        self.arrow.pack(side="left")
        self.title = tk.Label(head, text=title, bg=T["panel"], fg=T["text"], font=ed.f(10, "bold"))
        self.title.pack(side="left", padx=(4, 0))
        for w in (head, self.arrow, self.title):
            w.bind("<Button-1>", lambda e: self.toggle())
        self.body = tk.Frame(self.frame, bg=T["panel"])
        self.body.pack(fill="x", padx=16, pady=(0, 10))
        tk.Frame(self.frame, bg=T["border"], height=1).pack(fill="x", side="bottom")
        self.open = True

    def toggle(self):
        self.open = not self.open
        self.arrow.config(text="▾" if self.open else "▸")
        if self.open:
            self.body.pack(fill="x", padx=16, pady=(0, 10), before=self.frame.winfo_children()[-1])
        else:
            self.body.pack_forget()

    def show(self):
        self.frame.pack(fill="x")

    def hide(self):
        self.frame.pack_forget()


def button_grid(parent, buttons, columns=2):
    """Lay out widgets in an even grid."""
    for i, b in enumerate(buttons):
        b.grid(row=i // columns, column=i % columns, sticky="ew", padx=2, pady=2)
    for col in range(columns):
        parent.columnconfigure(col, weight=1)
