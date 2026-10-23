"""Type (T), Scissors (C), Artboard (Shift+O), Eyedropper (I), Measure, Magic Wand (Y),
Lasso (Q), Hand (H) and Zoom (Z)."""

import math

from vectra.i18n import tr
from vectra.model import geometry as geo
from vectra.model import pathops
from vectra.model import shapes as sh
from vectra.ui.tooling.base import Tool, alt, shift

CUT_HIT = 7


class TypeTool(Tool):
    key = "type"
    cursor = "xterm"
    hover = True

    def press(self, e, wx, wy):
        ed = self.ed
        sid = ed.hit(e.x, e.y)
        s = ed.doc.by_id(sid) if sid else None
        if s is not None and s["type"] == "text":
            ed.edit_text(s)
        else:
            x, y = self.snap_point(wx, wy)
            ed.guides.end()
            ed.new_text_at(x, y - ed.font_size * 0.8)


class ScissorsTool(Tool):
    key = "scissors"
    cursor = "crosshair"
    hover = True

    def press(self, e, wx, wy):
        ed = self.ed
        best = None
        for s in reversed(ed.doc.editable()):
            if s["type"] == "text":
                continue
            p = s if s["type"] == "path" else sh.to_path(s)
            res = pathops.nearest_on_path(p, wx, wy)
            if res and res[2] * ed.view.zoom <= CUT_HIT and (best is None or res[2] < best[2][2]):
                best = (s, p, res)
        if not best:
            return
        s, p, (seg, t, _d, _x, _y) = best
        pieces = pathops.split_at(p, seg, t)
        if not pieces:
            ed.flash(tr("compound_no_cut"))
            return
        ed.push_undo()
        sid = s["id"]
        first = dict(pieces[0], id=sid)
        sh.replace_in_place(s, first)
        new_ids = {sid}
        if len(pieces) > 1:
            new_ids |= ed.doc.insert_copies(pieces[1:], 0, index=ed.doc.index_of(sid) + 1)
        ed.selected = new_ids
        ed.on_selection_changed()
        ed.render()


class ArtboardTool(Tool):
    key = "artboard"
    cursor = "arrow"

    def _handle_at(self, x, y):
        ab = self.ed.to_screen(list(self.ed.doc.artboard))
        for i, (hx, hy) in enumerate(geo.handle_points(*ab)):
            if abs(hx - x) <= 7 and abs(hy - y) <= 7:
                return i
        if ab[0] <= x <= ab[2] and ab[1] <= y <= ab[3]:
            return "move"
        return None

    def motion(self, e, wx, wy):
        h = self._handle_at(e.x, e.y)
        self.ed.canvas.config(cursor="sizing" if isinstance(h, int) else ("fleur" if h else "arrow"))

    def press(self, e, wx, wy):
        self.mode = self._handle_at(e.x, e.y)
        self.start = (wx, wy)
        self.orig = list(self.ed.doc.artboard)
        self.changed = False

    def drag(self, e, wx, wy):
        ed = self.ed
        if self.mode is None:
            return
        if not self.changed:
            ed.push_undo()
            self.changed = True
        if self.mode == "move":
            dx, dy = ed.snapv(wx - self.start[0]), ed.snapv(wy - self.start[1])
            o = self.orig
            ed.doc.artboard = [o[0] + dx, o[1] + dy, o[2] + dx, o[3] + dy]
        else:
            nb = geo.resize_bbox(self.orig, self.mode, ed.snapv(wx), ed.snapv(wy), shift(e))
            x0, x1 = sorted((nb[0], nb[2]))
            y0, y1 = sorted((nb[1], nb[3]))
            if x1 - x0 >= 10 and y1 - y0 >= 10:
                ed.doc.artboard = [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]
        ed.render()

    def release(self, e, wx, wy):
        self.mode = None
        self.ed.on_selection_changed()
        self.ed.render()

    def on_key(self, keysym):
        if keysym == "Return":
            self.ed.document_setup()
            return True
        return False

    def overlay(self, r):
        ed, c = self.ed, r.c
        col = r.T["selection"]
        ab = ed.to_screen(list(ed.doc.artboard))
        c.create_rectangle(*ab, outline=col, width=2)
        for hx, hy in geo.handle_points(*ab):
            c.create_rectangle(hx - 4, hy - 4, hx + 4, hy + 4, fill="#ffffff", outline=col, width=1.5)
        w, h = ed.doc.artboard[2] - ed.doc.artboard[0], ed.doc.artboard[3] - ed.doc.artboard[1]
        r.pill((ab[0] + ab[2]) / 2, ab[3] + 18, f"{w:.0f} × {h:.0f}")


class EyedropperTool(Tool):
    key = "eyedropper"
    cursor = "tcross"
    hover = True

    def press(self, e, wx, wy):
        sid = self.ed.hit(e.x, e.y)
        if sid:
            self.ed.copy_appearance(self.ed.doc.by_id(sid))


