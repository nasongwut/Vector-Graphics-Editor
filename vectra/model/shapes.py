"""Shape records.

A shape is a plain JSON-serialisable dict so documents save/undo trivially::

    {"id": 3, "type": "rect", "pts": [x0, y0, x1, y1],
     "fill": "#7c5cff", "stroke": "#0f172a", "width": 2,
     # optional keys (absent = default, see DEFAULTS)
     "rot": 0, "radius": 0, "dash": False, "hidden": False, "locked": False,
     "gid": None, "name": "", "size": 32, "text": "...", "font": "Inter"}

Geometry by type
  rect / ellipse  pts = two opposite corners of the *unrotated* box, ``rot`` turns
                  it around its centre (live shape, like Illustrator).
  line / polygon / pen (pencil)
                  pts = the points; rotation is baked into the points and
                  ``rot`` only records the accumulated angle for the UI.
  path            Bézier path drawn with the Pen tool.
                  pts    = anchors [x0, y0, x1, y1, ...]
                  ctrl   = handles per anchor [in_x, in_y, out_x, out_y, ...]
                           (a corner without handles has both equal to the anchor)
                  smooth = [bool, ...] per anchor, closed = bool
                  parts  = [[n_anchors, closed], ...]  (optional: compound path —
                           several sub-paths drawn as one shape, holes even-odd)
  text            pts = top-left anchor; ``rot`` turns around that anchor.
"""

import copy
import math

from vectra.i18n import tr
from vectra.model import geometry as g

SHAPE_TYPES = ("rect", "ellipse", "line", "polygon", "pen", "path", "text")
POINT_TYPES = ("line", "polygon", "pen", "path")   # geometry == the point list
STROKE_ONLY = ("line", "pen")                       # never filled
BOX_TYPES = ("rect", "ellipse")

DEFAULTS = {"rot": 0.0, "radius": 0, "dash": False, "hidden": False, "locked": False,
            "gid": None, "name": "", "size": 24, "text": "", "width": 0,
            "fill": None, "stroke": None, "closed": False, "font": None}


def prop(s, key):
    return s.get(key, DEFAULTS.get(key))


def type_label(typ):
    return tr("type_" + typ)


def display_name(s):
    if s.get("name"):
        return s["name"]
    label = type_label(s["type"])
    if s["type"] == "text":
        t = s.get("text", "").replace("\n", " ")
        label += f' "{t[:14]}{"…" if len(t) > 14 else ""}"'
    return label


def font_spec(s, family, size):
    """Tk font tuple for a text shape, including bold / italic."""
    style = " ".join(v for v in (s.get("weight"), s.get("slant")) if v)
    return (family, size, style) if style else (family, size)


def group_path(s):
    """Nested group ids, outermost first ([] when not grouped)."""
    if s.get("gid") is None:
        return []
    return list(s.get("gpath") or [s["gid"]])


def replace_in_place(s, new):
    """Swap the contents of shape dict ``s`` for ``new`` (keeps object identity)."""
    s.clear()
    s.update(new)


# ── creation ────────────────────────────────────────────────────────────────
def make_shape(typ, pts, style):
    """Create a new (id-less) shape using the current style dict."""
    s = {"id": 0, "type": typ, "pts": list(pts), "fill": style["fill"],
         "stroke": style["stroke"], "width": style["width"]}
    if typ in STROKE_ONLY:
        s["fill"] = None
        s["stroke"] = style["stroke"] or style["fill"] or "#000000"
        s["width"] = max(1, style["width"])
    if typ == "text":
        s["fill"] = style["fill"] or style["stroke"] or "#000000"
        s["stroke"] = None
        s["width"] = 0
        s["size"] = style["font_size"]
        s["text"] = ""
        if style.get("font"):
            s["font"] = style["font"]
    else:
        if style.get("dash"):
            s["dash"] = True
    if typ == "rect" and style.get("radius"):
        s["radius"] = style["radius"]
    if typ == "path":
        n = len(pts) // 2
        s["ctrl"] = [v for i in range(n) for v in (pts[2 * i], pts[2 * i + 1]) * 2]
        s["smooth"] = [False] * n
        s["closed"] = False
    return s


def make_path(pts, ctrl, smooth, closed, style, parts=None):
    s = make_shape("path", pts, style)
    s["ctrl"], s["smooth"], s["closed"] = list(ctrl), list(smooth), bool(closed)
    if parts and len(parts) > 1:
        s["parts"] = [[int(n), bool(c)] for n, c in parts]
    return s


# ── path helpers ────────────────────────────────────────────────────────────
def node_count(s):
    return len(s["pts"]) // 2


