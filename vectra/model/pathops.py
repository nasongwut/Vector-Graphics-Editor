"""Editing operations on Bézier ``path`` shapes (in place unless noted)."""

import copy
import math

from vectra.model import geometry as g
from vectra.model.shapes import (is_compound, node, node_count, part_of, path_segments, prop,
                                 segment_points)


def _set_node(s, i, anchor=None, hin=None, hout=None):
    if anchor is not None:
        s["pts"][2 * i:2 * i + 2] = [anchor[0], anchor[1]]
    if hin is not None:
        s["ctrl"][4 * i:4 * i + 2] = [hin[0], hin[1]]
    if hout is not None:
        s["ctrl"][4 * i + 2:4 * i + 4] = [hout[0], hout[1]]


def append_node(s, x, y, hout=None, smooth=False):
    """Add an anchor at the end (Pen tool). ``hout`` mirrors into the in-handle."""
    s["pts"] += [x, y]
    if hout is None:
        s["ctrl"] += [x, y, x, y]
    else:
        s["ctrl"] += [2 * x - hout[0], 2 * y - hout[1], hout[0], hout[1]]
    s["smooth"].append(bool(smooth))


def move_node(s, i, x, y):
    """Move an anchor together with its handles."""
    (ax, ay), hin, hout = node(s, i)
    dx, dy = x - ax, y - ay
    _set_node(s, i, (x, y), (hin[0] + dx, hin[1] + dy), (hout[0] + dx, hout[1] + dy))


def move_handle(s, i, which, x, y, mirror=True):
    """Drag the 'in' or 'out' handle; smooth nodes keep the opposite handle collinear."""
    (ax, ay), hin, hout = node(s, i)
    if which == "out":
        _set_node(s, i, hout=(x, y))
        other = hin
    else:
        _set_node(s, i, hin=(x, y))
        other = hout
    if mirror and s["smooth"][i]:
        ln = math.hypot(other[0] - ax, other[1] - ay)
        d = math.hypot(x - ax, y - ay)
        if d > 1e-9:
            ox, oy = ax - (x - ax) / d * ln, ay - (y - ay) / d * ln
            if which == "out":
                _set_node(s, i, hin=(ox, oy))
            else:
                _set_node(s, i, hout=(ox, oy))


def set_symmetric_handles(s, i, hx, hy):
    """Pen drag: out handle at (hx, hy), in handle mirrored."""
    (ax, ay), _hin, _hout = node(s, i)
    _set_node(s, i, hin=(2 * ax - hx, 2 * ay - hy), hout=(hx, hy))
    s["smooth"][i] = math.hypot(hx - ax, hy - ay) > 1e-9


def toggle_smooth(s, i):
    """Anchor Point tool: corner <-> smooth."""
    (ax, ay), hin, hout = node(s, i)
    has_handles = math.hypot(hin[0] - ax, hin[1] - ay) > 1e-9 or math.hypot(hout[0] - ax, hout[1] - ay) > 1e-9
    if has_handles:
        _set_node(s, i, hin=(ax, ay), hout=(ax, ay))
        s["smooth"][i] = False
        return
    start, n, closed = part_of(s, i)
    k = i - start
    prev_i = start + k - 1 if k > 0 else (start + n - 1 if closed else None)
    next_i = start + k + 1 if k < n - 1 else (start if closed else None)
    px, py = node(s, prev_i)[0] if prev_i is not None else (ax, ay)
    nx, ny = node(s, next_i)[0] if next_i is not None else (ax, ay)
    dx, dy = nx - px, ny - py
    d = math.hypot(dx, dy) or 1.0
    lin = math.hypot(ax - px, ay - py) / 3
    lout = math.hypot(nx - ax, ny - ay) / 3
    _set_node(s, i, hin=(ax - dx / d * lin, ay - dy / d * lin), hout=(ax + dx / d * lout, ay + dy / d * lout))
    s["smooth"][i] = True


def nearest_on_path(s, x, y, steps=24):
    """Closest point on the outline -> (segment (i, j), t, distance, qx, qy) or None."""
    best = None
    for i, j in path_segments(s):
        p0, c1, c2, p1 = segment_points(s, i, j)
        prev = p0
        for k in range(1, steps + 1):
            t1 = k / steps
            cur = g.cubic_point(p0, c1, c2, p1, t1)
            d, qx, qy, tt = g.dist_point_segment(x, y, prev[0], prev[1], cur[0], cur[1])
            if best is None or d < best[2]:
                best = ((i, j), (k - 1 + tt) / steps, d, qx, qy)
            prev = cur
    return best


