"""A small, tolerant PDF reader (standard library only).

Enough for vector artwork: objects found by scanning (no reliance on a correct
xref table), compressed object streams (PDF 1.5+), Flate/ASCIIHex/ASCII85/LZW/RunLength
filters, and a content-stream tokenizer. Encrypted PDFs are not supported.
"""

import re
import zlib


class PDFError(ValueError):
    pass


class Name(str):
    """A PDF name object (/Foo)."""


class Ref:
    __slots__ = ("num", "gen")

    def __init__(self, num, gen=0):
        self.num, self.gen = num, gen

    def __repr__(self):
        return f"Ref({self.num} {self.gen})"


class Stream(dict):
    """A stream: the dictionary plus its raw (still encoded) bytes."""

    def __init__(self, d, raw):
        super().__init__(d)
        self.raw = raw


class Operator(str):
    """A bare keyword in a content stream (m, l, re, Tj …)."""


WS = b" \t\r\n\f\x00"
DELIM = b"()<>[]{}/%"
_NUM = re.compile(rb"[+-]?(\d+\.?\d*|\.\d+)")


class Lexer:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def skip_ws(self):
        d, n = self.data, len(self.data)
        while self.pos < n:
            ch = d[self.pos]
            if ch in WS:
                self.pos += 1
            elif ch == 0x25:  # %
                while self.pos < n and d[self.pos] not in b"\r\n":
                    self.pos += 1
            else:
                break

    def next(self):
        """Next token: python value, Operator, or one of the delimiters as str."""
        self.skip_ws()
        d, n = self.data, len(self.data)
        if self.pos >= n:
            return None
        ch = d[self.pos]
        if ch == 0x2F:  # /
            self.pos += 1
            start = self.pos
            while self.pos < n and d[self.pos] not in WS and d[self.pos] not in DELIM:
                self.pos += 1
            raw = d[start:self.pos]
            raw = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), raw)
            return Name(raw.decode("latin-1"))
        if ch == 0x28:  # (
            return self._literal_string()
        if ch == 0x3C:  # <
            if d[self.pos:self.pos + 2] == b"<<":
                self.pos += 2
                return "<<"
            end = d.find(b">", self.pos)
            hexs = re.sub(rb"\s", b"", d[self.pos + 1:end if end >= 0 else n])
            self.pos = (end + 1) if end >= 0 else n
            if len(hexs) % 2:
                hexs += b"0"
            try:
                return bytes.fromhex(hexs.decode("latin-1"))
            except ValueError:
                return b""
        if ch == 0x3E:  # >
            if d[self.pos:self.pos + 2] == b">>":
                self.pos += 2
                return ">>"
            self.pos += 1
            return ">"
        if ch in b"[]{}":
            self.pos += 1
            return chr(ch)
        start = self.pos
        while self.pos < n and d[self.pos] not in WS and d[self.pos] not in DELIM:
            self.pos += 1
        if self.pos == start:  # stray delimiter like ')'
            self.pos += 1
            return self.next()
        word = d[start:self.pos]
        if _NUM.fullmatch(word):
            return float(word) if (b"." in word) else int(word)
        w = word.decode("latin-1")
        if w == "true":
            return True
        if w == "false":
            return False
        if w == "null":
            return None
        return Operator(w)

    def _literal_string(self):
        d, n = self.data, len(self.data)
        self.pos += 1
        depth, out = 1, bytearray()
        while self.pos < n:
            ch = d[self.pos]
            self.pos += 1
            if ch == 0x5C:  # backslash
                if self.pos >= n:
                    break
                e = d[self.pos]
                self.pos += 1
                if e in b"nrtbf":
                    out += {0x6E: b"\n", 0x72: b"\r", 0x74: b"\t", 0x62: b"\b", 0x66: b"\f"}[e]
                elif 0x30 <= e <= 0x37:
                    digits = bytes([e])
                    while len(digits) < 3 and self.pos < n and 0x30 <= d[self.pos] <= 0x37:
                        digits += bytes([d[self.pos]])
                        self.pos += 1
                    out.append(int(digits, 8) & 0xFF)
                elif e == 0x0D:
                    if self.pos < n and d[self.pos] == 0x0A:
                        self.pos += 1
                elif e == 0x0A:
                    pass
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
        return bytes(out)


def parse_object(lex, first=None):
    """Parse one object (dict / array / number / ref …) from the lexer."""
    tok = lex.next() if first is None else first
    if tok == "<<":
        d = {}
        while True:
            k = lex.next()
            if k == ">>" or k is None:
                break
            if not isinstance(k, Name):
                continue
            d[str(k)] = parse_object(lex)
        return d
    if tok == "[":
        arr = []
        while True:
            t = lex.next()
            if t == "]" or t is None:
                break
            arr.append(parse_object(lex, t))
        return arr
    if isinstance(tok, int) and not isinstance(tok, bool):
        save = lex.pos
        t2 = lex.next()
        if isinstance(t2, int) and not isinstance(t2, bool):
            t3 = lex.next()
            if t3 == "R":
                return Ref(tok, t2)
        lex.pos = save
        return tok
    return tok


