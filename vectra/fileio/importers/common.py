"""Shared pieces for the .ai / .eps / .pdf importers: matrices, colours, path builder."""

import math
import re

from vectra.model import shapes as sh

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mat_mul(m, n):
    """Apply m first, then n (PDF/PostScript row-vector convention)."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def mat_scale(m):
    return math.sqrt(abs(m[0] * m[3] - m[1] * m[2])) or 1.0


def _c(v):
    return max(0, min(255, int(round(float(v) * 255))))


def rgb_hex(r, g, b):
    return f"#{_c(r):02x}{_c(g):02x}{_c(b):02x}"


def gray_hex(v):
    return rgb_hex(v, v, v)


def cmyk_hex(c, m, y, k):
    """CMYK -> sRGB with a polynomial fitted to a SWOP press profile (the same
    approach PDF viewers use), much closer to what design apps show than the naive
    (1-c)(1-k) formula."""
    c, m, y, k = (max(0.0, min(1.0, float(v))) for v in (c, m, y, k))
    r = (255 + c * (-4.387332384609988 * c + 54.48615194189176 * m + 18.82290502165302 * y
                    + 212.25662451639585 * k - 285.2331026137004)
         + m * (1.7149763477362134 * m - 5.6096736904047315 * y - 17.873870861415444 * k
                - 5.497006427196366)
         + y * (-2.5217340131683033 * y - 21.248923337353073 * k + 17.5119270841813)
         + k * (-21.86122147463605 * k - 189.48180835922747))
    g = (255 + c * (8.841041422036149 * c + 60.118027045597366 * m + 6.871425592049007 * y
                    + 31.159100130055922 * k - 79.2970844816548)
         + m * (-15.310361306967817 * m + 17.575251261109482 * y + 131.35250912493976 * k
                - 190.9453302588951)
         + y * (4.444339102852739 * y + 9.8632861493405 * k - 24.86741582555878)
         + k * (-20.737325471181034 * k - 187.80453709719578))
    b = (255 + c * (0.8842522430003296 * c + 8.078677503112928 * m + 30.89978309703729 * y
                    - 0.23883238689178934 * k - 14.183576799673286)
         + m * (10.49593273432072 * m + 63.02378494754052 * y + 50.606957656360734 * k
                - 112.23884253719248)
         + y * (0.03296041114873217 * y + 115.60384449646641 * k - 193.58209356861505)
         + k * (-22.33816807309886 * k - 180.12613974708367))
    return rgb_hex(r / 255, g / 255, b / 255)


def color_from_components(vals):
    """Guess the colour space from the number of components."""
    vals = [float(v) for v in vals]
    if len(vals) >= 4:
        return cmyk_hex(*vals[:4])
    if len(vals) == 3:
        return rgb_hex(*vals)
    if len(vals) == 1:
        return gray_hex(vals[0])
    return "#808080"


def font_family_from(name):
    """'ABCDEF+MyriadPro-BoldIt' -> 'Myriad Pro'."""
    if not name:
        return None
    name = str(name)
    if "+" in name[:8]:
        name = name.split("+", 1)[1]
    base = re.split(r"[-,]", name)[0]
    base = re.sub(r"(MT|PS|Std|Pro)$", lambda m: " " + m.group(1) if m.group(1) in ("Pro", "Std") else "", base)
    base = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base).strip()
    return base or None


class ImportResult:
    def __init__(self, shapes, artboard, notes=None, source="", layers=None):
        self.shapes = shapes
        self.artboard = artboard
        self.notes = notes or {}
        self.source = source
        self.layers = layers or []     # [{"id", "name", "visible", "locked", "color"}] bottom → top


def decode_text_string(b):
    """PDF / PostScript text string -> str (UTF-16 with BOM, UTF-8 or Latin-1)."""
    if isinstance(b, str):
        return b
    if b[:2] == b"\xfe\xff":
        return b[2:].decode("utf-16-be", errors="replace")
    if b[:2] == b"\xff\xfe":
        return b[2:].decode("utf-16-le", errors="replace")
    if b[:3] == b"\xef\xbb\xbf":
        return b[3:].decode("utf-8", errors="replace")
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")


class PathBuilder:
    """Collects sub-paths in device space; emits one Vectra ``path`` shape."""

    def __init__(self):
        self.parts = []
        self._after_close = False

    def clear(self):
        self.parts = []
        self._after_close = False

    def empty(self):
        return not any(len(p["nodes"]) >= 2 for p in self.parts)

    def current(self):
        if not self.parts or not self.parts[-1]["nodes"]:
            return None
        n = self.parts[-1]["nodes"][-1]
        return n[0], n[1]

    def moveto(self, x, y):
        if self.parts and len(self.parts[-1]["nodes"]) == 1:
            self.parts.pop()  # a lone moveto replaced by another
        self.parts.append({"nodes": [[x, y, x, y, x, y]], "closed": False})
        self._after_close = False

    def _ensure(self):
        if self._after_close or not self.parts:
            p = self.current_start() if self.parts else (0.0, 0.0)
            self.moveto(*p)

    def current_start(self):
        n = self.parts[-1]["nodes"][0]
        return n[0], n[1]

    def lineto(self, x, y):
        self._ensure()
        self.parts[-1]["nodes"].append([x, y, x, y, x, y])

    def curveto(self, x1, y1, x2, y2, x3, y3):
        self._ensure()
        last = self.parts[-1]["nodes"][-1]
        last[4], last[5] = x1, y1
        self.parts[-1]["nodes"].append([x3, y3, x2, y2, x3, y3])

    def closepath(self):
        if not self.parts:
            return
        part = self.parts[-1]
        nodes = part["nodes"]
        if len(nodes) > 2 and math.hypot(nodes[-1][0] - nodes[0][0], nodes[-1][1] - nodes[0][1]) < 1e-6:
            nodes[0][2], nodes[0][3] = nodes[-1][2], nodes[-1][3]
            nodes.pop()
        part["closed"] = True
        self._after_close = True

    def rect(self, m, x, y, w, h):
        pts = [apply(m, x, y), apply(m, x + w, y), apply(m, x + w, y + h), apply(m, x, y + h)]
        self.moveto(*pts[0])
        for p in pts[1:]:
            self.lineto(*p)
        self.closepath()

    def to_shape(self, flip, fill, stroke, width, dash=False, close_for_fill=False):
        parts = [p for p in self.parts if len(p["nodes"]) >= 2]
        if not parts:
            return None
        pts, ctrl, smooth, info = [], [], [], []
        for p in parts:
            closed = p["closed"] or (close_for_fill and not stroke)
            info.append([len(p["nodes"]), closed and len(p["nodes"]) >= 2])
            for ax, ay, ix, iy, ox, oy in p["nodes"]:
                AX, AY = flip(ax, ay)
                IX, IY = flip(ix, iy)
                OX, OY = flip(ox, oy)
                pts += [AX, AY]
                ctrl += [IX, IY, OX, OY]
                smooth.append(_is_smooth(AX, AY, IX, IY, OX, OY))
        style = {"fill": fill, "stroke": stroke, "width": width if stroke else 0,
                 "font_size": 12, "dash": dash}
        s = sh.make_path(pts, ctrl, smooth, info[0][1] if len(info) == 1 else any(c for _n, c in info),
                         style, parts=info if len(info) > 1 else None)
        s["width"] = round(width, 3) if stroke else 0
        if not dash:
            s.pop("dash", None)
        return s


def _is_smooth(ax, ay, ix, iy, ox, oy):
    v1x, v1y, v2x, v2y = ix - ax, iy - ay, ox - ax, oy - ay
    l1, l2 = math.hypot(v1x, v1y), math.hypot(v2x, v2y)
    if l1 < 1e-6 or l2 < 1e-6:
        return False
    cross = (v1x * v2y - v1y * v2x) / (l1 * l2)
    dot = (v1x * v2x + v1y * v2y) / (l1 * l2)
    return abs(cross) < 0.02 and dot < 0


def font_style_from(name):
    """('bold' | None, 'italic' | None) guessed from a PostScript font name."""
    n = str(name or "").lower()
    bold = any(w in n for w in ("bold", "black", "heavy", "semibold", "demi", "extrabold"))
    italic = "italic" in n or "oblique" in n
    return ("bold" if bold else None), ("italic" if italic else None)


def make_text(x, y, text, size, color, font=None, rot=0.0, style=(None, None)):
    s = {"id": 0, "type": "text", "pts": [x, y], "fill": color or "#000000", "stroke": None,
         "width": 0, "size": max(1, round(size, 2)), "text": text}
    if font:
        s["font"] = font
    if style and style[0]:
        s["weight"] = style[0]
    if style and style[1]:
        s["slant"] = style[1]
    if rot:
        s["rot"] = round(rot, 3)
    return s
