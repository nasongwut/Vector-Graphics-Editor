"""Tool icons drawn with canvas primitives on a 24×24 grid (no image files needed)."""

import math


def _poly(c, pts, color, fill="", w=1.4):
    c.create_polygon(*pts, outline=color, fill=fill, width=w, joinstyle="round")


def _line(c, pts, color, w=1.4, **kw):
    c.create_line(*pts, fill=color, width=w, capstyle="round", joinstyle="round", **kw)


def _arrow(c, color, hollow):
    pts = [7, 3, 7, 19, 11, 15.5, 13.8, 21, 16.3, 19.8, 13.6, 14.5, 18.5, 14.5]
    _poly(c, pts, color, fill="" if hollow else color)


def _nib(c, color, ox=0, oy=0, s=1.0):
    def p(*xy):
        return [v * s + (ox if i % 2 == 0 else oy) for i, v in enumerate(xy)]
    _poly(c, p(12, 3, 18, 12, 15, 19, 9, 19, 6, 12), color)
    _line(c, p(12, 3, 12, 11), color)
    c.create_oval(*p(10.6, 10.6, 13.4, 13.4), outline=color, width=1.2)
    _line(c, p(8.5, 21, 15.5, 21), color)


def draw(c, key, color):
    """Draw icon ``key`` onto canvas ``c`` (24×24)."""
    if key == "select":
        _arrow(c, color, hollow=False)
    elif key == "direct":
        _arrow(c, color, hollow=True)
    elif key == "magic_wand":
        _line(c, [5, 20, 14, 11], color, w=2)
        for a in range(0, 360, 45):
            r = 4 if a % 90 == 0 else 2.5
            x, y = 17 + r * math.cos(math.radians(a)), 7 + r * math.sin(math.radians(a))
            _line(c, [17, 7, x, y], color, w=1.1)
    elif key == "lasso":
        c.create_oval(4, 4, 20, 14, outline=color, width=1.4)
        _line(c, [8, 13, 7, 17, 10, 20, 8, 22], color, smooth=True)
    elif key == "pen":
        _nib(c, color)
    elif key in ("add_anchor", "delete_anchor"):
        _nib(c, color, ox=-2, oy=1, s=0.85)
        _line(c, [15, 6, 21, 6], color, w=1.6)
        if key == "add_anchor":
            _line(c, [18, 3, 18, 9], color, w=1.6)
    elif key == "anchor_point":
        _line(c, [5, 18, 12, 6, 19, 18], color, w=1.6)
    elif key == "type":
        _line(c, [6, 5, 18, 5], color, w=2)
        _line(c, [12, 5, 12, 20], color, w=2)
        _line(c, [9.5, 20, 14.5, 20], color, w=1.4)
    elif key == "line":
        _line(c, [5, 19, 19, 5], color, w=1.6)
    elif key == "arc":
        c.create_arc(-6, 5, 18, 29, start=0, extent=90, style="arc", outline=color, width=1.6)
    elif key == "spiral":
        pts = []
        for k in range(0, 60):
            a = k / 6.0
            r = 1 + a * 1.25
            pts += [12 + r * math.cos(a), 12 + r * math.sin(a)]
        _line(c, pts, color, w=1.3, smooth=True)
    elif key == "rect":
        c.create_rectangle(4, 6, 20, 18, outline=color, width=1.6)
    elif key == "rounded_rect":
        _poly(c, [7, 6, 17, 6, 20, 9, 20, 15, 17, 18, 7, 18, 4, 15, 4, 9], color, w=1.6)
    elif key == "ellipse":
        c.create_oval(4, 6, 20, 18, outline=color, width=1.6)
    elif key == "polygon":
        pts = []
        for i in range(6):
            a = math.radians(-90 + i * 60)
            pts += [12 + 8.5 * math.cos(a), 12.5 + 8.5 * math.sin(a)]
        _poly(c, pts, color, w=1.6)
    elif key == "star":
        pts = []
        for i in range(10):
            r = 9 if i % 2 == 0 else 4
            a = math.radians(-90 + i * 36)
            pts += [12 + r * math.cos(a), 13 + r * math.sin(a)]
        _poly(c, pts, color, w=1.4)
    elif key == "pencil":
        _poly(c, [16, 4, 20, 8, 9, 19, 4, 20, 5, 15], color)
        _line(c, [14, 6, 18, 10], color, w=1.1)
    elif key == "scissors":
        c.create_oval(3, 13, 9, 19, outline=color, width=1.4)
        c.create_oval(13, 15, 19, 21, outline=color, width=1.4)
        _line(c, [8, 14, 20, 4], color)
        _line(c, [14, 16, 9, 4], color)
    elif key == "rotate":
        c.create_arc(5, 5, 19, 19, start=110, extent=280, style="arc", outline=color, width=1.6)
        _poly(c, [7, 2, 7, 9, 13, 6.5], color, fill=color, w=1)
    elif key == "reflect":
        _poly(c, [4, 18, 10, 6, 10, 18], color, fill=color)
        _poly(c, [20, 18, 14, 6, 14, 18], color)
        _line(c, [12, 3, 12, 21], color, w=1, dash=(2, 2))
    elif key == "scale":
        c.create_rectangle(4, 9, 15, 20, outline=color, width=1.3)
        c.create_rectangle(9, 4, 20, 15, outline=color, width=1.3, dash=(2, 2))
        _line(c, [7, 17, 17, 7], color, w=1.3, arrow="last", arrowshape=(5, 6, 2))
    elif key == "artboard":
        c.create_rectangle(7, 7, 17, 17, outline=color, width=1.4)
        for x0, y0, x1, y1 in ((7, 2, 7, 5), (2, 7, 5, 7), (17, 19, 17, 22), (19, 17, 22, 17),
                               (17, 2, 17, 5), (19, 7, 22, 7), (7, 19, 7, 22), (2, 17, 5, 17)):
            _line(c, [x0, y0, x1, y1], color, w=1.2)
    elif key == "eyedropper":
        _poly(c, [15, 4, 20, 9, 17, 12, 12, 7], color, fill=color)
        _line(c, [14, 10, 6, 18, 5, 21, 8, 20, 16, 12], color)
    elif key == "measure":
        _poly(c, [3, 16, 16, 3, 21, 8, 8, 21], color)
        for k in range(1, 6):
            x, y = 5.5 + k * 2.2, 18.5 - k * 2.2
            _line(c, [x, y, x - 1.6, y - 1.6], color, w=1)
    elif key == "hand":
        _poly(c, [7, 21, 5, 13, 6.5, 12, 8, 14, 8, 5, 10, 5, 10, 11, 10, 4, 12, 4, 12, 11,
                  12, 5, 14, 5, 14, 11, 14, 7, 16, 7, 16.5, 16, 14, 21], color)
    elif key == "zoom":
        c.create_oval(4, 4, 15, 15, outline=color, width=1.6)
        _line(c, [13.5, 13.5, 20, 20], color, w=2.4)
    else:
        c.create_text(12, 12, text="?", fill=color)


