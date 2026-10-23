"""Selection (V) and Direct Selection (A)."""

import math

from vectra.config import GRID
from vectra.model import geometry as geo
from vectra.model import pathops
from vectra.model import shapes as sh
from vectra.ui.tooling.base import Tool, alt, shift, snap_angle

ROTATE = "rotate"
ANCHOR_HIT = 6
HANDLE_HIT = 6


# ── shared: moving whole objects ────────────────────────────────────────────
def start_move(ed, wx, wy, copy):
    ed.drag = {"mode": "move", "start": (wx, wy), "orig": ed.orig_shapes(), "changed": False,
               "copy": copy, "bbox": ed.selection_bbox(), "dx": 0.0, "dy": 0.0}
    ed.guides.begin(exclude=ed.selected)


def drag_move(ed, e, wx, wy):
    d = ed.drag
    dx, dy = wx - d["start"][0], wy - d["start"][1]
    if ed.snap:
        dx, dy = round(dx / GRID) * GRID, round(dy / GRID) * GRID
    if shift(e):  # constrain to 45° directions
        ang = snap_angle(math.degrees(math.atan2(dy, dx)), 45)
        ln = math.hypot(dx, dy)
        dx, dy = ln * math.cos(math.radians(ang)), ln * math.sin(math.radians(ang))
    elif d["bbox"]:
        b = d["bbox"]
        gx, gy = ed.guides.snap_box((b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy))
        dx, dy = dx + gx, dy + gy
    if (dx or dy) and not d["changed"]:
        ed.push_undo()
        d["changed"] = True
        if d["copy"]:
            new_ids = ed.doc.insert_copies([d["orig"][k] for k in sorted(d["orig"])], 0)
            ed.selected = new_ids
            d["orig"] = ed.orig_shapes()
    if d["changed"]:
        for sid, orig in d["orig"].items():
            s = ed.doc.by_id(sid)
            if s is not None:
                s["pts"] = geo.translate_pts(orig["pts"], dx, dy)
                if "ctrl" in orig:
                    s["ctrl"] = geo.translate_pts(orig["ctrl"], dx, dy)
    d["dx"], d["dy"] = dx, dy


def finish_move(ed):
    d = ed.drag
    if d["changed"]:
        ed.last_transform = ("move", d["dx"], d["dy"], d["copy"])


def marquee_rect(ed, d):
    (sx, sy), (ex, ey) = d["start"], d["cur"]
    if abs(ex - sx) <= 2 and abs(ey - sy) <= 2:
        return None
    x0, y0 = ed.to_world(min(sx, ex), min(sy, ey))
    x1, y1 = ed.to_world(max(sx, ex), max(sy, ey))
    return x0, y0, x1, y1


