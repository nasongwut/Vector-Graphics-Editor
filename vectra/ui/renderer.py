"""Draws the document, the selection and tool overlays on the Tk canvas.

The renderer reads editor state but never changes it.
"""

from vectra.config import GRID
from vectra.i18n import tr
from vectra.model import shapes as sh
from vectra.ui.theme import T

ROTATE_HANDLE_GAP = 24   # px above the selection box
ROTATE = "rotate"        # handle id of the rotation knob
OUTLINE = "#000000"


def dash_pattern(width, zoom):
    w = max(1.0, width) * zoom
    return (max(1, min(255, int(round(w * 3)))), max(1, min(255, int(round(w * 2)))))


class Renderer:
    T = T

    def __init__(self, editor):
        self.ed = editor

    @property
    def c(self):
        return self.ed.canvas

    # ── full frame ──────────────────────────────────────────────────────────
    def render(self):
        ed, c = self.ed, self.c
        c.delete("all")
        W, H = max(1, c.winfo_width()), max(1, c.winfo_height())
        step = ed.view.grid_step(GRID)
        self._draw_artboard(W, H, step)
        for s in ed.doc.shapes:
            if s["id"] != ed.editing_id:
                self.draw_shape(s)
        if ed.temp:
            self.draw_shape(ed.temp, temp=True)
        tool = ed.active_tool
        if tool.hover:
            self._hover_box()
        if tool.box == "full":
            self._selection_box(handles=True)
        elif tool.box == "plain":
            self._selection_box(handles=False)
        if tool.box:
            self.draw_marquee()
        tool.overlay(self)
        self._draw_guides()

    def _draw_artboard(self, W, H, step):
        c, ed = self.c, self.ed
        ab = ed.doc.artboard
        ax0, ay0, ax1, ay1 = ed.view.to_screen(list(ab))
        c.create_rectangle(ax0 + 3, ay0 + 4, ax1 + 3, ay1 + 4, fill=T["shadow"], outline="")
        c.create_rectangle(ax0, ay0, ax1, ay1, fill=T["board"], outline="#000000" if ed.outline_mode else "")
        if ed.show_grid:
            x = ax0
            while x <= ax1 + 0.5:
                if 0 <= x <= W:
                    c.create_line(x, max(ay0, 0), x, min(ay1, H), fill=T["board_grid"])
                x += step
            y = ay0
            while y <= ay1 + 0.5:
                if 0 <= y <= H:
                    c.create_line(max(ax0, 0), y, min(ax1, W), y, fill=T["board_grid"])
                y += step
        c.create_text(ax0, ay0 - 6, anchor="sw", fill=T["text"], font=ed.f(9),
                      text=tr("artboard_name", n=1))

    # ── shapes ──────────────────────────────────────────────────────────────
    def draw_shape(self, s, temp=False):
        if not temp and not self.ed.doc.shape_visible(s):
            return
        c, ed = self.c, self.ed
        z = ed.view.zoom
        to_screen = ed.view.to_screen
        tags = ("temp",) if temp else ("shape", f"s{s['id']}")
        typ = s["type"]
        fill = s.get("fill") or ""
        stroke = s.get("stroke") or ""
        sw = s.get("width", 0)
        outline = stroke if (stroke and sw > 0) else ""
        w = max(1.0, sw * z) if outline else 0
        dash = dash_pattern(sw, z) if sh.prop(s, "dash") else None
        if ed.outline_mode:
            fill, outline, stroke, w, dash = "", OUTLINE, OUTLINE, 1, None
            sw = 0
        extra = {"dash": dash} if dash and outline else {}

        if typ in ("rect", "ellipse") and sh.renders_as_polygon(s):
            poly = to_screen(sh.outline(s))
            c.create_polygon(*poly, fill=fill, outline=outline, width=w, joinstyle="round",
                             tags=tags, **extra)
        elif typ == "rect":
            c.create_rectangle(*to_screen(s["pts"]), fill=fill, outline=outline, width=w, tags=tags, **extra)
        elif typ == "ellipse":
            c.create_oval(*to_screen(s["pts"]), fill=fill, outline=outline, width=w, tags=tags, **extra)
        elif typ in ("line", "pen"):
            pts = to_screen(s["pts"])
            if len(pts) == 2:
                pts = pts + pts
            col = stroke or fill or "#000000"
            line_extra = {"dash": dash} if dash else {}
            lw = 1 if ed.outline_mode else max(1.0, max(sw, 1) * z)
            c.create_line(*pts, fill=col, width=lw, capstyle="round",
                          joinstyle="round", smooth=(typ == "pen"), tags=tags, **line_extra)
        elif typ == "polygon":
            pts = to_screen(s["pts"])
            if len(pts) >= 6:
                c.create_polygon(*pts, fill=fill, outline=outline, width=w, joinstyle="round",
                                 tags=tags, **extra)
        elif typ == "path":
            parts = [to_screen(r) for r in sh.raw_parts(s)]
            if not any(len(r) >= 8 for r in parts):
                if parts and len(parts[0]) == 2:
                    x, y = parts[0]
                    c.create_oval(x - 2, y - 2, x + 2, y + 2, fill=T["selection"], outline="", tags=tags)
                return
            if fill:
                raw = to_screen(sh.fill_raw(s))
                if len(raw) >= 8:
                    c.create_polygon(*raw, fill=fill, outline="", smooth="raw", splinesteps=24, tags=tags)
            for raw in parts:
                if len(raw) < 8:
                    continue
                if outline:
                    c.create_line(*raw, fill=outline, width=w, smooth="raw", splinesteps=24,
                                  capstyle="round", joinstyle="round", tags=tags, **extra)
                elif not fill:  # invisible path: keep it hittable and visible as a hairline
                    c.create_line(*raw, fill="#9a9a9a", width=1, smooth="raw", splinesteps=24,
                                  dash=(2, 2), tags=tags)
        elif typ == "text":
            pts = to_screen(s["pts"])
            size = -max(1, int(round(sh.prop(s, "size") * z)))
            family = s.get("font") or ed.ui_font
            c.create_text(pts[0], pts[1], text=s.get("text", ""), anchor="nw",
                          angle=-sh.prop(s, "rot"),
                          fill=OUTLINE if ed.outline_mode else (fill or stroke or "#000000"),
                          font=sh.font_spec(s, family, size), tags=tags)

    # ── overlays ────────────────────────────────────────────────────────────
    def _hover_box(self):
        ed, c = self.ed, self.c
        if ed.hover_id and ed.hover_id not in ed.selected and not ed.drag:
            s = ed.doc.by_id(ed.hover_id)
            if s:
                if s["type"] in ("text",):
                    b = ed.view.to_screen(list(ed.shape_bbox(s)))
                    c.create_rectangle(*b, outline=ed.sel_color(s), width=1)
                else:
                    p = s if s["type"] == "path" else sh.to_path(s)
                    for r in sh.raw_parts(p):
                        raw = ed.view.to_screen(r)
                        if len(raw) >= 8:
                            c.create_line(*raw, fill=ed.sel_color(s), width=1.5, smooth="raw", splinesteps=16)

    def _selection_box(self, handles):
        ed, c = self.ed, self.c
        if not ed.selected:
            return
        col = ed.sel_color()
        sel = ed.selected_shapes()
        for s in sel:  # path highlight in each object's layer colour
            if s["type"] == "text":
                continue
            p = s if s["type"] == "path" else sh.to_path(s)
            for r in sh.raw_parts(p):
                raw = ed.view.to_screen(r)
                if len(raw) >= 8:
                    c.create_line(*raw, fill=ed.sel_color(s), width=1, smooth="raw", splinesteps=16)
        bb = ed.selection_bbox()
        if not bb:
            return
        sb = ed.view.to_screen(list(bb))
        x0, y0, x1, y1 = sb[0] - 1, sb[1] - 1, sb[2] + 1, sb[3] + 1
        c.create_rectangle(x0, y0, x1, y1, outline=col, width=1)
        mode = ed.drag["mode"] if ed.drag else None
        if handles and mode not in ("move", "rotate"):
            for hx, hy in ed.handle_screen_points(x0, y0, x1, y1):
                c.create_rectangle(hx - 3.5, hy - 3.5, hx + 3.5, hy + 3.5, fill="#ffffff",
                                   outline=col, width=1)
            rx, ry = ed.rotate_handle_screen(x0, y0, x1, y1)
            c.create_line((x0 + x1) / 2, y0, rx, ry, fill=col)
            c.create_oval(rx - 4.5, ry - 4.5, rx + 4.5, ry + 4.5, fill="#ffffff", outline=col, width=1.2)
        if handles:
            if mode == "rotate":
                label = f"{ed.drag.get('angle', 0):.1f}°"
            elif mode == "move" and ed.drag.get("changed"):
                label = f"dX {ed.drag['dx']:.0f}  dY {ed.drag['dy']:.0f}"
            else:
                label = f"W {bb[2] - bb[0]:.0f}  H {bb[3] - bb[1]:.0f}"
            self.pill((x0 + x1) / 2, y1 + 18, label)

    def draw_marquee(self):
        ed = self.ed
        if ed.drag and ed.drag.get("mode") == "marquee":
            (sx, sy), (ex, ey) = ed.drag["start"], ed.drag["cur"]
            self.c.create_rectangle(sx, sy, ex, ey, outline=T["selection"], dash=(4, 3), width=1)

    def _draw_guides(self):
        ed, c = self.ed, self.c
        for kind, v, a, b in ed.guides.lines:
            if kind == "v":
                x, y0 = ed.to_screen([v, a])
                _x, y1 = ed.to_screen([v, b])
                c.create_line(x, y0 - 12, x, y1 + 12, fill=T["smart"], width=1)
            else:
                x0, y = ed.to_screen([a, v])
                x1, _y = ed.to_screen([b, v])
                c.create_line(x0 - 12, y, x1 + 12, y, fill=T["smart"], width=1)

    def pill(self, x, y, label, bg=None):
        c, ed = self.c, self.ed
        tid = c.create_text(x, y, text=label, fill="#ffffff", font=(ed.mono, 9))
        tb = c.bbox(tid)
        pill = c.create_rectangle(tb[0] - 6, tb[1] - 3, tb[2] + 6, tb[3] + 3,
                                  fill=bg or "#5a5a5a", outline="")
        c.tag_lower(pill, tid)
