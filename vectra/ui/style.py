"""Fill / stroke / character: keeps current style, selection and the panels in sync."""

from tkinter import colorchooser

from vectra.i18n import tr
from vectra.model import shapes as sh

WHITE, BLACK = "#ffffff", "#000000"


def _accepts(s, prop, value):
    """Can property ``prop`` be applied to shape ``s``?"""
    t = s["type"]
    if prop in ("size", "font"):
        return t == "text"
    if prop in ("width", "stroke", "dash"):
        return t != "text"
    if prop == "fill":
        return t not in sh.STROKE_ONLY and not (value is None and t == "text")
    if prop == "radius":
        return t == "rect"
    return True


class StyleMixin:
    # ── selection -> current style ──────────────────────────────────────────
    def on_selection_changed(self):
        sel = self.selected_shapes()
        sig = frozenset(self.selected)
        if sig != getattr(self, "_layer_sel_sig", None):
            self._layer_sel_sig = sig
            if sel and self.doc.layer(sel[-1].get("layer")) is not None:
                self.doc.active_layer = sel[-1]["layer"]   # like Illustrator: current layer follows
        if sel:
            s = sel[0]
            if s["type"] == "text":
                self.fill = s.get("fill")
                self.font_size = s.get("size", self.font_size)
                self.font_family = s.get("font") or self.font_family
            else:
                self.fill = s.get("fill") if s["type"] not in sh.STROKE_ONLY else self.fill
                self.stroke = s.get("stroke")
                self.width = s.get("width", self.width)
                self.dash = sh.prop(s, "dash")
                if s["type"] == "rect":
                    self.radius = sh.prop(s, "radius")
        self.refresh_panel()

    def refresh_panel(self):
        self.panel.refresh()
        self.control.refresh()
        self.toolbar.refresh()

    def _refresh_geo(self):
        self._geo_job = None
        try:
            self.panel.show_geometry()
            self.control.show_geometry()
        except Exception:  # noqa: BLE001 - widgets may be mid-rebuild
            pass

    # ── style -> selection ──────────────────────────────────────────────────
    def apply_props(self, values, key=None):
        """Apply {prop: value} to every selected shape that accepts it (one undo step)."""
        changes = []
        for s in self.selected_shapes():
            for prop, value in values.items():
                if not _accepts(s, prop, value):
                    continue
                if prop == "width" and s["type"] in sh.STROKE_ONLY:
                    value = max(1, value)
                if sh.prop(s, prop) != value:
                    changes.append((s, prop, value))
        if not changes:
            return False
        self.push_undo(key)
        for s, prop, value in changes:
            if prop in ("dash", "radius") and not value:
                s.pop(prop, None)
            else:
                s[prop] = value
        self.render()
        return True

    def apply_prop(self, prop, value, key=None):
        return self.apply_props({prop: value}, key)

    def pick_color(self, which):
        cur = getattr(self, which) or WHITE
        res = colorchooser.askcolor(color=cur, parent=self.root,
                                    title=tr("pick_fill") if which == "fill" else tr("pick_stroke"))
        if res and res[1]:
            self.set_color(which, res[1])

    def set_color(self, which, color):
        setattr(self, which, color)
        if color:
            self.last_color = color
        if which == "stroke" and color and not self.width:
            self.width = 1
            self.apply_props({"stroke": color, "width": 1})
        else:
            self.apply_prop(which, color)
        self.refresh_panel()

    def set_color_focus(self, which):
        self.color_focus = which
        self.toolbar.refresh()

    def set_focus_color(self, color):
        """Swatch / None button: applies to the active Fill or Stroke."""
        self.set_color(self.color_focus, color)

    def apply_last_color(self):
        self.set_focus_color(self.last_color or WHITE)

    def swap_colors(self):
        self.fill, self.stroke = self.stroke, self.fill
        targets = [s for s in self.selected_shapes()
                   if s["type"] not in sh.STROKE_ONLY and s["type"] != "text"]
        if targets:
            self.push_undo()
        for s in targets:
            s["fill"], s["stroke"] = s.get("stroke"), s.get("fill")
            if s["stroke"] and not s.get("width"):
                s["width"] = max(1, self.width)
        self.refresh_panel()
        self.render()

    def default_colors(self):
        self.fill, self.stroke = WHITE, BLACK
        self.width = max(1, self.width)
        self.apply_props({"fill": WHITE, "stroke": BLACK, "width": self.width})
        self.refresh_panel()

    def toggle_color_focus(self):
        self.set_color_focus("stroke" if self.color_focus == "fill" else "fill")

    def toggle_dash(self):
        self.dash = not self.dash
        self.apply_prop("dash", self.dash)
        self.refresh_panel()

    def copy_appearance(self, src):
        """Eyedropper: take ``src``'s look for the selection and for new shapes."""
        if src["type"] == "text":
            values = {"fill": src.get("fill"), "font": src.get("font"), "size": src.get("size")}
        else:
            values = {"fill": src.get("fill"), "stroke": src.get("stroke"),
                      "width": src.get("width", self.width), "dash": sh.prop(src, "dash")}
            if src["type"] in sh.STROKE_ONLY:
                values.pop("fill")
        attr = {"size": "font_size", "font": "font_family"}
        for k, v in values.items():
            if v is not None or k in ("fill", "stroke"):
                setattr(self, attr.get(k, k), v)
        targets = [s for s in self.selected_shapes() if s["id"] != src["id"]]
        if targets:
            saved, self.selected = self.selected, {s["id"] for s in targets}
            self.apply_props({k: v for k, v in values.items() if v is not None or k in ("fill", "stroke")})
            self.selected = saved
        self.refresh_panel()
        self.render()
        self.flash(tr("flash_appearance"))

    # ── numeric fields ──────────────────────────────────────────────────────
    def set_stroke_width(self, v):
        v = max(0, int(round(v)))
        self.width = v
        self.apply_prop("width", v, key="width")
        self.refresh_panel()

    def set_radius(self, v):
        v = max(0.0, float(v))
        self.radius = v
        self.apply_prop("radius", v, key="radius")
        self.refresh_panel()

    def set_font_size(self, v):
        v = max(1, int(round(v)))
        self.font_size = v
        self.apply_prop("size", v, key="size")
        self.refresh_panel()

    def set_font_family(self, family):
        if not family:
            return
        self.font_family = family
        self.apply_prop("font", family)
        self.refresh_panel()
