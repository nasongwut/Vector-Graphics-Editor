"""Left tool bar: grouped tools with fly-outs + the Fill / Stroke widget."""

import tkinter as tk

from vectra.config import IS_MAC
from vectra.i18n import tr
from vectra.ui import icons
from vectra.ui.keys import acc
from vectra.ui.theme import T
from vectra.ui.tooling import TOOL_GROUPS, shortcut_label
from vectra.ui.widgets import Tooltip

BTN_W, BTN_H = 40, 30
SEPARATE_BEFORE = {3, 7, 9, 12, 13}
HOLD_MS = 380


class ToolButton(tk.Canvas):
    def __init__(self, bar, index):
        super().__init__(bar.frame, width=BTN_W, height=BTN_H, bg=T["panel"], highlightthickness=0,
                         cursor="hand2")
        self.bar, self.ed, self.index = bar, bar.ed, index
        self.group = TOOL_GROUPS[index]
        self._hold = None
        self._hover = False
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Double-Button-1>", self._double)
        self.bind("<Button-2>" if IS_MAC else "<Button-3>", lambda e: self.flyout())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.tip = Tooltip(self, "", side="right", font=self.ed.f(9))

    @property
    def current(self):
        return self.bar.current[self.index]

    def _set_hover(self, h):
        self._hover = h
        self.paint()

    def paint(self):
        active = self.ed.tool == self.current
        self.delete("all")
        bg = T["tool_active"] if active else (T["hover"] if self._hover else T["panel"])
        self.config(bg=bg)
        if active:
            self.create_rectangle(0, 0, 2, BTN_H, fill=T["accent"], outline="")
        self.move_icon()
        if len(self.group) > 1:
            self.create_polygon(BTN_W - 4, BTN_H - 8, BTN_W - 4, BTN_H - 4, BTN_W - 8, BTN_H - 4,
                                fill=T["muted"], outline="")
        sc = shortcut_label(self.current)
        self.tip.text = f"{tr('tool_' + self.current)}  ({acc(sc)})" if sc else tr("tool_" + self.current)

    def move_icon(self):
        """Draw the 24×24 icon centred in the button."""
        col = "#ffffff" if self.ed.tool == self.current else T["text"]
        before = set(self.find_all())
        icons.draw(self, self.current, col)
        for item in set(self.find_all()) - before:
            self.move(item, (BTN_W - 24) / 2, (BTN_H - 24) / 2)

    def _press(self, e):
        self._hold = self.after(HOLD_MS, self.flyout) if len(self.group) > 1 else None

    def _release(self, e):
        if self._hold:
            self.after_cancel(self._hold)
            self._hold = None
        if 0 <= e.x <= BTN_W and 0 <= e.y <= BTN_H:
            self.ed.set_tool(self.current)

    def _double(self, e):
        tool = self.ed.tools.get(self.current)
        if getattr(tool, "dialog", ""):
            self.ed.open_transform_dialog(tool.dialog)

    def flyout(self):
        self._hold = None
        ed = self.ed
        m = tk.Menu(self, tearoff=0, bg=T["menu"], fg=T["text"], activebackground=T["accent"],
                    activeforeground="#ffffff", font=ed.f(10), bd=0)
        for key in self.group:
            m.add_command(label=("■ " if key == self.current else "   ") + tr("tool_" + key),
                          accelerator=acc(shortcut_label(key)),
                          command=lambda k=key: ed.set_tool(k))
        try:
            m.tk_popup(self.winfo_rootx() + BTN_W + 2, self.winfo_rooty())
        finally:
            m.grab_release()


