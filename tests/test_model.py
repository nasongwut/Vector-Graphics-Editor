"""Unit tests for the Tk-free parts:  python -m unittest discover tests"""

import json
import os
import tempfile
import unittest

from vectra import i18n
from vectra.fileio import json_io, svg_export
from vectra.model import geometry as g
from vectra.model import pathops
from vectra.model import shapes as sh
from vectra.model.document import Document
from vectra.model.history import History

STYLE = {"fill": "#ff0000", "stroke": "#000000", "width": 2, "font_size": 20, "radius": 0, "dash": False,
         "font": None}


def rect(doc, x0, y0, x1, y1, **kw):
    s = sh.make_shape("rect", [x0, y0, x1, y1], STYLE)
    s.update(kw)
    return doc.add(s)


class GeometryTest(unittest.TestCase):
    def test_rotate_point_clockwise_on_screen(self):
        x, y = g.rotate_point(10, 0, 0, 0, 90)
        self.assertAlmostEqual(x, 0)
        self.assertAlmostEqual(y, 10)  # y grows downward => clockwise

    def test_normalize_angle(self):
        self.assertEqual(g.normalize_angle(190), -170)
        self.assertEqual(g.normalize_angle(-180), 180)
        self.assertEqual(g.normalize_angle(360), 0)

    def test_resize_keep_ratio(self):
        nb = g.resize_bbox((0, 0, 100, 50), 4, 300, 60, keep_ratio=True)
        self.assertEqual(nb, (0, 0, 300, 150))

    def test_star(self):
        pts = g.star_points(0, 0, 10, 5, 5)
        self.assertEqual(len(pts), 20)
        self.assertAlmostEqual(pts[1], -10)  # first point straight up

    def test_nearest_segment(self):
        idx, d, qx, qy = g.nearest_segment([0, 0, 10, 0, 10, 10], 5, 1, closed=False)
        self.assertEqual(idx, 1)
        self.assertAlmostEqual(d, 1)


class ShapesTest(unittest.TestCase):
    def test_line_never_filled(self):
        s = sh.make_shape("line", [0, 0, 1, 1], STYLE)
        self.assertIsNone(s["fill"])
        self.assertEqual(s["stroke"], "#000000")

    def test_rotated_rect_keeps_size_and_moves_centre(self):
        s = sh.make_shape("rect", [0, 0, 20, 10], STYLE)
        r = sh.rotated(s, 90, 0, 0)
        self.assertEqual(r["rot"], 90)
        cx, cy = sh.box_center(r)
        self.assertAlmostEqual(cx, -5)
        self.assertAlmostEqual(cy, 10)
        self.assertAlmostEqual(r["pts"][2] - r["pts"][0], 20)
        bb = sh.geometry_bbox(r)
        self.assertAlmostEqual(bb[2] - bb[0], 10)  # rotated: width/height swap
        self.assertAlmostEqual(bb[3] - bb[1], 20)

    def test_rotate_back_removes_rot(self):
        s = sh.make_shape("rect", [0, 0, 20, 10], STYLE)
        r = sh.rotated(sh.rotated(s, 30, 10, 5), -30, 10, 5)
        self.assertNotIn("rot", r)

    def test_scaled_text_size(self):
        s = sh.make_shape("text", [0, 0], STYLE)
        n = sh.scaled(s, (0, 0, 10, 10), (0, 0, 20, 20))
        self.assertEqual(n["size"], 40)

    def test_flip_polygon(self):
        s = sh.make_shape("polygon", [0, 0, 10, 0, 10, 10], STYLE)
        f = sh.flipped(s, "h", 5, sh.geometry_bbox(s))
        self.assertEqual(f["pts"], [10, 0, 0, 0, 0, 10])

    def test_to_path(self):
        s = sh.make_shape("rect", [0, 0, 10, 10], dict(STYLE, radius=3))
        p = sh.to_path(s)
        self.assertEqual(p["type"], "path")
        self.assertEqual(len(p["pts"]), 16)  # rounded corners -> 8 anchors
        self.assertNotIn("radius", p)


