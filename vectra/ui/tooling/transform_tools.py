"""Rotate (R), Reflect (O) and Scale (S).

Click to set the reference point (default: centre of the selection), then drag.
Shift constrains (45° / uniform). Hold Alt when releasing to transform a copy.
Double-click the tool button for a dialog with exact values.
"""

import math

from vectra.model import geometry as geo
from vectra.model import shapes as sh
from vectra.ui.tooling.base import Tool, alt, shift, snap_angle


class _TransformTool(Tool):
    cursor = "crosshair"
    box = "plain"
    dialog = ""

    def __init__(self, ed):
        super().__init__(ed)
        self.pivot = None
        self._sel_sig = None

    def activate(self):
        self.pivot = None

    def current_pivot(self):
        ed = self.ed
        if self.pivot and self._sel_sig == frozenset(ed.selected):
            return self.pivot
        bb = ed.selection_bbox()
        return geo.bbox_center(bb) if bb else None

    def press(self, e, wx, wy):
        ed = self.ed
        self.press_screen = (e.x, e.y)
        self.press_w = (wx, wy)
        self.changed = False
        self.active = bool(ed.selected)
        if not self.active:
            return
        self.p = self.current_pivot()
        self.orig = ed.orig_shapes()
        self.boxes = {sid: ed.shape_bbox(s) for sid, s in self.orig.items()}
        ed.drag = {"mode": "transform", "orig": self.orig}

    def drag(self, e, wx, wy):
        ed = self.ed
        if not self.active or not self.moved(e):
            return
        fn = self.transform(e, wx, wy)
        if fn is None:
            return
        if not self.changed:
            ed.push_undo()
            self.changed = True
        ed.apply_from_orig(ed.drag, fn)
        ed.render()

    def release(self, e, wx, wy):
        ed = self.ed
        ed.drag = None
        if not self.active:
            return
        if not self.changed:
            self.pivot = self.snap_point(*self.press_w)
            self._sel_sig = frozenset(ed.selected)
            ed.guides.end()
            ed.render()
            return
        copy = alt(e)
        if copy:
            transformed = [dict(ed.doc.by_id(sid)) for sid in sorted(self.orig)]
            for sid, o in self.orig.items():
                sh.replace_in_place(ed.doc.by_id(sid), o)
            ed.selected = ed.doc.insert_copies(transformed, 0)
        ed.last_transform = self.record(copy)
        if self.pivot:
            self._sel_sig = frozenset(ed.selected)
        ed.on_selection_changed()
        ed.render()

    def overlay(self, r):
        p = self.current_pivot()
        if not p:
            return
        x, y = self.ed.to_screen(list(p))
        col = r.T["selection"]
        r.c.create_oval(x - 6, y - 6, x + 6, y + 6, outline=col, width=1.5)
        r.c.create_line(x - 10, y, x + 10, y, fill=col)
        r.c.create_line(x, y - 10, x, y + 10, fill=col)

    def _angle(self, x, y):
        return math.degrees(math.atan2(y - self.p[1], x - self.p[0]))


class RotateTool(_TransformTool):
    key = "rotate"
    dialog = "rotate"

    def transform(self, e, wx, wy):
        ang = self._angle(wx, wy) - self._angle(*self.press_w)
        if shift(e):
            ang = snap_angle(ang, 45)
        self.value = geo.normalize_angle(ang)
        px, py = self.p
        return lambda o: sh.rotated(o, self.value, px, py)

    def record(self, copy):
        return ("rotate", self.value, copy)


class ReflectTool(_TransformTool):
    key = "reflect"
    dialog = "reflect"

    def transform(self, e, wx, wy):
        axis = self._angle(wx, wy)
        if shift(e):
            axis = snap_angle(axis, 45)
        self.value = axis
        px, py = self.p
        return lambda o: sh.reflected(o, axis, px, py, self.boxes[o["id"]])

    def record(self, copy):
        return ("reflect", self.value, copy)


class ScaleTool(_TransformTool):
    key = "scale"
    dialog = "scale"

    def transform(self, e, wx, wy):
        px, py = self.p
        sx, sy = self.press_w
        if shift(e):
            d0 = math.hypot(sx - px, sy - py)
            k = math.hypot(wx - px, wy - py) / d0 if d0 > 1e-9 else 1.0
            kx = ky = k
        else:
            # an axis where the press was (almost) level with the origin stays unscaled
            min_d = 6 / self.ed.view.zoom
            kx = (wx - px) / (sx - px) if abs(sx - px) > min_d else 1.0
            ky = (wy - py) / (sy - py) if abs(sy - py) > min_d else 1.0
        if abs(kx) < 1e-3 or abs(ky) < 1e-3:
            return None
        self.value = (kx, ky)
        return lambda o: sh.scaled_about(o, kx, ky, px, py)

    def record(self, copy):
        return ("scale", self.value[0], self.value[1], copy)