# ── Selection tool ──────────────────────────────────────────────────────────
class SelectTool(Tool):
    key = "select"
    cursor = "arrow"
    box = "full"
    hover = True

    def press(self, e, wx, wy):
        ed = self.ed
        self.press_screen = (e.x, e.y)
        h = ed.handle_at(e.x, e.y)
        if h == ROTATE:
            cx, cy = geo.bbox_center(ed.selection_bbox())
            ed.drag = {"mode": "rotate", "center": (cx, cy), "angle": 0.0,
                       "start": math.degrees(math.atan2(wy - cy, wx - cx)),
                       "orig": ed.orig_shapes(), "changed": False}
            return
        if h is not None:
            ed.drag = {"mode": "resize", "h": h, "bbox": ed.selection_bbox(), "nb": None,
                       "orig": ed.orig_shapes(), "changed": False}
            return
        sid = ed.hit(e.x, e.y)
        if sid:
            ids = ed.doc.expand_groups({sid})
            if shift(e):
                if sid in ed.selected:
                    ed.selected -= ids
                else:
                    ed.selected |= ids
            elif sid not in ed.selected:
                ed.selected = ids
            start_move(ed, wx, wy, copy=alt(e))
        else:
            if not shift(e):
                ed.selected = set()
            ed.drag = {"mode": "marquee", "start": (e.x, e.y), "cur": (e.x, e.y),
                       "base": set(ed.selected)}
        ed.on_selection_changed()
        ed.render()

    def drag(self, e, wx, wy):
        ed, d = self.ed, self.ed.drag
        if not d:
            return
        mode = d["mode"]
        if mode == "move":
            drag_move(ed, e, wx, wy)
        elif mode == "resize":
            nb = geo.resize_bbox(d["bbox"], d["h"], ed.snapv(wx), ed.snapv(wy), shift(e))
            if alt(e):  # scale from the centre
                cx, cy = geo.bbox_center(d["bbox"])
                w2 = max(abs(nb[2] - cx), abs(nb[0] - cx)) if d["h"] not in (1, 5) else (d["bbox"][2] - d["bbox"][0]) / 2
                h2 = max(abs(nb[3] - cy), abs(nb[1] - cy)) if d["h"] not in (3, 7) else (d["bbox"][3] - d["bbox"][1]) / 2
                nb = (cx - w2, cy - h2, cx + w2, cy + h2)
            if not d["changed"]:
                ed.push_undo()
                d["changed"] = True
            d["nb"] = nb
            ed.apply_from_orig(d, lambda o: sh.scaled(o, d["bbox"], nb))
        elif mode == "rotate":
            cx, cy = d["center"]
            ang = math.degrees(math.atan2(wy - cy, wx - cx)) - d["start"]
            if shift(e):
                ang = snap_angle(ang, 45)
            ang = geo.normalize_angle(ang)
            d["angle"] = ang
            if ang and not d["changed"]:
                ed.push_undo()
                d["changed"] = True
            ed.apply_from_orig(d, lambda o: sh.rotated(o, ang, cx, cy))
        elif mode == "marquee":
            d["cur"] = (e.x, e.y)
        ed.render()

    def release(self, e, wx, wy):
        ed, d = self.ed, self.ed.drag
        if not d:
            return
        mode = d["mode"]
        if mode == "marquee":
            rect = marquee_rect(ed, d)
            if rect:
                x0, y0, x1, y1 = rect
                hits = set()
                for s in ed.doc.editable():
                    b = ed.shape_bbox(s)
                    if b[0] <= x1 and b[2] >= x0 and b[1] <= y1 and b[3] >= y0:
                        hits.add(s["id"])
                ed.selected = d["base"] | ed.doc.expand_groups(hits)
        elif mode == "move":
            finish_move(ed)
        elif mode == "resize" and d["changed"] and d["nb"]:
            kx, ky = geo.scale_factors(d["bbox"], d["nb"])
            ed.last_transform = ("scale", kx, ky, False)
        elif mode == "rotate" and d["changed"]:
            ed.last_transform = ("rotate", d["angle"], False)
        ed.guides.end()
        ed.drag = None
        ed.on_selection_changed()
        ed.render()

    def double(self, e, wx, wy):
        ed = self.ed
        sid = ed.hit(e.x, e.y)
        s = ed.doc.by_id(sid) if sid else None
        if s and s["type"] == "text":
            ed.drag = None
            ed.edit_text(s)
            return True
        return False

    def on_key(self, keysym):
        if keysym == "Return" and self.ed.selected:
            self.ed.open_transform_dialog("move")
            return True
        return False