class DocumentTest(unittest.TestCase):
    def setUp(self):
        self.doc = Document()
        self.a = rect(self.doc, 0, 0, 10, 10)
        self.b = rect(self.doc, 20, 0, 30, 10)
        self.c = rect(self.doc, 40, 0, 50, 10)

    def order(self):
        return [s["id"] for s in self.doc.shapes]

    def test_ids_increment(self):
        self.assertEqual(self.order(), [1, 2, 3])
        self.assertEqual(self.doc.next_id, 4)

    def test_stacking(self):
        self.doc.bring_front({1})
        self.assertEqual(self.order(), [2, 3, 1])
        self.doc.send_backward({1})
        self.assertEqual(self.order(), [2, 1, 3])
        self.doc.send_back({3})
        self.assertEqual(self.order(), [3, 2, 1])

    def test_group_makes_members_contiguous(self):
        gid = self.doc.group({1, 3})
        self.assertEqual(self.order(), [2, 1, 3])
        self.assertEqual(self.doc.expand_groups({1}), {1, 3})
        self.assertEqual(len(self.doc.units({1, 2, 3})), 2)
        self.assertTrue(self.doc.ungroup({1, 3}))
        self.assertIsNone(self.doc.by_id(1).get("gid"))
        self.assertIsNotNone(gid)

    def test_copies_get_new_group(self):
        self.doc.group({1, 2})
        new = self.doc.insert_copies(self.doc.of_ids({1, 2}), 5)
        gids = {self.doc.by_id(i)["gid"] for i in new}
        self.assertEqual(len(gids), 1)
        self.assertNotEqual(gids.pop(), self.doc.by_id(1)["gid"])

    def test_editable_excludes_hidden_and_locked(self):
        self.a["hidden"] = True
        self.b["locked"] = True
        self.assertEqual([s["id"] for s in self.doc.editable()], [3])


class HistoryTest(unittest.TestCase):
    def test_undo_redo_and_coalescing(self):
        t = [0.0]
        h = History(clock=lambda: t[0])
        state = {"v": 0}
        snap = lambda: dict(state)  # noqa: E731
        self.assertTrue(h.record(snap, "nudge"))
        state["v"] = 1
        t[0] = 0.5
        self.assertFalse(h.record(snap, "nudge"))  # coalesced
        state["v"] = 2
        self.assertEqual(h.undo(snap), {"v": 0})
        self.assertEqual(h.redo(snap), {"v": 2})


class FileIOTest(unittest.TestCase):
    def test_json_roundtrip_and_validation(self):
        doc = Document()
        rect(doc, 0, 0, 10, 10, rot=15, radius=2)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.json")
            json_io.save(p, doc.shapes, (0, 0, 100, 100))
            shapes, artboard = json_io.load(p)
            self.assertEqual(shapes, doc.shapes)
            self.assertEqual(artboard, [0, 0, 100, 100])
            with open(p, "w") as fh:
                json.dump({"shapes": [{"id": 1, "type": "blob", "pts": [0, 0]}]}, fh)
            with self.assertRaises(ValueError):
                json_io.load(p)

    def test_v1_file_loads(self):
        v1 = {"app": "vectra", "version": 1, "artboard": [0, 0, 1000, 700], "shapes": [
            {"id": 1, "type": "ellipse", "pts": [0, 0, 5, 5], "fill": "#fff", "stroke": None, "width": 0}]}
        self.assertEqual(json_io.validate(v1["shapes"]), v1["shapes"])

    def test_svg(self):
        doc = Document()
        rect(doc, 0, 0, 10, 10, rot=45, radius=2, dash=True)
        rect(doc, 0, 0, 10, 10, hidden=True)
        t = doc.add(dict(sh.make_shape("text", [1, 2], STYLE), text="<ก&ข>"))
        doc.group({1, t["id"]})
        svg = svg_export.build_svg(doc.shapes, (0, 0, 100, 100))
        self.assertIn('transform="rotate(45 5 5)"', svg)
        self.assertIn('rx="2"', svg)
        self.assertIn("stroke-dasharray", svg)
        self.assertIn("&lt;ก&amp;ข&gt;", svg)
        self.assertIn('<g id="group-1">', svg)
        self.assertEqual(svg.count("<rect"), 2)  # background + visible rect


