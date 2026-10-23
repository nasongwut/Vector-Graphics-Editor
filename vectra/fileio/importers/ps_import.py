"""PostScript / EPS and legacy (PostScript-based) Illustrator importer.

A small PostScript interpreter that understands:

* the core language a typical EPS uses for vector art: procedures and ``def``,
  stack / math / control operators, gsave/grestore, CTM operators, paths
  (incl. arc/arcn, relative ops, rect*), fill/stroke, colours, dashes, ``show``;
* the Illustrator file-format operators (m L C v y f F s S b B n N, g G k K x X
  Xa XA Xx XX, *u *U compound paths, u U groups, To Tp Tf Tx … text), which is
  what legacy .ai files, Illustrator EPS files and the native data inside modern
  .ai files are written in.

For Illustrator-made files the (huge) procset prolog is skipped and the built-in
meaning of the operators is used. Unsupported things (images, gradients, clipping,
patterns) are skipped and counted in ``notes``.
"""

import math
import re

from vectra.fileio.importers.common import (IDENT, ImportResult, PathBuilder, apply, cmyk_hex,
                                            decode_text_string,
                                            font_family_from, font_style_from, gray_hex, make_text, mat_mul,
                                            mat_scale, rgb_hex)

MAX_OPS = 3_000_000
MAX_DEPTH = 60


class LitName(str):
    """/name"""


class Mark:
    pass


MARK = Mark()


class Proc(list):
    """{ ... } executable array"""


class PSError(ValueError):
    pass


# ── tokenizer ───────────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(
    rb"""
    (?P<ws>[\s\x00]+)
  | (?P<comment>%[^\r\n]*)
  | (?P<str>\()
  | (?P<dictopen><<) | (?P<dictclose>>>)
  | (?P<hex><[0-9A-Fa-f\s]*>)
  | (?P<a85><~.*?~>)
  | (?P<open>[\[{]) | (?P<close>[\]}])
  | (?P<lit>/[^\s()<>\[\]{}/%]*)
  | (?P<word>[^\s()<>\[\]{}/%]+)
    """, re.X | re.S)
_NUM_RE = re.compile(rb"[+-]?(\d+\.?\d*([eE][+-]?\d+)?|\.\d+([eE][+-]?\d+)?)$")
_RADIX_RE = re.compile(rb"(\d+)#([0-9A-Za-z]+)$")


def _read_string(data, pos):
    depth, out, n = 1, bytearray(), len(data)
    while pos < n:
        ch = data[pos]
        pos += 1
        if ch == 0x5C and pos < n:
            e = data[pos]
            pos += 1
            if e in b"nrtbf":
                out += {0x6E: b"\n", 0x72: b"\r", 0x74: b"\t", 0x62: b"\b", 0x66: b"\f"}[e]
            elif 0x30 <= e <= 0x37:
                digits = bytes([e])
                while len(digits) < 3 and pos < n and 0x30 <= data[pos] <= 0x37:
                    digits += bytes([data[pos]])
                    pos += 1
                out.append(int(digits, 8) & 0xFF)
            elif e in b"\r\n":
                if e == 0x0D and pos < n and data[pos] == 0x0A:
                    pos += 1
            else:
                out.append(e)
        elif ch == 0x28:
            depth += 1
            out.append(ch)
        elif ch == 0x29:
            depth -= 1
            if depth == 0:
                break
            out.append(ch)
        else:
            out.append(ch)
    return bytes(out), pos


def tokenize(data):
    """Parse the whole program into a flat list where {...} are nested Proc lists."""
    root = []
    stack = [root]
    pos, n = 0, len(data)
    while pos < n:
        m = _TOKEN_RE.match(data, pos)
        if not m:
            pos += 1
            continue
        kind = m.lastgroup
        tok = m.group(kind)
        pos = m.end()
        cur = stack[-1]
        if kind in ("ws", "comment"):
            if kind == "comment" and tok.startswith(b"%%BeginData:"):
                pos = _skip_data(data, pos, tok)
            elif kind == "comment" and tok.startswith(b"%%BeginBinary:"):
                try:
                    pos += int(tok.split(b":")[1].split()[0])
                except (ValueError, IndexError):
                    pass
            continue
        if kind == "str":
            s, pos = _read_string(data, pos)
            cur.append(s)
        elif kind == "hex":
            h = re.sub(rb"\s", b"", tok[1:-1])
            if len(h) % 2:
                h += b"0"
            cur.append(bytes.fromhex(h.decode("latin-1")) if h else b"")
        elif kind == "a85":
            cur.append(b"")
        elif kind == "open":
            if tok == b"{":
                p = Proc()
                cur.append(p)
                stack.append(p)
            else:
                cur.append("[")
        elif kind == "close":
            if tok == b"}":
                if len(stack) > 1:
                    stack.pop()
            else:
                cur.append("]")
        elif kind == "dictopen":
            cur.append("<<")
        elif kind == "dictclose":
            cur.append(">>")
        elif kind == "lit":
            cur.append(LitName(tok[1:].lstrip(b"/").decode("latin-1")))
        else:
            if _NUM_RE.match(tok):
                cur.append(float(tok) if (b"." in tok or b"e" in tok.lower()) else int(tok))
            elif _RADIX_RE.match(tok):
                r, v = _RADIX_RE.match(tok).groups()
                try:
                    cur.append(int(v, int(r)))
                except ValueError:
                    cur.append(tok.decode("latin-1"))
            else:
                cur.append(tok.decode("latin-1"))
    return root


