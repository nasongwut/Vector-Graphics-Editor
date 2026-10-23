"""Arrange tab: align / distribute, stacking order, object commands, view toggles."""

import tkinter as tk

from vectra.i18n import tr
from vectra.ui.panels.common import button_grid, section
from vectra.ui.theme import T
from vectra.ui.widgets import FlatButton


class ArrangeTab:
    def __init__(self, ed, parent):
        self.ed = ed
        p = parent

        def btn(frame, text, cmd, tip=None, danger=False, font_size=9):
            return FlatButton(frame, text, cmd, font=ed.f(font_size), bg=T["panel2"], padx=6, pady=6,
                              tooltip=tip, tip_font=ed.f(9), hover=T["danger_hover"] if danger else None)

        # ── align ──────────────────────────────────────────────────────────
        s = section(p, ed, tr("sec_align"), first=True)
        g = tk.Frame(s, bg=T["panel"])
        g.pack(fill="x")
        button_grid(g, [
            btn(g, "⫷", lambda: ed.align("left"), tr("align_left"), font_size=12),
            btn(g, "⫼", lambda: ed.align("hcenter"), tr("align_hcenter"), font_size=12),
            btn(g, "⫸", lambda: ed.align("right"), tr("align_right"), font_size=12),
            btn(g, "⊤", lambda: ed.align("top"), tr("align_top"), font_size=12),
            btn(g, "⊝", lambda: ed.align("vcenter"), tr("align_vcenter"), font_size=12),
            btn(g, "⊥", lambda: ed.align("bottom"), tr("align_bottom"), font_size=12),
        ], columns=3)
        g2 = tk.Frame(s, bg=T["panel"])
        g2.pack(fill="x", pady=(4, 0))
        button_grid(g2, [
            btn(g2, tr("distribute_h"), lambda: ed.distribute("h"), tr("tip_distribute")),
            btn(g2, tr("distribute_v"), lambda: ed.distribute("v"), tr("tip_distribute")),
        ])
        tk.Label(s, text=tr("align_to_artboard"), bg=T["panel"], fg=T["muted"], font=ed.f(8),
                 wraplength=230, justify="left").pack(anchor="w", pady=(6, 0))

        # ── stacking order ─────────────────────────────────────────────────
        s = section(p, ed, tr("sec_arrange"))
        g = tk.Frame(s, bg=T["panel"])
        g.pack(fill="x")
        button_grid(g, [
            btn(g, tr("bring_front"), ed.bring_front, "Shift+]"),
            btn(g, tr("bring_forward"), ed.bring_forward, "]"),
            btn(g, tr("send_backward"), ed.send_backward, "["),
            btn(g, tr("send_back"), ed.send_back, "Shift+["),
        ])

        # ── object ─────────────────────────────────────────────────────────
        s = section(p, ed, tr("sec_object"))
        g = tk.Frame(s, bg=T["panel"])
        g.pack(fill="x")
        button_grid(g, [
            btn(g, tr("group"), ed.group_sel, "Ctrl+G"),
            btn(g, tr("ungroup"), ed.ungroup_sel, "Ctrl+Shift+G"),
            btn(g, tr("flip_h"), lambda: ed.flip("h")),
            btn(g, tr("flip_v"), lambda: ed.flip("v")),
            btn(g, tr("rotate_ccw"), lambda: ed.rotate_sel(-90)),
            btn(g, tr("rotate_cw"), lambda: ed.rotate_sel(90)),
            btn(g, tr("lock"), ed.lock_sel, "Ctrl+2"),
            btn(g, tr("unlock_all"), ed.unlock_all, "Ctrl+Alt+2"),
            btn(g, tr("hide"), ed.hide_sel, "Ctrl+3"),
            btn(g, tr("show_all"), ed.show_all, "Ctrl+Alt+3"),
            btn(g, tr("duplicate"), ed.duplicate, "Ctrl+D"),
            btn(g, tr("delete"), ed.delete_sel, "Delete", danger=True),
        ])

        # ── view ───────────────────────────────────────────────────────────
        s = section(p, ed, tr("sec_view"))
        row = tk.Frame(s, bg=T["panel"])
        row.pack(fill="x")
        self.grid_btn = FlatButton(row, tr("grid"), ed.toggle_grid, font=ed.f(9), bg=T["panel2"],
                                   padx=8, pady=6, tooltip=tr("tip_grid"), tip_font=ed.f(9))
        self.grid_btn.pack(side="left", fill="x", expand=True, padx=2)
        self.snap_btn = FlatButton(row, tr("snap"), ed.toggle_snap, font=ed.f(9), bg=T["panel2"],
                                   padx=8, pady=6, tooltip=tr("tip_snap"), tip_font=ed.f(9))
        self.snap_btn.pack(side="left", fill="x", expand=True, padx=2)
        tk.Label(p, text=tr("panel_footer"), bg=T["panel"], fg=T["muted"],
                 font=ed.f(8)).pack(pady=(18, 12))

    def refresh(self):
        self.grid_btn.set_active(self.ed.show_grid)
        self.snap_btn.set_active(self.ed.snap)