class PathTest(unittest.TestCase):
    def test_ellipse_to_path_is_close(self):
        e = sh.make_shape("ellipse", [0, 0, 100, 50], STYLE)
        p = sh.to_path(e)
        self.assertEqual(p["type"], "path")
        self.assertTrue(p["closed"])
        bb = sh.geometry_bbox(p)
        for a, b in zip(bb, (0, 0, 100, 50)):
            self.assertAlmostEqual(a, b, delta=0.6)

    def test_rounded_rect_and_pencil_to_path(self):
        r = sh.to_path(sh.make_shape("rect", [0, 0, 100, 60], dict(STYLE, radius=10)))
        self.assertEqual(sh.node_count(r), 8)
        pen = sh.to_path(sh.make_shape("pen", [0, 0, 10, 10, 20, 0, 30, 10, 40, 0], STYLE))
        self.assertEqual(pen["pts"][:2], [0, 0])
        self.assertEqual(pen["pts"][-2:], [40, 0])

    def test_insert_delete_split_join(self):
        p = sh.to_path(sh.make_shape("line", [0, 0, 100, 0], STYLE))
        seg, t, d, qx, qy = pathops.nearest_on_path(p, 50, 3)
        self.assertAlmostEqual(d, 3)
        idx = pathops.insert_node(p, seg, t)
        self.assertEqual(sh.node_count(p), 3)
        self.assertAlmostEqual(p["pts"][2 * idx], 50)
        a, b = pathops.split_at(p, (0, 1), 0.5)
        self.assertEqual(a["pts"][-2:], b["pts"][:2])
        j = pathops.join(a, b)
        self.assertEqual(sh.node_count(j), 5)
        self.assertTrue(pathops.delete_node(j, 1))

    def test_split_closed_opens_it(self):
        p = sh.to_path(sh.make_shape("rect", [0, 0, 10, 10], STYLE))
        pieces = pathops.split_at(p, (0, 1), 0.5)
        self.assertEqual(len(pieces), 1)
        self.assertFalse(pieces[0]["closed"])
        self.assertEqual(sh.node_count(pieces[0]), 6)

    def test_smooth_handles_mirror(self):
        p = sh.make_shape("path", [0, 0, 50, 0, 100, 0], STYLE)
        pathops.set_symmetric_handles(p, 1, 60, 10)
        self.assertEqual(sh.node(p, 1)[1], (40, -10))
        pathops.move_handle(p, 1, "out", 50, 20)
        hin = sh.node(p, 1)[1]
        self.assertAlmostEqual(hin[0], 50)
        self.assertLess(hin[1], 0)
        pathops.toggle_smooth(p, 1)
        self.assertEqual(sh.node(p, 1)[1], (50, 0))

    def test_transforms_move_handles(self):
        p = sh.make_shape("path", [0, 0, 10, 0], STYLE)
        pathops.set_symmetric_handles(p, 1, 15, 5)
        r = sh.rotated(p, 90, 0, 0)
        self.assertAlmostEqual(r["ctrl"][6], -5)
        self.assertAlmostEqual(r["ctrl"][7], 15)
        f = sh.reflected(p, 90, 0, 0, sh.geometry_bbox(p))  # vertical axis -> mirror x
        self.assertAlmostEqual(f["pts"][2], -10)
        self.assertAlmostEqual(f["pts"][3], 0)

    def test_path_svg(self):
        p = sh.to_path(sh.make_shape("ellipse", [0, 0, 10, 10], STYLE))
        p["id"] = 1
        svg = svg_export.shape_to_svg(p)
        self.assertIn("<path", svg)
        self.assertIn("C", svg)
        self.assertIn("Z", svg)