# ── filters ─────────────────────────────────────────────────────────────────
def _flate(data):
    try:
        return zlib.decompress(data)
    except zlib.error:
        d = zlib.decompressobj()
        try:
            return d.decompress(data)
        except zlib.error:
            # some writers emit raw deflate without the zlib header
            try:
                return zlib.decompressobj(-15).decompress(data)
            except zlib.error:
                return b""


def _ascii_hex(data):
    data = re.sub(rb"\s", b"", data).split(b">")[0]
    if len(data) % 2:
        data += b"0"
    return bytes.fromhex(data.decode("latin-1"))


def _ascii85(data):
    import base64
    data = re.sub(rb"\s", b"", data)
    if data.startswith(b"<~"):
        data = data[2:]
    if data.endswith(b"~>"):
        data = data[:-2]
    try:
        return base64.a85decode(data)
    except ValueError:
        return b""


def _lzw(data, early=1):
    out, table = bytearray(), [bytes([i]) for i in range(256)] + [b"", b""]
    bits, code_len, buf, prev = 0, 9, 0, None
    for byte in data:
        buf = (buf << 8) | byte
        bits += 8
        while bits >= code_len:
            bits -= code_len
            code = (buf >> bits) & ((1 << code_len) - 1)
            if code == 256:
                table = table[:258]
                code_len, prev = 9, None
                continue
            if code == 257:
                return bytes(out)
            if prev is None:
                entry = table[code]
            elif code < len(table):
                entry = table[code]
                table.append(prev + entry[:1])
            else:
                entry = prev + prev[:1]
                table.append(entry)
            out += entry
            prev = entry
            if len(table) + early >= (1 << code_len) and code_len < 12:
                code_len += 1
    return bytes(out)


def _run_length(data):
    out, i = bytearray(), 0
    while i < len(data):
        n = data[i]
        if n == 128:
            break
        if n < 128:
            out += data[i + 1:i + 2 + n]
            i += n + 2
        else:
            out += data[i + 1:i + 2] * (257 - n)
            i += 2
    return bytes(out)


