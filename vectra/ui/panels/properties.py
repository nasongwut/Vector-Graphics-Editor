"""Properties panel: shows only what applies to the current selection or tool."""

import tkinter as tk
from tkinter import ttk

from vectra.i18n import tr
from vectra.model import shapes as sh
from vectra.ui import icons
from vectra.ui.panels.common import Section, button_grid
from vectra.ui.theme import T, font_families
from vectra.ui.widgets import DarkEntry, DarkSpin, FlatButton, IconButton, Swatch


class PropertiesTab:
    def __init__(self, ed, parent):
        self.ed = ed
        p = parent
        lbl = dict(bg=T["panel"], fg=T["muted"], font=ed.f(9))

        # ── header (what is selected) ──────────────────────────────────────
        self.header = tk.Label(p, text="", bg=T["panel"], fg=T["text"], font=ed.f(11, "bold"),
                               anchor="w")
        self.header.pack(fill="x", padx=14, pady=(12, 2))
        tk.Frame(p, bg=T["border"], height=1).pack(fill="x", pady=(8, 0))
        self.holder = tk.Frame(p, bg=T["panel"])
        self.holder.pack(fill="x")

        # ── Document (nothing selected) ────────────────────────────────────
        self.doc_sec = Section(self.holder, ed, tr("sec_document"))
        b = self.doc_sec.body
        row = tk.Frame(b, bg=T["panel"])
        row.pack(fill="x")
        self.ab_entries = {}
        for key, label in (("w", "W"), ("h", "H")):
            tk.Label(row, text=label, **lbl).pack(side="left", padx=(0, 4))
            e = DarkEntry(row, font=(ed.mono, 9), width=7, on_commit=lambda v, k=key: ed.set_artboard_size(k, v))
            e.pack(side="left", padx=(0, 10), ipady=2)
            self.ab_entries[key] = e
        FlatButton(b, tr("m_document_setup"), ed.document_setup, font=ed.f(9), bg=T["panel2"],
                   padx=8, pady=4).pack(fill="x", pady=(8, 0))
        tk.Label(b, text=tr("rulers_grids"), **lbl).pack(anchor="w", pady=(10, 4))
        g = tk.Frame(b, bg=T["panel"])
        g.pack(fill="x")
        self.t_rulers = FlatButton(g, tr("m_rulers"), ed.toggle_rulers, font=ed.f(9), bg=T["panel2"], padx=6, pady=4)
        self.t_grid = FlatButton(g, tr("m_grid"), ed.toggle_grid, font=ed.f(9), bg=T["panel2"], padx=6, pady=4)
        self.t_smart = FlatButton(g, tr("m_smart_guides"), ed.toggle_smart_guides, font=ed.f(9), bg=T["panel2"],
                                  padx=6, pady=4)
        self.t_snap = FlatButton(g, tr("m_snap_grid"), ed.toggle_snap, font=ed.f(9), bg=T["panel2"], padx=6, pady=4)
        button_grid(g, [self.t_rulers, self.t_grid, self.t_smart, self.t_snap])

        # ── Transform ──────────────────────────────────────────────────────
        self.xf_sec = Section(self.holder, ed, tr("sec_transform"))
        b = self.xf_sec.body
        grid = tk.Frame(b, bg=T["panel"])
        grid.pack(fill="x")
        self.entries = {}
        for i, (key, label) in enumerate((("x", "X"), ("y", "Y"), ("w", "W"), ("h", "H"))):
            r, c = divmod(i, 2)
            tk.Label(grid, text=label, **lbl).grid(row=r, column=c * 2, sticky="w", padx=(0 if c == 0 else 10, 6), pady=3)
            e = DarkEntry(grid, font=(ed.mono, 9), width=8, on_commit=lambda v, k=key: ed.apply_transform(k, v))
            e.grid(row=r, column=c * 2 + 1, sticky="ew", pady=3, ipady=2)
            self.entries[key] = e
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)
        row = tk.Frame(b, bg=T["panel"])
        row.pack(fill="x", pady=(6, 0))
        tk.Label(row, text="⟳", **lbl).pack(side="left", padx=(0, 6))
        self.rot_entry = DarkEntry(row, font=(ed.mono, 9), width=6, on_commit=lambda v: ed.apply_transform("rot", v))
        self.rot_entry.pack(side="left", ipady=2)
        tk.Label(row, text="°", **lbl).pack(side="left", padx=(2, 10))
        for kind, fn in (("flip_h", lambda: ed.flip("h")), ("flip_v", lambda: ed.flip("v"))):
            IconButton(row, lambda c, col, k=kind: icons.draw_align(c, k, col), fn, size=24,
                       tooltip=tr("m_" + kind), font=ed.f(9)).pack(side="left", padx=2)
        self.link_btn = FlatButton(row, "🔗", ed.toggle_keep_ratio, font=ed.f(9), bg=T["panel2"], padx=6, pady=2,
                                   tooltip=tr("tip_keep_ratio"), tip_font=ed.f(9))
        self.link_btn.pack(side="right")

        # ── Appearance ─────────────────────────────────────────────────────
        self.ap_sec = Section(self.holder, ed, tr("sec_appearance"))
        b = self.ap_sec.body
        self.fill_sw, self.fill_hex = self._color_row(b, tr("fill"), "fill")
        self.stroke_sw, self.stroke_hex = self._color_row(b, tr("stroke"), "stroke")
        row = tk.Frame(b, bg=T["panel"])
        row.pack(fill="x", pady=(6, 0))
        tk.Label(row, text=tr("stroke_width"), **lbl).pack(side="left")
        self.width_spin = DarkSpin(row, 0, 200, lambda v: ed.set_stroke_width(v), font=(ed.mono, 9), width=5)
        self.width_spin.pack(side="right", ipady=2)
        row = tk.Frame(b, bg=T["panel"])
        row.pack(fill="x", pady=(6, 0))
        self.dash_btn = FlatButton(row, "┅ " + tr("dashed"), ed.toggle_dash, font=ed.f(9), bg=T["panel2"],
                                   padx=8, pady=3)
        self.dash_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
        FlatButton(row, tr("swap"), ed.swap_colors, font=ed.f(9), bg=T["panel2"], padx=8, pady=3,
                   tooltip=tr("tip_swap"), tip_font=ed.f(9)).pack(side="left", fill="x", expand=True, padx=2)
        FlatButton(row, tr("default_colors"), ed.default_colors, font=ed.f(9), bg=T["panel2"], padx=8, pady=3,
                   tooltip=tr("tip_default_colors"), tip_font=ed.f(9)).pack(side="left", fill="x", expand=True,
                                                                           padx=(2, 0))
        self.radius_row = tk.Frame(b, bg=T["panel"])
        tk.Label(self.radius_row, text=tr("corner_radius"), **lbl).pack(side="left")
        self.radius_spin = DarkSpin(self.radius_row, 0, 1000, lambda v: ed.set_radius(v), font=(ed.mono, 9), width=5)
        self.radius_spin.pack(side="right", ipady=2)

        # ── Character ──────────────────────────────────────────────────────
        self.ch_sec = Section(self.holder, ed, tr("sec_character"))
        b = self.ch_sec.body
        self.font_box = ttk.Combobox(b, values=font_families(ed.root), style="Dark.TCombobox", font=ed.f(9))
        self.font_box.pack(fill="x")
        self.font_box.bind("<<ComboboxSelected>>", lambda e: ed.set_font_family(self.font_box.get()))
        self.font_box.bind("<Return>", lambda e: ed.set_font_family(self.font_box.get()))
        row = tk.Frame(b, bg=T["panel"])
        row.pack(fill="x", pady=(6, 0))
        tk.Label(row, text=tr("font_size"), **lbl).pack(side="left")
        self.size_spin = DarkSpin(row, 1, 1000, lambda v: ed.set_font_size(v), font=(ed.mono, 9), width=5)
        self.size_spin.pack(side="right", ipady=2)

        # ── Align ──────────────────────────────────────────────────────────
        self.al_sec = Section(self.holder, ed, tr("sec_align"))
        b = self.al_sec.body
        row = tk.Frame(b, bg=T["panel"])
        row.pack(fill="x")
        for kind in ("left", "hcenter", "right", "top", "vcenter", "bottom", "dist_h", "dist_v"):
            fn = (lambda k=kind: ed.distribute(k[-1])) if kind.startswith("dist") else (lambda k=kind: ed.align(k))
            key = "m_distribute_" + kind[-1] if kind.startswith("dist") else "align_" + kind
            IconButton(row, lambda c, col, k=kind: icons.draw_align(c, k, col), fn, size=26,
                       tooltip=tr(key), font=ed.f(9)).pack(side="left", padx=1)
        row = tk.Frame(b, bg=T["panel"])
        row.pack(fill="x", pady=(6, 0))
        tk.Label(row, text=tr("align_to"), **lbl).pack(side="left")
        self.align_to_btns = {}
        for key in ("selection", "artboard"):
            bt = FlatButton(row, tr("align_to_" + key), lambda k=key: ed.set_align_to(k), font=ed.f(9),
                            bg=T["panel2"], padx=6, pady=2)
            bt.pack(side="left", padx=(6, 0))
            self.align_to_btns[key] = bt

        # ── Quick actions ──────────────────────────────────────────────────
        self.qa_sec = Section(self.holder, ed, tr("sec_quick"))
        self.qa_body = self.qa_sec.body
        self.qa_buttons = {}
        for key, fn in (("m_group", ed.group_sel), ("m_ungroup", ed.ungroup_sel),
                        ("m_convert_path", ed.convert_to_path), ("m_join", ed.join_paths),
                        ("m_make_compound", ed.make_compound), ("m_release_compound", ed.release_compound),
                        ("m_edit_text", ed.edit_selected_text), ("m_bring_front", ed.bring_front),
                        ("m_send_back", ed.send_back), ("m_duplicate", ed.duplicate),
                        ("m_lock", ed.lock_sel), ("m_hide", ed.hide_sel), ("m_clear", ed.delete_sel)):
            self.qa_buttons[key] = FlatButton(self.qa_body, tr(key), fn, font=ed.f(9), bg=T["panel2"], padx=6,
                                              pady=4, hover=T["danger_hover"] if key == "m_clear" else None)

        self.sections = [self.doc_sec, self.xf_sec, self.ap_sec, self.ch_sec, self.al_sec, self.qa_sec]

    def _color_row(self, parent, label, which):
        ed = self.ed
        row = tk.Frame(parent, bg=T["panel"])
        row.pack(fill="x", pady=3)
        sw = Swatch(row, 26, command=lambda: (ed.set_color_focus(which), ed.pick_color(which)))
        sw.pack(side="left")
        col = tk.Frame(row, bg=T["panel"])
        col.pack(side="left", padx=10)
        tk.Label(col, text=label, bg=T["panel"], fg=T["text"], font=ed.f(9)).pack(anchor="w")
        hx = tk.Label(col, text="", bg=T["panel"], fg=T["muted"], font=(ed.mono, 8))
        hx.pack(anchor="w")
        FlatButton(row, tr("none"), lambda: ed.set_color(which, None), font=ed.f(9),
                   bg=T["panel2"], padx=8, pady=2).pack(side="right")
        return sw, hx

    # ── refresh ─────────────────────────────────────────────────────────────
    def refresh(self):
        ed = self.ed
        sel = ed.selected_shapes()
        types = {s["type"] for s in sel}
        if not sel:
            self.header.config(text=tr("no_selection"))
        elif len(sel) == 1:
            self.header.config(text=sh.display_name(sel[0]))
        elif len({s.get("gid") for s in sel}) == 1 and sel[0].get("gid") is not None:
            self.header.config(text=tr("group_of", n=len(sel)))
        else:
            self.header.config(text=tr("n_selected", n=len(sel)))

        visible = []
        if not sel:
            visible.append(self.doc_sec)
            ab = ed.doc.artboard
            self.ab_entries["w"].show(f"{ab[2] - ab[0]:g}")
            self.ab_entries["h"].show(f"{ab[3] - ab[1]:g}")
            self.t_rulers.set_active(ed.show_rulers)
            self.t_grid.set_active(ed.show_grid)
            self.t_smart.set_active(ed.smart_guides)
            self.t_snap.set_active(ed.snap)
        else:
            visible.append(self.xf_sec)
        visible.append(self.ap_sec)
        if "text" in types or ed.tool == "type":
            visible.append(self.ch_sec)
            self.font_box.set(ed.font_family)
            self.size_spin.show(ed.font_size)
        if sel:
            visible += [self.al_sec, self.qa_sec]
        for s in self.sections:
            s.hide()
        for s in visible:
            s.show()

        self.fill_sw.set(ed.fill)
        self.stroke_sw.set(ed.stroke)
        self.fill_hex.config(text=(ed.fill or tr("none")).upper())
        self.stroke_hex.config(text=(ed.stroke or tr("none")).upper())
        self.width_spin.show(ed.width)
        self.dash_btn.set_active(ed.dash)
        if "rect" in types or ed.tool in ("rect", "rounded_rect"):
            self.radius_spin.show(ed.radius)
            self.radius_row.pack(fill="x", pady=(6, 0))
        else:
            self.radius_row.pack_forget()
        self.link_btn.set_active(ed.keep_ratio)
        for k, bt in self.align_to_btns.items():
            bt.set_active(ed.align_to == k)

        # quick actions depend on the selection
        for bt in self.qa_buttons.values():
            bt.grid_forget()
        wanted = []
        grouped = any(s.get("gid") is not None for s in sel)
        if len(sel) > 1 and not (len({s.get("gid") for s in sel}) == 1 and grouped):
            wanted.append("m_group")
        if grouped:
            wanted.append("m_ungroup")
        if types & {"rect", "ellipse", "polygon", "line", "pen"}:
            wanted.append("m_convert_path")
        if sum(1 for s in sel if s["type"] in ("path", "line", "pen") and not sh.prop(s, "closed")) >= 1:
            wanted.append("m_join")
        if len([s for s in sel if s["type"] != "text"]) > 1:
            wanted.append("m_make_compound")
        if any(sh.is_compound(s) for s in sel):
            wanted.append("m_release_compound")
        if types == {"text"} and len(sel) == 1:
            wanted.append("m_edit_text")
        wanted += ["m_bring_front", "m_send_back", "m_duplicate", "m_lock", "m_hide", "m_clear"]
        button_grid(self.qa_body, [self.qa_buttons[k] for k in wanted])
        self.show_geometry()

    def show_geometry(self):
        ed = self.ed
        bb = ed.selection_bbox()
        if not bb:
            return
        ab = ed.doc.artboard
        self.entries["x"].show(f"{bb[0] - ab[0]:.1f}")
        self.entries["y"].show(f"{bb[1] - ab[1]:.1f}")
        self.entries["w"].show(f"{bb[2] - bb[0]:.1f}")
        self.entries["h"].show(f"{bb[3] - bb[1]:.1f}")
        sel = ed.selected_shapes()
        self.rot_entry.show(f"{-sh.prop(sel[0], 'rot') + 0:g}" if len(sel) == 1 else "0")
