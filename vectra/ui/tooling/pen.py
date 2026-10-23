"""Pen (P), Add Anchor (+), Delete Anchor (-) and Anchor Point (Shift+C)."""

import math

from vectra.model import pathops
from vectra.model import shapes as sh
from vectra.ui.tooling.base import Tool, shift, snap_angle

CLOSE_HIT = 8
ANCHOR_HIT = 6


def _constrain(x0, y0, x, y):
    ang = snap_angle(math.degrees(math.atan2(y - y0, x - x0)), 45)
    ln = math.hypot(x - x0, y - y0)
    return x0 + ln * math.cos(math.radians(ang)), y0 + ln * math.sin(math.radians(ang))


class PenTool(Tool):
    key = "pen"
    cursor = "crosshair"

    def __init__(self, ed):
        super().__init__(ed)
        self.path = None
        self.cursor_w = None
        self.dragging = None   # index of the node whose handles follow the mouse
        self.closing = False

    def activate(self):
        self.path, self.dragging, self.closing = None, None, False

    def deactivate(self):
        self.finish()

    def finish(self, close=False):
        ed = self.ed
        p = self.path
        self.path, self.dragging, self.closing = None, None, False
        ed.temp = None
        ed.guides.end()
        if p and sh.node_count(p) >= 2:
            if close:
                p["closed"] = True
            ed.add_shape(p)
            ed.on_selection_changed()
        ed.render()

    def press(self, e, wx, wy):
        ed = self.ed
        self.press_screen = (e.x, e.y)
        x, y = self.snap_point(wx, wy)
        if self.path is None:
            style = ed.current_style()
            self.path = sh.make_shape("path", [x, y], style)
            ed.temp = self.path
            self.dragging = 0
            ed.render()
            return
        n = sh.node_count(self.path)
        fx, fy = ed.to_screen(list(sh.node(self.path, 0)[0]))
        if n >= 2 and math.hypot(e.x - fx, e.y - fy) <= CLOSE_HIT:
            self.closing = True
            self.dragging = 0
            return
        if shift(e):
            lx, ly = sh.node(self.path, n - 1)[0]
            x, y = _constrain(lx, ly, x, y)
        pathops.append_node(self.path, x, y)
        self.dragging = n
        ed.render()

    def drag(self, e, wx, wy):
        if self.path is None or self.dragging is None or not self.moved(e, 2):
            return
        (ax, ay), _i, _o = sh.node(self.path, self.dragging)
        hx, hy = (wx, wy)
        if shift(e):
            hx, hy = _constrain(ax, ay, hx, hy)
        pathops.set_symmetric_handles(self.path, self.dragging, hx, hy)
        self.cursor_w = None
        self.ed.render()

    def release(self, e, wx, wy):
        self.dragging = None
        if self.closing:
            self.finish(close=True)

    def motion(self, e, wx, wy):
        if self.path is not None:
            self.cursor_w = (wx, wy)
            self.ed.render()

    def on_key(self, keysym):
        if keysym in ("Return", "Escape", "KP_Enter") and self.path is not None:
            self.finish()
            return True
        if keysym in ("Delete", "BackSpace") and self.path is not None:
            if sh.node_count(self.path) > 1:
                pathops.delete_node(self.path, sh.node_count(self.path) - 1) or self._drop_last()
            else:
                self.path = None
                self.ed.temp = None
            self.ed.render()
            return True
        return False

    def _drop_last(self):
        p = self.path
        del p["pts"][-2:]
        del p["ctrl"][-4:]
        del p["smooth"][-1]

    def overlay(self, r):
        p, ed, c = self.path, self.ed, r.c
        if p is None:
            return
        col = r.T["selection"]
        n = sh.node_count(p)
        if self.cursor_w and self.dragging is None:
            (lx, ly), _hin, hout = sh.node(p, n - 1)
            cx, cy = self.cursor_w
            raw = ed.to_screen([lx, ly, hout[0], hout[1], cx, cy, cx, cy])
            c.create_line(*raw, fill=col, width=1, smooth="raw", splinesteps=16, dash=(4, 3))
        for i in range(n):
            (ax, ay), _hin, _hout = sh.node(p, i)
            sx, sy = ed.to_screen([ax, ay])
            big = 4.5 if i == 0 and n > 1 else 3.5
            c.create_rectangle(sx - big, sy - big, sx + big, sy + big,
                               fill=col if i == n - 1 else "#ffffff", outline=col)
        (ax, ay), hin, hout = sh.node(p, n - 1)
        for hx, hy in (hin, hout):
            if math.hypot(hx - ax, hy - ay) > 1e-6:
                sx, sy, hx2, hy2 = ed.to_screen([ax, ay, hx, hy])
                c.create_line(sx, sy, hx2, hy2, fill=col)
                c.create_oval(hx2 - 3, hy2 - 3, hx2 + 3, hy2 + 3, fill=col, outline=col)


