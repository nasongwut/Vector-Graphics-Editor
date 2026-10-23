"""Zstandard decompression for Illustrator's native data (``%AI24_ZStandard_Data``).

Uses a fast compiled implementation when one is available (Python 3.14's
``compression.zstd``, or the ``zstandard`` / ``pyzstd`` packages) and otherwise a
pure-Python decoder that follows RFC 8878. The fallback is slower (a few seconds
for a typical file) but needs nothing to be installed.
"""


class ZstdError(ValueError):
    pass


def decompress(data):
    for backend in (_stdlib, _zstandard, _pyzstd):
        out = backend(data)
        if out is not None:
            return out
    return decompress_pure(data)


def _stdlib(data):
    try:
        from compression import zstd  # Python 3.14+
    except ImportError:
        return None
    try:
        return zstd.decompress(data)
    except Exception:  # noqa: BLE001
        return None


def _zstandard(data):
    try:
        import zstandard
    except ImportError:
        return None
    try:
        return zstandard.ZstdDecompressor().decompressobj().decompress(data)
    except Exception:  # noqa: BLE001
        return None


def _pyzstd(data):
    try:
        import pyzstd
    except ImportError:
        return None
    try:
        return pyzstd.decompress(data)
    except Exception:  # noqa: BLE001
        return None


# ── pure-Python decoder ─────────────────────────────────────────────────────
LL_BASE = list(range(16)) + [16, 18, 20, 22, 24, 28, 32, 40, 48, 64, 128, 256, 512, 1024, 2048, 4096,
                             8192, 16384, 32768, 65536]