def node(s, i):
    """(anchor, in_handle, out_handle) of a path node as point tuples."""
    p, c = s["pts"], s["ctrl"]
    return (p[2 * i], p[2 * i + 1]), (c[4 * i], c[4 * i + 1]), (c[4 * i + 2], c[4 * i + 3])


def parts(s):
    """[[n_anchors, closed], ...] — one entry unless it is a compound path."""
    if s.get("parts"):
        return s["parts"]
    return [[node_count(s), bool(prop(s, "closed"))]]


def is_compound(s):
    return s["type"] == "path" and len(s.get("parts") or []) > 1


def part_of(s, i):
    """(start index, count, closed) of the sub-path containing anchor ``i``."""
    off = 0
    for n, closed in parts(s):
        if off <= i < off + n:
            return off, n, closed
        off += n
    return 0, node_count(s), bool(prop(s, "closed"))


def path_segments(s):
    """[(i, j)] node index pairs of every segment (incl. closing ones)."""
    segs, off = [], 0
    for n, closed in parts(s):
        segs += [(i, i + 1) for i in range(off, off + n - 1)]
        if closed and n >= 2:
            segs.append((off + n - 1, off))
        off += n
    return segs


def segment_points(s, i, j):
    a, _ai, ao = node(s, i)
    b, bi, _bo = node(s, j)
    return a, ao, bi, b


def _raw_part(s, off, n, closed):
    out = list(node(s, off)[0])
    segs = [(i, i + 1) for i in range(off, off + n - 1)]
    if closed and n >= 2:
        segs.append((off + n - 1, off))
    for i, j in segs:
        _a, c1, c2, b = segment_points(s, i, j)
        out += [c1[0], c1[1], c2[0], c2[1], b[0], b[1]]
    return out


def raw_parts(s):
    """One flat [p0, c1, c2, p1, ...] list per sub-path, for Tk's smooth='raw'."""
    out, off = [], 0
    for n, closed in parts(s):
        if n > 0:
            out.append(_raw_part(s, off, n, closed))
        off += n
    return out


def raw_bezier(s):
    """Raw Bézier list of the first sub-path (the whole path when not compound)."""
    rp = raw_parts(s)
    return rp[0] if rp else []


def fill_raw(s):
    """All sub-paths joined into one raw polygon with zero-width bridges back to the
    first point, so an even-odd fill shows holes (letters, rings …)."""
    rp = []
    for r in raw_parts(s):
        if len(r) < 8:
            continue
        if (r[-2], r[-1]) != (r[0], r[1]):           # open sub-path: close it for the fill
            r = r + [r[-2], r[-1], r[0], r[1], r[0], r[1]]
        rp.append(r)
    if not rp:
        return []
    out = list(rp[0])
    x0, y0 = rp[0][0], rp[0][1]
    for r in rp[1:]:
        lx, ly = out[-2], out[-1]
        out += [lx, ly, r[0], r[1], r[0], r[1]]          # bridge out
        out += r[2:]
        lx, ly = out[-2], out[-1]
        out += [lx, ly, x0, y0, x0, y0]                  # and back
    return out


def sample_path(s, steps=12):
    if node_count(s) == 0:
        return []
    out = list(s["pts"])
    for i, j in path_segments(s):
        out += g.sample_cubic(*segment_points(s, i, j), steps=steps)
    return out


def is_straight(s):
    """True when no node has handles (all segments are straight lines)."""
    c, p = s["ctrl"], s["pts"]
    return all(abs(c[4 * i + k] - p[2 * i + (k % 2)]) < 1e-9
               for i in range(node_count(s)) for k in range(4))


# ── geometry queries ────────────────────────────────────────────────────────
def box_center(s):
    p = s["pts"]
    return (p[0] + p[2]) / 2, (p[1] + p[3]) / 2


def renders_as_polygon(s):
    """rect/ellipse that Tk cannot draw natively (rotated, or rounded corners)."""
    if s["type"] == "rect":
        return bool(prop(s, "rot")) or prop(s, "radius") > 0
    if s["type"] == "ellipse":
        return bool(prop(s, "rot"))
    return False


def outline(s):
    """World-space outline polygon (curves sampled); None for text."""
    t = s["type"]
    if t == "path":
        return sample_path(s)
    if t in POINT_TYPES:
        return list(s["pts"])
    if t not in BOX_TYPES:
        return None
    x0, y0, x1, y1 = s["pts"]
    if t == "rect":
        pts = g.rounded_rect_points(x0, y0, x1, y1, prop(s, "radius"))
    else:
        pts = g.ellipse_points(x0, y0, x1, y1)
    rot = prop(s, "rot")
    if rot:
        cx, cy = box_center(s)
        pts = g.rotate_pts(pts, cx, cy, rot)
    return pts