class MeasureTool(Tool):
    key = "measure"
    cursor = "crosshair"

    def __init__(self, ed):
        super().__init__(ed)
        self.a = self.b = None

    def activate(self):
        self.a = self.b = None

    def press(self, e, wx, wy):
        self.a = self.b = self.snap_point(wx, wy)
        self.ed.guides.end()

    def drag(self, e, wx, wy):
        self.b = self.snap_point(wx, wy)
        self.ed.guides.end()
        self.ed.render()

    def info(self):
        (x0, y0), (x1, y1) = self.a, self.b
        d = math.hypot(x1 - x0, y1 - y0)
        ang = -math.degrees(math.atan2(y1 - y0, x1 - x0))
        return tr("measure_info", d=d, w=x1 - x0, h=y1 - y0, a=ang)

    def release(self, e, wx, wy):
        if self.a and self.b:
            self.ed.flash(self.info(), ms=6000)
        self.ed.render()

    def overlay(self, r):
        if not self.a or not self.b or self.a == self.b:
            return
        x0, y0, x1, y1 = self.ed.to_screen([*self.a, *self.b])
        col = r.T["smart"]
        r.c.create_line(x0, y0, x1, y1, fill=col, width=1.5, arrow="both", arrowshape=(8, 9, 3))
        (ax, ay), (bx, by) = self.a, self.b
        r.pill((x0 + x1) / 2, (y0 + y1) / 2 - 16, f"{math.hypot(bx - ax, by - ay):.1f} px")


class MagicWandTool(Tool):
    key = "magic_wand"
    cursor = "tcross"
    hover = True

    def press(self, e, wx, wy):
        ed = self.ed
        sid = ed.hit(e.x, e.y)
        if not sid:
            if not shift(e):
                ed.selected = set()
        else:
            ref = ed.doc.by_id(sid)
            attr = "fill" if ref.get("fill") else "stroke"
            val = ref.get(attr)
            same = {s["id"] for s in ed.doc.editable() if s.get(attr) == val}
            ed.selected = (ed.selected | same) if shift(e) else same
            if alt(e):
                ed.selected -= same
        ed.on_selection_changed()
        ed.render()


class LassoTool(Tool):
    key = "lasso"
    cursor = "crosshair"

    def __init__(self, ed):
        super().__init__(ed)
        self.pts = []

    def press(self, e, wx, wy):
        self.pts = [e.x, e.y]
        self.add = shift(e)

    def drag(self, e, wx, wy):
        if self.pts and math.hypot(e.x - self.pts[-2], e.y - self.pts[-1]) > 3:
            self.pts += [e.x, e.y]
            self.ed.render()

    def release(self, e, wx, wy):
        ed = self.ed
        if len(self.pts) >= 6:
            poly = []
            for i in range(0, len(self.pts), 2):
                poly += ed.to_world(self.pts[i], self.pts[i + 1])
            hits = set()
            for s in ed.doc.editable():
                if s["type"] == "text":
                    cx, cy = geo.bbox_center(ed.shape_bbox(s))
                    pts = [(cx, cy)]
                else:
                    pts = sh.anchors(s)
                if any(geo.point_in_polygon(x, y, poly) for x, y in pts):
                    hits.add(s["id"])
            ed.selected = (ed.selected | hits) if self.add else hits
        elif not self.add:
            ed.selected = set()
        self.pts = []
        ed.on_selection_changed()
        ed.render()

    def overlay(self, r):
        if len(self.pts) >= 4:
            r.c.create_line(*self.pts, fill=r.T["selection"], dash=(3, 2))


class HandTool(Tool):
    key = "hand"
    cursor = "fleur"

    def press(self, e, wx, wy):
        self.ed.pan_start(e)

    def drag(self, e, wx, wy):
        self.ed.pan_move(e)

    def release(self, e, wx, wy):
        self.ed.end_pan()


class ZoomTool(Tool):
    key = "zoom"
    cursor = "plus"

    def press(self, e, wx, wy):
        self.press_screen = (e.x, e.y)
        self.ed.drag = {"mode": "marquee", "start": (e.x, e.y), "cur": (e.x, e.y)}

    def drag(self, e, wx, wy):
        if self.ed.drag:
            self.ed.drag["cur"] = (e.x, e.y)
            self.ed.render()

    def release(self, e, wx, wy):
        ed = self.ed
        d, ed.drag = ed.drag, None
        if d and self.moved(e, 6) and not alt(e):
            (sx, sy), (ex, ey) = d["start"], d["cur"]
            x0, y0 = ed.to_world(min(sx, ex), min(sy, ey))
            x1, y1 = ed.to_world(max(sx, ex), max(sy, ey))
            ed.zoom_to_rect((x0, y0, x1, y1), margin=0)
        else:
            ed.zoom_at(1 / 2 if alt(e) else 2, e.x, e.y)

    def overlay(self, r):
        r.draw_marquee()
