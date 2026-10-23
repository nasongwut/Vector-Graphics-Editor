"""Turn a PDF page (also the PDF part of a modern .ai file) into Vectra shapes.

Supported: paths (incl. compound paths), fill / stroke colours in Gray, RGB, CMYK,
ICC, spot (Separation/DeviceN) and indexed colour spaces, stroke width and dashes,
transforms, form XObjects, text (with ToUnicode). Gradients become their middle
colour; images, clipping masks, transparency and blend modes are skipped (counted
in ``notes``).
"""

import copy
import math
import re

from vectra.fileio.importers.common import (IDENT, ImportResult, PathBuilder, apply, decode_text_string,
                                            cmyk_hex, color_from_components, font_family_from, font_style_from,
                                            gray_hex, make_text, mat_mul, mat_scale, rgb_hex)
from vectra.fileio.importers.pdf import Name, PDFDocument, PDFError, Stream, tokenize_content

MAX_DEPTH = 12


# ── PostScript calculator functions (Type 4) ────────────────────────────────
def _eval_type4(code, inputs):
    toks = re.findall(rb"\{|\}|[^\s{}]+", code)

    def parse(i):
        out = []
        while i < len(toks):
            t = toks[i]
            if t == b"{":
                sub, i = parse(i + 1)
                out.append(sub)
            elif t == b"}":
                return out, i + 1
            else:
                out.append(t.decode("latin-1"))
                i += 1
        return out, i
    prog, _ = parse(0)
    if len(prog) == 1 and isinstance(prog[0], list):
        prog = prog[0]
    st = list(inputs)

    def run(p):
        for t in p:
            if isinstance(t, list):
                st.append(t)
                continue
            try:
                st.append(float(t))
                continue
            except ValueError:
                pass
            if t in ("add", "sub", "mul", "div", "exp", "max", "min", "atan"):
                b, a = st.pop(), st.pop()
                st.append({"add": a + b, "sub": a - b, "mul": a * b, "div": a / b if b else 0,
                           "exp": a ** b if a >= 0 else 0, "max": max(a, b), "min": min(a, b),
                           "atan": math.degrees(math.atan2(a, b))}[t])
            elif t in ("neg", "abs", "sqrt", "floor", "ceiling", "round", "truncate", "cvr", "cvi",
                       "sin", "cos", "ln", "log"):
                a = st.pop()
                st.append({"neg": -a, "abs": abs(a), "sqrt": math.sqrt(max(a, 0)), "floor": math.floor(a),
                           "ceiling": math.ceil(a), "round": round(a), "truncate": int(a), "cvr": a,
                           "cvi": int(a), "sin": math.sin(math.radians(a)), "cos": math.cos(math.radians(a)),
                           "ln": math.log(a) if a > 0 else 0, "log": math.log10(a) if a > 0 else 0}[t])
            elif t == "dup":
                st.append(st[-1])
            elif t == "pop":
                st.pop()
            elif t == "exch":
                st[-1], st[-2] = st[-2], st[-1]
            elif t == "copy":
                n = int(st.pop())
                st.extend(st[-n:] if n else [])
            elif t == "index":
                n = int(st.pop())
                st.append(st[-1 - n])
            elif t == "roll":
                j, n = int(st.pop()), int(st.pop())
                if n:
                    seg = st[-n:]
                    j %= n
                    st[-n:] = seg[-j:] + seg[:-j] if j else seg
            elif t in ("eq", "ne", "gt", "ge", "lt", "le"):
                b, a = st.pop(), st.pop()
                st.append({"eq": a == b, "ne": a != b, "gt": a > b, "ge": a >= b, "lt": a < b, "le": a <= b}[t])
            elif t in ("true", "false"):
                st.append(t == "true")
            elif t == "not":
                a = st.pop()
                st.append(not a if isinstance(a, bool) else ~int(a))
            elif t in ("and", "or"):
                b, a = st.pop(), st.pop()
                st.append((a and b) if t == "and" else (a or b))
            elif t == "if":
                proc, cond = st.pop(), st.pop()
                if cond:
                    run(proc)
            elif t == "ifelse":
                p2, p1, cond = st.pop(), st.pop(), st.pop()
                run(p1 if cond else p2)
    try:
        run(prog)
    except (IndexError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None
    return [float(v) for v in st if isinstance(v, (int, float))]


class PDFImporter:
    def __init__(self, doc):
        self.doc = doc
        self.notes = {"images": 0, "gradients": 0, "text": 0, "paths": 0}
        self._fonts = {}
        self.layers, self._layer_of_ocg, self._oc_stack = [], {}, []

    # ── helpers ─────────────────────────────────────────────────────────────
    def R(self, x):
        return self.doc.resolve(x)

    def _res(self, resources, cat, name):
        d = self.R(self.R(resources or {}).get(cat)) if isinstance(self.R(resources), dict) else None
        return self.R(d.get(str(name))) if isinstance(d, dict) else None

    # ── functions & colour spaces ───────────────────────────────────────────
    def eval_function(self, fn, inputs):
        fn = self.R(fn)
        if isinstance(fn, list):  # array of 1-out functions
            out = []
            for f in fn:
                out += self.eval_function(f, inputs) or [0.0]
            return out
        if not isinstance(fn, dict):
            return None
        ft = int(fn.get("FunctionType", -1))
        x = inputs[0] if inputs else 0.0
        if ft == 2:
            c0 = [float(v) for v in self.R(fn.get("C0")) or [0.0]]
            c1 = [float(v) for v in self.R(fn.get("C1")) or [1.0]]
            n = float(fn.get("N", 1))
            t = max(0.0, x) ** n
            return [a + t * (b - a) for a, b in zip(c0, c1)]
        if ft == 3:
            funcs = self.R(fn.get("Functions")) or []
            bounds = [float(b) for b in self.R(fn.get("Bounds")) or []]
            domain = [float(v) for v in self.R(fn.get("Domain")) or [0, 1]]
            enc = [float(v) for v in self.R(fn.get("Encode")) or []]
            k = 0
            while k < len(bounds) and x >= bounds[k]:
                k += 1
            k = min(k, len(funcs) - 1)
            lo = domain[0] if k == 0 else bounds[k - 1]
            hi = domain[1] if k >= len(bounds) else bounds[k]
            e0, e1 = (enc[2 * k], enc[2 * k + 1]) if len(enc) > 2 * k + 1 else (0.0, 1.0)
            t = e0 + (x - lo) / (hi - lo) * (e1 - e0) if hi != lo else e0
            return self.eval_function(funcs[k], [t]) if funcs else None
        if ft == 4 and isinstance(fn, Stream):
            return _eval_type4(self.doc.decode(fn), inputs)
        if ft == 0 and isinstance(fn, Stream):
            data = self.doc.decode(fn)
            rng = [float(v) for v in self.R(fn.get("Range")) or [0, 1]]
            nout = len(rng) // 2
            size = [int(v) for v in self.R(fn.get("Size")) or [2]]
            bps = int(fn.get("BitsPerSample", 8))
            if bps != 8 or not data:
                return None
            idx = int(round(max(0.0, min(1.0, x)) * (size[0] - 1)))
            vals = data[idx * nout:(idx + 1) * nout]
            return [rng[2 * i] + v / 255 * (rng[2 * i + 1] - rng[2 * i]) for i, v in enumerate(vals)]
        return None

    def cs_info(self, cs, resources):
        """Normalise a colour space to (kind, extra)."""
        cs = self.R(cs)
        if isinstance(cs, Name) or isinstance(cs, str):
            name = str(cs)
            if name in ("DeviceGray", "G", "CalGray"):
                return ("gray", None)
            if name in ("DeviceRGB", "RGB", "CalRGB"):
                return ("rgb", None)
            if name in ("DeviceCMYK", "CMYK"):
                return ("cmyk", None)
            if name == "Pattern":
                return ("pattern", None)
            sub = self._res(resources, "ColorSpace", name)
            if sub is not None and sub is not cs:
                return self.cs_info(sub, resources)
            return ("rgb", None)
        if isinstance(cs, list) and cs:
            kind = str(self.R(cs[0]))
            if kind == "ICCBased":
                st = self.R(cs[1])
                n = int(st.get("N", 3)) if isinstance(st, dict) else 3
                return {1: ("gray", None), 3: ("rgb", None), 4: ("cmyk", None)}.get(n, ("rgb", None))
            if kind in ("CalRGB", "Lab"):
                return ("rgb", None) if kind == "CalRGB" else ("lab", None)
            if kind == "CalGray":
                return ("gray", None)
            if kind in ("Separation", "DeviceN"):
                names = self.R(cs[1])
                alt = self.cs_info(cs[2], resources)
                return ("tint", (alt, cs[3], names))
            if kind == "Indexed":
                base = self.cs_info(cs[1], resources)
                lookup = self.R(cs[3])
                if isinstance(lookup, Stream):
                    lookup = self.doc.decode(lookup)
                return ("indexed", (base, lookup or b""))
            if kind == "Pattern":
                return ("pattern", None)
        return ("rgb", None)

    def to_hex(self, info, comps):
        kind, extra = info
        comps = [float(c) for c in comps if isinstance(c, (int, float))]
        if kind == "gray":
            return gray_hex(comps[0] if comps else 0)
        if kind == "rgb":
            return rgb_hex(*(comps + [0, 0, 0])[:3])
        if kind == "cmyk":
            return cmyk_hex(*(comps + [0, 0, 0, 0])[:4])
        if kind == "lab":
            L = comps[0] if comps else 50
            return gray_hex(L / 100)
        if kind == "tint":
            alt, fn, names = extra
            names = [str(n) for n in (names if isinstance(names, list) else [names])]
            if names == ["None"]:
                return None
            if names in (["All"], ["Black"]) and comps:
                return gray_hex(1 - comps[0])
            out = self.eval_function(fn, comps)
            if out:
                return self.to_hex(alt, out)
            return gray_hex(1 - (comps[0] if comps else 1))
        if kind == "indexed":
            base, lookup = extra
            n = {"gray": 1, "rgb": 3, "cmyk": 4}.get(base[0], 3)
            i = int(comps[0]) if comps else 0
            vals = lookup[i * n:(i + 1) * n] if isinstance(lookup, (bytes, bytearray)) else b""
            return self.to_hex(base, [v / 255 for v in vals]) if len(vals) == n else "#808080"
        return color_from_components(comps)

    def pattern_color(self, name, resources):
        pat = self._res(resources, "Pattern", name)
        self.notes["gradients"] += 1
        if not isinstance(pat, dict):
            return "#808080"
        if int(pat.get("PatternType", 1)) == 2:
            sh_ = self.R(pat.get("Shading"))
            if isinstance(sh_, dict):
                return self.shading_color(sh_, resources)
        return "#808080"

    def shading_color(self, shading, resources):
        info = self.cs_info(shading.get("ColorSpace"), resources)
        fn = shading.get("Function")
        if fn is not None:
            dom = [float(v) for v in self.R(shading.get("Domain")) or [0, 1]]
            out = self.eval_function(fn, [(dom[0] + dom[-1]) / 2])
            if out:
                return self.to_hex(info, out)
        return "#808080"

    # ── fonts ───────────────────────────────────────────────────────────────
    def font(self, name, resources):
        fd = self._res(resources, "Font", name)
        key = id(fd)
        if key not in self._fonts:
            self._fonts[key] = PDFFont(self, fd if isinstance(fd, dict) else {})
        return self._fonts[key]

    # ── page ────────────────────────────────────────────────────────────────
    def page_box(self, page):
        box = self.R(page.get("CropBox")) or self.R(page.get("MediaBox")) or [0, 0, 612, 792]
        box = [float(self.R(v)) for v in box]
        x0, x1 = sorted((box[0], box[2]))
        y0, y1 = sorted((box[1], box[3]))
        return x0, y0, x1, y1

    def import_page(self, page):
        x0, y0, x1, y1 = self.page_box(page)
        self.flip = lambda x, y: (round(x - x0, 4), round(y1 - y, 4))
        self.shapes = []
        self._setup_layers()
        content = self.doc.page_content(page)
        self.run(content, page.get("Resources"), IDENT, 0)
        return ImportResult(self.shapes, [0, 0, round(x1 - x0, 3), round(y1 - y0, 3)], self.notes,
                            layers=self.layers)

    # ── layers (optional content groups = Illustrator layers) ───────────────
    def _setup_layers(self):
        try:
            cat = self.doc.catalog()
        except PDFError:
            return
        ocp = self.R(cat.get("OCProperties"))
        if not isinstance(ocp, dict):
            return
        ocgs = [self.R(x) for x in (self.R(ocp.get("OCGs")) or [])]
        ocgs = [o for o in ocgs if isinstance(o, dict)]
        d = self.R(ocp.get("D")) or {}

        def flat(arr, out):
            for x in self.R(arr) or []:
                x = self.R(x)
                if isinstance(x, list):
                    flat(x, out)
                elif isinstance(x, dict):
                    out.append(x)
            return out
        order = flat(d.get("Order"), [])          # panel order: top layer first
        off = {id(o) for o in flat(d.get("OFF"), [])}
        locked = {id(o) for o in flat(d.get("Locked"), [])}
        bottom_to_top = list(reversed(order)) if order else list(ocgs)
        for o in ocgs:
            if all(o is not x for x in bottom_to_top):
                bottom_to_top.append(o)
        for o in bottom_to_top:
            if id(o) in self._layer_of_ocg:
                continue
            lid = len(self.layers) + 1
            name = self.R(o.get("Name"))
            self.layers.append({"id": lid, "name": decode_text_string(name) if name else f"Layer {lid}",
                                "visible": id(o) not in off, "locked": id(o) in locked, "color": None})
            self._layer_of_ocg[id(o)] = lid

    def _oc_layer(self, props, resources):
        """Layer id for a /OC marked-content property (name or inline dict)."""
        if isinstance(props, Name):
            props = self._res(resources, "Properties", props)
        props = self.R(props)
        if isinstance(props, dict) and str(props.get("Type")) == "OCMD":
            members = self.R(props.get("OCGs"))
            props = self.R(members[0]) if isinstance(members, list) and members else self.R(members)
        if isinstance(props, dict):
            return self._layer_of_ocg.get(id(props))
        return None

    def current_layer(self):
        for lid in reversed(self._oc_stack):
            if lid is not None:
                return lid
        return None

    def run(self, data, resources, ctm, depth):
        if depth > MAX_DEPTH:
            return
        resources = self.R(resources) or {}
        gs = {"ctm": ctm, "fill": "#000000", "stroke": "#000000", "fcs": ("gray", None),
              "scs": ("gray", None), "lw": 1.0, "dash": False, "ca": 1.0, "CA": 1.0,
              "font": None, "size": 12.0, "tc": 0.0, "tw": 0.0, "th": 1.0, "tl": 0.0,
              "rise": 0.0, "tr": 0}
        stack = []
        path = PathBuilder()
        clip_pending = False
        tm = tlm = IDENT
        runs = []

        def P(x, y):
            return apply(gs["ctm"], float(x), float(y))

        def paint(fill, stroke, evenodd=False):
            nonlocal clip_pending
            clip_pending = False
            f = gs["fill"] if fill and gs["ca"] > 0 else None
            s = gs["stroke"] if stroke and gs["CA"] > 0 else None
            if f or s:
                shape = path.to_shape(self.flip, f, s, gs["lw"] * mat_scale(gs["ctm"]), gs["dash"],
                                      close_for_fill=True)
                if shape:
                    lid = self.current_layer()
                    if lid is not None:
                        shape["layer"] = lid
                    self.shapes.append(shape)
                    self.notes["paths"] += 1
            path.clear()

        def flush_text():
            lid = self.current_layer()
            for r in _merge_runs(runs):
                if lid is not None:
                    r["layer"] = lid
                self.shapes.append(r)
                self.notes["text"] += 1
            runs.clear()

        def show(items):
            nonlocal tm
            if gs["font"] is None:
                return
            font = gs["font"]
            size = gs["size"]
            for it in items:
                if isinstance(it, (int, float)):
                    tx = -float(it) / 1000 * size * gs["th"]
                    tm = mat_mul((1, 0, 0, 1, tx, 0), tm)
                    if -float(it) > 180 and runs:
                        runs[-1]["gap"] = True
                    continue
                if not isinstance(it, (bytes, bytearray)):
                    continue
                glyphs = font.decode(it)
                text = "".join(ch for _code, ch in glyphs)
                trm = mat_mul((size * gs["th"], 0, 0, size, 0, gs["rise"]), mat_mul(tm, gs["ctm"]))
                ox, oy = trm[4], trm[5]
                dev_size = math.hypot(trm[2], trm[3])
                width = 0.0
                for code, ch in glyphs:
                    w = font.width(code) / 1000 * size + gs["tc"] + (gs["tw"] if ch == " " else 0)
                    width += w * gs["th"]
                tm = mat_mul((1, 0, 0, 1, width, 0), tm)
                end = apply(mat_mul(tm, gs["ctm"]), 0, gs["rise"])
                if gs["tr"] in (3, 7) or not text.strip("\x00"):
                    continue
                ang = math.degrees(math.atan2(trm[1], trm[0]))
                runs.append({"text": text.replace("\x00", ""), "o": (ox, oy), "end": end,
                             "size": dev_size, "color": gs["fill"] if gs["tr"] not in (1,) else gs["stroke"],
                             "font": font.family, "style": font.style, "ang": ang, "flip": self.flip, "gap": False})

        for ops, op in tokenize_content(data):
            try:
                if op == "q":
                    stack.append(copy.copy(gs))
                elif op == "Q":
                    if stack:
                        gs = stack.pop()
                elif op == "cm" and len(ops) >= 6:
                    gs["ctm"] = mat_mul(tuple(float(v) for v in ops[-6:]), gs["ctm"])
                elif op == "w" and ops:
                    gs["lw"] = float(ops[-1])
                elif op == "d" and ops:
                    arr = ops[0] if isinstance(ops[0], list) else []
                    gs["dash"] = bool([v for v in arr if isinstance(v, (int, float)) and v > 0])
                elif op == "gs" and ops:
                    eg = self._res(resources, "ExtGState", ops[-1])
                    if isinstance(eg, dict):
                        if "LW" in eg:
                            gs["lw"] = float(self.R(eg["LW"]))
                        if "ca" in eg:
                            gs["ca"] = float(self.R(eg["ca"]))
                        if "CA" in eg:
                            gs["CA"] = float(self.R(eg["CA"]))
                # path construction
                elif op == "m" and len(ops) >= 2:
                    path.moveto(*P(*ops[-2:]))
                elif op == "l" and len(ops) >= 2:
                    path.lineto(*P(*ops[-2:]))
                elif op == "c" and len(ops) >= 6:
                    a, b, c = P(*ops[-6:-4]), P(*ops[-4:-2]), P(*ops[-2:])
                    path.curveto(*a, *b, *c)
                elif op == "v" and len(ops) >= 4:
                    cur = path.current() or P(0, 0)
                    b, c = P(*ops[-4:-2]), P(*ops[-2:])
                    path.curveto(*cur, *b, *c)
                elif op == "y" and len(ops) >= 4:
                    a, c = P(*ops[-4:-2]), P(*ops[-2:])
                    path.curveto(*a, *c, *c)
                elif op == "h":
                    path.closepath()
                elif op == "re" and len(ops) >= 4:
                    path.rect(gs["ctm"], *(float(v) for v in ops[-4:]))
                elif op in ("W", "W*"):
                    clip_pending = True
                # painting
                elif op in ("f", "F", "f*"):
                    paint(True, False)
                elif op == "S":
                    paint(False, True)
                elif op == "s":
                    path.closepath()
                    paint(False, True)
                elif op in ("B", "B*"):
                    paint(True, True)
                elif op in ("b", "b*"):
                    path.closepath()
                    paint(True, True)
                elif op == "n":
                    path.clear()
                    clip_pending = False
                # colour
                elif op in ("g", "G") and ops:
                    k = "fill" if op == "g" else "stroke"
                    gs[k] = gray_hex(float(ops[-1]))
                    gs["fcs" if op == "g" else "scs"] = ("gray", None)
                elif op in ("rg", "RG") and len(ops) >= 3:
                    k = "fill" if op == "rg" else "stroke"
                    gs[k] = rgb_hex(*(float(v) for v in ops[-3:]))
                    gs["fcs" if op == "rg" else "scs"] = ("rgb", None)
                elif op in ("k", "K") and len(ops) >= 4:
                    k = "fill" if op == "k" else "stroke"
                    gs[k] = cmyk_hex(*(float(v) for v in ops[-4:]))
                    gs["fcs" if op == "k" else "scs"] = ("cmyk", None)
                elif op in ("cs", "CS") and ops:
                    info = self.cs_info(ops[-1], resources)
                    gs["fcs" if op == "cs" else "scs"] = info
                    default = {"gray": "#000000", "cmyk": "#000000", "rgb": "#000000"}.get(info[0], "#000000")
                    gs["fill" if op == "cs" else "stroke"] = default
                elif op in ("sc", "scn", "SC", "SCN"):
                    target = "fill" if op in ("sc", "scn") else "stroke"
                    info = gs["fcs" if target == "fill" else "scs"]
                    if ops and isinstance(ops[-1], Name):
                        gs[target] = self.pattern_color(ops[-1], resources)
                    else:
                        gs[target] = self.to_hex(info, ops)
                elif op == "sh":
                    self.notes["gradients"] += 1
                # marked content: /OC … BDC = Illustrator layer
                elif op == "BDC" and len(ops) >= 2:
                    self._oc_stack.append(self._oc_layer(ops[-1], resources) if str(ops[-2]) == "OC" else None)
                elif op == "BMC":
                    self._oc_stack.append(None)
                elif op == "EMC":
                    if self._oc_stack:
                        self._oc_stack.pop()
                # XObjects
                elif op == "Do" and ops:
                    xo = self._res(resources, "XObject", ops[-1])
                    if isinstance(xo, Stream):
                        sub = str(xo.get("Subtype"))
                        if sub == "Form":
                            m = tuple(float(self.R(v)) for v in (self.R(xo.get("Matrix")) or IDENT))
                            oc = xo.get("OC")
                            if oc is not None:
                                self._oc_stack.append(self._oc_layer(oc, resources))
                            self.run(self.doc.decode(xo), xo.get("Resources") or resources,
                                     mat_mul(m, gs["ctm"]), depth + 1)
                            if oc is not None and self._oc_stack:
                                self._oc_stack.pop()
                        elif sub == "Image":
                            self.notes["images"] += 1
                # text
                elif op == "BT":
                    tm = tlm = IDENT
                elif op == "ET":
                    flush_text()
                elif op == "Tf" and len(ops) >= 2:
                    gs["font"] = self.font(ops[-2], resources)
                    gs["size"] = float(ops[-1])
                elif op == "Tc" and ops:
                    gs["tc"] = float(ops[-1])
                elif op == "Tw" and ops:
                    gs["tw"] = float(ops[-1])
                elif op == "Tz" and ops:
                    gs["th"] = float(ops[-1]) / 100
                elif op == "TL" and ops:
                    gs["tl"] = float(ops[-1])
                elif op == "Ts" and ops:
                    gs["rise"] = float(ops[-1])
                elif op == "Tr" and ops:
                    gs["tr"] = int(ops[-1])
                elif op in ("Td", "TD") and len(ops) >= 2:
                    tx, ty = float(ops[-2]), float(ops[-1])
                    if op == "TD":
                        gs["tl"] = -ty
                    tlm = mat_mul((1, 0, 0, 1, tx, ty), tlm)
                    tm = tlm
                elif op == "Tm" and len(ops) >= 6:
                    tlm = tm = tuple(float(v) for v in ops[-6:])
                elif op == "T*":
                    tlm = mat_mul((1, 0, 0, 1, 0, -gs["tl"]), tlm)
                    tm = tlm
                elif op == "Tj" and ops:
                    show([ops[-1]])
                elif op == "TJ" and ops and isinstance(ops[-1], list):
                    show(ops[-1])
                elif op in ("'", '"') and ops:
                    if op == '"' and len(ops) >= 3:
                        gs["tw"], gs["tc"] = float(ops[-3]), float(ops[-2])
                    tlm = mat_mul((1, 0, 0, 1, 0, -gs["tl"]), tlm)
                    tm = tlm
                    show([ops[-1]])
            except (TypeError, ValueError, IndexError, ZeroDivisionError):
                continue
        flush_text()


def _merge_runs(runs):
    """Join runs on the same baseline into text objects."""
    out, cur = [], None
    for r in runs:
        if cur is not None and abs(r["ang"] - cur["ang"]) < 0.5 and abs(r["size"] - cur["size"]) < 0.5 \
                and r["color"] == cur["color"] and r["font"] == cur["font"] \
                and r.get("style") == cur.get("style"):
            ex, ey = cur["end"]
            ox, oy = r["o"]
            a = math.radians(cur["ang"])
            along = (ox - ex) * math.cos(a) + (oy - ey) * math.sin(a)
            across = -(ox - ex) * math.sin(a) + (oy - ey) * math.cos(a)
            if abs(across) < cur["size"] * 0.3 and -cur["size"] * 0.6 < along < cur["size"] * 1.5:
                sep = " " if (along > cur["size"] * 0.22 or cur.get("gap")) and not cur["text"].endswith(" ") \
                    and not r["text"].startswith(" ") else ""
                cur["text"] += sep + r["text"]
                cur["end"] = r["end"]
                cur["gap"] = r.get("gap")
                continue
        if cur is not None:
            out.append(_run_to_shape(cur))
        cur = dict(r)
    if cur is not None:
        out.append(_run_to_shape(cur))
    return out


def _run_to_shape(r):
    flip = r["flip"]
    x, y = flip(*r["o"])
    rot = -r["ang"]                      # PDF is y-up (counter-clockwise); screen rot is clockwise
    a = math.radians(rot)
    asc = r["size"] * 0.8
    tx, ty = x + asc * math.sin(a), y - asc * math.cos(a)
    return make_text(round(tx, 3), round(ty, 3), r["text"].strip("\r\n"), r["size"], r["color"],
                     r["font"], round(rot, 3) if abs(rot) > 0.01 else 0, r.get("style") or (None, None))


# ── fonts ───────────────────────────────────────────────────────────────────
_GLYPHS = {"space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$", "percent": "%",
           "ampersand": "&", "quotesingle": "'", "quoteright": "’", "quoteleft": "‘", "parenleft": "(",
           "parenright": ")", "asterisk": "*", "plus": "+", "comma": ",", "hyphen": "-", "minus": "−",
           "period": ".", "slash": "/", "colon": ":", "semicolon": ";", "less": "<", "equal": "=",
           "greater": ">", "question": "?", "at": "@", "bracketleft": "[", "backslash": "\\",
           "bracketright": "]", "underscore": "_", "braceleft": "{", "bar": "|", "braceright": "}",
           "asciitilde": "~", "endash": "–", "emdash": "—", "bullet": "•", "copyright": "©",
           "registered": "®", "trademark": "™", "quotedblleft": "“", "quotedblright": "”",
           "ellipsis": "…", "degree": "°", "fi": "fi", "fl": "fl"}
_DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def _glyph_to_char(name):
    if name in _GLYPHS:
        return _GLYPHS[name]
    if name in _DIGITS:
        return str(_DIGITS.index(name))
    if len(name) == 1:
        return name
    m = re.fullmatch(r"uni([0-9A-Fa-f]{4,6})", name) or re.fullmatch(r"u([0-9A-Fa-f]{4,6})", name)
    if m:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return ""
    return ""


def parse_cmap(data):
    """ToUnicode CMap -> ({code: str}, code_bytes)."""
    out = {}
    nbytes = 1
    m = re.search(rb"begincodespacerange\s*<([0-9A-Fa-f]+)>", data)
    if m:
        nbytes = max(1, len(m.group(1)) // 2)

    def u16(h):
        try:
            return bytes.fromhex(h.decode("latin-1")).decode("utf-16-be", errors="ignore")
        except ValueError:
            return ""
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", block):
            out[int(src, 16)] = u16(dst)
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for lo, hi, rest in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]*>)", block):
            lo, hi = int(lo, 16), int(hi, 16)
            if rest.startswith(b"["):
                for k, h in enumerate(re.findall(rb"<([0-9A-Fa-f]*)>", rest)):
                    out[lo + k] = u16(h)
            else:
                base = rest[1:-1]
                if not base:
                    continue
                start = int(base, 16)
                width = len(base)
                for k in range(min(hi - lo + 1, 65536)):
                    out[lo + k] = u16(format(start + k, f"0{width}X").encode())
    return out, nbytes


