"""Window chrome: top bar, status bar, tool bar and context menu."""

import tkinter as tk

from vectra.config import APP_NAME
from vectra.i18n import LANGUAGES, get_language, tr
from vectra.ui.theme import T
from vectra.ui.tools import TOOLS
from vectra.ui.widgets import FlatButton


def build_topbar(ed, root):
    top = tk.Frame(root, bg=T["panel"], height=54)
    top.pack(side="top", fill="x")
    top.pack_propagate(False)

    logo = tk.Canvas(top, width=30, height=30, bg=T["panel"], highlightthickness=0)
    logo.pack(side="left", padx=(18, 8))
    logo.create_polygon(15, 3, 27, 26, 3, 26, fill=T["accent"], outline="")
    logo.create_oval(10, 13, 20, 23, fill=T["panel"], outline="")
    tk.Label(top, text=APP_NAME, bg=T["panel"], fg=T["text"], font=ed.f(14, "bold")).pack(side="left")
    tk.Label(top, text=tr("app_subtitle"), bg=T["panel"], fg=T["muted"],
             font=ed.f(10)).pack(side="left", padx=(6, 22))

    def tb(text, cmd, tip):
        b = FlatButton(top, text, cmd, font=ed.f(10), padx=12, pady=7, tooltip=tip, tip_font=ed.f(9))
        b.pack(side="left", padx=2, pady=10)
        return b

    def vsep():
        tk.Frame(top, bg=T["border"], width=1).pack(side="left", fill="y", padx=10, pady=14)

    tb(tr("btn_new"), ed.new_doc, tr("tip_new"))
    tb(tr("btn_open"), ed.open_doc, tr("tip_open"))
    tb(tr("btn_save"), ed.save, tr("tip_save"))
    tb(tr("btn_save_as"), lambda: ed.save(True), tr("tip_save_as"))
    vsep()
    tb("↶", ed.undo, tr("tip_undo"))
    tb("↷", ed.redo, tr("tip_redo"))

    FlatButton(top, tr("btn_export"), ed.export_svg, font=ed.f(10, "bold"),
               bg=T["accent"], fg="#ffffff", hover=T["accent2"], padx=16, pady=7,
               tooltip=tr("tip_export"), tip_font=ed.f(9)).pack(side="right", padx=(8, 18), pady=10)

    # language switch: "TH | EN" segmented control
    lang = tk.Frame(top, bg=T["panel2"])
    lang.pack(side="right", pady=12, padx=6)
    for code in LANGUAGES:
        b = FlatButton(lang, code.upper(), lambda c=code: ed.set_language(c), font=ed.f(9, "bold"),
                       bg=T["panel2"], padx=8, pady=2, tooltip=tr("tip_lang"), tip_font=ed.f(9))
        b.pack(side="left")
        b.set_active(code == get_language())

    zf = tk.Frame(top, bg=T["panel2"])
    zf.pack(side="right", pady=12, padx=6)
    FlatButton(zf, "−", lambda: ed.zoom_center(1 / 1.2), font=ed.f(11), bg=T["panel2"],
               padx=10, pady=2).pack(side="left")
    ed.zoom_lbl = FlatButton(zf, "100%", lambda: ed.set_zoom(1.0), font=(ed.mono, 10),
                             bg=T["panel2"], padx=6, pady=2, width=5,
                             tooltip=tr("tip_zoom100"), tip_font=ed.f(9))
    ed.zoom_lbl.pack(side="left")
    FlatButton(zf, "+", lambda: ed.zoom_center(1.2), font=ed.f(11), bg=T["panel2"],
               padx=10, pady=2).pack(side="left")
    FlatButton(top, tr("btn_fit"), ed.zoom_fit, font=ed.f(10), padx=10, pady=7,
               tooltip=tr("tip_fit"), tip_font=ed.f(9)).pack(side="right", pady=10)

    tk.Frame(root, bg=T["border"], height=1).pack(side="top", fill="x")


def build_statusbar(ed, root):
    status = tk.Frame(root, bg=T["panel"], height=28)
    status.pack(side="bottom", fill="x")
    status.pack_propagate(False)
    tk.Frame(root, bg=T["border"], height=1).pack(side="bottom", fill="x")
    ed.status_l = tk.Label(status, text="", bg=T["panel"], fg=T["muted"], font=ed.f(9), anchor="w")
    ed.status_l.pack(side="left", padx=14)
    ed.status_r = tk.Label(status, text="", bg=T["panel"], fg=T["muted"], font=(ed.mono, 9))
    ed.status_r.pack(side="right", padx=14)


def build_toolbar(ed, parent):
    """Vertical tool strip. Returns {tool_key: FlatButton}."""
    left = tk.Frame(parent, bg=T["panel"], width=64)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)
    tk.Frame(parent, bg=T["border"], width=1).pack(side="left", fill="y")
    tk.Frame(left, bg=T["panel"], height=8).pack()
    buttons = {}
    for item in TOOLS:
        if item is None:
            tk.Frame(left, bg=T["border"], height=1, width=32).pack(pady=6)
            continue
        key, icon, name_key, shortcut = item
        b = FlatButton(left, icon, lambda k=key: ed.set_tool(k),
                       font=(ed.ui_font, 15), width=2, padx=6, pady=4,
                       tooltip=f"{tr(name_key)}   {shortcut}", tip_side="right", tip_font=ed.f(9))
        b.pack(pady=2)
        buttons[key] = b
    return buttons


def build_context_menu(ed, root):
    menu = tk.Menu(root, tearoff=0, bg=T["panel2"], fg=T["text"], bd=0,
                   activebackground=T["accent"], activeforeground="#ffffff",
                   font=ed.f(10), relief="flat")
    items = [
        ("menu_copy", ed.copy_sel, "Ctrl+C"), ("menu_paste", ed.paste, "Ctrl+V"),
        ("menu_duplicate", ed.duplicate, "Ctrl+D"), None,
        ("menu_group", ed.group_sel, "Ctrl+G"), ("menu_ungroup", ed.ungroup_sel, "Ctrl+Shift+G"), None,
        ("menu_bring_front", ed.bring_front, "Shift+]"), ("menu_bring_forward", ed.bring_forward, "]"),
        ("menu_send_backward", ed.send_backward, "["), ("menu_send_back", ed.send_back, "Shift+["), None,
        ("menu_flip_h", lambda: ed.flip("h"), ""), ("menu_flip_v", lambda: ed.flip("v"), ""), None,
        ("menu_lock", ed.lock_sel, "Ctrl+2"), ("menu_hide", ed.hide_sel, "Ctrl+3"), None,
        ("menu_delete", ed.delete_sel, "Del"),
    ]
    for item in items:
        if item is None:
            menu.add_separator()
        else:
            key, cmd, acc = item
            menu.add_command(label=tr(key), command=cmd, accelerator=acc)
    return menu