def corner_points(s):
    """Four (rotated) corners of a rect/ellipse box."""
    x0, y0, x1, y1 = s["pts"]
    pts = [x0, y0, x1, y0, x1, y1, x0, y1]
    rot = prop(s, "rot")
    if rot:
        cx, cy = box_center(s)
        pts = g.rotate_pts(pts, cx, cy, rot)
    return pts


def text_fallback_bbox(s):
    x, y = s["pts"]
    size = prop(s, "size")
    lines = max(1, s.get("text", "").count("\n") + 1)
    return (x, y, x + size * max(1, len(s.get("text", "")) * 0.55), y + size * 1.25 * lines)


def geometry_bbox(s):
    """Axis-aligned bbox for non-text shapes (text needs the canvas to measure)."""
    t = s["type"]
    if t == "text":
        return text_fallback_bbox(s)
    if t == "path":
        return g.points_bbox(sample_path(s, 8))
    if t in BOX_TYPES and prop(s, "rot"):
        return g.points_bbox(corner_points(s) if t == "rect" else outline(s))
    return g.points_bbox(s["pts"])


def anchors(s):
    """Editable anchors for Direct Selection (index-compatible with to_path(s))."""
    if s["type"] == "text":
        return []
    p = s["pts"] if s["type"] == "path" else to_path(s)["pts"]
    return [(p[i], p[i + 1]) for i in range(0, len(p), 2)]


