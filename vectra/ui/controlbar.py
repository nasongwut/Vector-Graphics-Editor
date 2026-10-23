"""Context-sensitive Control bar under the menu (Window ▸ Control)."""

import tkinter as tk
from tkinter import ttk

from vectra.i18n import tr
from vectra.model import shapes as sh
from vectra.ui import icons
from vectra.ui.theme import T, font_families
from vectra.ui.widgets import DarkEntry, DarkSpin, FlatButton, IconButton, Swatch, Tooltip


class ControlBar:
    def __init__(self, ed, parent):
        self.ed = ed
        f = self.frame = tk.Frame(parent, bg=T["panel"], height=36)
        f.pack_propagate(False)
        lbl = dict(bg=T["panel"], fg=T["muted"], font=ed.f(9))

        self.sel_label = tk.Label(f, text="", bg=T["panel"], fg=T["text"], font=ed.f(10, "bold"),
                                  width=16, anchor="w")
        self.sel_label.pack(side="left", padx=(12, 6))

        self.fill_sw = Swatch(f, 22, command=lambda: self._swatch("fill"))
        self.fill_sw.pack(side="left", padx=2)
        Tooltip(self.fill_sw, tr("fill"), side="below", font=ed.f(9))
        self.stroke_sw = Swatch(f, 22, command=lambda: self._swatch("stroke"))
        self.stroke_sw.pack(side="left", padx=(2, 8))
        Tooltip(self.stroke_sw, tr("stroke"), side="below", font=ed.f(9))

        tk.Label(f, text=tr("stroke") + ":", **lbl).pack(side="left")
        self.width_spin = DarkSpin(f, 0, 200, lambda v: ed.set_stroke_width(v), font=(ed.mono, 9), width=4)
        self.width_spin.pack(side="left", padx=(4, 2), ipady=2)
        tk.Label(f, text="px", **lbl).pack(side="left", padx=(0, 6))
        self.dash_btn = FlatButton(f, "┅", ed.toggle_dash, font=ed.f(10), bg=T["panel2"], padx=6, pady=1,
                                   tooltip=tr("dashed"), tip_font=ed.f(9))
        self.dash_btn.pack(side="left", padx=(0, 8))

        # context: rectangle corner radius
        self.rect_frame = tk.Frame(f, bg=T["panel"])
        tk.Label(self.rect_frame, text=tr("corner") + ":", **lbl).pack(side="left")
        self.radius_spin = DarkSpin(self.rect_frame, 0, 1000, lambda v: ed.set_radius(v),
                                    font=(ed.mono, 9), width=4)
        self.radius_spin.pack(side="left", padx=4, ipady=2)

        # context: character
        self.text_frame = tk.Frame(f, bg=T["panel"])
        tk.Label(self.text_frame, text=tr("character") + ":", **lbl).pack(side="left")
        self.font_box = ttk.Combobox(self.text_frame, values=font_families(ed.root), width=18,
                                     style="Dark.TCombobox", font=ed.f(9))
        self.font_box.pack(side="left", padx=4)
        self.font_box.bind("<<ComboboxSelected>>", lambda e: ed.set_font_family(self.font_box.get()))
        self.font_box.bind("<Return>", lambda e: ed.set_font_family(self.font_box.get()))
        self.size_spin = DarkSpin(self.text_frame, 1, 1000, lambda v: ed.set_font_size(v),
                                  font=(ed.mono, 9), width=4)
        self.size_spin.pack(side="left", padx=4, ipady=2)

        # right side: align, then transform fields
        self.align_frame = tk.Frame(f, bg=T["panel"])
        self.align_frame.pack(side="right", padx=(6, 12))
        for kind in ("left", "hcenter", "right", "top", "vcenter", "bottom"):
            IconButton(self.align_frame, lambda c, col, k=kind: icons.draw_align(c, k, col),
                       lambda k=kind: ed.align(k), size=24, tooltip=tr("align_" + kind),
                       font=ed.f(9)).pack(side="left", padx=1)

        self.xf = tk.Frame(f, bg=T["panel"])
        self.xf.pack(side="right", padx=6)
        self.entries = {}
        for key, label in (("x", "X"), ("y", "Y"), ("w", "W"), ("h", "H")):
            tk.Label(self.xf, text=label + ":", **lbl).pack(side="left", padx=(6, 2))
            e = DarkEntry(self.xf, font=(ed.mono, 9), width=7,
                          on_commit=lambda v, k=key: ed.apply_transform(k, v))
            e.pack(side="left", ipady=2)
            self.entries[key] = e

    def _swatch(self, which):
        self.ed.set_color_focus(which)
        self.ed.pick_color(which)

    def pack(self, **kw):
        self.frame.pack(**kw)

    def pack_forget(self):
        self.frame.pack_forget()

    def refresh(self):
        ed = self.ed
        sel = ed.selected_shapes()
        if not sel:
            label = tr("no_selection")
        elif len(sel) == 1:
            label = sh.display_name(sel[0])
        elif len({s.get("gid") for s in sel}) == 1 and sel[0].get("gid") is not None:
            label = tr("group")
        else:
            label = tr("mixed_objects")
        self.sel_label.config(text=label[:22])
        self.fill_sw.set(ed.fill)
        self.stroke_sw.set(ed.stroke)
        self.width_spin.show(ed.width)
        self.dash_btn.set_active(ed.dash)
        types = {s["type"] for s in sel}
        self.rect_frame.pack_forget()
        self.text_frame.pack_forget()
        if "rect" in types or ed.tool in ("rect", "rounded_rect"):
            self.radius_spin.show(ed.radius)
            self.rect_frame.pack(side="left", padx=(0, 8))
        if "text" in types or ed.tool == "type":
            self.font_box.set(ed.font_family)
            self.size_spin.show(ed.font_size)
            self.text_frame.pack(side="left", padx=(0, 8))
        self.show_geometry()

    def show_geometry(self):
        bb = self.ed.selection_bbox()
        for k, e in self.entries.items():
            e.config(state="normal" if bb else "disabled")
        if not bb:
            for e in self.entries.values():
                e.show("")
            return
        self.entries["x"].show(f"{bb[0] - self.ed.doc.artboard[0]:.1f}")
        self.entries["y"].show(f"{bb[1] - self.ed.doc.artboard[1]:.1f}")
        self.entries["w"].show(f"{bb[2] - bb[0]:.1f}")
        self.entries["h"].show(f"{bb[3] - bb[1]:.1f}")
