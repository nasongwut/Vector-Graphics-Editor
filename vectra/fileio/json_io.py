"""Native document format (.json)."""

import json
import numbers

from vectra.config import APP_ID, FILE_VERSION
from vectra.model.shapes import SHAPE_TYPES


def save(path, shapes, artboard, layers=None, active_layer=None):
    data = {"app": APP_ID, "version": FILE_VERSION, "artboard": list(artboard), "shapes": shapes}
    if layers:
        data["layers"] = layers
        data["active_layer"] = active_layer
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def validate(shapes):
    if not isinstance(shapes, list):
        raise ValueError("'shapes' must be a list")
    seen = set()
    for s in shapes:
        if not isinstance(s, dict):
            raise ValueError("shape must be an object")
        if s.get("type") not in SHAPE_TYPES:
            raise ValueError(f"unknown shape type: {s.get('type')!r}")
        pts = s.get("pts")
        if not isinstance(pts, list) or not pts or len(pts) % 2 or \
                not all(isinstance(v, numbers.Real) for v in pts):
            raise ValueError(f"bad points in shape {s.get('id')!r}")
        if s["type"] == "path":
            ctrl = s.get("ctrl")
            if not isinstance(ctrl, list) or len(ctrl) != 2 * len(pts) or \
                    not all(isinstance(v, numbers.Real) for v in ctrl):
                raise ValueError(f"bad handles in path {s.get('id')!r}")
            sm = s.get("smooth")
            if not isinstance(sm, list) or len(sm) != len(pts) // 2:
                s["smooth"] = [False] * (len(pts) // 2)
            pr = s.get("parts")
            if pr is not None and (not isinstance(pr, list) or
                                   sum(int(p[0]) for p in pr) != len(pts) // 2):
                raise ValueError(f"bad sub-paths in path {s.get('id')!r}")
        if not isinstance(s.get("id"), int) or s["id"] in seen:
            raise ValueError(f"missing or duplicate id: {s.get('id')!r}")
        seen.add(s["id"])
    return shapes


def load(path):
    """Read a drawing -> (shapes, artboard). Raises OSError / ValueError on a bad file."""
    shapes, artboard, _layers, _active = load_full(path)
    return shapes, artboard


def _valid_layers(layers):
    if not isinstance(layers, list):
        return None
    out = []
    for l in layers:
        if isinstance(l, dict) and isinstance(l.get("id"), int):
            out.append(l)
    return out or None


def load_full(path):
    """-> (shapes, artboard, layers or None, active layer id or None)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "shapes" not in data:
        raise ValueError("not a Vectra drawing")
    artboard = data.get("artboard")
    if not (isinstance(artboard, list) and len(artboard) == 4 and
            all(isinstance(v, numbers.Real) for v in artboard) and
            artboard[2] > artboard[0] and artboard[3] > artboard[1]):
        artboard = None
    return validate(data["shapes"]), artboard, _valid_layers(data.get("layers")), data.get("active_layer")
