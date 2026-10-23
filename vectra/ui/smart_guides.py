"""Smart Guides: snap to edges / centres of other objects and the artboard.

Candidates are collected once when a drag starts (``begin``); ``lines`` holds the
magenta guide lines for the renderer and is cleared by ``end``.
"""

from vectra.model import shapes as sh

TOLERANCE_PX = 5


class SmartGuides:
    def __init__(self, ed):
        self.ed = ed
        self.xs, self.ys = [], []
        self.lines = []
        self.active = False

    @property
    def enabled(self):
        return self.ed.smart_guides

    def begin(self, exclude=()):
        ed = self.ed
        self.xs, self.ys = [], []
        boxes = [tuple(ed.doc.artboard)]
        for s in ed.doc.shapes:
            if s["id"] in exclude or not ed.doc.shape_visible(s):
                continue
            boxes.append(ed.shape_bbox(s))
            if s["type"] != "text":
                for ax, ay in sh.anchors(s)[:64]:
                    self.xs.append((ax, ay, ay))
                    self.ys.append((ay, ax, ax))
        for b in boxes:
            for x in (b[0], (b[0] + b[2]) / 2, b[2]):
                self.xs.append((x, b[1], b[3]))
            for y in (b[1], (b[1] + b[3]) / 2, b[3]):
                self.ys.append((y, b[0], b[2]))
        self.active = True
        self.lines = []

    def end(self):
        self.active = False
        self.lines = []

    def _tol(self):
        return TOLERANCE_PX / self.ed.view.zoom

    def _best(self, values, cands):
        """Smallest correction that brings one of ``values`` onto a candidate."""
        tol = self._tol()
        best = None
        for v in values:
            for c, a, b in cands:
                d = c - v
                if abs(d) <= tol and (best is None or abs(d) < abs(best[0])):
                    best = (d, c, a, b)
        return best

    def snap_box(self, box):
        """Returns (dx, dy) to apply so the box aligns; records guide lines."""
        self.lines = []
        if not (self.enabled and self.active):
            return 0.0, 0.0
        x0, y0, x1, y1 = box
        bx = self._best((x0, (x0 + x1) / 2, x1), self.xs)
        by = self._best((y0, (y0 + y1) / 2, y1), self.ys)
        dx = bx[0] if bx else 0.0
        dy = by[0] if by else 0.0
        if bx:
            self.lines.append(("v", bx[1], min(bx[2], y0 + dy), max(bx[3], y1 + dy)))
        if by:
            self.lines.append(("h", by[1], min(by[2], x0 + dx), max(by[3], x1 + dx)))
        return dx, dy

    def snap_point(self, x, y):
        self.lines = []
        if not self.enabled:
            return x, y
        if not self.active:
            self.begin(exclude=())
        bx = self._best((x,), self.xs)
        by = self._best((y,), self.ys)
        if bx:
            x = bx[1]
        if by:
            y = by[1]
        if bx:
            self.lines.append(("v", x, min(bx[2], y), max(bx[3], y)))
        if by:
            self.lines.append(("h", y, min(by[2], x), max(by[3], x)))
        return x, y
