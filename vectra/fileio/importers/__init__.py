"""Importers for artwork made in other apps: .ai, .eps / .ps and .pdf.

* Modern Illustrator files (.ai, CS and later) are PDF files; the PDF page is read.
  When the file was saved *without* "Create PDF Compatible File", the native
  Illustrator data embedded in the file is read instead.
* Legacy Illustrator files (AI 3–8) and EPS files are PostScript; a small
  PostScript interpreter handles them (DOS-binary EPS headers are stripped).

``import_file(path)`` returns an ``ImportResult`` (shapes, artboard, notes).
"""

import os

from vectra.fileio.importers.common import ImportResult  # noqa: F401  (re-export)

__all__ = ["ImportResult", "ImportFailed", "import_bytes", "import_file", "is_importable", "detect"]

IMPORT_EXTENSIONS = (".ai", ".eps", ".epsf", ".ps", ".pdf")


class ImportFailed(ValueError):
    """Raised with a short reason key: 'unsupported', 'empty', 'encrypted', 'no_pdf_content',
    'corrupted'."""

    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


def detect(data):
    if data[:4] == b"\xc5\xd0\xd3\xc6":            # DOS EPS binary header
        return "ps"
    head = data[:1024]
    if b"%PDF-" in head:
        return "pdf"
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n\x00")
    if stripped.startswith(b"%!"):
        return "ps"
    # some writers put a preview / junk before the real header
    big = data[:1 << 20]
    if b"%PDF-" in big:
        return "pdf"
    i = big.find(b"%!PS-Adobe")
    if i >= 0:
        return "ps"
    if b"%%BoundingBox" in big[:65536] or b"%AI5_" in big[:65536]:
        return "ps"
    return None


def describe_header(data):
    """Short, printable description of the first bytes (for error messages)."""
    head = data[:24]
    text = "".join(chr(b) if 32 <= b < 127 else "." for b in head)
    return f"{text}  [{head[:12].hex(' ')}]"


def looks_text_mangled(data):
    """True when binary bytes were replaced by U+FFFD (EF BF BD) — the file went
    through a text/UTF-8 conversion (e.g. a broken upload or copy) and the
    compressed artwork inside can no longer be decoded."""
    bad = data.count(b"\xef\xbf\xbd")
    return bad > 64 and bad * 3 > len(data) * 0.05


def import_bytes(data, page_index=0, ext=""):
    if looks_text_mangled(data):
        raise ImportFailed("corrupted", describe_header(data))
    kind = detect(data)
    if kind is None and ext in (".eps", ".epsf", ".ps", ".ai") and data.lstrip()[:1] == b"%":
        kind = "ps"   # PostScript that starts with a plain comment instead of %!
    if kind == "pdf":
        from vectra.fileio.importers.pdf import PDFError
        from vectra.fileio.importers.pdf_import import import_pdf_bytes
        try:
            res = import_pdf_bytes(data, page_index)
        except PDFError as ex:
            reason = "encrypted" if "ncrypt" in str(ex) else "unsupported"
            raise ImportFailed(reason, str(ex)) from ex
    elif kind == "ps":
        from vectra.fileio.importers.ps_import import import_ps_bytes
        res = import_ps_bytes(data)
    else:
        raise ImportFailed("unsupported", describe_header(data))
    if not res.shapes:
        raise ImportFailed("no_pdf_content" if res.notes.get("no_pdf_content") else "empty")
    for i, s in enumerate(res.shapes, start=1):
        s["id"] = i
    _finish_layers(res)
    res.source = kind
    return res


def _finish_layers(res):
    """Every imported shape belongs to a layer; drop empty duplicate defaults."""
    if not res.layers:
        res.layers = [{"id": 1, "name": "Layer 1", "visible": True, "locked": False, "color": None}]
    ids = {l["id"] for l in res.layers}
    bottom = res.layers[0]["id"]
    for s in res.shapes:
        if s.get("layer") not in ids:
            s["layer"] = bottom


def import_file(path, page_index=0):
    with open(path, "rb") as fh:
        data = fh.read()
    return import_bytes(data, page_index, os.path.splitext(path)[1].lower())


def is_importable(path):
    return os.path.splitext(path)[1].lower() in IMPORT_EXTENSIONS