LL_BITS = [0] * 16 + [1, 1, 1, 1, 2, 2, 3, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
ML_BASE = [i + 3 for i in range(32)] + [35, 37, 39, 41, 43, 47, 51, 59, 67, 83, 99, 131, 259, 515, 1027,
                                         2051, 4099, 8195, 16387, 32771, 65539]
ML_BITS = [0] * 32 + [1, 1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

LL_DEFAULT = ([4, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 1, 1, 1, 1, 1,
               -1, -1, -1, -1], 6)
ML_DEFAULT = ([1, 4, 3, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
               1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, -1, -1], 6)
OF_DEFAULT = ([1, 1, 1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1], 5)


class _BackReader:
    """Reads a bit-stream backwards (zstd FSE / Huffman streams)."""
    __slots__ = ("data", "start", "pos", "acc", "n", "overflow")

    def __init__(self, data, start, end):
        if end <= start:
            raise ZstdError("empty bitstream")
        last = data[end - 1]
        if last == 0:
            raise ZstdError("bad bitstream end mark")
        self.data, self.start, self.pos = data, start, end - 1
        hb = last.bit_length() - 1          # drop the padding marker bit
        self.acc = last & ((1 << hb) - 1)
        self.n = hb
        self.overflow = 0                   # bits read past the beginning

    def read(self, k):
        if k == 0:
            return 0
        while self.n < k:
            if self.pos > self.start:
                self.pos -= 1
                self.acc = (self.acc << 8) | self.data[self.pos]
                self.n += 8
            else:                           # past the start: zeros
                need = k - self.n
                self.acc <<= need
                self.n += need
                self.overflow += need
        self.n -= k
        v = self.acc >> self.n
        self.acc &= (1 << self.n) - 1
        return v

    def finished(self):
        return self.pos <= self.start and self.n == 0

    def overflowed(self):
        return self.overflow > 0


def _read_ncount(data, pos, max_symbol, max_log):
    """FSE normalised counts (forward bit order). -> (counts, table_log, new_pos)."""
    bitpos = pos * 8

    def peek(n):
        v = 0
        for i in range(n):
            idx = (bitpos + i) >> 3
            byte = data[idx] if idx < len(data) else 0
            v |= ((byte >> ((bitpos + i) & 7)) & 1) << i
        return v

    table_log = peek(4) + 5
    bitpos += 4
    if table_log > max_log:
        raise ZstdError("FSE table log too large")
    remaining = (1 << table_log) + 1
    threshold = 1 << table_log
    nb = table_log + 1
    counts = []
    previous0 = False
    while remaining > 1 and len(counts) <= max_symbol:
        if previous0:
            while True:
                r = peek(2)
                bitpos += 2
                counts.extend([0] * r)
                if r != 3:
                    break
            if len(counts) > max_symbol:
                break
        mx = (2 * threshold - 1) - remaining
        low = peek(nb - 1)
        if low < mx:
            count = low
            bitpos += nb - 1
        else:
            count = peek(nb)
            if count >= threshold:
                count -= mx
            bitpos += nb
        count -= 1
        remaining -= -count if count < 0 else count
        counts.append(count)
        previous0 = count == 0
        while remaining < threshold:
            nb -= 1
            threshold >>= 1
    if remaining != 1:
        raise ZstdError("bad FSE normalised counts")
    return counts, table_log, (bitpos + 7) >> 3


def _build_fse(counts, table_log):
    """-> list of (symbol, nb_bits, baseline) for each state."""
    size = 1 << table_log
    sym = [0] * size
    high = size - 1
    nxt = [0] * len(counts)
    for s, c in enumerate(counts):
        if c == -1:
            sym[high] = s
            high -= 1
            nxt[s] = 1
        else:
            nxt[s] = c
    step = (size >> 1) + (size >> 3) + 3
    mask = size - 1
    p = 0
    for s, c in enumerate(counts):
        for _ in range(max(c, 0)):
            sym[p] = s
            p = (p + step) & mask
            while p > high:
                p = (p + step) & mask
    table = [None] * size
    for u in range(size):
        s = sym[u]
        ns = nxt[s]
        nxt[s] += 1
        nbits = table_log - (ns.bit_length() - 1)
        table[u] = (s, nbits, (ns << nbits) - size)
    return table, table_log


def _rle_table(symbol):
    return [(symbol, 0, 0)], 0


class _Huffman:
    __slots__ = ("table", "maxbits")

    def __init__(self, table, maxbits):
        self.table, self.maxbits = table, maxbits


def _read_huffman(data, pos):
    """Huffman tree description -> (_Huffman, new_pos)."""
    header = data[pos]
    pos += 1
    if header < 128:          # FSE-compressed weights
        end = pos + header
        counts, tlog, p2 = _read_ncount(data, pos, 255, 6)
        table, _ = _build_fse(counts, tlog)
        br = _BackReader(data, p2, end)
        s1 = br.read(tlog)
        s2 = br.read(tlog)
        weights = []
        while True:
            sy, nb, base = table[s1]
            weights.append(sy)
            s1 = base + br.read(nb)
            if br.overflowed():
                weights.append(table[s2][0])
                break
            sy, nb, base = table[s2]
            weights.append(sy)
            s2 = base + br.read(nb)
            if br.overflowed():
                weights.append(table[s1][0])
                break
            if len(weights) > 255:
                raise ZstdError("too many Huffman weights")
        pos = end
    else:                     # 4-bit direct weights
        n = header - 127
        weights = []
        for i in range((n + 1) // 2):
            b = data[pos + i]
            weights += [b >> 4, b & 15]
        weights = weights[:n]
        pos += (n + 1) // 2
    total = sum(1 << (w - 1) for w in weights if w > 0)
    if total == 0:
        raise ZstdError("bad Huffman weights")
    maxbits = total.bit_length()
    left = (1 << maxbits) - total
    if left & (left - 1):
        raise ZstdError("bad Huffman weights")
    weights.append(left.bit_length())
    if maxbits > 11:
        raise ZstdError("Huffman code too long")
    size = 1 << maxbits
    rank = [0] * (maxbits + 2)
    for w in weights:
        if w:
            rank[w] += 1
    start, p = [0] * (maxbits + 2), 0
    for w in range(1, maxbits + 1):
        start[w] = p
        p += rank[w] << (w - 1)
    table = [None] * size
    for s, w in enumerate(weights):
        if w:
            ln = 1 << (w - 1)
            entry = (s, maxbits + 1 - w)
            st = start[w]
            for i in range(st, st + ln):
                table[i] = entry
            start[w] += ln
    return _Huffman(table, maxbits), pos


def _huff_stream(h, data, start, end, count, out):
    br = _BackReader(data, start, end)
    table, mb = h.table, h.maxbits
    # inline reader for speed
    acc, n, pos, d = br.acc, br.n, br.pos, data
    for _ in range(count):
        while n < mb:
            if pos > start:
                pos -= 1
                acc = (acc << 8) | d[pos]
                n += 8
            else:
                acc <<= mb - n
                n = mb
        sym, nb = table[acc >> (n - mb)]
        out.append(sym)
        n -= nb
        acc &= (1 << n) - 1


class _Frame:
    def __init__(self):
        self.huf = None
        self.ll = self.of = self.ml = None
        self.rep = [1, 4, 8]


def _literals(data, pos, fr):
    b0 = data[pos]
    ltype = b0 & 3
    sf = (b0 >> 2) & 3
    if ltype in (0, 1):
        if sf in (0, 2):
            size, pos = b0 >> 3, pos + 1
        elif sf == 1:
            size, pos = (b0 >> 4) + (data[pos + 1] << 4), pos + 2
        else:
            size, pos = (b0 >> 4) + (data[pos + 1] << 4) + (data[pos + 2] << 12), pos + 3
        if ltype == 0:
            return bytes(data[pos:pos + size]), pos + size
        return bytes([data[pos]]) * size, pos + 1
    if sf == 0:
        hb, bits, streams = 3, 10, 1
    elif sf == 1:
        hb, bits, streams = 3, 10, 4
    elif sf == 2:
        hb, bits, streams = 4, 14, 4
    else:
        hb, bits, streams = 5, 18, 4
    h = int.from_bytes(data[pos:pos + hb], "little")
    regen = (h >> 4) & ((1 << bits) - 1)
    comp = h >> (4 + bits)
    pos += hb
    end = pos + comp
    if ltype == 2:
        fr.huf, p = _read_huffman(data, pos)
    else:
        if fr.huf is None:
            raise ZstdError("treeless literals without a table")
        p = pos
    out = bytearray()
    if streams == 1:
        _huff_stream(fr.huf, data, p, end, regen, out)
    else:
        s1 = data[p] | data[p + 1] << 8
        s2 = data[p + 2] | data[p + 3] << 8
        s3 = data[p + 4] | data[p + 5] << 8
        p += 6
        seg = (regen + 3) // 4
        bounds = [p, p + s1, p + s1 + s2, p + s1 + s2 + s3, end]
        for i in range(4):
            cnt = seg if i < 3 else regen - 3 * seg
            _huff_stream(fr.huf, data, bounds[i], bounds[i + 1], cnt, out)
    return bytes(out), end


def _seq_table(mode, data, pos, default, max_symbol, max_log, prev):
    if mode == 0:
        return _build_fse(*default), pos
    if mode == 1:
        return _rle_table(data[pos]), pos + 1
    if mode == 2:
        counts, tlog, pos = _read_ncount(data, pos, max_symbol, max_log)
        return _build_fse(counts, tlog), pos
    if prev is None:
        raise ZstdError("repeat table without a previous one")
    return prev, pos


def _block(data, pos, end, fr, out):
    lits, pos = _literals(data, pos, fr)
    b0 = data[pos]
    if b0 == 0:
        nseq, pos = 0, pos + 1
    elif b0 < 128:
        nseq, pos = b0, pos + 1
    elif b0 < 255:
        nseq, pos = ((b0 - 128) << 8) + data[pos + 1], pos + 2
    else:
        nseq, pos = data[pos + 1] + (data[pos + 2] << 8) + 0x7F00, pos + 3
    if nseq == 0:
        out += lits
        return
    modes = data[pos]
    pos += 1
    fr.ll, pos = _seq_table(modes >> 6, data, pos, LL_DEFAULT, 35, 9, fr.ll)
    fr.of, pos = _seq_table((modes >> 4) & 3, data, pos, OF_DEFAULT, 31, 8, fr.of)
    fr.ml, pos = _seq_table((modes >> 2) & 3, data, pos, ML_DEFAULT, 52, 9, fr.ml)
    (llt, lll), (oft, ofl), (mlt, mll) = fr.ll, fr.of, fr.ml
    br = _BackReader(data, pos, end)
    rd = br.read
    sll, sof, sml = rd(lll), rd(ofl), rd(mll)
    rep = fr.rep
    lp = 0
    for i in range(nseq):
        llc, llnb, llb = llt[sll]
        ofc, ofnb, ofb = oft[sof]
        mlc, mlnb, mlb = mlt[sml]
        ov = (1 << ofc) + rd(ofc)
        ml = ML_BASE[mlc] + rd(ML_BITS[mlc])
        ll = LL_BASE[llc] + rd(LL_BITS[llc])
        if ov > 3:
            off = ov - 3
            rep[2], rep[1], rep[0] = rep[1], rep[0], off
        else:
            idx = ov - 1 if ll else ov
            if idx == 0:
                off = rep[0]
            elif idx == 3:
                off = rep[0] - 1
                rep[2], rep[1], rep[0] = rep[1], rep[0], off
            else:
                off = rep[idx]
                if idx == 2:
                    rep[2] = rep[1]
                rep[1] = rep[0]
                rep[0] = off
        if i != nseq - 1:
            sll = llb + rd(llnb)
            sml = mlb + rd(mlnb)
            sof = ofb + rd(ofnb)
        if ll:
            out += lits[lp:lp + ll]
            lp += ll
        if off <= 0 or off > len(out):
            raise ZstdError("bad match offset")
        if off >= ml:
            st = len(out) - off
            out += out[st:st + ml]
        else:
            st = len(out) - off
            chunk = out[st:]
            reps, rem = divmod(ml, off)
            out += chunk * reps + chunk[:rem]
    out += lits[lp:]


def decompress_pure(data):
    data = memoryview(bytes(data))
    pos, n = 0, len(data)
    out = bytearray()
    while pos + 4 <= n:
        magic = int.from_bytes(data[pos:pos + 4], "little")
        pos += 4
        if 0x184D2A50 <= magic <= 0x184D2A5F:          # skippable frame
            size = int.from_bytes(data[pos:pos + 4], "little")
            pos += 4 + size
            continue
        if magic != 0xFD2FB528:
            if out:
                break
            raise ZstdError("not zstd data")
        fhd = data[pos]
        pos += 1
        fcs_flag, single, checksum, did_flag = fhd >> 6, (fhd >> 5) & 1, (fhd >> 2) & 1, fhd & 3
        if not single:
            pos += 1
        pos += (0, 1, 2, 4)[did_flag]
        pos += (1 if single else 0, 2, 4, 8)[fcs_flag]
        fr = _Frame()
        frame_out = bytearray()
        while True:
            bh = data[pos] | data[pos + 1] << 8 | data[pos + 2] << 16
            pos += 3
            last, btype, bsize = bh & 1, (bh >> 1) & 3, bh >> 3
            if btype == 0:
                frame_out += data[pos:pos + bsize]
                pos += bsize
            elif btype == 1:
                frame_out += bytes([data[pos]]) * bsize
                pos += 1
            elif btype == 2:
                _block(data, pos, pos + bsize, fr, frame_out)
                pos += bsize
            else:
                raise ZstdError("reserved block type")
            if last:
                break
        if checksum:
            pos += 4
        out += frame_out
    return bytes(out)
