"""Edit text directly on the canvas (Type tool / double-click a text object).

Esc or clicking elsewhere commits · Ctrl+Enter commits · Enter = new line.
"""

import tkinter as tk

from vectra.model import shapes as sh
from vectra.ui.theme import T


class InlineTextEditor:
    def __init__(self, ed, shape, is_new):
        self.ed = ed
        self.shape = shape
        self.is_new = is_new
        z = ed.view.zoom
        family = shape.get("font") or ed.ui_font
        size = -max(6, int(round(sh.prop(shape, "size") * z)))
        color = shape.get("fill") or "#000000"
        self.text = tk.Text(ed.canvas, font=sh.font_spec(shape, family, size), fg=color, bg="#ffffff",
                            insertbackground=color, relief="flat", bd=0, wrap="none",
                            highlightthickness=1, highlightbackground=T["selection"],
                            highlightcolor=T["selection"], undo=True, padx=0, pady=0)
        self.text.insert("1.0", shape.get("text", ""))
        x, y = ed.to_screen(shape["pts"])
        self.win = ed.canvas.create_window(x, y, window=self.text, anchor="nw")
        self.text.bind("<Escape>", lambda e: (self.commit(), "break")[1])
        self.text.bind("<Control-Return>", lambda e: (self.commit(), "break")[1])
        self.text.bind("<KeyRelease>", lambda e: self._fit())
        self._fit()
        self.text.focus_set()
        self.text.mark_set("insert", "end-1c")
        self.text.tag_add("sel", "1.0", "end-1c") if not is_new else None
        self.done = False

    def _fit(self):
        content = self.text.get("1.0", "end-1c")
        lines = content.split("\n") or [""]
        self.text.config(width=max(4, max(len(ln) for ln in lines) + 2), height=max(1, len(lines)))

    def commit(self):
        if self.done:
            return
        self.done = True
        ed, s = self.ed, self.shape
        value = self.text.get("1.0", "end-1c").rstrip("\n")
        try:
            self.text.destroy()
        except tk.TclError:
            pass
        ed.text_editor = None
        ed.editing_id = None
        if self.is_new:
            if value.strip():
                s["text"] = value
                ed.add_shape(s)
        else:
            current = ed.doc.by_id(s["id"])
            if current is not None:
                if not value.strip():
                    ed.push_undo()
                    ed.doc.remove({s["id"]})
                    ed.selected.discard(s["id"])
                elif value != current.get("text"):
                    ed.push_undo()
                    current["text"] = value
        ed.canvas.focus_set()
        ed.on_selection_changed()
        ed.render()