def _png_predictor(data, columns, colors=1, bpc=8):
    bpp = max(1, colors * bpc // 8)
    row_len = (columns * colors * bpc + 7) // 8
    out, prev = bytearray(), bytearray(row_len)
    i = 0
    while i + row_len < len(data) + 1 and i < len(data):
        ft = data[i]
        row = bytearray(data[i + 1:i + 1 + row_len])
        for x in range(len(row)):
            a = row[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if ft == 1:
                row[x] = (row[x] + a) & 0xFF
            elif ft == 2:
                row[x] = (row[x] + b) & 0xFF
            elif ft == 3:
                row[x] = (row[x] + (a + b) // 2) & 0xFF
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[x] = (row[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 0xFF
        out += row
        prev = row
        i += row_len + 1
    return bytes(out)


# ── document ────────────────────────────────────────────────────────────────
_OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj\b")


class PDFDocument:
    def __init__(self, data):
        if b"/Encrypt" in data[-4096:] or re.search(rb"/Encrypt\s+\d+\s+\d+\s+R", data):
            raise PDFError("encrypted PDF is not supported")
        self.data = data
        self.offsets = {}
        for m in _OBJ_RE.finditer(data):
            self.offsets[int(m.group(1))] = m.end()
        self.cache = {}
        self.in_objstm = {}
        self._index_object_streams()

    # objects ---------------------------------------------------------------
    def _parse_at(self, pos):
        lex = Lexer(self.data, pos)
        obj = parse_object(lex)
        save = lex.pos
        tok = lex.next()
        if tok == "stream":
            start = lex.pos
            if self.data[start:start + 2] == b"\r\n":
                start += 2
            elif self.data[start:start + 1] in (b"\n", b"\r"):
                start += 1
            length = obj.get("Length") if isinstance(obj, dict) else None
            if isinstance(length, Ref):
                length = self._resolve_length(length)
            end = None
            if isinstance(length, int) and 0 <= length and \
                    self.data[start + length:start + length + 30].lstrip().startswith(b"endstream"):
                end = start + length
            if end is None:
                end = self.data.find(b"endstream", start)
                if end < 0:
                    end = len(self.data)
                while end > start and self.data[end - 1:end] in (b"\n", b"\r"):
                    end -= 1
            return Stream(obj if isinstance(obj, dict) else {}, self.data[start:end])
        lex.pos = save
        return obj

    def _resolve_length(self, ref):
        pos = self.offsets.get(ref.num)
        if pos is None:
            return None
        v = parse_object(Lexer(self.data, pos))
        return v if isinstance(v, int) else None

    def _index_object_streams(self):
        for num, pos in list(self.offsets.items()):
            head = self.data[pos:pos + 300]
            if b"/ObjStm" not in head:
                continue
            try:
                st = self._parse_at(pos)
                if not isinstance(st, Stream) or st.get("Type") != "ObjStm":
                    continue
                raw = self.decode(st)
                n, first = int(st.get("N", 0)), int(st.get("First", 0))
                lex = Lexer(raw)
                pairs = []
                for _ in range(n):
                    a, b = lex.next(), lex.next()
                    if not isinstance(a, int) or not isinstance(b, int):
                        break
                    pairs.append((a, b))
                for onum, off in pairs:
                    if onum not in self.offsets:
                        self.in_objstm[onum] = (raw, first + off)
            except Exception:  # noqa: BLE001 - keep going with what we can read
                continue

    def get(self, num):
        if isinstance(num, Ref):
            num = num.num
        if num in self.cache:
            return self.cache[num]
        obj = None
        if num in self.offsets:
            try:
                obj = self._parse_at(self.offsets[num])
            except Exception:  # noqa: BLE001
                obj = None
        elif num in self.in_objstm:
            raw, pos = self.in_objstm[num]
            obj = parse_object(Lexer(raw, pos))
        self.cache[num] = obj
        return obj

    def resolve(self, x, depth=0):
        while isinstance(x, Ref) and depth < 32:
            x = self.get(x)
            depth += 1
        return x

    # streams ---------------------------------------------------------------
    def decode(self, stream):
        data = stream.raw
        filters = self.resolve(stream.get("Filter"))
        parms = self.resolve(stream.get("DecodeParms"))
        if filters is None:
            return data
        if not isinstance(filters, list):
            filters, parms = [filters], [parms]
        elif not isinstance(parms, list):
            parms = [parms] * len(filters)
        for f, p in zip(filters, parms + [None] * len(filters)):
            f = str(self.resolve(f))
            p = self.resolve(p) or {}
            if f in ("FlateDecode", "Fl"):
                data = _flate(data)
            elif f in ("ASCIIHexDecode", "AHx"):
                data = _ascii_hex(data)
            elif f in ("ASCII85Decode", "A85"):
                data = _ascii85(data)
            elif f in ("LZWDecode", "LZW"):
                data = _lzw(data, int(p.get("EarlyChange", 1)) if isinstance(p, dict) else 1)
            elif f in ("RunLengthDecode", "RL"):
                data = _run_length(data)
            else:
                return b""  # image codecs (DCT, JBIG2 …) are not needed for vectors
            if isinstance(p, dict) and int(p.get("Predictor", 1) or 1) >= 10:
                data = _png_predictor(data, int(p.get("Columns", 1)), int(p.get("Colors", 1)),
                                      int(p.get("BitsPerComponent", 8)))
        return data

    # pages -----------------------------------------------------------------
    def catalog(self):
        roots = re.findall(rb"/Root\s+(\d+)\s+(\d+)\s+R", self.data)
        if roots:
            cat = self.get(int(roots[-1][0]))
            if isinstance(cat, dict):
                return cat
        for num in list(self.offsets) + list(self.in_objstm):
            o = self.get(num)
            if isinstance(o, dict) and o.get("Type") == "Catalog":
                return o
        raise PDFError("no document catalog")

    def pages(self):
        out = []

        def walk(node, inherited, depth=0):
            node = self.resolve(node)
            if not isinstance(node, dict) or depth > 40:
                return
            inh = dict(inherited)
            for k in ("Resources", "MediaBox", "CropBox", "Rotate"):
                if k in node:
                    inh[k] = node[k]
            if node.get("Type") == "Pages" or "Kids" in node:
                for kid in self.resolve(node.get("Kids")) or []:
                    walk(kid, inh, depth + 1)
            else:
                page = dict(inh)
                page.update(node)
                out.append(page)
        walk(self.catalog().get("Pages"), {})
        return out

    def page_content(self, page):
        c = self.resolve(page.get("Contents"))
        parts = c if isinstance(c, list) else [c]
        data = b""
        for p in parts:
            p = self.resolve(p)
            if isinstance(p, Stream):
                data += self.decode(p) + b"\n"
        return data


def tokenize_content(data):
    """Yield (operands, operator) from a content stream; inline images are skipped."""
    lex = Lexer(data)
    operands = []
    while True:
        tok = lex.next()
        if tok is None:
            return
        if isinstance(tok, Operator):
            if tok == "BI":
                end = re.compile(rb"\sEI[\s]").search(data, lex.pos)
                lex.pos = end.end() if end else len(data)
                operands = []
                continue
            yield operands, str(tok)
            operands = []
        elif tok in ("<<", "["):
            operands.append(parse_object(lex, tok))
        elif tok in ("]", ">>", "{", "}", ">"):
            continue
        else:
            operands.append(tok)
