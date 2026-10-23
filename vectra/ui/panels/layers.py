"""Layers panel, modelled on Illustrator's:

* one row per layer (top layer first) with visibility eye, lock, colour bar, name,
  target circle and the coloured "selected art" square;
* expand a layer (▸) to see its objects, groups expand to their members;
* click a layer to make it the current layer (new art goes there), double-click to
  rename; click an object to select it, the target circle selects everything on it;
* footer: layer count · locate object · move selection to current layer · move layer
  up/down · new layer · delete layer.
"""

import tkinter as tk

from vectra.config import ALT_MASK, SHIFT_MASK
from vectra.i18n import tr
from vectra.model import shapes as sh
from vectra.ui.theme import T
from vectra.ui.widgets import FlatButton, Tooltip

ROW_H = 24
MAX_ROWS_PER_LAYER = 400
ACTIVE_BG = "#3c4a63"
SEL_BG = "#373c45"


def object_label(s):
    """Illustrator-style object name: <Path>, <Group>, <Compound Path> … or the text."""
    if s.get("name"):
        return s["name"]
    if s["type"] == "text":
        t = s.get("text", "").replace("\n", " ")
        return t[:40] or tr("obj_text")
    if sh.is_compound(s):
        return tr("obj_compound")
    return tr("obj_" + s["type"])


def _draw_eye(c, on, color):
    c.delete("all")
    if not on:
        return
    c.create_oval(4, 7, 18, 15, outline=color, width=1.2)
    c.create_oval(9, 9, 13, 13, fill=color, outline=color)


def _draw_lock(c, on, color):
    c.delete("all")
    if not on:
        return
    c.create_arc(7, 4, 15, 12, start=0, extent=180, style="arc", outline=color, width=1.4)
    c.create_rectangle(6, 9, 16, 17, fill=color, outline=color)


