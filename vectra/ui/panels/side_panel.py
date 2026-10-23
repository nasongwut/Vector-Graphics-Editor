"""Right-hand panel dock with tabs: Properties · Layers · Swatches."""

import tkinter as tk

from vectra.i18n import tr
from vectra.ui.panels.layers import LayersTab
from vectra.ui.panels.properties import PropertiesTab
from vectra.ui.panels.swatches import SwatchesTab
from vectra.ui.theme import T
from vectra.ui.widgets import ScrollFrame

TABS = (("props", "tab_props"), ("layers", "tab_layers"), ("swatches", "tab_swatches"))


class SidePanel:
    def __init__(self, ed, parent, current="props"):
        self.ed = ed
        bar = tk.Frame(parent, bg=T["panel3"])
        bar.pack(side="top", fill="x")
        self.tab_labels, self.frames = {}, {}
        for key, label in TABS:
            lb = tk.Label(bar, text=tr(label), bg=T["panel3"], fg=T["muted"], font=ed.f(9, "bold"),
                          padx=12, pady=7, cursor="hand2")
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, k=key: self.show(k))
            self.tab_labels[key] = lb
            if key == "layers":   # list scrolls, footer buttons stay put
                box = tk.Frame(parent, bg=T["panel"])
                footer = tk.Frame(box, bg=T["panel3"], height=30)
                footer.pack(side="bottom", fill="x")
                footer.pack_propagate(False)
                box.scroll = ScrollFrame(box, bg=T["panel"])
                box.scroll.pack(side="top", fill="both", expand=True)
                box.footer = footer
                self.frames[key] = box
            else:
                self.frames[key] = ScrollFrame(parent, bg=T["panel"])

        self.props = PropertiesTab(ed, self.frames["props"].inner)
        lbox = self.frames["layers"]
        self.layers = LayersTab(ed, lbox.scroll.inner, lbox.footer, lbox.scroll)
        self.swatches = SwatchesTab(ed, self.frames["swatches"].inner)
        self.current = None
        self.show(current)

    def show(self, key):
        if key == self.current:
            return
        if self.current:
            self.frames[self.current].pack_forget()
        self.current = key
        self.frames[key].pack(side="top", fill="both", expand=True)
        for k, lb in self.tab_labels.items():
            lb.config(bg=T["panel"] if k == key else T["panel3"], fg=T["text"] if k == key else T["muted"])
        if key == "layers":
            self.layers.refresh(force=True)

    def refresh(self):
        self.props.refresh()
        self.layers.refresh()

    def show_geometry(self):
        self.props.show_geometry()