def _skip_data(data, pos, header):
    """%%BeginData: <n> [Hex|Binary|ASCII] [Bytes|Lines]"""
    parts = header.split(b":", 1)[1].split()
    try:
        count = int(parts[0])
    except (ValueError, IndexError):
        return pos
    unit = parts[2] if len(parts) > 2 else b"Bytes"
    # the data starts on the line after the operator line that follows the comment
    nl = data.find(b"\n", pos)
    if nl < 0:
        return len(data)
    start = nl + 1
    if unit.lower().startswith(b"line"):
        p = start
        for _ in range(count):
            q = data.find(b"\n", p)
            if q < 0:
                return len(data)
            p = q + 1
        return p
    return start + count


# ── helpers ─────────────────────────────────────────────────────────────────
def _arc_to_beziers(cx, cy, r, a1, a2, clockwise):
    """Yield cubic segments (p0, c1, c2, p3) approximating an arc (angles in degrees)."""
    if clockwise:
        while a2 > a1:
            a2 -= 360
    else:
        while a2 < a1:
            a2 += 360
    total = a2 - a1
    n = max(1, int(math.ceil(abs(total) / 90 - 1e-9)))
    step = math.radians(total / n)
    k = 4 / 3 * math.tan(step / 4)
    a = math.radians(a1)
    for _ in range(n):
        b = a + step
        p0 = (cx + r * math.cos(a), cy + r * math.sin(a))
        p3 = (cx + r * math.cos(b), cy + r * math.sin(b))
        c1 = (p0[0] - k * r * math.sin(a), p0[1] + k * r * math.cos(a))
        c2 = (p3[0] + k * r * math.sin(b), p3[1] - k * r * math.cos(b))
        yield p0, c1, c2, p3
        a = b