# ── Direct Selection tool ───────────────────────────────────────────────────
class DirectSelectTool(Tool):
    key = "direct"
    cursor = "arrow"
    hover = True

    def __init__(self, ed):
        super().__init__(ed)
        self.nodes = set()  # {(shape id, anchor index)}

    def activate(self):
        self.nodes = set()

    def _valid_nodes(self):
        out = set()
        for sid, i in self.nodes:
            s = self.ed.doc.by_id(sid)
            if s is not None and sid in self.ed.selected and i < len(sh.anchors(s)):
                out.add((sid, i))
        self.nodes = out
        return out

    def _handle_hits(self):
        """Visible handles: (sid, i, 'in'|'out', x, y) for selected anchors on paths."""
        out = []
        for sid, i in self._valid_nodes():
            s = self.ed.doc.by_id(sid)
            if s["type"] != "path":
                continue
            (ax, ay), hin, hout = sh.node(s, i)
            for which, (hx, hy) in (("in", hin), ("out", hout)):
                if math.hypot(hx - ax, hy - ay) > 1e-6:
                    out.append((sid, i, which, hx, hy))
        return out

    def _anchor_at(self, x, y):
        ed = self.ed
        cands = list(reversed(ed.selected_shapes()))
        hov = ed.doc.by_id(ed.hit(x, y)) if ed.hit(x, y) else None
        if hov is not None and hov not in cands:
            cands.append(hov)
        for s in cands:
            for i, (ax, ay) in enumerate(sh.anchors(s)):
                px, py = ed.to_screen([ax, ay])
                if abs(px - x) <= ANCHOR_HIT and abs(py - y) <= ANCHOR_HIT:
                    return s["id"], i
        return None

    def anchor_under(self, x, y):
        return self._anchor_at(x, y) is not None

    def press(self, e, wx, wy):
        ed = self.ed
        self.press_screen = (e.x, e.y)
        for sid, i, which, hx, hy in self._handle_hits():
            px, py = ed.to_screen([hx, hy])
            if abs(px - e.x) <= HANDLE_HIT and abs(py - e.y) <= HANDLE_HIT:
                ed.drag = {"mode": "handle", "sid": sid, "i": i, "which": which, "changed": False}
                return
        a = self._anchor_at(e.x, e.y)
        if a:
            if shift(e):
                self.nodes ^= {a}
            elif a not in self.nodes:
                self.nodes = {a}
            if shift(e):
                ed.selected |= {sid for sid, _ in self.nodes} | {a[0]}
            else:
                ed.selected = {sid for sid, _ in self.nodes} or {a[0]}
            orig = {}
            for sid, i in self.nodes:
                s = ed.doc.by_id(sid)
                orig[(sid, i)] = sh.anchors(s)[i]
            ed.drag = {"mode": "nodes", "start": (wx, wy), "orig": orig, "changed": False,
                       "primary": a}
            ed.guides.begin(exclude=ed.selected)
        else:
            sid = ed.hit(e.x, e.y)
            self.nodes = set()
            if sid:
                if shift(e):
                    ed.selected ^= {sid}
                elif sid not in ed.selected:
                    ed.selected = {sid}
                start_move(ed, wx, wy, copy=alt(e))
            else:
                ed.drag = {"mode": "marquee", "start": (e.x, e.y), "cur": (e.x, e.y),
                           "base": set(ed.selected) if shift(e) else set(),
                           "base_nodes": set(self.nodes) if shift(e) else set()}
                if not shift(e):
                    ed.selected = set()
        ed.on_selection_changed()
        ed.render()

    def _convert(self, s):
        if s["type"] not in ("path", "text"):
            sh.replace_in_place(s, sh.to_path(s))

    def drag(self, e, wx, wy):
        ed, d = self.ed, self.ed.drag
        if not d:
            return
        mode = d["mode"]
        if mode == "nodes":
            px, py = d["orig"][d["primary"]]
            nx, ny = self.snap_point(px + wx - d["start"][0], py + wy - d["start"][1])
            dx, dy = nx - px, ny - py
            if shift(e):
                if abs(dx) > abs(dy):
                    dy = 0
                else:
                    dx = 0
            if (dx or dy) and not d["changed"]:
                ed.push_undo()
                d["changed"] = True
                for sid in {sid for sid, _ in d["orig"]}:
                    self._convert(ed.doc.by_id(sid))
            if d["changed"]:
                for (sid, i), (ox, oy) in d["orig"].items():
                    pathops.move_node(ed.doc.by_id(sid), i, ox + dx, oy + dy)
        elif mode == "handle":
            if not d["changed"]:
                ed.push_undo()
                d["changed"] = True
            pathops.move_handle(ed.doc.by_id(d["sid"]), d["i"], d["which"], wx, wy, mirror=not alt(e))
        elif mode == "move":
            drag_move(ed, e, wx, wy)
        elif mode == "marquee":
            d["cur"] = (e.x, e.y)
        ed.render()

    def release(self, e, wx, wy):
        ed, d = self.ed, self.ed.drag
        if not d:
            return
        if d["mode"] == "marquee":
            rect = marquee_rect(ed, d)
            if rect:
                x0, y0, x1, y1 = rect
                nodes, shapes_hit = set(d["base_nodes"]), set(d["base"])
                for s in ed.doc.editable():
                    pts = sh.anchors(s)
                    inside = [i for i, (ax, ay) in enumerate(pts) if x0 <= ax <= x1 and y0 <= ay <= y1]
                    if inside:
                        nodes |= {(s["id"], i) for i in inside}
                        shapes_hit.add(s["id"])
                    elif s["type"] == "text":
                        b = ed.shape_bbox(s)
                        if b[0] <= x1 and b[2] >= x0 and b[1] <= y1 and b[3] >= y0:
                            shapes_hit.add(s["id"])
                self.nodes = nodes
                ed.selected = shapes_hit
        elif d["mode"] == "move":
            finish_move(ed)
        ed.guides.end()
        ed.drag = None
        ed.on_selection_changed()
        ed.render()

    def double(self, e, wx, wy):
        """Double-click on a segment adds an anchor there."""
        ed = self.ed
        ed.drag = None
        for s in reversed(ed.selected_shapes()):
            if s["type"] == "text":
                continue
            p = s if s["type"] == "path" else sh.to_path(s)
            res = pathops.nearest_on_path(p, wx, wy)
            if res and res[2] * ed.view.zoom <= 6:
                ed.push_undo()
                if p is not s:
                    sh.replace_in_place(s, p)
                idx = pathops.insert_node(s, res[0], res[1])
                self.nodes = {(s["id"], idx)}
                ed.render()
                return True
        return False

    def on_key(self, keysym):
        ed = self.ed
        nodes = self._valid_nodes()
        if keysym in ("Delete", "BackSpace") and nodes:
            ed.push_undo()
            remove = set()
            for sid, i in sorted(nodes, key=lambda n: -n[1]):
                s = ed.doc.by_id(sid)
                if s is None or sid in remove or s["type"] == "text":
                    continue
                self._convert(s)
                if not pathops.delete_node(s, i):
                    remove.add(sid)
            if remove:
                ed.doc.remove(remove)
                ed.selected -= remove
            self.nodes = set()
            ed.on_selection_changed()
            ed.render()
            return True
        arrows = {"Left": (-1, 0), "Right": (1, 0), "Up": (0, -1), "Down": (0, 1)}
        if keysym.split("+")[-1] in arrows and nodes:
            dx, dy = arrows[keysym.split("+")[-1]]
            k = 10 if keysym.startswith("Shift+") else 1
            ed.push_undo("nudge-nodes")
            for sid, i in nodes:
                s = ed.doc.by_id(sid)
                ax, ay = sh.anchors(s)[i]
                self._convert(s)
                pathops.move_node(s, i, ax + dx * k, ay + dy * k)
            ed.render()
            return True
        if keysym == "Escape":
            self.nodes = set()
        return False

    def overlay(self, r):
        ed, c = self.ed, r.c
        col = r.T["selection"]
        nodes = self._valid_nodes()
        for s in ed.selected_shapes():
            col = ed.sel_color(s)
            if s["type"] == "text":
                b = ed.to_screen(list(ed.shape_bbox(s)))
                c.create_rectangle(*b, outline=col, dash=(3, 3))
                continue
            p = s if s["type"] == "path" else sh.to_path(s)
            for part in sh.raw_parts(p):
                raw = ed.to_screen(part)
                if len(raw) >= 8:
                    c.create_line(*raw, fill=col, width=1, smooth="raw", splinesteps=16)
            for i, (ax, ay) in enumerate(sh.anchors(s)):
                sx, sy = ed.to_screen([ax, ay])
                on = (s["id"], i) in nodes
                c.create_rectangle(sx - 3.5, sy - 3.5, sx + 3.5, sy + 3.5,
                                   fill=col if on else "#ffffff", outline=col, width=1.2)
        for sid, i, _which, hx, hy in self._handle_hits():
            s = ed.doc.by_id(sid)
            ax, ay = sh.node(s, i)[0]
            sx, sy, hx2, hy2 = ed.to_screen([ax, ay, hx, hy])
            c.create_line(sx, sy, hx2, hy2, fill=col)
            c.create_oval(hx2 - 3, hy2 - 3, hx2 + 3, hy2 + 3, fill=col, outline=col)
        r.draw_marquee()