class FillStrokeWidget(tk.Canvas):
    """Overlapping Fill / Stroke squares, swap arrow and default-colours icon."""
    W, H = 46, 50

    def __init__(self, master, ed):
        super().__init__(master, width=self.W, height=self.H, bg=T["panel"], highlightthickness=0)
        self.ed = ed
        self.bind("<Button-1>", self._click)
        self.bind("<Double-Button-1>", self._double)
        Tooltip(self, tr("tip_fill_stroke"), side="right", font=ed.f(9))

    def paint(self):
        ed = self.ed
        self.delete("all")
        fill_box, stroke_box = (5, 5, 27, 27), (17, 17, 39, 39)

        def draw_fill():
            self.create_rectangle(*fill_box, fill=ed.fill or "#ffffff", outline=T["border"])
            if not ed.fill:
                self.create_line(fill_box[0] + 2, fill_box[3] - 2, fill_box[2] - 2, fill_box[1] + 2,
                                 fill=T["danger"], width=2)

        def draw_stroke():
            x0, y0, x1, y1 = stroke_box
            col = ed.stroke or "#ffffff"
            self.create_rectangle(x0, y0, x1, y1, fill=T["panel"], outline=T["border"])
            self.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, outline=col, width=6)
            self.create_rectangle(x0 + 7, y0 + 7, x1 - 7, y1 - 7, outline=T["border"], fill=T["panel"])
            if not ed.stroke:
                self.create_line(x0 + 2, y1 - 2, x1 - 2, y0 + 2, fill=T["danger"], width=2)

        if ed.color_focus == "fill":
            draw_stroke()
            draw_fill()
        else:
            draw_fill()
            draw_stroke()
        # swap arrow (top right) & default colours (bottom left)
        self.create_line(32, 4, 41, 4, 41, 12, fill=T["text"], arrow="both", arrowshape=(4, 4, 2))
        self.create_rectangle(4, 38, 10, 44, fill="#000000", outline=T["text"])
        self.create_rectangle(1, 35, 7, 41, fill="#ffffff", outline=T["text"])

    def _hit(self, e):
        if e.x >= 30 and e.y <= 14:
            return "swap"
        if e.x <= 12 and e.y >= 33:
            return "default"
        in_fill = 5 <= e.x <= 27 and 5 <= e.y <= 27
        in_stroke = 17 <= e.x <= 39 and 17 <= e.y <= 39
        if in_fill and in_stroke:
            return self.ed.color_focus
        if in_fill:
            return "fill"
        if in_stroke:
            return "stroke"
        return None

    def _click(self, e):
        what = self._hit(e)
        if what == "swap":
            self.ed.swap_colors()
        elif what == "default":
            self.ed.default_colors()
        elif what in ("fill", "stroke"):
            self.ed.set_color_focus(what)

    def _double(self, e):
        what = self._hit(e)
        if what in ("fill", "stroke"):
            self.ed.pick_color(what)


class ToolBar:
    def __init__(self, ed, parent):
        self.ed = ed
        self.current = [g[0] for g in TOOL_GROUPS]
        self.outer = tk.Frame(parent, bg=T["panel"], width=46)
        self.frame = tk.Frame(self.outer, bg=T["panel"])
        self.frame.pack(side="top", pady=(6, 0))
        self.buttons = []
        for i in range(len(TOOL_GROUPS)):
            if i in SEPARATE_BEFORE:
                tk.Frame(self.frame, bg=T["divider"], height=1, width=28).pack(pady=4)
            b = ToolButton(self, i)
            b.pack()
            self.buttons.append(b)
        tk.Frame(self.frame, bg=T["divider"], height=1, width=28).pack(pady=(6, 6))
        self.fs = FillStrokeWidget(self.frame, ed)
        self.fs.pack()
        row = tk.Frame(self.frame, bg=T["panel"])
        row.pack(pady=(4, 6))
        self.color_btn = tk.Canvas(row, width=18, height=18, bg=T["panel"], highlightthickness=0, cursor="hand2")
        self.color_btn.pack(side="left", padx=2)
        self.none_btn = tk.Canvas(row, width=18, height=18, bg=T["panel"], highlightthickness=0, cursor="hand2")
        self.none_btn.pack(side="left", padx=2)
        self.none_btn.create_rectangle(2, 2, 16, 16, fill="#ffffff", outline=T["border"])
        self.none_btn.create_line(3, 15, 15, 3, fill=T["danger"], width=2)
        self.color_btn.bind("<Button-1>", lambda e: self.ed.apply_last_color())
        self.none_btn.bind("<Button-1>", lambda e: self.ed.set_focus_color(None))
        Tooltip(self.color_btn, tr("tip_color_btn"), side="right", font=ed.f(9))
        Tooltip(self.none_btn, tr("tip_none_btn"), side="right", font=ed.f(9))

    def pack(self, **kw):
        self.outer.pack(**kw)

    def pack_forget(self):
        self.outer.pack_forget()

    def set_current(self, key):
        for i, grp in enumerate(TOOL_GROUPS):
            if key in grp:
                self.current[i] = key

    def refresh(self):
        self.set_current(self.ed.tool)
        for b in self.buttons:
            b.paint()
        self.fs.paint()
        self.color_btn.delete("all")
        self.color_btn.create_rectangle(2, 2, 16, 16, fill=self.ed.last_color or "#ffffff", outline=T["border"])
