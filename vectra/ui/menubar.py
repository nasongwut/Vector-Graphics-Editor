"""Application menu bar: File · Edit · Object · Type · Select · View · Window · Help."""

import tkinter as tk

from vectra.i18n import LANGUAGES, get_language, tr
from vectra.ui.keys import acc
from vectra.ui.theme import T

FONT_SIZES = (8, 9, 10, 11, 12, 14, 18, 24, 30, 36, 48, 60, 72, 96, 144)


def _menu(parent, ed):
    return tk.Menu(parent, tearoff=0, bg=T["menu"], fg=T["text"], bd=0, relief="flat",
                   activebackground=T["accent"], activeforeground="#ffffff",
                   selectcolor=T["text"], font=ed.f(10), disabledforeground=T["dim"])


def build_menubar(ed, root):
    v = ed.menu_vars = {k: tk.BooleanVar(root) for k in
                        ("outline", "rulers", "smart", "grid", "snap", "tools", "control")}
    lang_var = tk.StringVar(root, value=get_language())
    bar = _menu(root, ed)

    def cmd(menu, key, fn, sc=""):
        menu.add_command(label=tr(key), command=fn, accelerator=acc(sc))

    def check(menu, key, var, fn, sc=""):
        menu.add_checkbutton(label=tr(key), variable=v[var], command=fn, accelerator=acc(sc))

    # File
    m = _menu(bar, ed)
    cmd(m, "m_new", ed.new_doc, "Ctrl+N")
    cmd(m, "m_open", ed.open_doc, "Ctrl+O")
    cmd(m, "m_place", ed.place_file, "Ctrl+Shift+P")
    m.add_separator()
    cmd(m, "m_save", ed.save, "Ctrl+S")
    cmd(m, "m_save_as", lambda: ed.save(True), "Ctrl+Shift+S")
    m.add_separator()
    cmd(m, "m_export_svg", ed.export_svg, "Ctrl+Alt+E")
    m.add_separator()
    cmd(m, "m_document_setup", ed.document_setup, "Ctrl+Alt+P")
    m.add_separator()
    cmd(m, "m_exit", ed.on_close, "Ctrl+Q")
    bar.add_cascade(label=tr("menu_file"), menu=m)

    # Edit
    m = _menu(bar, ed)
    cmd(m, "m_undo", ed.undo, "Ctrl+Z")
    cmd(m, "m_redo", ed.redo, "Ctrl+Shift+Z")
    m.add_separator()
    cmd(m, "m_cut", ed.cut_sel, "Ctrl+X")
    cmd(m, "m_copy", ed.copy_sel, "Ctrl+C")
    cmd(m, "m_paste", ed.paste, "Ctrl+V")
    cmd(m, "m_paste_front", ed.paste_in_front, "Ctrl+F")
    cmd(m, "m_paste_back", ed.paste_in_back, "Ctrl+B")
    cmd(m, "m_paste_place", ed.paste_in_place, "Ctrl+Shift+V")
    cmd(m, "m_clear", ed.delete_sel, "Del")
    m.add_separator()
    cmd(m, "m_duplicate", ed.duplicate)
    m.add_separator()
    langs = _menu(m, ed)
    for code, name in LANGUAGES.items():
        langs.add_radiobutton(label=name, value=code, variable=lang_var,
                              command=lambda c=code: ed.set_language(c))
    m.add_cascade(label=tr("m_language"), menu=langs)
    bar.add_cascade(label=tr("menu_edit"), menu=m)

    # Object
    m = _menu(bar, ed)
    sub = _menu(m, ed)
    cmd(sub, "m_transform_again", ed.transform_again, "Ctrl+D")
    sub.add_separator()
    cmd(sub, "m_move", lambda: ed.open_transform_dialog("move"), "Ctrl+Shift+M")
    cmd(sub, "m_rotate", lambda: ed.open_transform_dialog("rotate"))
    cmd(sub, "m_reflect", lambda: ed.open_transform_dialog("reflect"))
    cmd(sub, "m_scale", lambda: ed.open_transform_dialog("scale"))
    sub.add_separator()
    cmd(sub, "m_flip_h", lambda: ed.flip("h"))
    cmd(sub, "m_flip_v", lambda: ed.flip("v"))
    m.add_cascade(label=tr("m_transform"), menu=sub)
    sub = _menu(m, ed)
    cmd(sub, "m_bring_front", ed.bring_front, "Ctrl+Shift+]")
    cmd(sub, "m_bring_forward", ed.bring_forward, "Ctrl+]")
    cmd(sub, "m_send_backward", ed.send_backward, "Ctrl+[")
    cmd(sub, "m_send_back", ed.send_back, "Ctrl+Shift+[")
    sub.add_separator()
    cmd(sub, "m_send_to_layer", ed.move_selection_to_layer)
    m.add_cascade(label=tr("m_arrange"), menu=sub)
    sub = _menu(m, ed)
    for key in ("left", "hcenter", "right", "top", "vcenter", "bottom"):
        cmd(sub, "align_" + key, lambda k=key: ed.align(k))
    sub.add_separator()
    cmd(sub, "m_distribute_h", lambda: ed.distribute("h"))
    cmd(sub, "m_distribute_v", lambda: ed.distribute("v"))
    m.add_cascade(label=tr("m_align"), menu=sub)
    m.add_separator()
    cmd(m, "m_group", ed.group_sel, "Ctrl+G")
    cmd(m, "m_ungroup", ed.ungroup_sel, "Ctrl+Shift+G")
    m.add_separator()
    cmd(m, "m_lock", ed.lock_sel, "Ctrl+2")
    cmd(m, "m_unlock_all", ed.unlock_all, "Ctrl+Alt+2")
    cmd(m, "m_hide", ed.hide_sel, "Ctrl+3")
    cmd(m, "m_show_all", ed.show_all, "Ctrl+Alt+3")
    m.add_separator()
    sub = _menu(m, ed)
    cmd(sub, "m_join", ed.join_paths, "Ctrl+J")
    cmd(sub, "m_close_path", ed.close_paths)
    cmd(sub, "m_reverse_path", ed.reverse_paths)
    m.add_cascade(label=tr("m_path"), menu=sub)
    sub = _menu(m, ed)
    cmd(sub, "m_make_compound", ed.make_compound, "Ctrl+8")
    cmd(sub, "m_release_compound", ed.release_compound, "Ctrl+Alt+Shift+8")
    m.add_cascade(label=tr("m_compound"), menu=sub)
    cmd(m, "m_convert_path", ed.convert_to_path)
    m.add_separator()
    cmd(m, "m_fit_artboard_art", ed.fit_artboard_to_art)
    bar.add_cascade(label=tr("menu_object"), menu=m)

    # Type
    m = _menu(bar, ed)
    sub = _menu(m, ed)
    for size in FONT_SIZES:
        sub.add_command(label=f"{size} px", command=lambda s=size: ed.set_font_size(s))
    m.add_cascade(label=tr("m_font_size"), menu=sub)
    cmd(m, "m_character", lambda: ed.show_panel("props"))
    cmd(m, "m_edit_text", ed.edit_selected_text)
    bar.add_cascade(label=tr("menu_type"), menu=m)

    # Select
    m = _menu(bar, ed)
    cmd(m, "m_select_all", ed.select_all, "Ctrl+A")
    cmd(m, "m_deselect", ed.deselect, "Ctrl+Shift+A")
    cmd(m, "m_inverse", ed.select_inverse)
    m.add_separator()
    sub = _menu(m, ed)
    for key in ("fill", "stroke", "width", "type"):
        cmd(sub, "same_" + key, lambda k=key: ed.select_same(k))
    m.add_cascade(label=tr("m_same"), menu=sub)
    bar.add_cascade(label=tr("menu_select"), menu=m)

    # View
    m = _menu(bar, ed)
    check(m, "m_outline", "outline", ed.toggle_outline, "Ctrl+Y")
    m.add_separator()
    cmd(m, "m_zoom_in", lambda: ed.zoom_center(1.25), "Ctrl++")
    cmd(m, "m_zoom_out", lambda: ed.zoom_center(0.8), "Ctrl+-")
    cmd(m, "m_fit_artboard", ed.zoom_fit, "Ctrl+0")
    cmd(m, "m_actual_size", lambda: ed.set_zoom(1.0), "Ctrl+1")
    m.add_separator()
    check(m, "m_rulers", "rulers", ed.toggle_rulers, "Ctrl+R")
    check(m, "m_smart_guides", "smart", ed.toggle_smart_guides, "Ctrl+U")
    check(m, "m_grid", "grid", ed.toggle_grid, "Ctrl+'")
    check(m, "m_snap_grid", "snap", ed.toggle_snap, "Ctrl+Shift+'")
    bar.add_cascade(label=tr("menu_view"), menu=m)

    # Window
    m = _menu(bar, ed)
    check(m, "m_win_tools", "tools", ed.toggle_toolbar)
    check(m, "m_win_control", "control", ed.toggle_controlbar)
    m.add_separator()
    cmd(m, "tab_props", lambda: ed.show_panel("props"))
    cmd(m, "tab_layers", lambda: ed.show_panel("layers"), "F7")
    cmd(m, "m_new_layer", ed.new_layer, "Ctrl+L")
    cmd(m, "tab_swatches", lambda: ed.show_panel("swatches"))
    m.add_separator()
    cmd(m, "m_hide_panels", ed.toggle_all_panels, "Tab")
    bar.add_cascade(label=tr("menu_window"), menu=m)

    # Help
    m = _menu(bar, ed)
    cmd(m, "m_shortcuts", ed.show_shortcuts, "F1")
    cmd(m, "m_about", ed.show_about)
    bar.add_cascade(label=tr("menu_help"), menu=m)

    root.config(menu=bar)
    return bar
