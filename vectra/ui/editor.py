"""The main window / controller.

``VectorEditor`` owns the state and wires the pieces together. Behaviour is split
into mixins by concern so each file stays readable:

    interaction.py  canvas events → active tool, panning, wheel, keys
    commands.py     edit / select / object / view commands
    style.py        fill, stroke, character … and panel sync
    files.py        new / open / save / export
    tooling/        one class per tool (Selection, Pen, Rectangle, …)
"""

import copy
import os
import tkinter as tk

from vectra import i18n, settings
from vectra.config import (APP_NAME, DEFAULT_FILL, DEFAULT_FONT_SIZE, DEFAULT_STAR_POINTS,
                           DEFAULT_STROKE, DEFAULT_WIDTH, GRID)
from vectra.i18n import tr
from vectra.model import geometry as geo
from vectra.model import shapes as sh
from vectra.model.document import Document
from vectra.model.history import History
from vectra.ui import dialogs
from vectra.ui.chrome import build_context_menu, build_doc_tab, build_statusbar
from vectra.ui.commands import CommandsMixin
from vectra.ui.controlbar import ControlBar
from vectra.ui.files import FilesMixin
from vectra.ui.interaction import InteractionMixin
from vectra.ui.menubar import build_menubar
from vectra.ui.panels.side_panel import SidePanel
from vectra.ui.renderer import ROTATE, ROTATE_HANDLE_GAP, Renderer
from vectra.ui.rulers import Ruler
from vectra.ui.shortcuts import bind_shortcuts
from vectra.ui.smart_guides import SmartGuides
from vectra.ui.style import StyleMixin
from vectra.ui.text_editor import InlineTextEditor
from vectra.ui.theme import T, pick_font, pick_mono_font
from vectra.ui.toolbar import ToolBar
from vectra.ui.tooling import create_tools
from vectra.ui.viewport import Viewport
from vectra.ui.widgets import setup_ttk_style

HANDLE_HIT = 7  # px


