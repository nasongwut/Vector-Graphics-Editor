"""Horizontal / vertical rulers (View ▸ Rulers, Ctrl+R). Origin = artboard top-left."""

import tkinter as tk

from vectra.model.geometry import nice_step
from vectra.ui.theme import T

SIZE = 18


class Ruler(tk.Canvas):
    def __init__(self, master, ed, horizontal):
        kw = {"height": SIZE} if horizontal else {"width": SIZE}
        super().__init__(master, bg=T["ruler"], highlightthickness=0, bd=0, **kw)
        self.ed = ed
        self.horizontal = horizontal

    def draw(self):
        ed = self.ed
        self.delete("all")
        length = self.winfo_width() if self.horizontal else self.winfo_height()
        if length <= 1:
            return
        z = ed.view.zoom
        origin_w = ed.doc.artboard[0] if self.horizontal else ed.doc.artboard[1]
        offset = ed.view.ox if self.horizontal else ed.view.oy
        major = nice_step(60, z)
        minor = major / 5 if (major / 5) * z >= 5 else major / 2
        # first world value visible
        w0 = (0 - offset) / z - origin_w
        k = int(w0 // minor) - 1
        font = (ed.mono, 7)
        def on_step(v, step):
            return abs(v / step - round(v / step)) < 1e-6

        while True:
            wv = k * minor
            sp = (wv + origin_w) * z + offset
            if sp > length:
                break
            if on_step(wv, major):
                tick = SIZE
            elif on_step(wv, major / 2):
                tick = 8
            else:
                tick = 4
            if self.horizontal:
                self.create_line(sp, SIZE, sp, SIZE - tick, fill=T["dim"])
                if tick == SIZE:
                    self.create_text(sp + 3, 1, text=f"{wv:g}", anchor="nw", fill=T["ruler_text"], font=font)
            else:
                self.create_line(SIZE, sp, SIZE - tick, sp, fill=T["dim"])
                if tick == SIZE:
                    self.create_text(1, sp + 3, text=f"{wv:g}", anchor="ne", angle=90,
                                     fill=T["ruler_text"], font=font)
            k += 1
        if self.horizontal:
            self.create_line(0, SIZE - 1, length, SIZE - 1, fill=T["border"])
        else:
            self.create_line(SIZE - 1, 0, SIZE - 1, length, fill=T["border"])
        # cursor marker
        cx, cy = ed.cursor_w
        if self.horizontal:
            x = cx * z + ed.view.ox
            self.create_line(x, 0, x, SIZE, fill=T["accent2"])
        else:
            y = cy * z + ed.view.oy
            self.create_line(0, y, SIZE, y, fill=T["accent2"])
