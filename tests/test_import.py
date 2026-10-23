"""Importer tests (.pdf / .ai / .eps) with small hand-made files:
python -m unittest discover tests"""

import struct
import unittest
import zlib

from vectra.fileio.importers import ImportFailed, detect, import_bytes
from vectra.model import shapes as sh


def make_pdf(content, extra_objs=(), resources=b"<< >>", page_extra=b"", compress=True, size=(400, 300)):
    """Tiny PDF writer: catalog, pages, one page with ``content``."""
    stream = zlib.compress(content) if compress else content
    filt = b"/Filter /FlateDecode " if compress else b""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R /Resources %s %s>>"
        % (size[0], size[1], resources, page_extra),
        b"<< " + filt + b"/Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ] + list(extra_objs)
    out = b"%PDF-1.7\n"
    for i, body in enumerate(objs, start=1):
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    return out + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"


class DetectTest(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(detect(b"%PDF-1.4 ..."), "pdf")
        self.assertEqual(detect(b"%!PS-Adobe-3.0 EPSF-3.0"), "ps")
        self.assertEqual(detect(b"\xc5\xd0\xd3\xc6" + b"\0" * 30), "ps")
        self.assertIsNone(detect(b"hello"))
        with self.assertRaises(ImportFailed):
            import_bytes(b"not a drawing")

    def test_text_mangled_file_is_reported(self):
        good = make_pdf(b"0 0 10 10 re f")
        bad = good.replace(b"\n", b"\n\xef\xbf\xbd" * 30)
        with self.assertRaises(ImportFailed) as cm:
            import_bytes(bad)
        self.assertEqual(cm.exception.reason, "corrupted")


class PDFImportTest(unittest.TestCase):
    def test_paths_colours_and_flip(self):
        content = (b"1 0 0 rg 0 0 0 1 K 4 w 10 10 100 50 re B "
                   b"0 0 1 rg 200 100 m 250 200 300 200 350 100 c h f "
                   b"[6 3] 0 d 0.5 G 2 w 10 280 m 390 280 l S")
        res = import_bytes(make_pdf(content))
        self.assertEqual(res.source, "pdf")
        self.assertEqual(res.artboard, [0, 0, 400, 300])
        rect, curve, line = res.shapes
        self.assertEqual(rect["fill"], "#ff0000")
        self.assertEqual(rect["width"], 4)
        # PDF y-up -> screen y-down: rect bottom at y=10 becomes 290
        self.assertEqual(max(rect["pts"][1::2]), 290)
        self.assertTrue(curve["closed"])
        self.assertEqual(curve["fill"], "#0000ff")
        self.assertFalse(sh.is_straight(curve))
        self.assertTrue(line.get("dash"))
        self.assertIsNone(line["fill"])
        self.assertEqual(line["stroke"], "#808080")

    def test_compound_path_with_hole(self):
        content = b"0 g 0 0 m 100 0 l 100 100 l 0 100 l h 25 25 m 25 75 l 75 75 l 75 25 l h f*"
        res = import_bytes(make_pdf(content))
        self.assertEqual(len(res.shapes), 1)
        s = res.shapes[0]
        self.assertTrue(sh.is_compound(s))
        self.assertEqual(sh.parts(s), [[4, True], [4, True]])

    def test_text_with_font(self):
        font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
        content = b"BT /F1 24 Tf 1 0 0 1 50 100 Tm (Hello) Tj ET"
        res = import_bytes(make_pdf(content, [font], resources=b"<< /Font << /F1 5 0 R >> >>"))
        t = [s for s in res.shapes if s["type"] == "text"][0]
        self.assertEqual(t["text"], "Hello")
        self.assertAlmostEqual(t["size"], 24)
        self.assertEqual(t.get("weight"), "bold")
        self.assertEqual(t["font"], "Helvetica")

    def test_form_xobject_and_cmyk(self):
        form_body = b"0 0 1 0 k 0 0 10 10 re f"
        form = (b"<< /Type /XObject /Subtype /Form /BBox [0 0 10 10] /Length %d >>\nstream\n"
                % len(form_body) + form_body + b"\nendstream")
        content = b"q 3 0 0 3 100 100 cm /X0 Do Q"
        res = import_bytes(make_pdf(content, [form], resources=b"<< /XObject << /X0 5 0 R >> >>"))
        s = res.shapes[0]
        self.assertEqual(sh.geometry_bbox(s), (100, 170, 130, 200))
        r, g, b = (int(s["fill"][i:i + 2], 16) for i in (1, 3, 5))
        self.assertGreater(r, 200)
        self.assertGreater(g, 200)
        self.assertLess(b, 120)  # yellow

    def test_ai_without_pdf_content_uses_private_data(self):
        native = (b"%!PS-Adobe-3.0\n%%Creator: Adobe Illustrator(R) 17.0\n%%BoundingBox: 0 0 400 300\n"
                  b"%%EndSetup\n0 1 1 0 k\n10 10 m\n110 10 l\n110 110 l\n10 110 l\nf\n%%Trailer\n")
        priv = b"%AI12_CompressedData" + zlib.compress(native)
        priv_obj = b"<< /Length %d >>\nstream\n" % len(priv) + priv + b"\nendstream"
        font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        content = b"BT /F1 10 Tf 20 150 Td (This is an Adobe Illustrator File that was saved without PDF Content.) Tj ET"
        pdf = make_pdf(content, [font, priv_obj], resources=b"<< /Font << /F1 5 0 R >> >>",
                       page_extra=b"/PieceInfo << /Illustrator << /Private << /AIPrivateData1 6 0 R >> >> >> ")
        res = import_bytes(pdf)
        self.assertEqual(res.notes.get("from_private"), 1)
        self.assertEqual(len(res.shapes), 1)
        self.assertEqual(res.shapes[0]["type"], "path")
        self.assertEqual(sh.geometry_bbox(res.shapes[0]), (10, 190, 110, 290))


class LayerImportTest(unittest.TestCase):
    def test_pdf_optional_content_becomes_layers(self):
        ocgs = [b"<< /Type /OCG /Name (fill) >>", b"<< /Type /OCG /Name (art) >>",
                b"<< /Type /OCG /Name <feff0e020e2d0e1a> >>"]          # UTF-16 Thai name
        # objects 5,6,7 = OCGs ; Order lists the top layer first (as Illustrator writes it)
        content = (b"/OC /MC0 BDC 0 g 0 0 10 10 re f EMC /OC /MC1 BDC 1 0 0 rg 20 0 10 10 re f EMC "
                   b"/OC /MC2 BDC 0 0 1 rg 40 0 10 10 re f EMC")
        res_dict = b"<< /Properties << /MC0 5 0 R /MC1 6 0 R /MC2 7 0 R >> >>"
        pdf = make_pdf(content, ocgs, resources=res_dict)
        pdf = pdf.replace(b"<< /Type /Catalog /Pages 2 0 R >>",
                          b"<< /Type /Catalog /Pages 2 0 R /OCProperties << /OCGs [5 0 R 6 0 R 7 0 R] "
                          b"/D << /Order [7 0 R 6 0 R 5 0 R] /OFF [6 0 R] /Locked [5 0 R] >> >> >>")
        res = import_bytes(pdf)
        self.assertEqual([l["name"] for l in res.layers], ["fill", "art", "ขอบ"])
        self.assertFalse(res.layers[1]["visible"])
        self.assertTrue(res.layers[0]["locked"])
        self.assertEqual([s["layer"] for s in res.shapes], [1, 2, 3])

    def test_legacy_ai_layers(self):
        ai = (b"%!PS-Adobe-3.0\n%%Creator: Adobe Illustrator(R) 8.0\n%%BoundingBox: 0 0 100 100\n"
              b"%%EndSetup\n%AI5_BeginLayer\n1 1 1 1 0 0 0 79 128 255 Lb\n(Back) Ln\n0 g\n"
              b"0 0 m 10 0 l 10 10 l f\nLB\n%AI5_EndLayer--\n%AI5_BeginLayer\n0 1 0 1 0 0 1 255 79 79 Lb\n"
              b"(Front) Ln\n20 0 m 30 0 l 30 10 l f\nLB\n%%Trailer\n")
        res = import_bytes(ai)
        self.assertEqual([(l["name"], l["visible"], l["locked"], l["color"]) for l in res.layers],
                         [("Back", True, False, "#4f80ff"), ("Front", False, True, "#ff4f4f")])
        self.assertEqual([s["layer"] for s in res.shapes], [1, 2])


class ZstdTest(unittest.TestCase):
    def test_pure_python_decoder(self):
        from vectra.fileio.importers.zstd import decompress_pure
        src = (b"%AI5_BeginLayer\n" + b"0 0 m 10 0 l 10 10 l f\n" * 40 + b"Hello zstd! " * 20)
        self.assertEqual(decompress_pure(bytes.fromhex("28b52ffd609803ed0100f402254149355f426567696e4c617965720a302030206d2031302030206c20313020316648656c6c6f207a7374642120480300e017eaffea2c96d62503")), src)
        self.assertEqual(decompress_pure(bytes.fromhex("28b52ffd60980b1d0a002413000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff254149355f426567696e4c617965720a302030206d2031302030206c203130203130206c206648656c6c6f207a73746421200300e1172af9af4ef500f43bf0d329")), bytes(range(256)) * 8 + src)


class NestedGroupTest(unittest.TestCase):
    def test_nested_groups_and_ungroup_one_level(self):
        ai = (b"%!PS-Adobe-3.0\n%%Creator: Adobe Illustrator(R) 24.0\n%%BoundingBox: 0 0 100 100\n"
              b"%%EndSetup\nu\n0 g\n0 0 m 10 0 l 10 10 l f\nu\n20 0 m 30 0 l 30 10 l f\n"
              b"40 0 m 50 0 l 50 10 l f\nU\nU\n60 0 m 70 0 l 70 10 l f\n%%Trailer\n")
        res = import_bytes(ai)
        a, b, c, d = res.shapes
        self.assertEqual(sh.group_path(a), [a["gid"]])
        self.assertEqual(len(sh.group_path(b)), 2)
        self.assertEqual(sh.group_path(b), sh.group_path(c))
        self.assertEqual(sh.group_path(d), [])
        from vectra.model.document import Document
        doc = Document()
        doc.load(res.shapes)
        self.assertEqual(doc.expand_groups({a["id"]}), {a["id"], b["id"], c["id"]})
        doc.ungroup({a["id"], b["id"], c["id"]})
        self.assertEqual(sh.group_path(a), [])
        self.assertEqual(len(sh.group_path(b)), 1)          # inner group survives
        self.assertEqual(doc.expand_groups({b["id"]}), {b["id"], c["id"]})
        doc.group({b["id"], d["id"]})
        self.assertEqual(len(sh.group_path(b)), 2)


class PSImportTest(unittest.TestCase):
    EPS = b"""%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 200 100
%%EndComments
/box { newpath moveto 50 0 rlineto 0 50 rlineto -50 0 rlineto closepath } def
0.2 0.4 0.6 setrgbcolor
10 10 box fill
gsave 100 0 translate 0 0 1 setrgbcolor 3 setlinewidth
newpath 50 50 30 0 360 arc stroke grestore
/Helvetica findfont 12 scalefont setfont 10 80 moveto (EPS text) show
showpage
%%EOF
"""

    def test_eps_procedures_arcs_text(self):
        res = import_bytes(self.EPS)
        self.assertEqual(res.source, "ps")
        self.assertEqual(res.artboard, [0, 0, 200, 100])
        types = [s["type"] for s in res.shapes]
        self.assertEqual(types.count("path"), 2)
        box = res.shapes[0]
        self.assertEqual(box["fill"], "#336699")
        self.assertEqual(sh.geometry_bbox(box), (10, 40, 60, 90))
        circle = res.shapes[1]
        self.assertIsNone(circle["fill"])
        self.assertEqual(circle["width"], 3)
        bb = sh.geometry_bbox(circle)
        self.assertAlmostEqual(bb[0], 120, delta=0.5)
        self.assertAlmostEqual(bb[2], 180, delta=0.5)
        txt = [s for s in res.shapes if s["type"] == "text"][0]
        self.assertEqual(txt["text"], "EPS text")

    def test_dos_binary_eps_header(self):
        ps = self.EPS
        header = b"\xc5\xd0\xd3\xc6" + struct.pack("<IIIIIIH", 30, len(ps), 0, 0, 0, 0, 0xFFFF)
        res = import_bytes(header + ps)
        self.assertEqual(len([s for s in res.shapes if s["type"] == "path"]), 2)

    def test_legacy_illustrator_operators(self):
        ai = b"""%!PS-Adobe-3.0
%%Creator: Adobe Illustrator(R) 8.0
%%BoundingBox: 0 0 300 200
%%EndComments
%%BeginProlog
garbage procset that must be skipped {{{
%%EndProlog
%%BeginSetup
%%EndSetup
u
1 0 0 Xa
0 0 0 1 K
2 w
20 20 m
120 20 l
120 120 l
20 120 l
b
*u
0 0 1 0 k
150 20 m 250 20 l 250 120 l 150 120 l 150 20 l f
175 45 m 175 95 l 225 95 l 225 45 l 175 45 l f
*U
U
0 To
1 0 0 1 30 150 0 Tp
TP
0 g
/_Helvetica-Bold 24 Tf
(Legacy) Tx
TO
%%Trailer
"""
        res = import_bytes(ai)
        rect, compound, text = res.shapes
        self.assertEqual(rect["fill"], "#ff0000")
        self.assertTrue(rect["closed"])
        self.assertEqual(rect["width"], 2)
        self.assertTrue(sh.is_compound(compound))
        self.assertIsNotNone(rect.get("gid"))
        self.assertEqual(rect.get("gid"), compound.get("gid"))
        self.assertEqual(text["text"], "Legacy")
        self.assertEqual(text.get("weight"), "bold")


if __name__ == "__main__":
    unittest.main()