class VectorEditor(InteractionMixin, CommandsMixin, StyleMixin, FilesMixin):
    def __init__(self, root):
        self.root = root
        sw, shh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{min(1440, sw - 40)}x{min(900, shh - 100)}")
        root.minsize(min(1100, sw - 40), min(680, shh - 100))
        root.configure(bg=T["bg"])

        self.ui_font = pick_font(root)
        self.mono = pick_mono_font(root)

        # document state
        self.doc = Document()
        self.history = History()
        self.selected = set()
        self.file_path = None
        self.dirty = False
        self.clipboard = []
        self.last_transform = None

        # style state (applies to new shapes & the selection)
        self.fill = DEFAULT_FILL
        self.stroke = DEFAULT_STROKE
        self.width = DEFAULT_WIDTH
        self.font_size = DEFAULT_FONT_SIZE
        self.font_family = self.ui_font
        self.radius = 0
        self.dash = False
        self.color_focus = "fill"
        self.last_color = DEFAULT_FILL
        self.star_points = DEFAULT_STAR_POINTS
        self.polygon_sides = 6

        # view state
        self.view = Viewport()
        self.show_grid = False
        self.snap = False
        self.smart_guides = True
        self.outline_mode = False
        self.show_rulers = True
        self.show_toolbar = True
        self.show_control = True
        self.panels_hidden = False
        self.keep_ratio = False
        self.align_to = "selection"

        # interaction state
        self.tool = "select"
        self.tools = create_tools(self)
        self.guides = SmartGuides(self)
        self.drag = None
        self.temp = None
        self.cursor_w = (0, 0)
        self.hover_id = None
        self.space = False
        self.editing_id = None
        self.text_editor = None
        self._flash_job = None
        self._geo_job = None
        self.panel = None

        self.build_ui()
        bind_shortcuts(self)
        self.set_tool("select")
        self.refresh_panel()
        self.update_title()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(60, self.zoom_fit)

    @property
    def active_tool(self):
        return self.tools[self.tool]

    # ── UI construction (re-run when the language changes) ─────────────────
    def build_ui(self):
        r = self.root
        tab = self.panel.current if self.panel else "props"
        if self.text_editor:
            self.text_editor.commit()
        for w in r.winfo_children():
            w.destroy()
        self._flash_job = None
        setup_ttk_style(r, self.f(9))

        build_menubar(self, r)
        self.control = ControlBar(self, r)
        self.control_sep = tk.Frame(r, bg=T["border"], height=1)
        build_statusbar(self, r)

        self.body = tk.Frame(r, bg=T["bg"])
        self.toolbar = ToolBar(self, self.body)
        self.tool_sep = tk.Frame(self.body, bg=T["border"], width=1)
        self.dock = tk.Frame(self.body, bg=T["panel"], width=300)
        self.dock.pack_propagate(False)
        self.dock_sep = tk.Frame(self.body, bg=T["border"], width=1)
        self.panel = SidePanel(self, self.dock, current=tab)

        self.center = tk.Frame(self.body, bg=T["bg"])
        build_doc_tab(self, self.center)
        self.stage = tk.Frame(self.center, bg=T["bg"])
        self.stage.pack(side="top", fill="both", expand=True)
        self.corner = tk.Frame(self.stage, bg=T["ruler"], width=18, height=18)
        self.ruler_h = Ruler(self.stage, self, horizontal=True)
        self.ruler_v = Ruler(self.stage, self, horizontal=False)
        self.canvas = tk.Canvas(self.stage, bg=T["canvas"], highlightthickness=0, bd=0)
        self.stage.rowconfigure(1, weight=1)
        self.stage.columnconfigure(1, weight=1)
        self.canvas.grid(row=1, column=1, sticky="nsew")

        self.renderer = Renderer(self)
        self.bind_canvas()
        self.menu = build_context_menu(self, r)
        self.layout_chrome()
        self.sync_menu_vars()

    def layout_chrome(self):
        """(Re)pack bars and panels according to the visibility toggles."""
        for w in (self.control.frame, self.control_sep, self.body, self.toolbar.outer, self.tool_sep,
                  self.dock, self.dock_sep, self.center):
            w.pack_forget()
        if self.show_control and not self.panels_hidden:
            self.control.pack(side="top", fill="x")
            self.control_sep.pack(side="top", fill="x")
        self.body.pack(side="top", fill="both", expand=True)
        if self.show_toolbar and not self.panels_hidden:
            self.toolbar.pack(side="left", fill="y")
            self.tool_sep.pack(side="left", fill="y")
        if not self.panels_hidden:
            self.dock.pack(side="right", fill="y")
            self.dock_sep.pack(side="right", fill="y")
        self.center.pack(side="left", fill="both", expand=True)
        if self.show_rulers:
            self.corner.grid(row=0, column=0, sticky="nsew")
            self.ruler_h.grid(row=0, column=1, sticky="ew")
            self.ruler_v.grid(row=1, column=0, sticky="ns")
        else:
            for w in (self.corner, self.ruler_h, self.ruler_v):
                w.grid_forget()

    def sync_menu_vars(self):
        v = getattr(self, "menu_vars", None)
        if not v:
            return
        v["outline"].set(self.outline_mode)
        v["rulers"].set(self.show_rulers)
        v["smart"].set(self.smart_guides)
        v["grid"].set(self.show_grid)
        v["snap"].set(self.snap)
        v["tools"].set(self.show_toolbar)
        v["control"].set(self.show_control)

    def set_language(self, code):
        if code == i18n.get_language():
            return
        i18n.set_language(code)
        settings.set("language", code)
        self.build_ui()
        self.set_tool(self.tool)
        self.refresh_panel()
        self.update_title()
        self.root.after(30, self.render)
        self.flash(tr("flash_lang"))

    # ── helpers ─────────────────────────────────────────────────────────────
    def f(self, size=10, weight="normal"):
        return (self.ui_font, size, weight)

    def to_world(self, sx, sy):
        return self.view.to_world(sx, sy)

    def to_screen(self, pts):
        return self.view.to_screen(pts)

    def snapv(self, v):
        return round(v / GRID) * GRID if self.snap else v

    def selected_shapes(self):
        return self.doc.of_ids(self.selected)

    def orig_shapes(self):
        return {s["id"]: copy.deepcopy(s) for s in self.selected_shapes()}

    def apply_from_orig(self, d, fn):
        for sid, orig in d["orig"].items():
            s = self.doc.by_id(sid)
            if s is not None:
                sh.replace_in_place(s, fn(orig))

    def current_style(self):
        return {"fill": self.fill, "stroke": self.stroke, "width": self.width,
                "font_size": self.font_size, "radius": self.radius, "dash": self.dash,
                "font": self.font_family}

    def shape_bbox(self, s):
        if s["type"] == "text" and self.doc.shape_visible(s) and s["id"] != self.editing_id:
            b = self.canvas.bbox(f"s{s['id']}")
            if b:
                x0, y0 = self.to_world(b[0], b[1])
                x1, y1 = self.to_world(b[2], b[3])
                return (x0, y0, x1, y1)
        return sh.geometry_bbox(s)

    def sel_color(self, s=None):
        """Selection colour = colour of the object's layer (like Illustrator)."""
        if s is None:
            sel = self.selected_shapes()
            s = sel[-1] if sel else None
        if s is None:
            return T["selection"]
        return self.doc.layer_of(s).get("color") or T["selection"]

    def selection_bbox(self):
        return geo.union_bbox([self.shape_bbox(s) for s in self.selected_shapes()])

    @staticmethod
    def handle_screen_points(x0, y0, x1, y1):
        return geo.handle_points(x0, y0, x1, y1)

    @staticmethod
    def rotate_handle_screen(x0, y0, x1, y1):
        return (x0 + x1) / 2, y0 - ROTATE_HANDLE_GAP

    def handle_at(self, sx, sy):
        """Index 0..7 of a resize handle, ROTATE for the rotation knob, or None."""
        bb = self.selection_bbox()
        if not bb:
            return None
        sbb = self.to_screen(list(bb))
        rx, ry = self.rotate_handle_screen(sbb[0] - 1, sbb[1] - 1, sbb[2] + 1, sbb[3] + 1)
        if abs(sx - rx) <= HANDLE_HIT and abs(sy - ry) <= HANDLE_HIT:
            return ROTATE
        for i, (hx, hy) in enumerate(self.handle_screen_points(*sbb)):
            if abs(sx - hx) <= HANDLE_HIT and abs(sy - hy) <= HANDLE_HIT:
                return i
        return None

    def hit(self, sx, sy):
        """Id of the top-most visible, unlocked shape under the screen point."""
        items = self.canvas.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)
        for it in reversed(items):
            for tag in self.canvas.gettags(it):
                if tag.startswith("s") and tag[1:].isdigit():
                    s = self.doc.by_id(int(tag[1:]))
                    if s and not self.doc.shape_locked(s) and self.doc.shape_visible(s):
                        return s["id"]
        return None

    def ask_form(self, title, fields, allow_copy=False, note=None):
        res = dialogs.ask_form(self, title, fields, allow_copy, note)
        return res[0] if res and not allow_copy else res

    # ── history ─────────────────────────────────────────────────────────────
    doc_version = 0   # bumped on every document change (cheap change detection for panels)

    def push_undo(self, key=None):
        self.doc_version += 1
        if self.history.record(self.doc.snapshot, key):
            self.set_dirty(True)

    def _restore(self, snap):
        self.doc_version += 1
        self.doc.restore(snap)
        self.selected &= self.doc.ids()
        self.set_dirty(True)
        self.on_selection_changed()
        self.render()

    def undo(self):
        self.commit_text_edit()
        snap = self.history.undo(self.doc.snapshot)
        if snap is not None:
            self._restore(snap)
            self.flash(tr("flash_undo"))

    def redo(self):
        snap = self.history.redo(self.doc.snapshot)
        if snap is not None:
            self._restore(snap)
            self.flash(tr("flash_redo"))

    def set_dirty(self, d):
        if self.dirty != d:
            self.dirty = d
            self.update_title()

    def doc_name(self):
        if self.file_path:
            return os.path.basename(self.file_path)
        return self.import_name or tr("untitled")

    def update_title(self):
        self.root.title(f"{'● ' if self.dirty else ''}{self.doc_name()} — {APP_NAME}")
        mode = tr("mode_outline") if self.outline_mode else tr("mode_preview")
        self.doc_tab.config(text=f"{self.doc_name()}{'*' if self.dirty else ''} @ "
                                 f"{self.view.zoom * 100:.0f}% (RGB/{mode})   ✕")

    # ── rendering / status ──────────────────────────────────────────────────
    def render(self):
        self.renderer.render()
        if self.show_rulers:
            self.ruler_h.draw()
            self.ruler_v.draw()
        self.update_status()
        if self.panel.current == "layers":
            self.panel.layers.refresh()
        if self._geo_job is None:
            self._geo_job = self.root.after_idle(self._refresh_geo)

    def status_text(self):
        x, y = self.cursor_w
        ab = self.doc.artboard
        return (f"X {x - ab[0]:7.1f}  Y {y - ab[1]:7.1f}   │   "
                f"{tr('status_objects', n=len(self.doc.shapes))}")

    def update_status(self):
        if not self._flash_job:
            self.status_l.config(text=self.active_tool.hint(), fg=T["muted"])
        self.status_r.config(text=self.status_text())
        self.zoom_entry.show(f"{self.view.zoom * 100:.0f}%")
        self.tool_label.config(text=self.active_tool.name())
        self.update_title()

    def flash(self, msg, ms=1800):
        self.status_l.config(text=f"✓  {msg}", fg=T["accent2"])
        if self._flash_job:
            self.root.after_cancel(self._flash_job)

        def back():
            self._flash_job = None
            self.status_l.config(fg=T["muted"], text=self.active_tool.hint())
        self._flash_job = self.root.after(ms, back)

    # ── zoom ────────────────────────────────────────────────────────────────
    def zoom_at(self, factor, sx, sy):
        self.view.zoom_at(factor, sx, sy)
        self.render()

    def zoom_center(self, factor):
        c = self.canvas
        self.zoom_at(factor, c.winfo_width() / 2, c.winfo_height() / 2)

    def set_zoom(self, z):
        self.zoom_center(z / self.view.zoom)

    def set_zoom_text(self, text):
        try:
            z = float(text.replace("%", "").replace(",", ".")) / 100
        except ValueError:
            return
        if z > 0:
            self.set_zoom(z)

    def zoom_to_rect(self, rect, margin=120):
        c = self.canvas
        if rect[2] - rect[0] < 1 or rect[3] - rect[1] < 1:
            return
        if self.view.fit(rect, c.winfo_width(), c.winfo_height(), margin=margin):
            self.render()

    def zoom_fit(self):
        self.zoom_to_rect(self.doc.artboard)

    def restore_cursor(self):
        self.canvas.config(cursor="fleur" if self.space else self.active_tool.cursor)

    # ── text editing on canvas ──────────────────────────────────────────────
    def edit_text(self, s):
        self.commit_text_edit()
        self.selected = {s["id"]}
        self.editing_id = s["id"]
        self.render()
        self.text_editor = InlineTextEditor(self, s, is_new=False)

    def new_text_at(self, x, y):
        self.commit_text_edit()
        s = self.new_shape("text", [x, y])
        self.editing_id = -1
        self.text_editor = InlineTextEditor(self, s, is_new=True)

    def edit_selected_text(self):
        sel = [s for s in self.selected_shapes() if s["type"] == "text"]
        if sel:
            self.edit_text(sel[0])

    def commit_text_edit(self):
        if self.text_editor:
            self.text_editor.commit()

    # ── dialogs ─────────────────────────────────────────────────────────────
    def show_shortcuts(self):
        dialogs.TextDialog(self, tr("m_shortcuts"), dialogs.shortcuts_text()).show()

    def show_about(self):
        dialogs.TextDialog(self, tr("m_about"), dialogs.about_text(), width=52, height=12).show()

    def show_panel(self, key):
        if self.panels_hidden:
            self.toggle_all_panels()
        self.panel.show(key)