# ── conversion to an editable path ──────────────────────────────────────────
def _corner_ctrl(pts):
    return [v for i in range(len(pts) // 2) for v in (pts[2 * i], pts[2 * i + 1]) * 2]


def _rotate_path(s, rot, cx, cy):
    if rot:
        s["pts"] = g.rotate_pts(s["pts"], cx, cy, rot)
        s["ctrl"] = g.rotate_pts(s["ctrl"], cx, cy, rot)


def to_path(s):
    """Convert any non-text shape into an equivalent Bézier ``path`` (new dict)."""
    t = s["type"]
    if t == "path":
        return copy.deepcopy(s)
    if t == "text":
        return None
    n = {k: copy.deepcopy(v) for k, v in s.items() if k not in ("radius",)}
    n["type"] = "path"
    k = g.KAPPA
    if t == "rect":
        x0, y0, x1, y1 = s["pts"]
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        r = max(0.0, min(prop(s, "radius"), (x1 - x0) / 2, (y1 - y0) / 2))
        if r <= 0:
            pts = [x0, y0, x1, y0, x1, y1, x0, y1]
            ctrl, smooth = _corner_ctrl(pts), [False] * 4
        else:
            kr = k * r
            nodes = [  # anchor, in, out
                ((x0 + r, y0), (x0 + r - kr, y0), (x0 + r, y0)),
                ((x1 - r, y0), (x1 - r, y0), (x1 - r + kr, y0)),
                ((x1, y0 + r), (x1, y0 + r - kr), (x1, y0 + r)),
                ((x1, y1 - r), (x1, y1 - r), (x1, y1 - r + kr)),
                ((x1 - r, y1), (x1 - r + kr, y1), (x1 - r, y1)),
                ((x0 + r, y1), (x0 + r, y1), (x0 + r - kr, y1)),
                ((x0, y1 - r), (x0, y1 - r + kr), (x0, y1 - r)),
                ((x0, y0 + r), (x0, y0 + r), (x0, y0 + r - kr)),
            ]
            pts = [v for a, _i, _o in nodes for v in a]
            ctrl = [v for _a, i, o in nodes for v in (i + o)]
            smooth = [True] * 8
        n.update(pts=pts, ctrl=ctrl, smooth=smooth, closed=True)
        _rotate_path(n, prop(s, "rot"), *box_center(s))
    elif t == "ellipse":
        cx, cy = box_center(s)
        x0, y0, x1, y1 = s["pts"]
        rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
        nodes = [
            ((cx + rx, cy), (cx + rx, cy - k * ry), (cx + rx, cy + k * ry)),
            ((cx, cy + ry), (cx + k * rx, cy + ry), (cx - k * rx, cy + ry)),
            ((cx - rx, cy), (cx - rx, cy + k * ry), (cx - rx, cy - k * ry)),
            ((cx, cy - ry), (cx - k * rx, cy - ry), (cx + k * rx, cy - ry)),
        ]
        n.update(pts=[v for a, _i, _o in nodes for v in a],
                 ctrl=[v for _a, i, o in nodes for v in (i + o)],
                 smooth=[True] * 4, closed=True)
        _rotate_path(n, prop(s, "rot"), cx, cy)
    elif t in ("polygon", "line"):
        n.update(pts=list(s["pts"]), ctrl=_corner_ctrl(s["pts"]),
                 smooth=[False] * (len(s["pts"]) // 2), closed=(t == "polygon"))
    elif t == "pen":
        # Tk draws pencil strokes as a quadratic B-spline through the midpoints.
        p = [(s["pts"][i], s["pts"][i + 1]) for i in range(0, len(s["pts"]), 2)]
        if len(p) < 3:
            n.update(pts=list(s["pts"]), ctrl=_corner_ctrl(s["pts"]), smooth=[False] * len(p),
                     closed=False)
        else:
            mids = [((p[i][0] + p[i + 1][0]) / 2, (p[i][1] + p[i + 1][1]) / 2) for i in range(len(p) - 1)]
            anchors_ = [p[0]] + mids[1:-1] + [p[-1]]
            ctrl = [list(a) * 2 for a in anchors_]
            for seg in range(len(anchors_) - 1):
                c1, c2 = g.quad_to_cubic(anchors_[seg], p[seg + 1], anchors_[seg + 1])
                ctrl[seg][2:4] = list(c1)
                ctrl[seg + 1][0:2] = list(c2)
            n.update(pts=[v for a in anchors_ for v in a], ctrl=[v for c in ctrl for v in c],
                     smooth=[False] + [True] * (len(anchors_) - 2) + [False], closed=False)
    return n


# ── transforms (all return a new dict) ──────────────────────────────────────
def _map_xy(n, fn):
    n["pts"] = fn(n["pts"])
    if "ctrl" in n:
        n["ctrl"] = fn(n["ctrl"])


def translate(s, dx, dy):
    """In place."""
    s["pts"] = g.translate_pts(s["pts"], dx, dy)
    if "ctrl" in s:
        s["ctrl"] = g.translate_pts(s["ctrl"], dx, dy)


def rotated(s, deg, cx, cy):
    n = copy.deepcopy(s)
    t = s["type"]
    if t in POINT_TYPES or t == "text":
        _map_xy(n, lambda p: g.rotate_pts(p, cx, cy, deg))
    else:
        bx, by = box_center(s)
        ncx, ncy = g.rotate_point(bx, by, cx, cy, deg)
        x0, y0, x1, y1 = s["pts"]
        hw, hh = abs(x1 - x0) / 2, abs(y1 - y0) / 2
        n["pts"] = [ncx - hw, ncy - hh, ncx + hw, ncy + hh]
    n["rot"] = round(g.normalize_angle(prop(s, "rot") + deg), 4)
    if not n["rot"]:
        n.pop("rot", None)
    return n


def scaled(s, bbox, new_bbox):
    """Scale ``s`` from the selection box ``bbox`` into ``new_bbox``."""
    n = copy.deepcopy(s)
    _map_xy(n, lambda p: g.scale_pts(p, bbox, new_bbox))
    kx, ky = g.scale_factors(bbox, new_bbox)
    k = math.sqrt(abs(kx * ky))
    if s["type"] == "text":
        n["size"] = max(1, int(round(prop(s, "size") * k)))
    if prop(s, "radius"):
        n["radius"] = max(0, round(prop(s, "radius") * k, 2))
    return n


def scaled_about(s, kx, ky, cx, cy):
    """Scale by (kx, ky) around the point (cx, cy)."""
    return scaled(s, (cx - 1, cy - 1, cx + 1, cy + 1), (cx - kx, cy - ky, cx + kx, cy + ky))


def flipped(s, axis, c, bbox):
    """Mirror across the vertical (axis='h') or horizontal (axis='v') line at ``c``.

    ``bbox`` is the shape's own bbox (needed to keep text reading left-to-right).
    """
    n = copy.deepcopy(s)
    p = s["pts"]
    idx = 0 if axis == "h" else 1
    if s["type"] == "text":
        x, y = p
        if axis == "h":
            n["pts"] = [2 * c - bbox[2] + (x - bbox[0]), y]
        else:
            n["pts"] = [x, 2 * c - bbox[3] + (y - bbox[1])]
    else:
        _map_xy(n, lambda q: [(2 * c - v) if i % 2 == idx else v for i, v in enumerate(q)])
    if prop(s, "rot"):
        n["rot"] = -prop(s, "rot")
    return n


def reflected(s, axis_deg, cx, cy, bbox):
    """Mirror across the line through (cx, cy) at ``axis_deg`` (0 = horizontal axis)."""
    f = flipped(s, "v", cy, bbox)
    if not axis_deg:
        return f
    return rotated(f, 2 * axis_deg, cx, cy)