def insert_node(s, seg, t):
    """Split segment ``seg`` = (i, j) at parameter t, keeping the curve's shape."""
    i, j = seg
    p0, c1, c2, p1 = segment_points(s, i, j)
    left, right = g.split_cubic(p0, c1, c2, p1, t)
    _set_node(s, i, hout=left[1])
    _set_node(s, j, hin=right[2])
    m = left[3]
    at = i + 1  # insert after i (for the closing segment j == 0, this appends)
    s["pts"][2 * at:2 * at] = [m[0], m[1]]
    s["ctrl"][4 * at:4 * at] = [left[2][0], left[2][1], right[1][0], right[1][1]]
    straight = all(abs(a - b) < 1e-9 for a, b in zip(left[1] + left[2], p0 + m)) and \
        all(abs(a - b) < 1e-9 for a, b in zip(right[1] + right[2], m + p1))
    s["smooth"].insert(at, not straight)
    if s.get("parts"):
        off = 0
        for part in s["parts"]:
            if off <= i < off + part[0]:
                part[0] += 1
                break
            off += part[0]
    return at


def delete_node(s, i):
    """Remove an anchor. Returns False if the path would become degenerate."""
    start, n, closed = part_of(s, i)
    if n <= 2 or (closed and n <= 3):
        return False
    if s.get("parts"):
        off = 0
        for part in s["parts"]:
            if off <= i < off + part[0]:
                part[0] -= 1
                break
            off += part[0]
    del s["pts"][2 * i:2 * i + 2]
    del s["ctrl"][4 * i:4 * i + 4]
    del s["smooth"][i]
    return True


def _sub_path(s, start, count, closed=False):
    """New path dict made of ``count`` consecutive nodes from ``start`` (wrapping)."""
    n = node_count(s)
    out = copy.deepcopy(s)
    out["pts"], out["ctrl"], out["smooth"] = [], [], []
    out.pop("parts", None)
    for k in range(count):
        i = (start + k) % n
        out["pts"] += s["pts"][2 * i:2 * i + 2]
        out["ctrl"] += s["ctrl"][4 * i:4 * i + 4]
        out["smooth"].append(s["smooth"][i])
    out["closed"] = closed
    return out


def split_at(s, seg, t):
    """Scissors: cut the path at (seg, t). Returns 1 (closed) or 2 (open) new paths.
    Compound paths are not cut (returns None) — release them first."""
    if is_compound(s):
        return None
    work = copy.deepcopy(s)
    at = insert_node(work, seg, t)
    n = node_count(work)
    if prop(work, "closed"):
        piece = _sub_path(work, at, n + 1, closed=False)  # start & end at the cut
        return [piece]
    a = _sub_path(work, 0, at + 1)
    b = _sub_path(work, at, n - at)
    for p in (a, b):  # cut ends are corners
        last = node_count(p) - 1
        p["smooth"][0] = p["smooth"][last] = False
    return [a, b]


def reverse(s):
    n = node_count(s)
    out = copy.deepcopy(s)
    out["pts"], out["ctrl"] = [], []
    for i in reversed(range(n)):
        (ax, ay), hin, hout = node(s, i)
        out["pts"] += [ax, ay]
        out["ctrl"] += [hout[0], hout[1], hin[0], hin[1]]
    out["smooth"] = list(reversed(s["smooth"]))
    if s.get("parts"):
        out["parts"] = [list(p) for p in reversed(s["parts"])]
    return out


def close(s):
    if s.get("parts"):
        for part in s["parts"]:
            part[1] = part[0] > 2
    s["closed"] = True


def make_compound(paths):
    """Combine several (non-compound or compound) paths into one compound path.
    Style comes from the first (back-most) path."""
    out = copy.deepcopy(paths[0])
    out["pts"], out["ctrl"], out["smooth"], out["parts"] = [], [], [], []
    for p in paths:
        out["pts"] += p["pts"]
        out["ctrl"] += p["ctrl"]
        out["smooth"] += p["smooth"]
        if p.get("parts"):
            out["parts"] += [list(x) for x in p["parts"]]
        else:
            out["parts"].append([node_count(p), bool(prop(p, "closed"))])
    out["closed"] = any(c for _n, c in out["parts"])
    return out


def release_compound(s):
    """Split a compound path into one path per sub-path."""
    out, off = [], 0
    for n, closed in s.get("parts") or [[node_count(s), prop(s, "closed")]]:
        piece = copy.deepcopy(s)
        piece.pop("parts", None)
        piece["pts"] = s["pts"][2 * off:2 * (off + n)]
        piece["ctrl"] = s["ctrl"][4 * off:4 * (off + n)]
        piece["smooth"] = s["smooth"][off:off + n]
        piece["closed"] = bool(closed)
        out.append(piece)
        off += n
    return out


def join(a, b):
    """Join two open paths at their nearest endpoints. Returns the merged path."""
    def ends(p):
        n = node_count(p)
        return node(p, 0)[0], node(p, n - 1)[0]
    a0, a1 = ends(a)
    b0, b1 = ends(b)
    options = [
        (math.dist(a1, b0), False, False),
        (math.dist(a1, b1), False, True),
        (math.dist(a0, b0), True, False),
        (math.dist(a0, b1), True, True),
    ]
    _d, rev_a, rev_b = min(options, key=lambda o: o[0])
    pa = reverse(a) if rev_a else copy.deepcopy(a)
    pb = reverse(b) if rev_b else b
    pa["pts"] += pb["pts"]
    pa["ctrl"] += pb["ctrl"]
    pa["smooth"] += pb["smooth"]
    pa["closed"] = False
    return pa