class PDFFont:
    def __init__(self, imp, fd):
        R = imp.R
        self.subtype = str(fd.get("Subtype", ""))
        self.family = font_family_from(R(fd.get("BaseFont")))
        self.style = font_style_from(R(fd.get("BaseFont")))
        self.two_byte = self.subtype == "Type0"
        self.map = {}
        tu = R(fd.get("ToUnicode"))
        if isinstance(tu, Stream):
            self.map, nb = parse_cmap(imp.doc.decode(tu))
            if self.two_byte:
                self.two_byte = nb != 1
        self.widths, self.first, self.default_w = {}, 0, 500.0
        if self.two_byte:
            desc = R(fd.get("DescendantFonts"))
            d0 = R(desc[0]) if isinstance(desc, list) and desc else {}
            if isinstance(d0, dict):
                if self.family is None:
                    self.family = font_family_from(R(d0.get("BaseFont")))
                    self.style = font_style_from(R(d0.get("BaseFont")))
                self.default_w = float(R(d0.get("DW", 1000)))
                w = R(d0.get("W")) or []
                i = 0
                while i < len(w):
                    c = R(w[i])
                    nxt = R(w[i + 1]) if i + 1 < len(w) else None
                    if isinstance(nxt, list):
                        for k, v in enumerate(nxt):
                            self.widths[int(c) + k] = float(R(v))
                        i += 2
                    else:
                        last, v = int(nxt or c), float(R(w[i + 2]) if i + 2 < len(w) else self.default_w)
                        for code in range(int(c), last + 1):
                            self.widths[code] = v
                        i += 3
        else:
            self.first = int(R(fd.get("FirstChar", 0)) or 0)
            ws = R(fd.get("Widths")) or []
            for k, v in enumerate(ws):
                self.widths[self.first + k] = float(R(v))
            enc = R(fd.get("Encoding"))
            if isinstance(enc, dict):
                diffs = R(enc.get("Differences")) or []
                code = 0
                for d in diffs:
                    d = R(d)
                    if isinstance(d, (int, float)):
                        code = int(d)
                    else:
                        ch = _glyph_to_char(str(d))
                        if ch and code not in self.map:
                            self.map[code] = ch
                        code += 1

    def decode(self, b):
        out = []
        if self.two_byte:
            for i in range(0, len(b) - 1, 2):
                code = (b[i] << 8) | b[i + 1]
                out.append((code, self.map.get(code, "")))
        else:
            for code in b:
                ch = self.map.get(code)
                if ch is None:
                    ch = bytes([code]).decode("cp1252", errors="replace")
                out.append((code, ch))
        return out

    def width(self, code):
        return self.widths.get(code, self.default_w if self.two_byte else 500.0)


