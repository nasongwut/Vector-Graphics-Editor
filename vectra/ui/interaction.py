"""Canvas events → active tool; panning, wheel zoom, context menu, editor keys."""

from vectra.config import CONTROL_MASK, IS_MAC, SHIFT_MASK
from vectra.ui.renderer import ROTATE


class InteractionMixin:
    # ── wiring ──────────────────────────────────────────────────────────────
    def bind_canvas(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_double)
        c.bind("<Motion>", self.on_motion)
        c.bind("<Leave>", lambda e: self._set_hover(None))
        pan_btn, ctx_btn = ("3", "2") if IS_MAC else ("2", "3")
        c.bind(f"<ButtonPress-{pan_btn}>", self.pan_start)
        c.bind(f"<B{pan_btn}-Motion>", self.pan_move)
        c.bind(f"<ButtonRelease-{pan_btn}>", lambda e: self.end_pan())
        c.bind(f"<ButtonPress-{ctx_btn}>", self.context_menu)
        c.bind("<MouseWheel>", self.on_wheel)
        c.bind("<Shift-MouseWheel>", lambda e: self.on_wheel(e, horizontal=True))
        c.bind("<Control-MouseWheel>", lambda e: self.on_wheel(e, zoom=True))
        c.bind("<Alt-MouseWheel>", lambda e: self.on_wheel(e, zoom=True))
        if IS_MAC:
            c.bind("<Command-MouseWheel>", lambda e: self.on_wheel(e, zoom=True))
            c.bind("<Option-MouseWheel>", lambda e: self.on_wheel(e, zoom=True))
        c.bind("<Button-4>", lambda e: self.on_wheel_linux(e, 1))
        c.bind("<Button-5>", lambda e: self.on_wheel_linux(e, -1))
        c.bind("<Configure>", lambda e: self.render())

    # ── tools ───────────────────────────────────────────────────────────────
    def set_tool(self, tool):
        if tool not in self.tools:
            return
        self.commit_text_edit()
        if tool != self.tool:
            self.active_tool.deactivate()
            self.tool = tool
            self.active_tool.activate()
        self.drag = None
        self.temp = None
        self.guides.end()
        self.hover_id = None
        self.toolbar.refresh()
        self.control.refresh()
        self.canvas.config(cursor=self.active_tool.cursor)
        if self._flash_job:
            self.root.after_cancel(self._flash_job)
            self._flash_job = None
        if tool == "type" or tool in ("rect", "rounded_rect"):
            self.panel.props.refresh()
        self.render()

    def handle_key(self, keysym):
        """Editor keys (arrows, Return, Escape, Delete). The tool gets first say."""
        if self.active_tool.on_key(keysym):
            return
        base = keysym.split("+")[-1]
        arrows = {"Left": (-1, 0), "Right": (1, 0), "Up": (0, -1), "Down": (0, 1)}
        if base in arrows:
            k = 10 if keysym.startswith("Shift+") else 1
            dx, dy = arrows[base]
            self.nudge(dx * k, dy * k)
        elif keysym in ("Delete", "BackSpace"):
            self.delete_sel()
        elif keysym == "Escape":
            if self.drag:
                self.drag, self.temp = None, None
            else:
                self.selected.clear()
                self.on_selection_changed()
            self.render()

    def space_key(self, down):
        if down and not self.space:
            self.space = True
            self.canvas.config(cursor="fleur")
        elif not down:
            self.space = False
            self.restore_cursor()

    # ── mouse → tool ────────────────────────────────────────────────────────
    def on_press(self, e):
        self.canvas.focus_set()
        if self.text_editor:
            self.commit_text_edit()
            if self.tool == "type":
                return
        if self.space:
            self.pan_start(e)
            return
        wx, wy = self.to_world(e.x, e.y)
        self.active_tool.press(e, wx, wy)

    def on_drag(self, e):
        if self.drag and self.drag.get("mode") == "pan":
            self.pan_move(e)
            return
        wx, wy = self.to_world(e.x, e.y)
        self.cursor_w = (wx, wy)
        self.active_tool.drag(e, wx, wy)
        if self.show_rulers:
            self.ruler_h.draw()
            self.ruler_v.draw()

    def on_release(self, e):
        if self.drag and self.drag.get("mode") == "pan":
            self.end_pan()
            return
        wx, wy = self.to_world(e.x, e.y)
        self.active_tool.release(e, wx, wy)

    def on_double(self, e):
        """Tk sends the 2nd press of a double-click only to <Double-Button-1>:
        if the tool has no double-click action, treat it as a normal press."""
        wx, wy = self.to_world(e.x, e.y)
        if not self.active_tool.double(e, wx, wy):
            self.on_press(e)

    def on_motion(self, e):
        wx, wy = self.to_world(e.x, e.y)
        self.cursor_w = (wx, wy)
        tool = self.active_tool
        if not self.space:
            if self.tool == "select" and self.selected:
                h = self.handle_at(e.x, e.y)
                if h == ROTATE:
                    self.canvas.config(cursor="exchange")
                elif h is not None:
                    self.canvas.config(cursor="sizing")
                else:
                    self.canvas.config(cursor=tool.cursor)
            elif self.tool == "direct":
                self.canvas.config(cursor="dotbox" if tool.anchor_under(e.x, e.y) else tool.cursor)
            if tool.hover:
                self._set_hover(self.hit(e.x, e.y))
        tool.motion(e, wx, wy)
        self.status_r.config(text=self.status_text())
        if self.show_rulers:
            self.ruler_h.draw()
            self.ruler_v.draw()

    def _set_hover(self, sid):
        if sid != self.hover_id:
            self.hover_id = sid
            self.render()

    # ── panning ─────────────────────────────────────────────────────────────
    def pan_start(self, e):
        self.drag = {"mode": "pan", "last": (e.x, e.y)}
        self.canvas.config(cursor="fleur")

    def pan_move(self, e):
        if self.drag and self.drag.get("mode") == "pan":
            lx, ly = self.drag["last"]
            self.view.pan(e.x - lx, e.y - ly)
            self.drag["last"] = (e.x, e.y)
            self.render()

    def end_pan(self):
        self.drag = None
        self.restore_cursor()

    # ── wheel / context menu ────────────────────────────────────────────────
    def on_wheel(self, e, horizontal=False, zoom=False):
        delta = e.delta
        if not IS_MAC:
            delta = delta / 120
        if zoom:
            self.zoom_at(1.1 ** delta, e.x, e.y)
            return
        amount = delta * (12 if IS_MAC else 40)
        if horizontal:
            self.view.pan(amount, 0)
        else:
            self.view.pan(0, amount)
        self.render()

    def on_wheel_linux(self, e, direction):
        if e.state & CONTROL_MASK:
            self.zoom_at(1.1 ** direction, e.x, e.y)
        elif e.state & SHIFT_MASK:
            self.view.pan(direction * 40, 0)
            self.render()
        else:
            self.view.pan(0, direction * 40)
            self.render()

    def context_menu(self, e):
        sid = self.hit(e.x, e.y)
        if sid and sid not in self.selected:
            self.selected = self.doc.expand_groups({sid}) if self.tool != "direct" else {sid}
            self.on_selection_changed()
            self.render()
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()
