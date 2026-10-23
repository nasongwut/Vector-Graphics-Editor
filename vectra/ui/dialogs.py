"""Small modal dialogs in the app theme."""

import tkinter as tk

from vectra.config import APP_NAME
from vectra.i18n import tr
from vectra.ui.theme import T
from vectra.ui.widgets import FlatButton


class _Dialog(tk.Toplevel):
    def __init__(self, ed, title):
        super().__init__(ed.root)
        self.ed = ed
        self.title(title)
        self.configure(bg=T["panel"])
        self.resizable(False, False)
        self.transient(ed.root)
        self.result = None
        self.body = tk.Frame(self, bg=T["panel"])
        self.body.pack(fill="both", expand=True, padx=18, pady=(16, 8))
        self.buttons = tk.Frame(self, bg=T["panel"])
        self.buttons.pack(fill="x", padx=18, pady=(4, 16))
        self.bind("<Escape>", lambda e: self.cancel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def add_button(self, text, cmd, primary=False):
        ed = self.ed
        b = FlatButton(self.buttons, text, cmd, font=ed.f(10, "bold" if primary else "normal"),
                       bg=T["accent"] if primary else T["panel2"], fg="#ffffff" if primary else T["text"],
                       hover=T["accent2"] if primary else T["hover"], padx=16, pady=6)
        b.pack(side="right", padx=(6, 0))
        return b

    def show(self):
        self.update_idletasks()
        r = self.ed.root
        x = r.winfo_rootx() + (r.winfo_width() - self.winfo_width()) // 2
        y = r.winfo_rooty() + (r.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.wait_window(self)
        return self.result

    def cancel(self):
        self.result = None
        self.destroy()


class FormDialog(_Dialog):
    """Numeric fields. ``fields`` = [(key, label, default)]. Returns (values, copy) or None."""

    def __init__(self, ed, title, fields, allow_copy=False, note=None):
        super().__init__(ed, title)
        self.entries = {}
        for r, (key, label, default) in enumerate(fields):
            tk.Label(self.body, text=label, bg=T["panel"], fg=T["text"], font=ed.f(10),
                     anchor="w").grid(row=r, column=0, sticky="w", pady=4, padx=(0, 14))
            e = tk.Entry(self.body, width=12, font=(ed.mono, 10), bg=T["entry"], fg=T["text"],
                         insertbackground=T["text"], relief="flat", highlightthickness=1,
                         highlightbackground=T["divider"], highlightcolor=T["accent"], justify="right")
            e.insert(0, f"{default:g}" if isinstance(default, (int, float)) else str(default))
            e.grid(row=r, column=1, sticky="ew", pady=4, ipady=3)
            self.entries[key] = e
        if note:
            tk.Label(self.body, text=note, bg=T["panel"], fg=T["muted"], font=ed.f(9),
                     wraplength=260, justify="left").grid(row=len(fields), column=0, columnspan=2,
                                                          sticky="w", pady=(8, 0))
        self.add_button(tr("ok"), lambda: self.done(False), primary=True)
        if allow_copy:
            self.add_button(tr("copy"), lambda: self.done(True))
        self.add_button(tr("cancel"), self.cancel)
        self.bind("<Return>", lambda e: self.done(False))
        first = next(iter(self.entries.values()), None)
        if first is not None:
            first.focus_set()
            first.select_range(0, "end")
        self.copy = False

    def done(self, copy):
        vals = {}
        for k, e in self.entries.items():
            try:
                vals[k] = float(e.get().replace(",", "."))
            except ValueError:
                e.config(highlightbackground=T["danger"])
                e.focus_set()
                return
        self.result = (vals, copy)
        self.destroy()


class TextDialog(_Dialog):
    """Read-only text (keyboard shortcuts, about)."""

    def __init__(self, ed, title, text, width=64, height=26):
        super().__init__(ed, title)
        t = tk.Text(self.body, width=width, height=height, bg=T["panel2"], fg=T["text"],
                    font=(ed.mono, 10), relief="flat", bd=0, padx=12, pady=10, wrap="word")
        t.insert("1.0", text)
        t.config(state="disabled")
        t.pack(fill="both", expand=True)
        self.add_button(tr("ok"), self.cancel, primary=True)


def ask_form(ed, title, fields, allow_copy=False, note=None):
    return FormDialog(ed, title, fields, allow_copy, note).show()


def shortcuts_text():
    rows = [
        ("tool_select", "V"), ("tool_direct", "A"), ("tool_magic_wand", "Y"), ("tool_lasso", "Q"),
        ("tool_pen", "P"), ("tool_add_anchor", "+"), ("tool_delete_anchor", "-"),
        ("tool_anchor_point", "Shift+C"), ("tool_type", "T"), ("tool_line", "\\"),
        ("tool_rect", "M"), ("tool_ellipse", "L"), ("tool_pencil", "N"), ("tool_scissors", "C"),
        ("tool_rotate", "R"), ("tool_reflect", "O"), ("tool_scale", "S"), ("tool_artboard", "Shift+O"),
        ("tool_eyedropper", "I"), ("tool_hand", "H / Space"), ("tool_zoom", "Z"),
        None,
        ("m_undo", "Ctrl+Z"), ("m_redo", "Ctrl+Shift+Z"), ("m_cut", "Ctrl+X"), ("m_copy", "Ctrl+C"),
        ("m_paste", "Ctrl+V"), ("m_paste_front", "Ctrl+F"), ("m_paste_back", "Ctrl+B"),
        ("m_paste_place", "Ctrl+Shift+V"), ("m_transform_again", "Ctrl+D"), ("m_move", "Ctrl+Shift+M"),
        ("m_group", "Ctrl+G"), ("m_ungroup", "Ctrl+Shift+G"), ("m_join", "Ctrl+J"),
        ("m_lock", "Ctrl+2"), ("m_unlock_all", "Ctrl+Alt+2"), ("m_hide", "Ctrl+3"), ("m_show_all", "Ctrl+Alt+3"),
        ("m_bring_front", "Ctrl+Shift+]"), ("m_bring_forward", "Ctrl+]"), ("m_send_backward", "Ctrl+["),
        ("m_send_back", "Ctrl+Shift+["), ("m_select_all", "Ctrl+A"), ("m_deselect", "Ctrl+Shift+A"),
        ("m_outline", "Ctrl+Y"), ("m_rulers", "Ctrl+R"), ("m_smart_guides", "Ctrl+U"), ("m_grid", "Ctrl+'"),
        ("m_snap_grid", "Ctrl+Shift+'"), ("m_fit_artboard", "Ctrl+0"), ("m_actual_size", "Ctrl+1"),
        ("m_zoom_in", "Ctrl++"), ("m_zoom_out", "Ctrl+-"), ("m_hide_panels", "Tab"),
        None,
        ("k_default_colors", "D"), ("k_toggle_focus", "X"), ("k_swap", "Shift+X"), ("k_none", "/"),
        ("k_nudge", "← ↑ → ↓  (Shift ×10)"), ("k_alt_drag", "Alt + drag"),
    ]
    out = []
    for row in rows:
        if row is None:
            out.append("")
            continue
        key, sc = row
        out.append(f"{tr(key):<34}{sc}")
    return "\n".join(out)


def about_text():
    return tr("about_text", app=APP_NAME)
