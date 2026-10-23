"""SVG export."""

from xml.sax.saxutils import escape, quoteattr

from vectra.model.shapes import box_center, node, parts, prop, segment_points


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _dash(w):
    w = max(1, w)
    return f' stroke-dasharray="{_n(w * 3)} {_n(w * 2)}"'


def shape_to_svg(s, font_family="sans-serif"):
    p = s["pts"]
    fill = s.get("fill") or "none"
    stroke = s.get("stroke") or "none"
    w = s.get("width", 0)
    if not w:
        stroke = "none"
    dash = _dash(w) if prop(s, "dash") and stroke != "none" else ""
    paint = f'fill="{fill}" stroke="{stroke}" stroke-width="{_n(w)}" stroke-linejoin="round"{dash}'
    rot = prop(s, "rot")
    name = f" id={quoteattr(s['name'])}" if s.get("name") else ""
    t = s["type"]

    def turn(cx, cy):
        return f' transform="rotate({_n(rot)} {_n(cx)} {_n(cy)})"' if rot else ""

    if t == "rect":
        x, y = min(p[0], p[2]), min(p[1], p[3])
        wd, ht = abs(p[2] - p[0]), abs(p[3] - p[1])
        r = min(prop(s, "radius"), wd / 2, ht / 2)
        rr = f' rx="{_n(r)}" ry="{_n(r)}"' if r > 0 else ""
        return (f'<rect{name} x="{_n(x)}" y="{_n(y)}" width="{_n(wd)}" height="{_n(ht)}"{rr} '
                f'{paint}{turn(*box_center(s))}/>')
    if t == "ellipse":
        cx, cy = box_center(s)
        return (f'<ellipse{name} cx="{_n(cx)}" cy="{_n(cy)}" rx="{_n(abs(p[2] - p[0]) / 2)}" '
                f'ry="{_n(abs(p[3] - p[1]) / 2)}" {paint}{turn(cx, cy)}/>')
    if t in ("line", "pen"):
        col = s.get("stroke") or s.get("fill") or "#000000"
        lp = (f'fill="none" stroke="{col}" stroke-width="{_n(max(1, w))}" stroke-linecap="round" '
              f'stroke-linejoin="round"{_dash(w) if prop(s, "dash") else ""}')
        if t == "line":
            return f'<line{name} x1="{_n(p[0])}" y1="{_n(p[1])}" x2="{_n(p[2])}" y2="{_n(p[3])}" {lp}/>'
        pts = list(zip(p[0::2], p[1::2]))
        d = [f"M{_n(pts[0][0])},{_n(pts[0][1])}"]
        for i in range(1, len(pts) - 1):
            mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
            d.append(f"Q{_n(pts[i][0])},{_n(pts[i][1])} {_n(mx)},{_n(my)}")
        d.append(f"L{_n(pts[-1][0])},{_n(pts[-1][1])}")
        return f'<path{name} d="{" ".join(d)}" {lp}/>'
    if t == "path":
        d, off = [], 0
        for n, closed in parts(s):
            a = node(s, off)[0]
            d.append(f"M{_n(a[0])},{_n(a[1])}")
            segs = [(i, i + 1) for i in range(off, off + n - 1)]
            if closed and n >= 2:
                segs.append((off + n - 1, off))
            for i, j in segs:
                p0, c1, c2, p1 = segment_points(s, i, j)
                if c1 == p0 and c2 == p1:
                    d.append(f"L{_n(p1[0])},{_n(p1[1])}")
                else:
                    d.append(f"C{_n(c1[0])},{_n(c1[1])} {_n(c2[0])},{_n(c2[1])} {_n(p1[0])},{_n(p1[1])}")
            if closed:
                d.append("Z")
            off += n
        rule = ' fill-rule="evenodd"' if len(parts(s)) > 1 else ""
        return f'<path{name} d="{" ".join(d)}" {paint}{rule}/>'
    if t == "polygon":
        pts = " ".join(f"{_n(x)},{_n(y)}" for x, y in zip(p[0::2], p[1::2]))
        return f'<polygon{name} points="{pts}" {paint}/>'
    if t == "text":
        col = s.get("fill") or s.get("stroke") or "#000000"
        family = s.get("font") or font_family
        weight = f' font-weight="{s["weight"]}"' if s.get("weight") else ""
        slant = f' font-style="{s["slant"]}"' if s.get("slant") else ""
        lines = s.get("text", "").split("\n")
        if len(lines) == 1:
            body = escape(lines[0])
        else:
            body = "".join(f'<tspan x="{_n(p[0])}" dy="{0 if k == 0 else 1.2}em">{escape(ln)}</tspan>'
                           for k, ln in enumerate(lines))
        return (f'<text{name} x="{_n(p[0])}" y="{_n(p[1])}" font-family={quoteattr(family + ", sans-serif")} '
                f'font-size="{_n(prop(s, "size"))}"{weight}{slant} fill="{col}" dominant-baseline="text-before-edge"'
                f'{turn(p[0], p[1])}>{body}</text>')
    return ""


def build_svg(shapes, artboard, font_family="sans-serif", layers=None):
    """``layers`` (bottom → top) become <g> elements named like the layer; hidden
    layers are written with display:none so nothing is lost."""
    x0, y0, x1, y1 = artboard
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0}" height="{y1 - y0}" '
           f'viewBox="{x0} {y0} {x1 - x0} {y1 - y0}">',
           f'  <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="#ffffff"/>']
    layer_list = layers or [{"id": None, "name": None, "visible": True}]
    for layer in layer_list:
        members = [s for s in shapes if layers is None or s.get("layer") == layer["id"]]
        if layers is not None and not members:
            continue
        pad = "  "
        if layers is not None:
            hide = "" if layer.get("visible", True) else ' style="display:none"'
            out.append(f'  <g id={quoteattr(str(layer["name"]))}{hide}>')
            pad = "    "
        open_gid = None
        for s in members:
            if prop(s, "hidden"):
                continue
            gid = s.get("gid")
            if gid != open_gid:
                if open_gid is not None:
                    out.append(pad + "</g>")
                if gid is not None:
                    out.append(pad + f'<g id="group-{gid}">')
                open_gid = gid
            indent = pad + "  " if gid is not None else pad
            out.append(indent + shape_to_svg(s, font_family))
        if open_gid is not None:
            out.append(pad + "</g>")
        if layers is not None:
            out.append("  </g>")
    out.append("</svg>")
    return "\n".join(out)


def export(path, shapes, artboard, font_family="sans-serif", layers=None):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_svg(shapes, artboard, font_family, layers))
