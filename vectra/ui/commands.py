"""Edit, Select, Object and View commands."""

import copy
from tkinter import messagebox, simpledialog

from vectra.i18n import tr
from vectra.model import geometry as geo
from vectra.model import pathops
from vectra.model import shapes as sh


class CommandsMixin:
    # ── creating shapes ─────────────────────────────────────────────────────
    def new_shape(self, typ, pts):
        return sh.make_shape(typ, pts, self.current_style())

    def add_shape(self, s):
        self.push_undo()
        s = self.doc.add(s)
        self.selected = {s["id"]}
        return s

    def _changed(self, flash=None):
        self.on_selection_changed()
        self.render()
        if flash:
            self.flash(flash)

    # ── Edit ────────────────────────────────────────────────────────────────
    def delete_sel(self):
        if not self.selected:
            return
        self.push_undo()
        self.doc.remove(self.selected)
        self.selected.clear()
        self._changed()

    def copy_sel(self):
        if self.selected:
            self.clipboard = copy.deepcopy(self.selected_shapes())
            self.flash(tr("flash_copied", n=len(self.clipboard)))

    def cut_sel(self):
        if self.selected:
            self.copy_sel()
            self.delete_sel()

    def _paste(self, offset=0.0, index=None, center=False):
        if not self.clipboard:
            return
        items = copy.deepcopy(self.clipboard)
        if center:  # paste in the middle of the view
            bb = geo.union_bbox([sh.geometry_bbox(s) for s in items])
            c = self.canvas
            vx, vy = self.to_world(c.winfo_width() / 2, c.winfo_height() / 2)
            dx, dy = vx - (bb[0] + bb[2]) / 2, vy - (bb[1] + bb[3]) / 2
            for s in items:
                sh.translate(s, dx, dy)
        self.push_undo()
        # like Illustrator, pasted art goes to the current layer
        self.selected = self.doc.insert_copies(items, offset, index=index, layer=self.doc.active_layer)
        self._changed()

    def paste(self):
        self._paste(center=True)

    def paste_in_place(self):
        self._paste()

    def paste_in_front(self):
        idx = max((self.doc.index_of(i) for i in self.selected), default=None)
        self._paste(index=None if idx is None else idx + 1)

    def paste_in_back(self):
        idx = min((self.doc.index_of(i) for i in self.selected), default=0)
        self._paste(index=idx)

    def duplicate(self):
        if self.selected:
            self.push_undo()
            self.selected = self.doc.insert_copies(self.selected_shapes(), 10)
            self._changed(tr("flash_duplicated"))

    def nudge(self, dx, dy):
        if not self.selected:
            return
        self.push_undo("nudge")
        for s in self.selected_shapes():
            sh.translate(s, dx, dy)
        self.render()

    # ── Select ──────────────────────────────────────────────────────────────
    def select_all(self):
        if self.tool not in ("select", "direct"):
            self.set_tool("select")
        self.selected = {s["id"] for s in self.doc.editable()}
        self._changed()

    def deselect(self):
        self.selected = set()
        self._changed()

    def select_inverse(self):
        self.selected = {s["id"] for s in self.doc.editable()} - self.selected
        self._changed()

    def select_same(self, attr):
        sel = self.selected_shapes()
        if not sel:
            return
        ref = sel[0]
        key = {"fill": "fill", "stroke": "stroke", "width": "width", "type": "type"}[attr]
        val = ref.get(key)
        self.selected = {s["id"] for s in self.doc.editable() if s.get(key) == val}
        self._changed()

    # ── stacking order ──────────────────────────────────────────────────────
    def _reorder(self, op):
        if self.selected:
            self.push_undo()
            op(self.selected)
            self.render()

    def bring_front(self):
        self._reorder(self.doc.bring_front)

    def send_back(self):
        self._reorder(self.doc.send_back)

    def bring_forward(self):
        self._reorder(self.doc.bring_forward)

    def send_backward(self):
        self._reorder(self.doc.send_backward)

    # ── groups ──────────────────────────────────────────────────────────────
    def group_sel(self):
        if len(self.selected) < 2:
            return
        self.push_undo()
        self.doc.group(self.selected)
        self._changed(tr("flash_grouped", n=len(self.selected)))

    def ungroup_sel(self):
        if any(s.get("gid") is not None for s in self.selected_shapes()):
            self.push_undo()
            self.doc.ungroup(self.selected)
            self._changed(tr("flash_ungrouped"))

    # ── lock / hide ─────────────────────────────────────────────────────────
    def _set_flag(self, flag, flash_key):
        if not self.selected:
            return
        n = len(self.selected)
        self.push_undo()
        for s in self.selected_shapes():
            s[flag] = True
        self.selected.clear()
        self._changed(tr(flash_key, n=n))

    def _clear_flag(self, flag, other, flash_key):
        flagged = [s for s in self.doc.shapes if sh.prop(s, flag)]
        if not flagged:
            return
        self.push_undo()
        for s in flagged:
            s.pop(flag, None)
        self.selected = {s["id"] for s in flagged if not sh.prop(s, other)}
        self._changed(tr(flash_key))

    def lock_sel(self):
        self._set_flag("locked", "flash_locked")

    def hide_sel(self):
        self._set_flag("hidden", "flash_hidden")

    def unlock_all(self):
        self._clear_flag("locked", "hidden", "flash_unlocked")

    def show_all(self):
        self._clear_flag("hidden", "locked", "flash_shown")

    def _toggle_flag(self, sid, flag):
        s = self.doc.by_id(sid)
        if not s:
            return
        self.push_undo()
        if sh.prop(s, flag):
            s.pop(flag, None)
        else:
            s[flag] = True
            self.selected.discard(sid)
        self._changed()

    def toggle_hidden(self, sid):
        self._toggle_flag(sid, "hidden")

    def toggle_locked(self, sid):
        self._toggle_flag(sid, "locked")

    # ── layers panel actions ────────────────────────────────────────────────
    def select_from_layers(self, sid, add=False):
        s = self.doc.by_id(sid)
        if not s or not self.doc.shape_visible(s) or self.doc.shape_locked(s):
            return
        if self.tool not in ("select", "direct"):
            self.set_tool("select")
        if add:
            self.selected ^= {sid}
        else:
            self.selected = {sid}
        self._changed()

    def rename_shape(self, sid):
        s = self.doc.by_id(sid)
        if not s:
            return
        name = simpledialog.askstring(tr("rename_title"), tr("rename_prompt"),
                                      initialvalue=s.get("name") or sh.display_name(s), parent=self.root)
        if name is None:
            return
        self.push_undo()
        name = name.strip()
        if name:
            s["name"] = name
        else:
            s.pop("name", None)
        self._changed()

    def select_ids(self, ids, add=False):
        ids = {i for i in ids if (s := self.doc.by_id(i)) is not None
               and self.doc.shape_visible(s) and not self.doc.shape_locked(s)}
        if not ids:
            return
        if self.tool not in ("select", "direct"):
            self.set_tool("select")
        self.selected = (self.selected | ids) if add else set(ids)
        self._changed()

    def toggle_group_flag(self, gid, flag):
        members = self.doc.group_members(gid)
        if not members:
            return
        self.push_undo()
        turn_on = not all(sh.prop(m, flag) for m in members)
        for m in members:
            if turn_on:
                m[flag] = True
                self.selected.discard(m["id"])
            else:
                m.pop(flag, None)
        self._changed()

    # ── layers ──────────────────────────────────────────────────────────────
    def set_active_layer(self, lid):
        if self.doc.layer(lid) is not None and self.doc.active_layer != lid:
            self.doc.active_layer = lid
            self.refresh_panel()

    def new_layer(self):
        self.push_undo()
        layer = self.doc.add_layer()
        self.panel.layers.expanded.discard(layer["id"])
        self._changed(tr("flash_new_layer", name=layer["name"]))

    def delete_layer(self, lid=None):
        lid = lid if lid is not None else self.doc.active_layer
        layer = self.doc.layer(lid)
        if layer is None:
            return
        n = len(self.doc.layer_shapes(lid))
        if n and not messagebox.askyesno(tr("delete_layer_title"),
                                         tr("delete_layer_msg", name=layer["name"], n=n), parent=self.root):
            return
        self.push_undo()
        gone = self.doc.delete_layer(lid)
        self.selected -= gone
        self._changed(tr("flash_layer_deleted", name=layer["name"]))

    def move_layer(self, delta, lid=None):
        lid = lid if lid is not None else self.doc.active_layer
        i, n = self.doc.layer_index(lid), len(self.doc.layers)
        if not 0 <= i + delta < n:
            return
        self.push_undo()
        self.doc.move_layer(lid, delta)
        self._changed()

    def rename_layer(self, lid):
        layer = self.doc.layer(lid)
        if layer is None:
            return
        name = simpledialog.askstring(tr("rename_layer_title"), tr("rename_layer_prompt"),
                                      initialvalue=layer["name"], parent=self.root)
        if name is None or not name.strip() or name.strip() == layer["name"]:
            return
        self.push_undo()
        layer["name"] = name.strip()
        self._changed()

    def toggle_layer_visible(self, lid, solo=False):
        layer = self.doc.layer(lid)
        if layer is None:
            return
        self.push_undo()
        if solo:   # Alt-click: show only this layer (again: show all)
            others = [l for l in self.doc.layers if l["id"] != lid]
            show_all = all(not l["visible"] for l in others)
            for l in others:
                l["visible"] = show_all
            layer["visible"] = True
        else:
            layer["visible"] = not layer["visible"]
        self.selected = {i for i in self.selected
                         if (s := self.doc.by_id(i)) is not None and self.doc.shape_visible(s)}
        self._changed()

    def toggle_layer_locked(self, lid):
        layer = self.doc.layer(lid)
        if layer is None:
            return
        self.push_undo()
        layer["locked"] = not layer["locked"]
        if layer["locked"]:
            self.selected = {i for i in self.selected if self.doc.by_id(i).get("layer") != lid}
        self._changed()

    def select_layer_objects(self, lid, add=False):
        self.select_ids({s["id"] for s in self.doc.layer_shapes(lid)}, add=add)

    def move_selection_to_layer(self, lid=None):
        """Object ▸ Arrange ▸ Send to Current Layer."""
        lid = lid if lid is not None else self.doc.active_layer
        if not self.selected or self.doc.layer(lid) is None:
            return
        self.push_undo()
        self.doc.move_to_layer(self.selected, lid)
        self._changed(tr("flash_moved_to_layer", name=self.doc.layer(lid)["name"]))

    # ── paths ───────────────────────────────────────────────────────────────
    def convert_to_path(self):
        targets = [s for s in self.selected_shapes() if s["type"] not in ("path", "text")]
        if not targets:
            return
        self.push_undo()
        for s in targets:
            sh.replace_in_place(s, sh.to_path(s))
        self._changed(tr("flash_converted", n=len(targets)))

    def join_paths(self):
        opens = [s for s in self.selected_shapes()
                 if s["type"] in ("path", "line", "pen") and not sh.prop(s, "closed")
                 and not sh.is_compound(s)]
        if not opens:
            return
        self.push_undo()
        for s in opens:
            if s["type"] != "path":
                sh.replace_in_place(s, sh.to_path(s))
        if len(opens) == 1:
            pathops.close(opens[0])
            self._changed(tr("flash_closed"))
            return
        merged = opens[0]
        for other in opens[1:]:
            j = pathops.join(merged, other)
            sh.replace_in_place(merged, dict(j, id=merged["id"]))
        self.doc.remove({s["id"] for s in opens[1:]})
        self.selected = {merged["id"]}
        self._changed(tr("flash_joined"))

    def make_compound(self):
        """Object ▸ Compound Path ▸ Make (Ctrl+8): one shape, holes where paths overlap."""
        targets = [s for s in self.selected_shapes() if s["type"] != "text"]
        if len(targets) < 2:
            return
        self.push_undo()
        paths = [s if s["type"] == "path" else sh.to_path(s) for s in targets]
        merged = pathops.make_compound(paths)
        keep = targets[0]["id"]
        merged["id"] = keep
        merged.pop("gid", None)
        merged.pop("gpath", None)
        sh.replace_in_place(targets[0], merged)
        self.doc.remove({s["id"] for s in targets[1:]})
        self.selected = {keep}
        self._changed(tr("flash_compound"))

    def release_compound(self):
        targets = [s for s in self.selected_shapes() if sh.is_compound(s)]
        if not targets:
            return
        self.push_undo()
        new_ids = set()
        for s in targets:
            pieces = pathops.release_compound(s)
            idx = self.doc.index_of(s["id"])
            sh.replace_in_place(s, dict(pieces[0], id=s["id"]))
            new_ids.add(s["id"])
            new_ids |= self.doc.insert_copies(pieces[1:], 0, index=idx + 1)
        self.selected = new_ids
        self._changed(tr("flash_released"))

    def close_paths(self):
        targets = [s for s in self.selected_shapes() if s["type"] in ("path", "line", "pen")
                   and not sh.prop(s, "closed") and len(s["pts"]) >= 6]
        if not targets:
            return
        self.push_undo()
        for s in targets:
            if s["type"] != "path":
                sh.replace_in_place(s, sh.to_path(s))
            pathops.close(s)
        self._changed()

    def reverse_paths(self):
        targets = [s for s in self.selected_shapes() if s["type"] == "path"]
        if not targets:
            return
        self.push_undo()
        for s in targets:
            sh.replace_in_place(s, pathops.reverse(s))
        self._changed()

    # ── align / distribute ──────────────────────────────────────────────────
    def set_align_to(self, key):
        self.align_to = key
        self.refresh_panel()

    def _unit_bbox(self, unit):
        return geo.union_bbox([self.shape_bbox(s) for s in unit])

    def align(self, how):
        units = self.doc.units(self.selected)
        if not units:
            return
        use_board = self.align_to == "artboard" or len(units) == 1
        tx0, ty0, tx1, ty1 = self.doc.artboard if use_board else self.selection_bbox()
        moves = []
        for unit in units:
            b = self._unit_bbox(unit)
            dx = dy = 0.0
            if how == "left":
                dx = tx0 - b[0]
            elif how == "right":
                dx = tx1 - b[2]
            elif how == "hcenter":
                dx = (tx0 + tx1) / 2 - (b[0] + b[2]) / 2
            elif how == "top":
                dy = ty0 - b[1]
            elif how == "bottom":
                dy = ty1 - b[3]
            elif how == "vcenter":
                dy = (ty0 + ty1) / 2 - (b[1] + b[3]) / 2
            if abs(dx) > 1e-9 or abs(dy) > 1e-9:
                moves.append((unit, dx, dy))
        if not moves:
            return
        self.push_undo()
        for unit, dx, dy in moves:
            for s in unit:
                sh.translate(s, dx, dy)
        self.render()

    def distribute(self, axis):
        units = self.doc.units(self.selected)
        if len(units) < 3:
            self.flash(tr("tip_distribute"))
            return
        i0 = 0 if axis == "h" else 1
        items = []
        for unit in units:
            b = self._unit_bbox(unit)
            items.append(((b[i0] + b[i0 + 2]) / 2, unit))
        items.sort(key=lambda t: t[0])
        first, last = items[0][0], items[-1][0]
        step = (last - first) / (len(items) - 1)
        self.push_undo()
        for k, (c, unit) in enumerate(items):
            delta = first + k * step - c
            for s in unit:
                sh.translate(s, delta if axis == "h" else 0, delta if axis == "v" else 0)
        self.render()

    # ── transforms ──────────────────────────────────────────────────────────
    def _transform_selection(self, fn, copy_=False):
        """Apply fn(shape, bbox) -> new shape to the selection (optionally to copies)."""
        if not self.selected:
            return
        self.push_undo()
        targets = self.selected_shapes()
        if copy_:
            self.selected = self.doc.insert_copies(targets, 0)
            targets = self.selected_shapes()
        boxes = {s["id"]: self.shape_bbox(s) for s in targets}
        for s in targets:
            sh.replace_in_place(s, fn(s, boxes[s["id"]]))
        self._changed()

    def flip(self, axis):
        bb = self.selection_bbox()
        if not bb:
            return
        cx, cy = geo.bbox_center(bb)
        self._transform_selection(lambda s, b: sh.flipped(s, axis, cx if axis == "h" else cy, b))

    def rotate_sel(self, deg, copy_=False):
        bb = self.selection_bbox()
        if not bb or not deg:
            return
        cx, cy = geo.bbox_center(bb)
        self._transform_selection(lambda s, b: sh.rotated(s, deg, cx, cy), copy_)

    def move_sel(self, dx, dy, copy_=False):
        def fn(s, b):
            n = copy.deepcopy(s)
            sh.translate(n, dx, dy)
            return n
        self._transform_selection(fn, copy_)

    def scale_sel(self, kx, ky, copy_=False):
        bb = self.selection_bbox()
        if not bb:
            return
        cx, cy = geo.bbox_center(bb)
        self._transform_selection(lambda s, b: sh.scaled_about(s, kx, ky, cx, cy), copy_)

    def reflect_sel(self, axis_deg, copy_=False):
        bb = self.selection_bbox()
        if not bb:
            return
        cx, cy = geo.bbox_center(bb)
        self._transform_selection(lambda s, b: sh.reflected(s, axis_deg, cx, cy, b), copy_)

    def transform_again(self):
        t = self.last_transform
        if not t or not self.selected:
            return
        kind = t[0]
        if kind == "move":
            self.move_sel(t[1], t[2], t[3])
        elif kind == "rotate":
            self.rotate_sel(t[1], t[2])
        elif kind == "scale":
            self.scale_sel(t[1], t[2], t[3])
        elif kind == "reflect":
            self.reflect_sel(t[1], t[2])

    def open_transform_dialog(self, kind):
        if not self.selected:
            self.flash(tr("need_selection"))
            return
        if kind == "move":
            res = self.ask_form(tr("m_move"), [("h", tr("horizontal"), 0.0), ("v", tr("vertical"), 0.0)],
                                allow_copy=True)
            if res:
                (v, cp) = res
                self.move_sel(v["h"], v["v"], cp)
                self.last_transform = ("move", v["h"], v["v"], cp)
        elif kind == "rotate":
            res = self.ask_form(tr("m_rotate"), [("a", tr("angle"), 45.0)], allow_copy=True,
                                note=tr("note_angle"))
            if res:
                (v, cp) = res
                self.rotate_sel(-v["a"], cp)
                self.last_transform = ("rotate", -v["a"], cp)
        elif kind == "scale":
            res = self.ask_form(tr("m_scale"), [("x", tr("scale_h"), 100.0), ("y", tr("scale_v"), 100.0)],
                                allow_copy=True)
            if res and res[0]["x"] and res[0]["y"]:
                (v, cp) = res
                self.scale_sel(v["x"] / 100, v["y"] / 100, cp)
                self.last_transform = ("scale", v["x"] / 100, v["y"] / 100, cp)
        elif kind == "reflect":
            res = self.ask_form(tr("m_reflect"), [("a", tr("axis_angle"), 90.0)], allow_copy=True,
                                note=tr("note_reflect"))
            if res:
                (v, cp) = res
                self.reflect_sel(-v["a"], cp)
                self.last_transform = ("reflect", -v["a"], cp)

    def apply_transform(self, field, text):
        """Called from the X / Y / W / H / angle fields (X/Y relative to the artboard)."""
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            self._refresh_geo()
            return
        bb = self.selection_bbox()
        if not bb:
            return
        x0, y0, x1, y1 = bb
        ab = self.doc.artboard
        if field in ("x", "y"):
            dx = value + ab[0] - x0 if field == "x" else 0
            dy = value + ab[1] - y0 if field == "y" else 0
            if dx or dy:
                self.push_undo()
                for s in self.selected_shapes():
                    sh.translate(s, dx, dy)
        elif field in ("w", "h"):
            w, h = x1 - x0, y1 - y0
            if value <= 0 or (field == "w" and w == 0) or (field == "h" and h == 0):
                self._refresh_geo()
                return
            if field == "w":
                nh = h * value / w if self.keep_ratio else h
                nb = (x0, y0, x0 + value, y0 + nh)
            else:
                nw = w * value / h if self.keep_ratio else w
                nb = (x0, y0, x0 + nw, y0 + value)
            self.push_undo()
            for s in self.selected_shapes():
                sh.replace_in_place(s, sh.scaled(s, bb, nb))
        elif field == "rot":
            sel = self.selected_shapes()
            current = sh.prop(sel[0], "rot") if len(sel) == 1 else 0
            # the field shows counter-clockwise degrees (like other design apps);
            # internally rot is clockwise on screen
            self.rotate_sel(geo.normalize_angle(-value - current))
            return
        self._changed()

    def toggle_keep_ratio(self):
        self.keep_ratio = not self.keep_ratio
        self.refresh_panel()

    # ── artboard ────────────────────────────────────────────────────────────
    def set_artboard_size(self, field, text):
        try:
            v = float(text.replace(",", "."))
        except ValueError:
            return
        if v < 1:
            return
        ab = list(self.doc.artboard)
        if field == "w":
            ab[2] = ab[0] + v
        else:
            ab[3] = ab[1] + v
        self.push_undo()
        self.doc.artboard = ab
        self._changed()

    def document_setup(self):
        ab = self.doc.artboard
        res = self.ask_form(tr("m_document_setup"), [("w", tr("width"), ab[2] - ab[0]),
                                                      ("h", tr("height"), ab[3] - ab[1])])
        if res and res["w"] >= 1 and res["h"] >= 1:
            self.push_undo()
            self.doc.artboard = [ab[0], ab[1], ab[0] + res["w"], ab[1] + res["h"]]
            self._changed()
            self.zoom_fit()

    def fit_artboard_to_art(self):
        bb = geo.union_bbox([self.shape_bbox(s) for s in self.doc.shapes if self.doc.shape_visible(s)])
        if not bb:
            return
        self.push_undo()
        self.doc.artboard = [round(v, 2) for v in bb]
        self._changed()
        self.zoom_fit()

    # ── view toggles ────────────────────────────────────────────────────────
    def _toggle(self, attr, flash_on=None, flash_off=None):
        setattr(self, attr, not getattr(self, attr))
        self.sync_menu_vars()
        self.refresh_panel()
        if flash_on:
            self.flash(tr(flash_on) if getattr(self, attr) else tr(flash_off))
        self.render()

    def toggle_grid(self):
        self._toggle("show_grid")

    def toggle_snap(self):
        self._toggle("snap", "flash_snap_on", "flash_snap_off")

    def toggle_smart_guides(self):
        self._toggle("smart_guides", "flash_smart_on", "flash_smart_off")

    def toggle_outline(self):
        self._toggle("outline_mode")

    def toggle_rulers(self):
        self.show_rulers = not self.show_rulers
        self.layout_chrome()
        self.sync_menu_vars()
        self.refresh_panel()
        self.root.after_idle(self.render)

    def toggle_toolbar(self):
        self.show_toolbar = not self.show_toolbar
        self.layout_chrome()
        self.sync_menu_vars()

    def toggle_controlbar(self):
        self.show_control = not self.show_control
        self.layout_chrome()
        self.sync_menu_vars()

    def toggle_all_panels(self):
        self.panels_hidden = not self.panels_hidden
        self.layout_chrome()
        self.root.after_idle(self.render)
