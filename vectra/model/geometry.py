"""Pure geometry helpers. Coordinates are world units; y grows downward.

Angles are in degrees and positive = clockwise on screen.
Point lists are flat: [x0, y0, x1, y1, ...].
"""

import math


def points_bbox(pts):
    xs, ys = pts[0::2], pts[1::2]
    return (min(xs), min(ys), max(xs), max(ys))


def union_bbox(bboxes):
    bboxes = [b for b in bboxes if b]
    if not bboxes:
        return None
    return (min(b[0] for b in bboxes), min(b[1] for b in bboxes),
            max(b[2] for b in bboxes), max(b[3] for b in bboxes))


def bbox_center(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def translate_pts(pts, dx, dy):
    return [v + (dx if i % 2 == 0 else dy) for i, v in enumerate(pts)]


def rotate_point(x, y, cx, cy, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    dx, dy = x - cx, y - cy
    return cx + dx * c - dy * s, cy + dx * s + dy * c


def rotate_pts(pts, cx, cy, deg):
    out = []
    for i in range(0, len(pts), 2):
        out.extend(rotate_point(pts[i], pts[i + 1], cx, cy, deg))
    return out


def normalize_angle(a):
    """Map to the range (-180, 180]."""
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def handle_points(x0, y0, x1, y1):
    """The 8 resize handles, clockwise from top-left."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    return [(x0, y0), (mx, y0), (x1, y0), (x1, my), (x1, y1), (mx, y1), (x0, y1), (x0, my)]


def resize_bbox(bbox, handle, wx, wy, keep_ratio):
    """New bbox when ``handle`` (0..7, see handle_points) is dragged to (wx, wy)."""
    bx0, by0, bx1, by1 = bbox
    bw, bh = bx1 - bx0, by1 - by0
    left, right = handle in (0, 6, 7), handle in (2, 3, 4)
    top, bottom = handle in (0, 1, 2), handle in (4, 5, 6)
    nx0, ny0, nx1, ny1 = bx0, by0, bx1, by1
    if left:
        nx0 = wx
    if right:
        nx1 = wx
    if top:
        ny0 = wy
    if bottom:
        ny1 = wy
    if keep_ratio and handle in (0, 2, 4, 6) and bw and bh:
        nw, nh = nx1 - nx0, ny1 - ny0
        k = max(abs(nw) / bw, abs(nh) / bh)
        nw2 = math.copysign(bw * k, nw or 1)
        nh2 = math.copysign(bh * k, nh or 1)
        if left:
            nx0 = nx1 - nw2
        else:
            nx1 = nx0 + nw2
        if top:
            ny0 = ny1 - nh2
        else:
            ny1 = ny0 + nh2
    return nx0, ny0, nx1, ny1


def scale_factors(bbox, new_bbox):
    bx0, by0, bx1, by1 = bbox
    nx0, ny0, nx1, ny1 = new_bbox
    bw, bh = bx1 - bx0, by1 - by0
    kx = (nx1 - nx0) / bw if bw else 1
    ky = (ny1 - ny0) / bh if bh else 1
    return kx, ky


def scale_pts(pts, bbox, new_bbox):
    kx, ky = scale_factors(bbox, new_bbox)
    bx0, by0 = bbox[0], bbox[1]
    nx0, ny0 = new_bbox[0], new_bbox[1]
    return [(nx0 + (v - bx0) * kx) if i % 2 == 0 else (ny0 + (v - by0) * ky)
            for i, v in enumerate(pts)]


def constrain_45(x0, y0, x1, y1):
    ang = math.atan2(y1 - y0, x1 - x0)
    ang = round(ang / (math.pi / 4)) * (math.pi / 4)
    ln = math.hypot(x1 - x0, y1 - y0)
    return x0 + ln * math.cos(ang), y0 + ln * math.sin(ang)


def constrain_square(x0, y0, x1, y1):
    m = max(abs(x1 - x0), abs(y1 - y0))
    return x0 + math.copysign(m, (x1 - x0) or 1), y0 + math.copysign(m, (y1 - y0) or 1)


def star_points(cx, cy, r_outer, r_inner, n, start_deg=-90.0):
    pts = []
    for i in range(n * 2):
        r = r_outer if i % 2 == 0 else r_inner
        a = math.radians(start_deg + i * 180.0 / n)
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def ellipse_points(x0, y0, x1, y1, segments=72):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
    pts = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        pts += [cx + rx * math.cos(a), cy + ry * math.sin(a)]
    return pts


def rounded_rect_points(x0, y0, x1, y1, r, arc_segments=8):
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    if r <= 0:
        return [x0, y0, x1, y0, x1, y1, x0, y1]
    pts = []
    corners = ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180))
    for cx, cy, start in corners:
        for k in range(arc_segments + 1):
            a = math.radians(start + 90.0 * k / arc_segments)
            pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def dist_point_segment(px, py, ax, ay, bx, by):
    """Distance from P to segment AB, plus the closest point and its t (0..1)."""
    vx, vy = bx - ax, by - ay
    ln2 = vx * vx + vy * vy
    t = 0.0 if ln2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / ln2))
    qx, qy = ax + t * vx, ay + t * vy
    return math.hypot(px - qx, py - qy), qx, qy, t


def nearest_segment(pts, px, py, closed):
    """Return (insert_index_in_points, distance, qx, qy) for the closest edge, or None."""
    n = len(pts) // 2
    if n < 2:
        return None
    best = None
    last = n if closed else n - 1
    for i in range(last):
        j = (i + 1) % n
        d, qx, qy, _t = dist_point_segment(px, py, pts[2 * i], pts[2 * i + 1], pts[2 * j], pts[2 * j + 1])
        if best is None or d < best[1]:
            best = (i + 1, d, qx, qy)
    return best


# ── Bézier curves ───────────────────────────────────────────────────────────
KAPPA = 0.5522847498  # handle length for a quarter circle


def cubic_point(p0, c1, c2, p1, t):
    u = 1 - t
    a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    return (a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0],
            a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1])


def sample_cubic(p0, c1, c2, p1, steps=16):
    """Points for t in (0, 1] — the start point is not included."""
    out = []
    for k in range(1, steps + 1):
        out.extend(cubic_point(p0, c1, c2, p1, k / steps))
    return out


def split_cubic(p0, c1, c2, p1, t):
    """de Casteljau split -> (left 4 points, right 4 points)."""
    def lerp(a, b):
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    a, b, c = lerp(p0, c1), lerp(c1, c2), lerp(c2, p1)
    d, e = lerp(a, b), lerp(b, c)
    m = lerp(d, e)
    return (p0, a, d, m), (m, e, c, p1)


def quad_to_cubic(a, q, b):
    """Control points of the cubic equal to the quadratic (a, q, b)."""
    c1 = (a[0] + 2 / 3 * (q[0] - a[0]), a[1] + 2 / 3 * (q[1] - a[1]))
    c2 = (b[0] + 2 / 3 * (q[0] - b[0]), b[1] + 2 / 3 * (q[1] - b[1]))
    return c1, c2


# ── generators ──────────────────────────────────────────────────────────────
def regular_polygon_points(cx, cy, r, sides, start_deg=-90.0):
    pts = []
    for i in range(sides):
        a = math.radians(start_deg + i * 360.0 / sides)
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def spiral_points(cx, cy, radius, turns=3.5, decay=0.8, steps_per_turn=36):
    """Archimedes-like decaying spiral from the outside in."""
    pts = []
    n = int(turns * steps_per_turn)
    for i in range(n + 1):
        frac = i / steps_per_turn
        r = radius * (decay ** (frac * 4))
        a = 2 * math.pi * frac
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def point_in_polygon(x, y, poly):
    inside = False
    n = len(poly) // 2
    j = n - 1
    for i in range(n):
        xi, yi = poly[2 * i], poly[2 * i + 1]
        xj, yj = poly[2 * j], poly[2 * j + 1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def nice_step(min_px, zoom):
    """A 1/2/5×10ⁿ world step whose on-screen size is at least ``min_px``."""
    raw = min_px / max(zoom, 1e-9)
    p = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if m * p >= raw:
            return m * p
    return 10 * p
