"""Window chrome: document tab, status bar and the canvas context menu."""

import tkinter as tk

from vectra.i18n import LANGUAGES, get_language, tr
from vectra.ui.keys import acc
from vectra.ui.theme import T
from vectra.ui.widgets import DarkEntry, FlatButton, Tooltip


def build_doc_tab(ed, parent):
    bar = tk.Frame(parent, bg=T["panel3"], height=28)
    bar.pack(side="top", fill="x")
    bar.pack_propagate(False)
    tab = tk.Frame(bar, bg=T["canvas"])
    tab.pack(side="left", fill="y", padx=(0, 1))
    ed.doc_tab = tk.Label(tab, text="", bg=T["canvas"], fg=T["text"], font=ed.f(9), padx=12)
    ed.doc_tab.pack(side="left", fill="y")
    return bar


def build_statusbar(ed, root):
    status = tk.Frame(root, bg=T["panel"], height=26)
    status.pack(side="bottom", fill="x")
    status.pack_propagate(False)
    tk.Frame(root, bg=T["border"], height=1).pack(side="bottom", fill="x")

    ed.zoom_entry = DarkEntry(status, font=(ed.mono, 9), width=6,
                              on_commit=lambda v: ed.set_zoom_text(v))
    ed.zoom_entry.pack(side="left", padx=(10, 4), ipady=1)
    Tooltip(ed.zoom_entry, tr("tip_zoom_field"), side="below", font=ed.f(9))
    tk.Label(status, text="◀  1  ▶", bg=T["panel"], fg=T["dim"], font=ed.f(9)).pack(side="left", padx=8)
    ed.tool_label = tk.Label(status, text="", bg=T["panel"], fg=T["text"], font=ed.f(9), width=18, anchor="w")
    ed.tool_label.pack(side="left", padx=(6, 0))
    lang = tk.Frame(status, bg=T["panel"])
    lang.pack(side="right", padx=(4, 10))
    for code in LANGUAGES:
        b = FlatButton(lang, code.upper(), lambda c=code: ed.set_language(c), font=ed.f(8, "bold"),
                       bg=T["panel"], padx=6, pady=1, tooltip=tr("tip_lang"), tip_font=ed.f(9))
        b.pack(side="left")
        b.set_active(code == get_language())
    ed.status_r = tk.Label(status, text="", bg=T["panel"], fg=T["muted"], font=(ed.mono, 9))
    ed.status_r.pack(side="right", padx=10)
    tk.Frame(status, bg=T["divider"], width=1).pack(side="left", fill="y", pady=5, padx=6)
    ed.status_l = tk.Label(status, text="", bg=T["panel"], fg=T["muted"], font=ed.f(9), anchor="w", width=1)
    ed.status_l.pack(side="left", fill="x", expand=True)



def build_context_menu(ed, root):
    menu = tk.Menu(root, tearoff=0, bg=T["menu"], fg=T["text"], bd=0,
                   activebackground=T["accent"], activeforeground="#ffffff",
                   font=ed.f(10), relief="flat")
    items = [
        ("m_undo", ed.undo, "Ctrl+Z"), ("m_redo", ed.redo, "Ctrl+Shift+Z"), None,
        ("m_cut", ed.cut_sel, "Ctrl+X"), ("m_copy", ed.copy_sel, "Ctrl+C"), ("m_paste", ed.paste, "Ctrl+V"),
        None,
        ("m_group", ed.group_sel, "Ctrl+G"), ("m_ungroup", ed.ungroup_sel, "Ctrl+Shift+G"),
        ("m_join", ed.join_paths, "Ctrl+J"), ("m_convert_path", ed.convert_to_path, ""), None,
        ("m_bring_front", ed.bring_front, "Ctrl+Shift+]"), ("m_bring_forward", ed.bring_forward, "Ctrl+]"),
        ("m_send_backward", ed.send_backward, "Ctrl+["), ("m_send_back", ed.send_back, "Ctrl+Shift+["), None,
        ("m_move", lambda: ed.open_transform_dialog("move"), "Ctrl+Shift+M"),
        ("m_rotate", lambda: ed.open_transform_dialog("rotate"), ""),
        ("m_reflect", lambda: ed.open_transform_dialog("reflect"), ""),
        ("m_scale", lambda: ed.open_transform_dialog("scale"), ""), None,
        ("m_lock", ed.lock_sel, "Ctrl+2"), ("m_hide", ed.hide_sel, "Ctrl+3"), None,
        ("m_clear", ed.delete_sel, "Del"),
    ]
    for item in items:
        if item is None:
            menu.add_separator()
        else:
            key, cmd, sc = item
            menu.add_command(label=tr(key), command=cmd, accelerator=acc(sc))
    return menu