def draw_align(c, kind, color, size=18):
    """Small align / distribute icons for the control bar and properties panel."""
    s = size / 18.0

    def r(x0, y0, x1, y1):
        c.create_rectangle(x0 * s, y0 * s, x1 * s, y1 * s, outline=color, fill=color)

    def ln(x0, y0, x1, y1):
        c.create_line(x0 * s, y0 * s, x1 * s, y1 * s, fill=color, width=1)
    if kind == "left":
        ln(2, 1, 2, 17); r(4, 4, 15, 7); r(4, 11, 10, 14)
    elif kind == "hcenter":
        ln(9, 1, 9, 17); r(3, 4, 15, 7); r(5, 11, 13, 14)
    elif kind == "right":
        ln(16, 1, 16, 17); r(3, 4, 14, 7); r(8, 11, 14, 14)
    elif kind == "top":
        ln(1, 2, 17, 2); r(4, 4, 7, 15); r(11, 4, 14, 10)
    elif kind == "vcenter":
        ln(1, 9, 17, 9); r(4, 3, 7, 15); r(11, 5, 14, 13)
    elif kind == "bottom":
        ln(1, 16, 17, 16); r(4, 3, 7, 14); r(11, 8, 14, 14)
    elif kind == "dist_h":
        r(2, 5, 5, 13); r(8, 5, 11, 13); r(14, 5, 17, 13)
        ln(1, 16, 17, 16)
    elif kind == "dist_v":
        r(5, 2, 13, 5); r(5, 8, 13, 11); r(5, 14, 13, 17)
        ln(16, 1, 16, 17)
    elif kind == "flip_h":
        c.create_polygon(2 * s, 14 * s, 8 * s, 4 * s, 8 * s, 14 * s, outline=color, fill=color)
        c.create_polygon(16 * s, 14 * s, 10 * s, 4 * s, 10 * s, 14 * s, outline=color, fill="")
    elif kind == "flip_v":
        c.create_polygon(4 * s, 2 * s, 14 * s, 8 * s, 4 * s, 8 * s, outline=color, fill=color)
        c.create_polygon(4 * s, 16 * s, 14 * s, 10 * s, 4 * s, 10 * s, outline=color, fill="")