def _hsb_hex(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return rgb_hex(r, g, b)


def _tinted(hexcol, tint):
    """Mix a colour with white by (1 - tint)."""
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    t = max(0.0, min(1.0, float(tint)))
    return rgb_hex(1 - t * (1 - r), 1 - t * (1 - g), 1 - t * (1 - b))


def find_bbox(data):
    # Illustrator: the artboard (crop marks) — not the art's bounding box
    for key in (rb"%AI3_Cropmarks:", rb"%%HiResBoundingBox:", rb"%%BoundingBox:"):
        m = re.search(key + rb"\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", data[:200000])
        if m:
            x0, y0, x1, y1 = (float(v) for v in m.groups())
            if x1 > x0 and y1 > y0:
                return x0, y0, x1, y1
    return None


def strip_dos_eps(data):
    """Binary 'DOS EPS' wrapper (C5 D0 D3 C6) -> the PostScript section."""
    if data[:4] == b"\xC5\xD0\xD3\xC6":
        start = int.from_bytes(data[4:8], "little")
        length = int.from_bytes(data[8:12], "little")
        return data[start:start + length]
    return data


# ── interpreter ─────────────────────────────────────────────────────────────
AI_OPS = {"m", "l", "L", "c", "C", "v", "V", "y", "Y", "h", "H", "f", "F", "s", "S", "b", "B", "n", "N",
          "g", "G", "k", "K", "x", "X", "Xa", "XA", "Xx", "XX", "w", "d", "j", "J", "M", "*u", "*U", "u", "U",
          "q", "Q", "O", "R", "A", "D", "W", "To", "TO", "Tp", "TP", "Tf", "Tx", "TX", "Tj", "Tk", "Tr",
          "Bb", "BB", "Bg", "Bm", "Bc", "BD", "Bh", "Bn", "Bs", "Lb", "LB", "Ln", "p", "P", "XR",
          "Xy", "XW", "Ap", "Ar", "XP"}


class GState:
    __slots__ = ("ctm", "fill", "stroke", "lw", "dash", "path", "font", "size")

    def __init__(self):
        self.ctm = IDENT
        self.fill = "#000000"
        self.stroke = "#000000"
        self.lw = 1.0
        self.dash = False
        self.path = PathBuilder()
        self.font = None
        self.size = 12.0

    def copy(self):
        g = GState()
        g.ctm, g.fill, g.stroke, g.lw, g.dash = self.ctm, self.fill, self.stroke, self.lw, self.dash
        g.font, g.size = self.font, self.size
        g.path = PathBuilder()
        g.path.parts = [{"nodes": [list(nd) for nd in p["nodes"]], "closed": p["closed"]}
                        for p in self.path.parts]
        g.path._after_close = self.path._after_close
        return g


class PSInterpreter:
    def __init__(self, flip, ai_mode=False):
        self.flip = flip
        self.ai_mode = ai_mode
        self.st = []
        self.dicts = [{}]
        self.gs = GState()
        self.gstack = []
        self.shapes = []
        self.notes = {"images": 0, "gradients": 0, "text": 0, "paths": 0}
        self.ops = 0
        self.compound = None      # PathBuilder collecting *u … *U
        self.group_depth = 0
        self.group_id = None
        self.group_stack = []
        self._next_gid = 1
        self.layers, self.layer_stack = [], []
        self.text = None          # current AI text object
        self.cur_point = None

    # stack helpers ----------------------------------------------------------
    def pop(self):
        return self.st.pop() if self.st else 0

    def popn(self, n):
        if len(self.st) < n:
            raise IndexError
        vals = self.st[-n:]
        del self.st[-n:]
        return vals

    def nums(self, n):
        vals = self.popn(n)
        return [float(v) for v in vals]

    def lookup(self, name):
        for d in reversed(self.dicts):
            if name in d:
                return d[name], True
        return None, False

    # execution --------------------------------------------------------------
    def run(self, tokens, depth=0):
        if depth > MAX_DEPTH:
            return
        for tok in tokens:
            self.ops += 1
            if self.ops > MAX_OPS:
                raise PSError("program too long")
            if isinstance(tok, str) and not isinstance(tok, LitName) and tok not in ("[", "]", "<<", ">>"):
                self.exec_name(tok, depth)
            elif tok == "[" or tok == "<<":
                self.st.append(MARK)
            elif tok == "]":
                self._close_array()
            elif tok == ">>":
                self._close_dict()
            else:
                self.st.append(tok)
            if len(self.st) > 5000:
                del self.st[:-200]

    def call(self, proc, depth):
        if isinstance(proc, Proc):
            self.run(proc, depth + 1)
        else:
            self.st.append(proc)

    def exec_name(self, name, depth):
        builtin = getattr(self, "op_" + _safe(name), None)
        ai_builtin = name in AI_OPS and builtin is not None
        if not (self.ai_mode and ai_builtin):
            val, found = self.lookup(name)
            if found:
                if isinstance(val, Proc):
                    self.run(val, depth + 1)
                elif callable(val):
                    val()
                else:
                    self.st.append(val)
                return
        if builtin is not None:
            try:
                builtin_args = builtin.__code__.co_argcount
                builtin(depth) if builtin_args > 1 else builtin()
            except (IndexError, TypeError, ValueError, ZeroDivisionError, OverflowError, KeyError, AttributeError):
                pass

    def _close_array(self):
        items = []
        while self.st and self.st[-1] is not MARK:
            items.append(self.st.pop())
        if self.st:
            self.st.pop()
        self.st.append(list(reversed(items)))

    def _close_dict(self):
        items = []
        while self.st and self.st[-1] is not MARK:
            items.append(self.st.pop())
        if self.st:
            self.st.pop()
        items.reverse()
        d = {}
        for i in range(0, len(items) - 1, 2):
            d[str(items[i])] = items[i + 1]
        self.st.append(d)

    # ── emit ────────────────────────────────────────────────────────────────
    def emit(self, fill, stroke):
        g = self.gs
        builder = g.path
        if self.compound is not None:
            # inside *u … *U: keep collecting sub-paths, remember the paint
            self.compound.parts += [p for p in builder.parts if len(p["nodes"]) >= 2]
            self.compound_paint = (fill, stroke, g.fill, g.stroke, g.lw * mat_scale(g.ctm), g.dash)
            builder.clear()
            return
        f = g.fill if fill else None
        s = g.stroke if stroke else None
        if f or s:
            shape = builder.to_shape(self.flip, f, s, g.lw * mat_scale(g.ctm), g.dash, close_for_fill=True)
            if shape:
                self._add(shape)
        builder.clear()

    def _add(self, shape):
        if self.group_stack:
            shape["gid"] = self.group_stack[0]
            if len(self.group_stack) > 1:
                shape["gpath"] = list(self.group_stack)
        if self.layer_stack:
            shape["layer"] = self.layer_stack[-1]
        self.shapes.append(shape)
        self.notes["paths" if shape["type"] != "text" else "text"] += 1

    def P(self, x, y):
        return apply(self.gs.ctm, x, y)

    # ── core PostScript ─────────────────────────────────────────────────────
    def op_def(self):
        val, key = self.pop(), self.pop()
        self.dicts[-1][str(key)] = val

    def op_bind(self):
        pass

    def op_load(self):
        key = self.pop()
        val, found = self.lookup(str(key))
        self.st.append(val if found else None)

    def op_exch(self):
        a, b = self.popn(2)
        self.st += [b, a]

    def op_pop(self):
        self.pop()

    def op_dup(self):
        self.st.append(self.st[-1])

    def op_copy(self):
        n = self.pop()
        if isinstance(n, int):
            if n:
                self.st += self.st[-n:]
        # copying dicts/strings is not needed for drawing

    def op_index(self):
        n = int(self.pop())
        self.st.append(self.st[-1 - n])

    def op_roll(self):
        j, n = int(self.pop()), int(self.pop())
        if n > 0:
            seg = self.st[-n:]
            j %= n
            self.st[-n:] = seg[-j:] + seg[:-j] if j else seg

    def op_clear(self):
        self.st.clear()

    def op_mark(self):
        self.st.append(MARK)

    def op_cleartomark(self):
        while self.st and self.st.pop() is not MARK:
            pass

    def op_counttomark(self):
        n = 0
        for v in reversed(self.st):
            if v is MARK:
                break
            n += 1
        self.st.append(n)

    def op_count(self):
        self.st.append(len(self.st))

    def op_dict(self):
        self.pop()
        self.st.append({})

    def op_begin(self):
        d = self.pop()
        self.dicts.append(d if isinstance(d, dict) else {})

    def op_end(self):
        if len(self.dicts) > 1:
            self.dicts.pop()

    def op_currentdict(self):
        self.st.append(self.dicts[-1])

    op_userdict = op_currentdict
    op_globaldict = op_currentdict
    op_systemdict = op_currentdict

    def op_put(self):
        val, key, obj = self.pop(), self.pop(), self.pop()
        if isinstance(obj, dict):
            obj[str(key)] = val
        elif isinstance(obj, list) and isinstance(key, int) and 0 <= key < len(obj):
            obj[key] = val

    def op_get(self):
        key, obj = self.pop(), self.pop()
        if isinstance(obj, dict):
            self.st.append(obj.get(str(key)))
        elif isinstance(obj, (list, bytes)) and isinstance(key, int) and 0 <= key < len(obj):
            self.st.append(obj[key])
        else:
            self.st.append(0)

    def op_known(self):
        key, obj = self.pop(), self.pop()
        self.st.append(isinstance(obj, dict) and str(key) in obj)

    def op_where(self):
        key = str(self.pop())
        for d in reversed(self.dicts):
            if key in d:
                self.st += [d, True]
                return
        self.st.append(False)

    def op_length(self):
        v = self.pop()
        self.st.append(len(v) if hasattr(v, "__len__") else 0)

    def op_array(self):
        n = int(self.pop())
        self.st.append([None] * max(0, min(n, 100000)))

    def op_string(self):
        n = int(self.pop())
        self.st.append(b"\x00" * max(0, min(n, 100000)))

    def op_aload(self):
        arr = self.pop()
        if isinstance(arr, list):
            self.st += arr
        self.st.append(arr)

    def op_astore(self):
        arr = self.pop()
        if isinstance(arr, list):
            n = len(arr)
            vals = self.popn(n)
            self.st.append(list(vals))

    def op_exec(self, depth):
        self.call(self.pop(), depth)

    def op_cvx(self):
        v = self.pop()
        self.st.append(Proc(v) if isinstance(v, list) else v)

    def op_cvlit(self):
        pass

    def op_cvi(self):
        self.st.append(int(float(self.pop())))

    def op_cvr(self):
        self.st.append(float(self.pop()))

    def op_if(self, depth):
        proc, cond = self.pop(), self.pop()
        if cond is True:
            self.call(proc, depth)

    def op_ifelse(self, depth):
        p2, p1, cond = self.pop(), self.pop(), self.pop()
        self.call(p1 if cond is True else p2, depth)

    def op_repeat(self, depth):
        proc, n = self.pop(), int(self.pop())
        for _ in range(max(0, min(n, 10000))):
            self.call(proc, depth)

    def op_for(self, depth):
        proc, limit, inc, init = self.pop(), self.pop(), self.pop(), self.pop()
        if not inc:
            return
        v, k = init, 0
        while (inc > 0 and v <= limit) or (inc < 0 and v >= limit):
            self.st.append(v)
            self.call(proc, depth)
            v += inc
            k += 1
            if k > 10000:
                break

    def op_forall(self, depth):
        proc, obj = self.pop(), self.pop()
        if isinstance(obj, list):
            for v in obj[:10000]:
                self.st.append(v)
                self.call(proc, depth)

    def op_stopped(self, depth):
        proc = self.pop()
        try:
            self.call(proc, depth)
            self.st.append(False)
        except PSError:
            raise
        except Exception:  # noqa: BLE001
            self.st.append(True)

    def _arith(self, fn):
        b, a = self.pop(), self.pop()
        self.st.append(fn(float(a), float(b)))

    def op_add(self):
        self._arith(lambda a, b: a + b)

    def op_sub(self):
        self._arith(lambda a, b: a - b)

    def op_mul(self):
        self._arith(lambda a, b: a * b)

    def op_div(self):
        self._arith(lambda a, b: a / b if b else 0.0)

    def op_idiv(self):
        self._arith(lambda a, b: float(int(a / b)) if b else 0.0)

    def op_mod(self):
        self._arith(lambda a, b: float(int(a) % int(b)) if int(b) else 0.0)

    def op_neg(self):
        self.st.append(-float(self.pop()))

    def op_abs(self):
        self.st.append(abs(float(self.pop())))

    def op_sqrt(self):
        self.st.append(math.sqrt(max(0.0, float(self.pop()))))

    def op_round(self):
        self.st.append(float(round(float(self.pop()))))

    def op_floor(self):
        self.st.append(float(math.floor(float(self.pop()))))

    def op_ceiling(self):
        self.st.append(float(math.ceil(float(self.pop()))))

    def op_truncate(self):
        self.st.append(float(int(float(self.pop()))))

    def op_sin(self):
        self.st.append(math.sin(math.radians(float(self.pop()))))

    def op_cos(self):
        self.st.append(math.cos(math.radians(float(self.pop()))))

    def op_atan(self):
        b, a = float(self.pop()), float(self.pop())
        self.st.append(math.degrees(math.atan2(a, b)) % 360)

    def _cmp(self, fn):
        b, a = self.pop(), self.pop()
        try:
            self.st.append(bool(fn(a, b)))
        except TypeError:
            self.st.append(False)

    def op_eq(self):
        self._cmp(lambda a, b: a == b)

    def op_ne(self):
        self._cmp(lambda a, b: a != b)

    def op_gt(self):
        self._cmp(lambda a, b: a > b)

    def op_ge(self):
        self._cmp(lambda a, b: a >= b)

    def op_lt(self):
        self._cmp(lambda a, b: a < b)

    def op_le(self):
        self._cmp(lambda a, b: a <= b)

    def op_not(self):
        a = self.pop()
        self.st.append(not a if isinstance(a, bool) else ~int(a))

    def op_and(self):
        b, a = self.pop(), self.pop()
        self.st.append((a and b) if isinstance(a, bool) else int(a) & int(b))

    def op_or(self):
        b, a = self.pop(), self.pop()
        self.st.append((a or b) if isinstance(a, bool) else int(a) | int(b))

    def op_true(self):
        self.st.append(True)

    def op_false(self):
        self.st.append(False)

    def op_null(self):
        self.st.append(None)

    def op_save(self):
        self.gstack.append(self.gs.copy())
        self.st.append("save-object")

    def op_restore(self):
        self.pop()
        if self.gstack:
            self.gs = self.gstack.pop()

    # ── graphics state ──────────────────────────────────────────────────────
    def op_gsave(self):
        self.gstack.append(self.gs.copy())

    def op_grestore(self):
        if self.gstack:
            self.gs = self.gstack.pop()

    def op_translate(self):
        x, y = self.nums(2)
        self.gs.ctm = mat_mul((1, 0, 0, 1, x, y), self.gs.ctm)

    def op_scale(self):
        x, y = self.nums(2)
        self.gs.ctm = mat_mul((x, 0, 0, y, 0, 0), self.gs.ctm)

    def op_rotate(self):
        a = math.radians(float(self.pop()))
        c, s = math.cos(a), math.sin(a)
        self.gs.ctm = mat_mul((c, s, -s, c, 0, 0), self.gs.ctm)

    def op_concat(self):
        m = self.pop()
        if isinstance(m, list) and len(m) == 6:
            self.gs.ctm = mat_mul(tuple(float(v) for v in m), self.gs.ctm)

    def op_matrix(self):
        self.st.append([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])

    def op_currentmatrix(self):
        self.pop()
        self.st.append(list(self.gs.ctm))

    def op_setmatrix(self):
        m = self.pop()
        if isinstance(m, list) and len(m) == 6:
            self.gs.ctm = tuple(float(v) for v in m)

    def op_initmatrix(self):
        self.gs.ctm = IDENT

    def op_setlinewidth(self):
        self.gs.lw = float(self.pop())

    def op_setdash(self):
        self.pop()
        arr = self.pop()
        self.gs.dash = isinstance(arr, list) and any(isinstance(v, (int, float)) and v > 0 for v in arr)

    def op_setlinecap(self):
        self.pop()

    op_setlinejoin = op_setlinecap
    op_setmiterlimit = op_setlinecap
    op_setflat = op_setlinecap
    op_setoverprint = op_setlinecap
    op_setstrokeadjust = op_setlinecap

    def _set_both(self, col):
        self.gs.fill = self.gs.stroke = col

    def op_setgray(self):
        self._set_both(gray_hex(float(self.pop())))

    def op_setrgbcolor(self):
        self._set_both(rgb_hex(*self.nums(3)))

    def op_setcmykcolor(self):
        self._set_both(cmyk_hex(*self.nums(4)))

    def op_sethsbcolor(self):
        self._set_both(_hsb_hex(*self.nums(3)))

    def op_setcolorspace(self):
        cs = self.pop()
        name = str(cs[0]) if isinstance(cs, list) and cs else str(cs)
        self.colorspace = {"DeviceGray": 1, "DeviceRGB": 3, "DeviceCMYK": 4}.get(name, 3)

    def op_setcolor(self):
        n = getattr(self, "colorspace", 3)
        vals = []
        while self.st and isinstance(self.st[-1], (int, float)) and len(vals) < n:
            vals.insert(0, float(self.st.pop()))
        if len(vals) == 4:
            self._set_both(cmyk_hex(*vals))
        elif len(vals) == 3:
            self._set_both(rgb_hex(*vals))
        elif vals:
            self._set_both(gray_hex(vals[0]))

    # ── paths ───────────────────────────────────────────────────────────────
    def op_newpath(self):
        self.gs.path.clear()

    def op_moveto(self):
        x, y = self.nums(2)
        self.gs.path.moveto(*self.P(x, y))
        self.cur_point = (x, y)

    def op_rmoveto(self):
        dx, dy = self.nums(2)
        x, y = self.cur_point or (0, 0)
        self.gs.path.moveto(*self.P(x + dx, y + dy))
        self.cur_point = (x + dx, y + dy)

    def op_lineto(self):
        x, y = self.nums(2)
        self.gs.path.lineto(*self.P(x, y))
        self.cur_point = (x, y)

    def op_rlineto(self):
        dx, dy = self.nums(2)
        x, y = self.cur_point or (0, 0)
        self.gs.path.lineto(*self.P(x + dx, y + dy))
        self.cur_point = (x + dx, y + dy)

    def op_curveto(self):
        x1, y1, x2, y2, x3, y3 = self.nums(6)
        self.gs.path.curveto(*self.P(x1, y1), *self.P(x2, y2), *self.P(x3, y3))
        self.cur_point = (x3, y3)

    def op_rcurveto(self):
        d = self.nums(6)
        x, y = self.cur_point or (0, 0)
        self.gs.path.curveto(*self.P(x + d[0], y + d[1]), *self.P(x + d[2], y + d[3]),
                             *self.P(x + d[4], y + d[5]))
        self.cur_point = (x + d[4], y + d[5])

    def op_closepath(self):
        self.gs.path.closepath()

    def _arc(self, clockwise):
        cx, cy, r, a1, a2 = self.nums(5)
        first = True
        for p0, c1, c2, p3 in _arc_to_beziers(cx, cy, r, a1, a2, clockwise):
            if first:
                if self.gs.path.current() is None or self.gs.path._after_close:
                    self.gs.path.moveto(*self.P(*p0))
                else:
                    self.gs.path.lineto(*self.P(*p0))
                first = False
            self.gs.path.curveto(*self.P(*c1), *self.P(*c2), *self.P(*p3))
            self.cur_point = p3

    def op_arc(self):
        self._arc(False)

    def op_arcn(self):
        self._arc(True)

    def op_currentpoint(self):
        x, y = self.cur_point or (0, 0)
        self.st += [x, y]

    def _rect_args(self):
        v = self.pop()
        if isinstance(v, list):
            vals = [float(x) for x in v]
        else:
            vals = [float(x) for x in self.popn(3)] + [float(v)]
        return [vals[i:i + 4] for i in range(0, len(vals) - 3, 4)]

    def op_rectfill(self):
        for x, y, w, h in self._rect_args():
            self.gs.path.clear()
            self.gs.path.rect(self.gs.ctm, x, y, w, h)
            self.emit(True, False)

    def op_rectstroke(self):
        for x, y, w, h in self._rect_args():
            self.gs.path.clear()
            self.gs.path.rect(self.gs.ctm, x, y, w, h)
            self.emit(False, True)

    def op_rectclip(self):
        self._rect_args()

    def op_fill(self):
        self.emit(True, False)

    op_eofill = op_fill

    def op_stroke(self):
        self.emit(False, True)

    def op_clip(self):
        pass

    op_eoclip = op_clip

    def op_shfill(self):
        self.pop()
        self.notes["gradients"] += 1

    def op_image(self):
        self.notes["images"] += 1
        self.st.clear()

    op_colorimage = op_image
    op_imagemask = op_image

    def op_showpage(self):
        pass

    # ── fonts & text (PostScript) ───────────────────────────────────────────
    def op_findfont(self):
        name = self.pop()
        self.st.append({"FontName": str(name), "size": 1.0})

    def op_scalefont(self):
        s = float(self.pop())
        f = self.pop()
        f = dict(f) if isinstance(f, dict) else {"FontName": None, "size": 1.0}
        f["size"] = f.get("size", 1.0) * s
        self.st.append(f)

    def op_makefont(self):
        m = self.pop()
        f = self.pop()
        f = dict(f) if isinstance(f, dict) else {"FontName": None, "size": 1.0}
        if isinstance(m, list) and len(m) == 6:
            f["size"] = f.get("size", 1.0) * math.hypot(float(m[2]), float(m[3]))
        self.st.append(f)

    def op_setfont(self):
        f = self.pop()
        if isinstance(f, dict):
            self.gs.font, self.gs.size = f.get("FontName"), float(f.get("size", 12))

    def op_selectfont(self):
        size, name = self.pop(), self.pop()
        self.gs.font = str(name)
        self.gs.size = float(size) if isinstance(size, (int, float)) else 12.0

    def _show(self, s):
        if not isinstance(s, (bytes, bytearray)) or self.cur_point is None:
            return
        text = s.decode("cp1252", errors="replace")
        if not text.strip():
            return
        x, y = self.cur_point
        m = self.gs.ctm
        ox, oy = apply(m, x, y)
        size = self.gs.size * mat_scale(m)
        ang = math.degrees(math.atan2(m[1], m[0]))
        self._add_text(ox, oy, text, size, self.gs.fill, font_family_from(self.gs.font), ang,
                       font_style_from(self.gs.font))
        self.cur_point = (x + len(text) * self.gs.size * 0.55, y)

    def op_glyphshow(self):
        """/glyphname glyphshow (matplotlib, Type 3 fonts) — collected into text runs."""
        name = self.pop()
        if self.cur_point is None:
            return
        from vectra.fileio.importers.pdf_import import _glyph_to_char
        ch = _glyph_to_char(str(name).split(".")[0]) or ""
        if not ch:
            return
        x, y = self.cur_point
        m = self.gs.ctm
        ox, oy = apply(m, x, y)
        size = self.gs.size * mat_scale(m)
        ang = math.degrees(math.atan2(m[1], m[0]))
        self._add_text(ox, oy, ch, size, self.gs.fill, font_family_from(self.gs.font), ang,
                       font_style_from(self.gs.font))

    def _add_text(self, ox, oy, text, size, color, font, ang, style=(None, None)):
        X, Y = self.flip(ox, oy)
        rot = -ang
        last = getattr(self, "_last_text", None)
        if last and last["shape"] is (self.shapes[-1] if self.shapes else None):
            sh_, (lx, ly), lsize = last["shape"], last["origin"], last["size"]
            same = (abs(lsize - size) < 0.5 and sh_.get("fill") == (color or "#000000")
                    and sh_.get("font") == font and abs(sh_.get("rot", 0) - (round(rot, 3) if abs(rot) > 0.01 else 0)) < 0.5)
            a = math.radians(rot)
            dx, dy = X - lx, Y - ly
            along = dx * math.cos(a) + dy * math.sin(a)
            across = -dx * math.sin(a) + dy * math.cos(a)
            expect = last["width"]
            if same and abs(across) < size * 0.3 and expect - size * 0.6 < along < expect + size * 1.2:
                sep = " " if along - expect > size * 0.33 and not sh_["text"].endswith(" ") else ""
                sh_["text"] += sep + text
                last["width"] = along + self._est_width(text, size)
                return
        a = math.radians(rot)
        asc = size * 0.8
        shape = make_text(round(X + asc * math.sin(a), 3), round(Y - asc * math.cos(a), 3),
                          text, size, color, font, round(rot, 3) if abs(rot) > 0.01 else 0, style)
        self._add(shape)
        self._last_text = {"shape": shape, "origin": (X, Y), "size": size,
                           "width": self._est_width(text, size)}

    @staticmethod
    def _est_width(text, size):
        def w(c):
            if c in " .,:;!|il'jtfr":
                return 0.3
            if c in "mwMW@":
                return 0.85
            if c.isupper():
                return 0.68
            return 0.56
        return sum(size * w(c) for c in text)

    def op_show(self):
        self._show(self.pop())

    def op_ashow(self):
        s = self.pop()
        self.popn(2)
        self._show(s)

    def op_widthshow(self):
        s = self.pop()
        self.popn(3)
        self._show(s)

    def op_awidthshow(self):
        s = self.pop()
        self.popn(5)
        self._show(s)

    def op_xshow(self):
        self.pop()
        self._show(self.pop())

    op_yshow = op_xshow
    op_xyshow = op_xshow

    def op_kshow(self):
        s = self.pop()
        self.pop()
        self._show(s)

    def op_stringwidth(self):
        s = self.pop()
        n = len(s) if isinstance(s, (bytes, bytearray)) else 0
        self.st += [n * self.gs.size * 0.55, 0.0]

    # ── Illustrator file-format operators ───────────────────────────────────
    def op_m(self):
        self.op_moveto()

    def op_l(self):
        self.op_lineto()

    op_L = op_l

    def op_c(self):
        self.op_curveto()

    op_C = op_c

    def op_v(self):
        x2, y2, x3, y3 = self.nums(4)
        cur = self.gs.path.current() or self.P(*(self.cur_point or (0, 0)))
        self.gs.path.curveto(*cur, *self.P(x2, y2), *self.P(x3, y3))
        self.cur_point = (x3, y3)

    op_V = op_v

    def op_y(self):
        x1, y1, x3, y3 = self.nums(4)
        p3 = self.P(x3, y3)
        self.gs.path.curveto(*self.P(x1, y1), *p3, *p3)
        self.cur_point = (x3, y3)

    op_Y = op_y

    def op_h(self):
        self.gs.path.closepath()

    op_H = op_h

    def op_f(self):
        self.gs.path.closepath()
        self.emit(True, False)

    def op_F(self):
        self.emit(True, False)

    def op_s(self):
        self.gs.path.closepath()
        self.emit(False, True)

    def op_S(self):
        self.emit(False, True)

    def op_b(self):
        self.gs.path.closepath()
        self.emit(True, True)

    def op_B(self):
        self.emit(True, True)

    def op_n(self):
        if self.compound is not None:
            self.compound.parts += [p for p in self.gs.path.parts if len(p["nodes"]) >= 2]
        self.gs.path.clear()

    op_N = op_n

    def op_g(self):
        self.gs.fill = gray_hex(float(self.pop()))

    def op_G(self):
        self.gs.stroke = gray_hex(float(self.pop()))

    def op_k(self):
        self.gs.fill = cmyk_hex(*self.nums(4))

    def op_K(self):
        self.gs.stroke = cmyk_hex(*self.nums(4))

    def op_Xa(self):
        self.gs.fill = rgb_hex(*self.nums(3))

    def op_XA(self):
        self.gs.stroke = rgb_hex(*self.nums(3))

    def _custom(self):
        """c m y k (name) tint x  — or AI8: comps (name) tint type Xx."""
        vals = []
        while self.st and not isinstance(self.st[-1], (bytes, bytearray)):
            vals.insert(0, self.st.pop())
        name = self.pop()
        comps = []
        while self.st and isinstance(self.st[-1], (int, float)) and len(comps) < 4:
            comps.insert(0, float(self.st.pop()))
        tint = float(vals[0]) if vals else 1.0
        kind = int(vals[1]) if len(vals) > 1 else 0
        if kind == 1 and len(comps) >= 3:
            base = rgb_hex(*comps[-3:])
        elif len(comps) >= 4:
            base = cmyk_hex(*comps[-4:])
        else:
            base = "#000000"
        del name
        return _tinted(base, tint)

    def op_x(self):
        self.gs.fill = self._custom()

    def op_X(self):
        self.gs.stroke = self._custom()

    op_Xx = op_x
    op_XX = op_X

    def op_w(self):
        self.gs.lw = float(self.pop())

    def op_d(self):
        self.pop()
        arr = self.pop()
        self.gs.dash = isinstance(arr, list) and any(isinstance(v, (int, float)) and v > 0 for v in arr)

    def _pop1(self):
        self.pop()

    op_j = op_J = op_M = op_O = op_R = op_A = op_D = op_Tr = _pop1

    def op_W(self):
        pass

    def op_q(self):
        self.op_gsave()

    def op_Q(self):
        self.op_grestore()

    def op__u(self):  # *u  (compound path begin)
        self.compound = PathBuilder()
        self.compound_paint = None

    def op__U(self):  # *U
        comp, self.compound = self.compound, None
        if comp is None or not self.compound_paint:
            return
        fill, stroke, fcol, scol, lw, dash = self.compound_paint
        shape = comp.to_shape(self.flip, fcol if fill else None, scol if stroke else None, lw, dash,
                              close_for_fill=True)
        if shape:
            self._add(shape)

    def op_u(self):
        """Begin group. Nested groups are kept as a path of group ids (outermost first)."""
        self.group_stack.append(self._next_gid)
        self._next_gid += 1
        self.group_depth = len(self.group_stack)
        self.group_id = self.group_stack[0]

    def op_U(self):
        if self.group_stack:
            self.group_stack.pop()
        self.group_depth = len(self.group_stack)
        self.group_id = self.group_stack[0] if self.group_stack else None

    # gradients / patterns / layers: consume and count
    def op_Bb(self):
        self.notes["gradients"] += 1

    def op_BB(self):
        self.pop()

    def _clear(self):
        self.st.clear()

    op_Bg = op_Bm = op_Bc = op_BD = op_Bh = op_Bn = op_Bs = op_p = op_P = _clear
    op_XR = op_Xy = op_XW = op_Ap = op_Ar = op_XP = _clear

    # Illustrator layers: "vis preview enabled print dim masks colorIdx r g b … Lb  (name) Ln … LB"
    def op_Lb(self):
        nums = [float(v) for v in self.st if isinstance(v, (int, float))]
        self.st.clear()
        if len(nums) > 14:          # leftovers from unknown operators before Lb
            nums = nums[-14:]
        if self.layer_stack:            # sub-layer: its art stays in the top-level layer
            self.layer_stack.append(self.layer_stack[-1])
            return
        lid = len(self.layers) + 1
        self.group_stack = []
        self.group_id = None
        color = None
        if len(nums) >= 10:
            # AI5: vis prev enabled print dim masks colorIdx r g b
            # AI8+: … colorIdx r g b dimPlaced dimPercent templateType  (rgb = 6th..4th from the end)
            rgb = nums[-6:-3] if len(nums) >= 13 else nums[7:10]
            r, g, b = (max(0, min(255, int(v))) for v in rgb)
            color = f"#{r:02x}{g:02x}{b:02x}"
        self.layers.append({"id": lid, "name": f"Layer {lid}", "color": color,
                            "visible": not nums or nums[0] != 0,
                            "locked": len(nums) > 2 and nums[2] == 0})
        self.layer_stack.append(lid)

    def op_Ln(self):
        name = self.pop()
        if len(self.layer_stack) == 1 and isinstance(name, (bytes, bytearray)) and self.layers:
            self.layers[-1]["name"] = decode_text_string(bytes(name)) or self.layers[-1]["name"]

    def op_LB(self):
        self.st.clear()
        if self.layer_stack:
            self.layer_stack.pop()

    # AI text objects
    def op_To(self):
        self.pop()
        self.text = {"m": IDENT, "chunks": [], "color": self.gs.fill, "font": self.gs.font,
                     "size": self.gs.size}

    def op_Tp(self):
        vals = self.nums(7)
        if self.text is not None:
            self.text["m"] = tuple(vals[:6])

    def op_TP(self):
        pass

    def op_Tf(self):
        # /_FontName size [ascent descent] Tf
        nums = []
        while self.st and isinstance(self.st[-1], (int, float)):
            nums.insert(0, float(self.st.pop()))
        name = self.pop()
        size = nums[0] if nums else 12.0
        self.gs.font, self.gs.size = str(name).lstrip("_"), size
        if self.text is not None:
            self.text["font"], self.text["size"] = self.gs.font, size

    def op_Tx(self):
        s = self.pop()
        if self.text is None:
            self.op_To() if False else None
            self.text = {"m": IDENT, "chunks": [], "color": self.gs.fill, "font": self.gs.font,
                         "size": self.gs.size}
        if isinstance(s, (bytes, bytearray)):
            self.text["chunks"].append(s.decode("cp1252", errors="replace"))
            self.text["color"] = self.gs.fill

    op_TX = op_Tj = op_Tx

    def op_Tk(self):
        self.popn(2)

    def op_TO(self):
        t, self.text = self.text, None
        if not t:
            return
        txt = "".join(t["chunks"]).replace("\r", "\n").strip("\n")
        if not txt.strip():
            return
        m = mat_mul(t["m"], self.gs.ctm)
        ox, oy = m[4], m[5]
        size = t["size"] * mat_scale(m)
        ang = math.degrees(math.atan2(m[1], m[0]))
        self._add_text(ox, oy, txt, size, t["color"], font_family_from(t["font"]), ang,
                       font_style_from(t["font"]))


def _safe(name):
    return name.replace("*", "_")


# ── entry points ────────────────────────────────────────────────────────────
def _is_illustrator(data):
    head = data[:4000]
    return b"Adobe Illustrator" in head or b"%AI" in head[:2000] or b"%%AI" in head


def _body(data):
    """For Illustrator files skip the prolog/procsets: start after %%EndSetup."""
    for marker in (b"%%EndSetup", b"%%EndProlog"):
        i = data.find(marker)
        if i >= 0:
            return data[i + len(marker):]
    return data


def _private_section(data):
    i = data.find(b"%AI9_PrivateDataBegin")
    if i < 0:
        return None
    priv = data[i:]
    j = priv.find(b"%AI12_CompressedData")
    if j < 0:
        j = priv.find(b"%AI24_ZStandard_Data")
    if j >= 0:
        from vectra.fileio.importers.pdf_import import decompress_ai_private
        return decompress_ai_private(priv[j:])
    return priv


def import_ps_bytes(data, artboard_hint=None, prefer_private=True):
    data = strip_dos_eps(data)
    ai = _is_illustrator(data)
    bbox = find_bbox(data)
    if ai and prefer_private:
        priv = _private_section(data)
        if priv and len(priv) > 200:
            res = import_ps_bytes(priv, artboard_hint=artboard_hint or _bbox_size(bbox), prefer_private=False)
            if res.shapes:
                res.notes["from_private"] = 1
                return res
        cut = data.find(b"%AI9_PrivateDataBegin")
        if cut > 0:
            data = data[:cut]
    if bbox:
        x0, y0, x1, y1 = bbox
    elif artboard_hint:
        x0, y0, x1, y1 = 0.0, 0.0, float(artboard_hint[2]), float(artboard_hint[3])
    else:
        x0, y0, x1, y1 = 0.0, 0.0, 612.0, 792.0
    flip = (lambda x, y: (round(x - x0, 4), round(y1 - y, 4)))
    interp = PSInterpreter(flip, ai_mode=ai)
    tokens = tokenize(_body(data) if ai else data)
    try:
        interp.run(tokens)
    except PSError:
        interp.notes["truncated"] = 1
    artboard = [0, 0, round(x1 - x0, 3), round(y1 - y0, 3)]
    if artboard_hint and not bbox:
        artboard = list(artboard_hint)
    return ImportResult(interp.shapes, artboard, interp.notes, layers=interp.layers)


def _bbox_size(b):
    return [0, 0, b[2] - b[0], b[3] - b[1]] if b else None