class I18nTest(unittest.TestCase):
    def test_both_languages_complete(self):
        for key, pair in i18n.STRINGS.items():
            self.assertEqual(len(pair), 2, key)
            self.assertTrue(all(pair), key)

    def test_switch(self):
        i18n.set_language("en")
        self.assertEqual(i18n.tr("m_save"), "Save")
        self.assertEqual(i18n.tr("flash_copied", n=2), "Copied 2 objects")
        i18n.set_language("th")
        self.assertEqual(i18n.tr("m_save"), "บันทึก")
        i18n.set_language("xx")
        self.assertEqual(i18n.get_language(), i18n.DEFAULT_LANGUAGE)


if __name__ == "__main__":
    unittest.main()


class LayerTest(unittest.TestCase):
    def setUp(self):
        self.doc = Document()
        self.a = rect(self.doc, 0, 0, 10, 10)          # on Layer 1
        self.top = self.doc.add_layer("Top")             # becomes active
        self.b = rect(self.doc, 20, 0, 30, 10)

    def test_new_shapes_go_to_active_layer_and_stay_grouped(self):
        self.assertEqual(self.a["layer"], 1)
        self.assertEqual(self.b["layer"], self.top["id"])
        self.doc.active_layer = 1
        c = rect(self.doc, 40, 0, 50, 10)
        # c is on the bottom layer, so it stays below b
        self.assertEqual([s["id"] for s in self.doc.shapes], [self.a["id"], c["id"], self.b["id"]])

    def test_bring_front_stays_inside_layer(self):
        self.doc.bring_front({self.a["id"]})
        self.assertEqual(self.doc.shapes[-1]["id"], self.b["id"])

    def test_move_layer_and_move_to_layer(self):
        self.doc.move_layer(self.top["id"], -1)
        self.assertEqual(self.doc.shapes[0]["id"], self.b["id"])
        self.doc.move_to_layer({self.a["id"]}, self.top["id"])
        self.assertEqual(self.a["layer"], self.top["id"])

    def test_hidden_or_locked_layer_not_editable(self):
        self.top["visible"] = False
        self.assertEqual([s["id"] for s in self.doc.editable()], [self.a["id"]])
        self.top["visible"] = True
        self.doc.layer(1)["locked"] = True
        self.assertEqual([s["id"] for s in self.doc.editable()], [self.b["id"]])

    def test_delete_layer_and_undo_snapshot(self):
        snap = self.doc.snapshot()
        gone = self.doc.delete_layer(self.top["id"])
        self.assertEqual(gone, {self.b["id"]})
        self.assertEqual(len(self.doc.layers), 1)
        self.doc.restore(snap)
        self.assertEqual(len(self.doc.layers), 2)
        self.assertEqual(len(self.doc.shapes), 2)

    def test_group_moves_to_top_members_layer(self):
        self.doc.group({self.a["id"], self.b["id"]})
        self.assertEqual(self.a["layer"], self.top["id"])

    def test_old_files_get_a_layer(self):
        d = Document()
        d.load([{"id": 1, "type": "rect", "pts": [0, 0, 1, 1]}])
        self.assertEqual(d.shapes[0]["layer"], 1)

    def test_json_and_svg_keep_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "l.json")
            json_io.save(p, self.doc.shapes, (0, 0, 100, 100), self.doc.layers, self.doc.active_layer)
            shapes, _ab, layers, active = json_io.load_full(p)
            self.assertEqual([l["name"] for l in layers], ["Layer 1", "Top"])
            self.assertEqual(active, self.top["id"])
        svg = svg_export.build_svg(self.doc.shapes, (0, 0, 100, 100), layers=self.doc.layers)
        self.assertIn('<g id="Top">', svg)