# ── entry points ────────────────────────────────────────────────────────────
def illustrator_private_data(doc, page):
    """Native Illustrator data stored inside the PDF (AI9+), decompressed, or None."""
    pi = doc.resolve(page.get("PieceInfo"))
    ill = doc.resolve(pi.get("Illustrator")) if isinstance(pi, dict) else None
    priv = doc.resolve(ill.get("Private")) if isinstance(ill, dict) else None
    if not isinstance(priv, dict):
        return None
    keys = sorted((k for k in priv if k.startswith("AIPrivateData")),
                  key=lambda k: int(re.sub(r"\D", "", k) or 0))
    raw = b""
    for k in keys:
        st = doc.resolve(priv[k])
        if isinstance(st, Stream):
            raw += doc.decode(st)
    return decompress_ai_private(raw) if raw else None


def decompress_ai_private(raw):
    if raw.startswith(b"%AI12_CompressedData"):
        import zlib
        body = raw[len(b"%AI12_CompressedData"):]
        try:
            return zlib.decompressobj().decompress(body)
        except zlib.error:
            return None
    if raw.startswith(b"%AI24_ZStandard_Data"):
        from vectra.fileio.importers.zstd import ZstdError, decompress
        try:
            return decompress(raw[len(b"%AI24_ZStandard_Data"):])
        except (ZstdError, IndexError, ValueError):
            return None
    return raw


