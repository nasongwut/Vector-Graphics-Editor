"""Shape tools: Rectangle (M), Rounded Rectangle, Ellipse (L), Polygon, Star,
Line Segment (\\), Arc, Spiral and Pencil (N).

Drag to draw · Shift constrains · Alt draws from the centre · a single click opens
a dialog to enter exact dimensions (like a pro vector app).
"""

import math

from vectra.config import STAR_INNER_RATIO
from vectra.i18n import tr
from vectra.model import geometry as geo
from vectra.model import shapes as sh
from vectra.ui.tooling.base import Tool, alt, shift


class _DragShape(Tool):
    cursor = "crosshair"
    shape_key = ""

    def press(self, e, wx, wy):
        ed = self.ed
        self.press_screen = (e.x, e.y)
        ed.guides.begin(exclude=())
        self.start = self.snap_point(wx, wy)
        self.alt = alt(e)
        self.last_event = e
        ed.temp = None
        ed.drag = {"mode": "draw"}

    def drag(self, e, wx, wy):
        if not self.ed.drag or not self.moved(e, 2):
            return
        self.cur = self.snap_point(wx, wy)
        self.last_event = e
        self.ed.temp = self.build(self.start, self.cur, shift(e), alt(e))
        self.ed.render()

    def release(self, e, wx, wy):
        ed = self.ed
        if not ed.drag:
            return
        ed.guides.end()
        ed.drag = None
        if ed.temp is None:
            shape = self.click_dialog(self.start, alt(e))
        else:
            shape = ed.temp
        ed.temp = None
        if shape is not None:
            ed.add_shape(shape)
            ed.on_selection_changed()
        ed.render()

    def rebuild(self):
        """Re-create the preview (used when ↑/↓ change the point count)."""
        if self.ed.drag and self.ed.temp is not None:
            e = self.last_event
            self.ed.temp = self.build(self.start, self.cur, shift(e), alt(e))
            self.ed.render()

    # subclasses
    def build(self, a, b, constrain, centred):
        raise NotImplementedError

    def click_dialog(self, at, centred):
        return None


# ── boxes ───────────────────────────────────────────────────────────────────
def _box(a, b, constrain, centred):
    (x0, y0), (x1, y1) = a, b
    if constrain:
        x1, y1 = geo.constrain_square(x0, y0, x1, y1)
    if centred:
        x0, y0 = 2 * x0 - x1, 2 * y0 - y1
    return [x0, y0, x1, y1]


class _BoxTool(_DragShape):
    shape_type = "rect"

    def style(self):
        return self.ed.current_style()

    def build(self, a, b, constrain, centred):
        return sh.make_shape(self.shape_type, _box(a, b, constrain, centred), self.style())

    def click_dialog(self, at, centred):
        res = self.ed.ask_form(tr("tool_" + self.key), [
            ("w", tr("width"), 100.0), ("h", tr("height"), 100.0)])
        if not res or res["w"] <= 0 or res["h"] <= 0:
            return None
        x, y = at
        if centred:
            x, y = x - res["w"] / 2, y - res["h"] / 2
        return sh.make_shape(self.shape_type, [x, y, x + res["w"], y + res["h"]], self.style())


class RectTool(_BoxTool):
    key = "rect"


class RoundedRectTool(_BoxTool):
    key = "rounded_rect"

    def style(self):
        st = self.ed.current_style()
        st["radius"] = self.ed.radius or 12
        return st


class EllipseTool(_BoxTool):
    key = "ellipse"
    shape_type = "ellipse"


# ── radial shapes ───────────────────────────────────────────────────────────
class _RadialTool(_DragShape):
    count_attr = ""
    count_min, count_max = 3, 50

    def angle(self, a, b, constrain):
        if constrain:
            return -90.0
        return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))

    def on_key(self, keysym):
        if keysym in ("Up", "Down") and self.ed.drag and self.count_attr:
            n = getattr(self.ed, self.count_attr) + (1 if keysym == "Up" else -1)
            setattr(self.ed, self.count_attr, max(self.count_min, min(self.count_max, n)))
            self.ed.flash(tr("flash_count", n=getattr(self.ed, self.count_attr)))
            self.rebuild()
            return True
        return False


class PolygonTool(_RadialTool):
    key = "polygon"
    count_attr = "polygon_sides"

    def build(self, a, b, constrain, centred):
        r = math.hypot(b[0] - a[0], b[1] - a[1])
        pts = geo.regular_polygon_points(a[0], a[1], r, self.ed.polygon_sides, self.angle(a, b, constrain))
        return sh.make_shape("polygon", pts, self.ed.current_style())

    def click_dialog(self, at, centred):
        res = self.ed.ask_form(tr("tool_polygon"), [
            ("r", tr("radius"), 50.0), ("n", tr("sides"), float(self.ed.polygon_sides))])
        if not res or res["r"] <= 0:
            return None
        self.ed.polygon_sides = max(3, min(50, int(res["n"])))
        pts = geo.regular_polygon_points(at[0], at[1], res["r"], self.ed.polygon_sides)
        return sh.make_shape("polygon", pts, self.ed.current_style())