def _anchor_hit(ed, x, y):
    """(shape, anchor index) under the screen point, top-most first."""
    for s in reversed(ed.doc.editable()):
        if s["type"] == "text":
            continue
        for i, (ax, ay) in enumerate(sh.anchors(s)):
            px, py = ed.to_screen([ax, ay])
            if abs(px - x) <= ANCHOR_HIT and abs(py - y) <= ANCHOR_HIT:
                return s, i
    return None


class _AnchorEditTool(Tool):
    """Shows anchors of the object under the cursor (or the selection)."""
    cursor = "crosshair"
    hover = True

    def overlay(self, r):
        ed, c = self.ed, r.c
        col = r.T["selection"]
        shapes = list(ed.selected_shapes())
        h = ed.doc.by_id(ed.hover_id) if ed.hover_id else None
        if h is not None and h not in shapes:
            shapes.append(h)
        for s in shapes:
            if s["type"] == "text":
                continue
            for ax, ay in sh.anchors(s):
                sx, sy = ed.to_screen([ax, ay])
                c.create_rectangle(sx - 3, sy - 3, sx + 3, sy + 3, fill="#ffffff", outline=col)

    def _as_path(self, s):
        if s["type"] != "path":
            sh.replace_in_place(s, sh.to_path(s))


class AddAnchorTool(_AnchorEditTool):
    key = "add_anchor"

    def press(self, e, wx, wy):
        ed = self.ed
        sid = ed.hit(e.x, e.y)
        s = ed.doc.by_id(sid) if sid else None
        if s is None or s["type"] == "text":
            return
        p = s if s["type"] == "path" else sh.to_path(s)
        res = pathops.nearest_on_path(p, wx, wy)
        if res and res[2] * ed.view.zoom <= 8:
            ed.push_undo()
            if p is not s:
                sh.replace_in_place(s, p)
            pathops.insert_node(s, res[0], res[1])
            ed.selected = {s["id"]}
            ed.on_selection_changed()
            ed.render()


class DeleteAnchorTool(_AnchorEditTool):
    key = "delete_anchor"

    def press(self, e, wx, wy):
        ed = self.ed
        hit = _anchor_hit(ed, e.x, e.y)
        if not hit:
            return
        s, i = hit
        ed.push_undo()
        self._as_path(s)
        if not pathops.delete_node(s, i):
            ed.doc.remove({s["id"]})
            ed.selected.discard(s["id"])
        ed.on_selection_changed()
        ed.render()


class AnchorPointTool(_AnchorEditTool):
    """Click a smooth anchor -> corner; drag from an anchor -> pull out new handles."""
    key = "anchor_point"

    def press(self, e, wx, wy):
        self.press_screen = (e.x, e.y)
        self.target = _anchor_hit(self.ed, e.x, e.y)
        self.changed = False

    def drag(self, e, wx, wy):
        if not self.target or not self.moved(e):
            return
        ed = self.ed
        s, i = self.target
        if not self.changed:
            ed.push_undo()
            self._as_path(s)
            self.changed = True
        pathops.set_symmetric_handles(s, i, wx, wy)
        ed.render()

    def release(self, e, wx, wy):
        if self.target and not self.changed:
            ed = self.ed
            s, i = self.target
            ed.push_undo()
            self._as_path(s)
            pathops.toggle_smooth(s, i)
            ed.selected = {s["id"]}
            ed.on_selection_changed()
            ed.render()
        self.target = None