def import_pdf_bytes(data, page_index=0):
    doc = PDFDocument(data)
    pages = doc.pages()
    if not pages:
        raise PDFError("no pages")
    page = pages[min(page_index, len(pages) - 1)]
    imp = PDFImporter(doc)

    # Illustrator's own data keeps groups, layer colours and sub-structure that the
    # PDF copy flattens away — prefer it when it holds the same artwork.
    priv = illustrator_private_data(doc, page)
    if priv:
        from vectra.fileio.importers.ps_import import import_ps_bytes
        box = imp.page_box(page)
        try:
            alt = import_ps_bytes(priv, artboard_hint=[0, 0, box[2] - box[0], box[3] - box[1]])
        except Exception:  # noqa: BLE001 - never worse than reading the PDF
            alt = None
        if alt is not None and alt.shapes and _matches_pdf(doc, page, box, alt):
            alt.notes["from_private"] = 1
            alt.notes["pages"] = len(pages)
            return alt

    res = imp.import_page(page)
    res.notes["pages"] = len(pages)
    texts = " ".join(s.get("text", "") for s in res.shapes if s["type"] == "text")
    if "PDF Content" in texts or "without PDF" in texts:
        if priv:
            from vectra.fileio.importers.ps_import import import_ps_bytes
            alt = import_ps_bytes(priv, artboard_hint=res.artboard)
            if alt.shapes:
                alt.notes["from_private"] = 1
                return alt
        res.notes["no_pdf_content"] = 1
    return res


_PAINT_RE = re.compile(rb"(?<![^\s\]>)])(?:f\*?|F|S|s|B\*?|b\*?)(?=[\s\[(/<]|$)")
_SHOW_RE = re.compile(rb"(?<![^\s\])])(?:Tj|TJ|'|\")(?=\s|$)")


def _matches_pdf(doc, page, box, native):
    """Cheap check that the native data reproduces what the PDF page paints:
    same artboard size and (almost) as many painted paths / text runs."""
    a = native.artboard
    if abs((a[2] - a[0]) - (box[2] - box[0])) > 2 or abs((a[3] - a[1]) - (box[3] - box[1])) > 2:
        return False
    content = doc.page_content(page)
    if b"PDF Content" in content or b"without PDF" in content:
        return True
    p_paths = len(_PAINT_RE.findall(content))
    p_text = len(_SHOW_RE.findall(content))
    n_paths = sum(1 for s in native.shapes if s["type"] != "text")
    n_text = sum(1 for s in native.shapes if s["type"] == "text")
    if p_paths and n_paths < 0.85 * p_paths:
        return False
    if p_text and n_text == 0 and n_paths < 0.85 * (p_paths + p_text):
        return False   # live text in the PDF that the native reader could not rebuild
    return True
