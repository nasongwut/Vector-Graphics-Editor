"""Keyboard shortcuts (bound on the root window), following common pro-app conventions."""

import tkinter as tk
from tkinter import ttk

from vectra.config import IS_MAC
from vectra.ui.tooling import SHORTCUTS


def _typing(e):
    """True while the user is typing in a field — shortcuts must not fire."""
    return isinstance(e.widget, (tk.Entry, tk.Text, tk.Spinbox, ttk.Entry))


def bind_shortcuts(ed):
    r = ed.root
    mods = ["Control"] + (["Command"] if IS_MAC else [])
    alt = "Option" if IS_MAC else "Alt"

    def on(sequence, fn, break_=True):
        def handler(e):
            if _typing(e):
                return None
            fn()
            return "break" if break_ else None
        r.bind(sequence, handler)

    def sc(key, fn, with_alt=False):
        for m in mods:
            on(f"<{m}-{alt}-Key-{key}>" if with_alt else f"<{m}-Key-{key}>", fn)

    # File
    sc("n", ed.new_doc)
    sc("o", ed.open_doc)
    sc("s", ed.save)
    sc("S", lambda: ed.save(True))
    sc("e", ed.export_svg, with_alt=True)
    sc("p", ed.document_setup, with_alt=True)
    if not IS_MAC:
        sc("q", ed.on_close)
    # Edit
    sc("z", ed.undo)
    sc("Z", ed.redo)
    sc("x", ed.cut_sel)
    sc("c", ed.copy_sel)
    sc("v", ed.paste)
    sc("V", ed.paste_in_place)
    sc("f", ed.paste_in_front)
    sc("b", ed.paste_in_back)
    # Object
    sc("d", ed.transform_again)
    sc("M", lambda: ed.open_transform_dialog("move"))
    sc("g", ed.group_sel)
    sc("G", ed.ungroup_sel)
    sc("j", ed.join_paths)
    sc("8", ed.make_compound)
    sc("l", ed.new_layer)
    sc("asterisk", ed.release_compound, with_alt=True)
    sc("8", ed.release_compound, with_alt=True)
    sc("P", ed.place_file)
    sc("2", ed.lock_sel)
    sc("2", ed.unlock_all, with_alt=True)
    sc("3", ed.hide_sel)
    sc("3", ed.show_all, with_alt=True)
    sc("bracketright", ed.bring_forward)
    sc("bracketleft", ed.send_backward)
    sc("braceright", ed.bring_front)
    sc("braceleft", ed.send_back)
    # Select
    sc("a", ed.select_all)
    sc("A", ed.deselect)
    # View
    sc("y", ed.toggle_outline)
    sc("r", ed.toggle_rulers)
    sc("u", ed.toggle_smart_guides)
    sc("apostrophe", ed.toggle_grid)
    sc("quotedbl", ed.toggle_snap)
    sc("0", ed.zoom_fit)
    sc("1", lambda: ed.set_zoom(1.0))
    sc("equal", lambda: ed.zoom_center(1.25))
    sc("plus", lambda: ed.zoom_center(1.25))
    sc("minus", lambda: ed.zoom_center(0.8))

    # Tools
    for tool, (_label, keysyms) in SHORTCUTS.items():
        for k in keysyms:
            on(f"<KeyPress-{k}>", lambda t=tool: ed.set_tool(t), break_=False)
    on("<KeyPress-d>", ed.default_colors, break_=False)
    on("<KeyPress-x>", ed.toggle_color_focus, break_=False)
    on("<KeyPress-X>", ed.swap_colors, break_=False)
    on("<KeyPress-slash>", lambda: ed.set_focus_color(None), break_=False)
    on("<KeyPress-comma>", ed.apply_last_color, break_=False)
    on("<F1>", ed.show_shortcuts)
    on("<F7>", lambda: ed.show_panel("layers"))
    on("<Tab>", ed.toggle_all_panels)

    # Editor keys go through the active tool first
    for keysym in ("Return", "KP_Enter", "Escape", "Delete", "BackSpace", "Left", "Right", "Up", "Down"):
        on(f"<KeyPress-{keysym}>", lambda k=keysym: ed.handle_key(k), break_=False)
    for keysym in ("Left", "Right", "Up", "Down"):
        on(f"<Shift-KeyPress-{keysym}>", lambda k=keysym: ed.handle_key("Shift+" + k), break_=False)

    def space(down):
        def handler(e):
            if not _typing(e):
                ed.space_key(down)
        return handler
    r.bind("<KeyPress-space>", space(True))
    r.bind("<KeyRelease-space>", space(False))