class StarTool(_RadialTool):
    key = "star"
    count_attr = "star_points"

    def build(self, a, b, constrain, centred):
        r = math.hypot(b[0] - a[0], b[1] - a[1])
        pts = geo.star_points(a[0], a[1], r, r * STAR_INNER_RATIO, self.ed.star_points,
                              self.angle(a, b, constrain))
        return sh.make_shape("polygon", pts, self.ed.current_style())

    def click_dialog(self, at, centred):
        res = self.ed.ask_form(tr("tool_star"), [
            ("r1", tr("radius1"), 50.0), ("r2", tr("radius2"), 25.0),
            ("n", tr("points"), float(self.ed.star_points))])
        if not res or res["r1"] <= 0 or res["r2"] <= 0:
            return None
        self.ed.star_points = max(3, min(50, int(res["n"])))
        pts = geo.star_points(at[0], at[1], res["r1"], res["r2"], self.ed.star_points)
        return sh.make_shape("polygon", pts, self.ed.current_style())


class SpiralTool(_RadialTool):
    key = "spiral"

    def build(self, a, b, constrain, centred):
        r = math.hypot(b[0] - a[0], b[1] - a[1])
        pts = geo.spiral_points(a[0], a[1], r)
        pts = geo.rotate_pts(pts, a[0], a[1], self.angle(a, b, constrain) + 90)
        return sh.make_shape("pen", pts, self.ed.current_style())

    def click_dialog(self, at, centred):
        res = self.ed.ask_form(tr("tool_spiral"), [("r", tr("radius"), 50.0)])
        if not res or res["r"] <= 0:
            return None
        return sh.make_shape("pen", geo.spiral_points(at[0], at[1], res["r"]), self.ed.current_style())


# ── lines ───────────────────────────────────────────────────────────────────
class LineTool(_DragShape):
    key = "line"

    def build(self, a, b, constrain, centred):
        (x0, y0), (x1, y1) = a, b
        if constrain:
            x1, y1 = geo.constrain_45(x0, y0, x1, y1)
        if centred:
            x0, y0 = 2 * x0 - x1, 2 * y0 - y1
        return sh.make_shape("line", [x0, y0, x1, y1], self.ed.current_style())

    def click_dialog(self, at, centred):
        res = self.ed.ask_form(tr("tool_line"), [("len", tr("length"), 100.0), ("ang", tr("angle"), 0.0)])
        if not res or res["len"] <= 0:
            return None
        a = math.radians(-res["ang"])
        x1, y1 = at[0] + res["len"] * math.cos(a), at[1] + res["len"] * math.sin(a)
        return sh.make_shape("line", [at[0], at[1], x1, y1], self.ed.current_style())


class ArcTool(_DragShape):
    key = "arc"

    def build(self, a, b, constrain, centred):
        (x0, y0), (x1, y1) = a, b
        if constrain:
            x1, y1 = geo.constrain_square(x0, y0, x1, y1)
        k = geo.KAPPA
        c1 = (x0, y0 + k * (y1 - y0))
        c2 = (x1 - k * (x1 - x0), y1)
        style = dict(self.ed.current_style())
        s = sh.make_path([x0, y0, x1, y1], [x0, y0, c1[0], c1[1], c2[0], c2[1], x1, y1],
                         [False, False], False, style)
        s["fill"] = None
        if not s.get("stroke"):
            s["stroke"] = style["fill"] or "#000000"
        s["width"] = max(1, s.get("width") or 1)
        return s


# ── freehand ────────────────────────────────────────────────────────────────
class PencilTool(Tool):
    key = "pencil"
    cursor = "pencil"

    def press(self, e, wx, wy):
        self.ed.temp = self.ed.new_shape("pen", [wx, wy])
        self.ed.drag = {"mode": "pen"}

    def drag(self, e, wx, wy):
        t = self.ed.temp
        if not t:
            return
        lx, ly = t["pts"][-2:]
        if math.hypot(wx - lx, wy - ly) * self.ed.view.zoom > 2:
            t["pts"] += [wx, wy]
            self.ed.render()

    def release(self, e, wx, wy):
        ed = self.ed
        t, ed.temp, ed.drag = ed.temp, None, None
        if t and len(t["pts"]) >= 4:
            ed.add_shape(t)
            ed.on_selection_changed()
        ed.render()
