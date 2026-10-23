"""The drawing: layers and an ordered list of shapes (index 0 = bottom of the stack).

Layers work like in Illustrator: ``layers`` is ordered bottom → top, every shape
has a ``layer`` id, and shapes are kept grouped by layer in stacking order
(``normalize``), so a whole layer always sits above or below another.
"""

import copy

from vectra.config import ARTBOARD
from vectra.model.shapes import prop

# Illustrator's default layer colours, in the order new layers receive them.
LAYER_COLORS = ["#4f80ff", "#ff4f4f", "#4fff4f", "#4f4fff", "#ffff4f", "#ff4fff", "#4fffff",
                "#9d9d9d", "#008000", "#008080", "#ff8000", "#800080", "#804000", "#000080"]


def new_layer_dict(lid, name, color=None, visible=True, locked=False):
    return {"id": lid, "name": name, "color": color or LAYER_COLORS[(lid - 1) % len(LAYER_COLORS)],
            "visible": bool(visible), "locked": bool(locked)}


class Document:
    def __init__(self, shapes=None, artboard=ARTBOARD):
        self.shapes = []
        self.next_id = 1
        self.artboard = list(artboard)
        self.layers = [new_layer_dict(1, "Layer 1")]
        self.active_layer = 1
        if shapes:
            self.load(shapes)

    # ── lifecycle ───────────────────────────────────────────────────────────
    def clear(self):
        self.shapes = []
        self.next_id = 1
        self.artboard = list(ARTBOARD)
        self.layers = [new_layer_dict(1, "Layer 1")]
        self.active_layer = 1

    def load(self, shapes, artboard=None, layers=None):
        self.shapes = shapes
        self.next_id = max((s["id"] for s in shapes), default=0) + 1
        if artboard:
            self.artboard = list(artboard)
        if layers:
            self.layers = [new_layer_dict(int(l["id"]), str(l.get("name") or f"Layer {l['id']}"),
                                          l.get("color"), l.get("visible", True), l.get("locked", False))
                           for l in layers]
        self.ensure_layers()

    def ensure_layers(self):
        """At least one layer; every shape on an existing layer; shapes grouped by layer."""
        if not self.layers:
            self.layers = [new_layer_dict(1, "Layer 1")]
        ids = {l["id"] for l in self.layers}
        if self.active_layer not in ids:
            self.active_layer = self.layers[-1]["id"]
        for s in self.shapes:
            if s.get("layer") not in ids:
                s["layer"] = self.active_layer
        self.normalize()

    def snapshot(self):
        return (copy.deepcopy(self.shapes), self.next_id, list(self.artboard),
                copy.deepcopy(self.layers), self.active_layer)

    def restore(self, snap):
        self.shapes, self.next_id = copy.deepcopy(snap[0]), snap[1]
        if len(snap) > 2:
            self.artboard = list(snap[2])
        if len(snap) > 4:
            self.layers, self.active_layer = copy.deepcopy(snap[3]), snap[4]
        self.ensure_layers()

    # ── layers ──────────────────────────────────────────────────────────────
    def layer(self, lid):
        for l in self.layers:
            if l["id"] == lid:
                return l
        return None

    def layer_index(self, lid):
        for i, l in enumerate(self.layers):
            if l["id"] == lid:
                return i
        return -1

    def layer_of(self, s):
        return self.layer(s.get("layer")) or self.layers[0]

    def layer_shapes(self, lid):
        return [s for s in self.shapes if s.get("layer") == lid]

    def normalize(self):
        """Stable-sort shapes so each layer's shapes are contiguous, bottom layer first."""
        order = {l["id"]: i for i, l in enumerate(self.layers)}
        self.shapes.sort(key=lambda s: order.get(s.get("layer"), 0))

    def add_layer(self, name=None, color=None):
        """New layer directly above the active one; it becomes active."""
        lid = max((l["id"] for l in self.layers), default=0) + 1
        layer = new_layer_dict(lid, name or f"Layer {lid}", color)
        idx = self.layer_index(self.active_layer)
        self.layers.insert(idx + 1 if idx >= 0 else len(self.layers), layer)
        self.active_layer = lid
        return layer

    def delete_layer(self, lid):
        """Remove a layer and its artwork. Returns the ids of the removed shapes."""
        if self.layer(lid) is None:
            return set()
        gone = {s["id"] for s in self.shapes if s.get("layer") == lid}
        idx = self.layer_index(lid)
        self.layers = [l for l in self.layers if l["id"] != lid]
        self.shapes = [s for s in self.shapes if s["id"] not in gone]
        if not self.layers:
            self.layers = [new_layer_dict(1, "Layer 1")]
        if self.active_layer == lid or self.layer(self.active_layer) is None:
            self.active_layer = self.layers[max(0, min(idx, len(self.layers)) - 1)]["id"]
        return gone

    def move_layer(self, lid, delta):
        """delta +1 = up one layer (towards the top), -1 = down."""
        i = self.layer_index(lid)
        j = i + delta
        if i < 0 or not 0 <= j < len(self.layers):
            return False
        self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
        self.normalize()
        return True

    def move_to_layer(self, ids, lid):
        """Move shapes (keeping their order) to the top of layer ``lid``."""
        moving = self.of_ids(ids)
        for s in moving:
            s["layer"] = lid
        self.shapes = [s for s in self.shapes if s["id"] not in ids] + moving
        self.normalize()

    def shape_visible(self, s):
        return not prop(s, "hidden") and self.layer_of(s)["visible"]

    def shape_locked(self, s):
        return prop(s, "locked") or self.layer_of(s)["locked"]

    # ── queries ─────────────────────────────────────────────────────────────
    def by_id(self, sid):
        for s in self.shapes:
            if s["id"] == sid:
                return s
        return None

    def ids(self):
        return {s["id"] for s in self.shapes}

    def of_ids(self, ids):
        """Shapes whose id is in ``ids``, in stacking order."""
        return [s for s in self.shapes if s["id"] in ids]

    def editable(self):
        """Shapes that can be selected (visible and unlocked, on a visible unlocked layer)."""
        return [s for s in self.shapes if self.shape_visible(s) and not self.shape_locked(s)]

    def group_members(self, gid):
        """All shapes inside group ``gid`` (at any nesting level)."""
        if gid is None:
            return []
        return [s for s in self.shapes
                if s.get("gid") == gid or gid in (s.get("gpath") or ())]

    def expand_groups(self, ids):
        """``ids`` plus every other member of any group they belong to."""
        gids = {s.get("gid") for s in self.of_ids(ids)} - {None}
        if not gids:
            return set(ids)
        return set(ids) | {s["id"] for s in self.shapes if s.get("gid") in gids}

    def units(self, ids):
        """Selection split into units that move together: each group is one unit."""
        units, by_gid = [], {}
        for s in self.of_ids(ids):
            gid = s.get("gid")
            if gid is None:
                units.append([s])
            elif gid in by_gid:
                by_gid[gid].append(s)
            else:
                by_gid[gid] = [s]
                units.append(by_gid[gid])
        return units

    def new_gid(self):
        used = [s.get("gid") or 0 for s in self.shapes]
        used += [g for s in self.shapes for g in (s.get("gpath") or ())]
        return max(used, default=0) + 1

    # ── mutations ───────────────────────────────────────────────────────────
    def _valid_layer(self, lid):
        return lid if self.layer(lid) is not None else self.active_layer

    def _top_of_layer(self, lid):
        """Insert position just above the last shape of layer ``lid``."""
        idx = self.layer_index(lid)
        pos = 0
        for i, s in enumerate(self.shapes):
            if self.layer_index(s.get("layer")) <= idx:
                pos = i + 1
        return pos

    def add(self, shape):
        s = copy.deepcopy(shape)
        s["id"] = self.next_id
        self.next_id += 1
        s["layer"] = self._valid_layer(s.get("layer"))
        self.shapes.insert(self._top_of_layer(s["layer"]), s)
        return s

    def insert_copies(self, items, offset, index=None, layer=None):
        """Insert deep copies shifted by ``offset`` (default: on top of their layer);
        groups get fresh ids. ``layer`` forces a target layer."""
        gid_map, new_ids = {}, set()
        next_gid = self.new_gid()
        for s in items:
            n = copy.deepcopy(s)
            n["id"] = self.next_id
            self.next_id += 1
            n["pts"] = [v + offset for v in n["pts"]]
            if "ctrl" in n:
                n["ctrl"] = [v + offset for v in n["ctrl"]]
            if n.get("gid") is not None:
                path = n.get("gpath") or [n["gid"]]
                new_path = []
                for g in path:
                    if g not in gid_map:
                        gid_map[g] = next_gid
                        next_gid += 1
                    new_path.append(gid_map[g])
                n["gid"] = new_path[0]
                if len(new_path) > 1:
                    n["gpath"] = new_path
                else:
                    n.pop("gpath", None)
            n.pop("locked", None)
            n.pop("hidden", None)
            n["layer"] = self._valid_layer(layer if layer is not None else n.get("layer"))
            if index is None:
                self.shapes.insert(self._top_of_layer(n["layer"]), n)
            else:
                self.shapes.insert(index, n)
                index += 1
            new_ids.add(n["id"])
        self.normalize()
        return new_ids

    def remove(self, ids):
        self.shapes = [s for s in self.shapes if s["id"] not in ids]

    def index_of(self, sid):
        for i, s in enumerate(self.shapes):
            if s["id"] == sid:
                return i
        return -1

    def replace(self, shape):
        for i, s in enumerate(self.shapes):
            if s["id"] == shape["id"]:
                self.shapes[i] = shape
                return

    # ── stacking order (always within the object's layer) ───────────────────
    def bring_front(self, ids):
        self.shapes = [s for s in self.shapes if s["id"] not in ids] + self.of_ids(ids)
        self.normalize()

    def send_back(self, ids):
        self.shapes = self.of_ids(ids) + [s for s in self.shapes if s["id"] not in ids]
        self.normalize()

    def bring_forward(self, ids):
        sh = self.shapes
        for i in range(len(sh) - 2, -1, -1):
            if sh[i]["id"] in ids and sh[i + 1]["id"] not in ids and sh[i].get("layer") == sh[i + 1].get("layer"):
                sh[i], sh[i + 1] = sh[i + 1], sh[i]

    def send_backward(self, ids):
        sh = self.shapes
        for i in range(1, len(sh)):
            if sh[i]["id"] in ids and sh[i - 1]["id"] not in ids and sh[i].get("layer") == sh[i - 1].get("layer"):
                sh[i], sh[i - 1] = sh[i - 1], sh[i]

    # ── groups ──────────────────────────────────────────────────────────────
    def group(self, ids):
        """Group shapes; like Illustrator the group goes to the top-most member's layer
        and its members become contiguous at that member's level."""
        members = self.of_ids(ids)
        if len(members) < 2:
            return None
        gid = self.new_gid()
        top = members[-1]
        for s in members:
            old = s.get("gpath") or ([s["gid"]] if s.get("gid") is not None else [])
            s["gid"] = gid
            if old:
                s["gpath"] = [gid] + old
            else:
                s.pop("gpath", None)
            s["layer"] = top.get("layer")
        top_index = max(i for i, s in enumerate(self.shapes) if s["id"] in ids)
        before = [s for s in self.shapes[:top_index + 1] if s["id"] not in ids]
        after = [s for s in self.shapes[top_index + 1:] if s["id"] not in ids]
        self.shapes = before + members + after
        self.normalize()
        return gid

    def ungroup(self, ids):
        """Remove one level of grouping (the outermost), like Illustrator."""
        changed = False
        for s in self.of_ids(ids):
            if s.get("gid") is None:
                continue
            path = (s.get("gpath") or [s["gid"]])[1:]
            if path:
                s["gid"] = path[0]
                if len(path) > 1:
                    s["gpath"] = path
                else:
                    s.pop("gpath", None)
            else:
                s.pop("gid", None)
                s.pop("gpath", None)
            changed = True
        return changed