class LayersTab:
    def __init__(self, ed, parent, footer=None, scroller=None):
        self.ed = ed
        self.parent = parent
        self.scroller = scroller
        self.body = tk.Frame(parent, bg=T["panel"])
        self.body.pack(fill="both", expand=True)
        self.expanded = set()        # layer ids
        self.expanded_groups = set()  # gids
        self._struct = None
        self._selsig = None
        self.rows = {}               # key -> (frame, label, right canvas, kind, ref)
        if footer is not None:
            self._build_footer(footer)

    # ── footer ──────────────────────────────────────────────────────────────
    def _build_footer(self, f):
        ed = self.ed
        self.count = tk.Label(f, text="", bg=T["panel3"], fg=T["muted"], font=ed.f(9))
        self.count.pack(side="left", padx=10)

        def btn(text, cmd, tip):
            b = FlatButton(f, text, cmd, font=ed.f(11), bg=T["panel3"], padx=7, pady=1,
                           tooltip=tip, tip_font=ed.f(9))
            b.pack(side="right", padx=1, pady=3)
            return b
        btn("🗑", ed.delete_layer, tr("tip_delete_layer"))
        btn("＋", ed.new_layer, tr("tip_new_layer"))
        btn("▼", lambda: ed.move_layer(-1), tr("tip_layer_down"))
        btn("▲", lambda: ed.move_layer(1), tr("tip_layer_up"))
        btn("⇥", ed.move_selection_to_layer, tr("tip_move_to_layer"))
        btn("⌖", self.locate_object, tr("tip_locate"))

    # ── signatures ──────────────────────────────────────────────────────────
    def _structure_sig(self):
        doc = self.ed.doc
        layers = tuple((l["id"], l["name"], l["color"], l["visible"], l["locked"]) for l in doc.layers)
        return (self.ed.doc_version, len(doc.shapes), layers, tuple(sorted(self.expanded)),
                tuple(sorted(self.expanded_groups)), doc.active_layer)

    def _selection_sig(self):
        return tuple(sorted(self.ed.selected))

    def refresh(self, force=False):
        struct = self._structure_sig()
        if force or struct != self._struct:
            self._struct = struct
            self._rebuild()
            self._selsig = None
        sel = self._selection_sig()
        if sel != self._selsig:
            self._selsig = sel
            self._paint_selection()

    # ── building rows ───────────────────────────────────────────────────────
    def _rebuild(self):
        doc = self.ed.doc
        for w in self.body.winfo_children():
            w.destroy()
        self.rows = {}
        if hasattr(self, "count"):
            n = len(doc.layers)
            self.count.config(text=tr("n_layers", n=n))
        for layer in reversed(doc.layers):
            self._layer_row(layer)
            if layer["id"] not in self.expanded:
                continue
            items = list(reversed(doc.layer_shapes(layer["id"])))
            self._shown = 0
            self._emit(items, layer, 0)

    def _emit(self, items, layer, level):
        """Rows for ``items`` (top first) at group nesting ``level``. False = row budget used up."""
        i = 0
        while i < len(items):
            if self._shown >= MAX_ROWS_PER_LAYER:
                tk.Label(self.body, text=tr("more_objects", n=len(items) - i), bg=T["panel"],
                         fg=T["muted"], font=self.ed.f(8), anchor="w").pack(fill="x", padx=48, pady=2)
                return False
            path = sh.group_path(items[i])
            if len(path) > level:
                gid = path[level]
                members = []
                while i < len(items):
                    p = sh.group_path(items[i])
                    if len(p) > level and p[level] == gid:
                        members.append(items[i])
                        i += 1
                    else:
                        break
                self._group_row(gid, members, layer, depth=level + 1)
                self._shown += 1
                if gid in self.expanded_groups and not self._emit(members, layer, level + 1):
                    return False
            else:
                self._object_row(items[i], layer, depth=level + 1)
                self._shown += 1
                i += 1
        return True

    def _row(self, bg):
        row = tk.Frame(self.body, bg=bg, height=ROW_H)
        row.pack(fill="x")
        row.pack_propagate(False)
        tk.Frame(self.body, bg=T["border"], height=1).pack(fill="x")
        return row

    def _cells(self, row, bg, visible, locked, on_eye, on_lock):
        ed = self.ed
        eye = tk.Canvas(row, width=22, height=ROW_H, bg=T["panel3"], highlightthickness=0, cursor="hand2")
        eye.pack(side="left")
        _draw_eye(eye, visible, T["text"])
        eye.bind("<Button-1>", on_eye)
        Tooltip(eye, tr("tip_eye"), side="below", font=ed.f(9))
        lock = tk.Canvas(row, width=22, height=ROW_H, bg=bg, highlightthickness=0, cursor="hand2")
        lock.pack(side="left")
        _draw_lock(lock, locked, T["muted"])
        lock.bind("<Button-1>", on_lock)
        Tooltip(lock, tr("tip_lock"), side="below", font=ed.f(9))
        tk.Frame(row, bg=T["border"], width=1).pack(side="left", fill="y")
        return eye, lock

    def _right(self, row, bg, on_target):
        c = tk.Canvas(row, width=34, height=ROW_H, bg=bg, highlightthickness=0, cursor="hand2")
        c.pack(side="right")
        c.bind("<Button-1>", on_target)
        Tooltip(c, tr("tip_target"), side="below", font=self.ed.f(9))
        return c

    def _layer_row(self, layer):
        ed = self.ed
        lid = layer["id"]
        active = ed.doc.active_layer == lid
        bg = ACTIVE_BG if active else T["panel2"]
        row = self._row(bg)
        self._cells(row, bg, layer["visible"], layer["locked"],
                    lambda e: (ed.toggle_layer_visible(lid, solo=bool(e.state & ALT_MASK)), "break")[1],
                    lambda e: (ed.toggle_layer_locked(lid), "break")[1])
        tk.Frame(row, bg=layer["color"], width=4).pack(side="left", fill="y")
        right = self._right(row, bg, lambda e: ed.select_layer_objects(lid, add=bool(e.state & SHIFT_MASK)))
        arrow = "▾" if lid in self.expanded else "▸"
        has = any(s.get("layer") == lid for s in ed.doc.shapes)
        lbl = tk.Label(row, text=f"{arrow if has else ' '}  {layer['name']}", bg=bg, fg=T["text"],
                       font=ed.f(10, "bold" if active else "normal"), anchor="w")
        lbl.pack(side="left", fill="both", expand=True, padx=(4, 0))
        if active:
            tk.Label(row, text="◣", bg=bg, fg=T["text"], font=ed.f(8)).pack(side="right")

        def click(e, lid=lid):
            if e.x < 22:
                self.toggle_layer(lid)
            else:
                ed.set_active_layer(lid)
        for w in (row, lbl):
            w.bind("<Button-1>", click)
            w.bind("<Double-Button-1>", lambda e, lid=lid: ed.rename_layer(lid))
        self.rows[("layer", lid)] = (row, lbl, right, "layer", layer)

    def _object_row(self, s, layer, depth):
        ed = self.ed
        sid = s["id"]
        bg = T["panel"]
        row = self._row(bg)
        self._cells(row, bg, not sh.prop(s, "hidden"), sh.prop(s, "locked"),
                    lambda e: (ed.toggle_hidden(sid), "break")[1],
                    lambda e: (ed.toggle_locked(sid), "break")[1])
        right = self._right(row, bg, lambda e: ed.select_from_layers(sid, add=bool(e.state & SHIFT_MASK)))
        swatch = tk.Canvas(row, width=16, height=ROW_H, bg=bg, highlightthickness=0)
        swatch.pack(side="left", padx=(8 + 14 * depth, 4))
        col = s.get("fill") or s.get("stroke")
        if col:
            swatch.create_rectangle(2, 6, 14, 18, fill=col, outline=T["border"])
        else:
            swatch.create_rectangle(2, 6, 14, 18, outline=T["muted"])
        lbl = tk.Label(row, text=object_label(s), bg=bg, fg=T["muted"] if sh.prop(s, "hidden") else T["text"],
                       font=ed.f(9), anchor="w")
        lbl.pack(side="left", fill="both", expand=True)
        for w in (row, lbl, swatch):
            w.bind("<Button-1>", lambda e, sid=sid: ed.select_from_layers(sid, add=bool(e.state & SHIFT_MASK)))
            w.bind("<Double-Button-1>", lambda e, sid=sid: ed.rename_shape(sid))
        self.rows[("obj", sid)] = (row, lbl, right, "obj", s)

    def _group_row(self, gid, members, layer, depth=1):
        ed = self.ed
        bg = T["panel"]
        row = self._row(bg)
        hidden = all(sh.prop(m, "hidden") for m in members)
        locked = all(sh.prop(m, "locked") for m in members)
        self._cells(row, bg, not hidden, locked,
                    lambda e: (ed.toggle_group_flag(gid, "hidden"), "break")[1],
                    lambda e: (ed.toggle_group_flag(gid, "locked"), "break")[1])
        ids = {m["id"] for m in members}
        right = self._right(row, bg, lambda e: ed.select_ids(ids, add=bool(e.state & SHIFT_MASK)))
        arrow = "▾" if gid in self.expanded_groups else "▸"
        lbl = tk.Label(row, text=f"{arrow}  {tr('obj_group')}", bg=bg, fg=T["text"], font=ed.f(9), anchor="w")
        lbl.pack(side="left", fill="both", expand=True, padx=(8 + 14 * depth, 0))

        def click(e, gid=gid, ids=ids):
            if e.x < 18 and e.widget is lbl:
                self.toggle_group(gid)
            else:
                ed.select_ids(ids, add=bool(e.state & SHIFT_MASK))
        for w in (row, lbl):
            w.bind("<Button-1>", click)
        self.rows[("group", gid)] = (row, lbl, right, "group", ids)

    # ── selection colouring (cheap, no rebuild) ─────────────────────────────
    def _paint_selection(self):
        ed, doc = self.ed, self.ed.doc
        sel = ed.selected
        sel_layers = {s.get("layer") for s in ed.selected_shapes()}
        for key, (row, lbl, right, kind, ref) in self.rows.items():
            right.delete("all")
            if kind == "layer":
                selected = ref["id"] in sel_layers
                color = ref["color"]
            elif kind == "obj":
                selected = ref["id"] in sel
                color = doc.layer_of(ref)["color"]
            else:
                selected = bool(ref) and ref <= sel
                color = doc.layer_of(doc.by_id(next(iter(ref))))["color"] if ref else T["muted"]
            right.create_oval(6, 7, 16, 17, outline=T["text"] if selected else T["muted"], width=1.4 if selected else 1)
            if selected or (kind == "layer" and ref["id"] in sel_layers):
                right.create_rectangle(21, 8, 29, 16, fill=color, outline=color)
            if kind in ("obj", "group"):
                bg = SEL_BG if selected else T["panel"]
                for w in (row, lbl):
                    w.config(bg=bg)
                for child in row.winfo_children():
                    if isinstance(child, tk.Canvas) and child is not right and child.cget("bg") != T["panel3"]:
                        child.config(bg=bg)
                right.config(bg=bg)

    # ── actions ─────────────────────────────────────────────────────────────
    def toggle_layer(self, lid):
        self.expanded ^= {lid}
        self.refresh(force=True)

    def toggle_group(self, gid):
        self.expanded_groups ^= {gid}
        self.refresh(force=True)

    def locate_object(self):
        """Expand the layer (and group) of the selection and scroll to it."""
        sel = self.ed.selected_shapes()
        if not sel:
            return
        s = sel[-1]
        self.expanded.add(s.get("layer"))
        if s.get("gid") is not None:
            self.expanded_groups.add(s["gid"])
        self.refresh(force=True)
        row = self.rows.get(("obj", s["id"]))
        if row and self.scroller is not None:
            self.body.update_idletasks()
            total = max(1, self.body.winfo_height())
            self.scroller.canvas.yview_moveto(max(0.0, (row[0].winfo_y() - 60) / total))
