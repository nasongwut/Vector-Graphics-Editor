#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vectra — Vector Graphics Editor (Python + Tkinter)
=================================================
โปรแกรมวาดภาพเวกเตอร์ สไตล์โมเดิร์น (ธีมมืด) ใช้ไลบรารีมาตรฐานของ Python ล้วน
ไม่ต้องติดตั้งอะไรเพิ่ม  —  รันด้วย:  python vectra.py

ความสามารถ
  • เครื่องมือ: เลือก/ย้าย/ย่อขยาย, เลื่อนมุมมอง, สี่เหลี่ยม, วงรี, เส้นตรง,
    รูปหลายเหลี่ยม, ปากกาวาดอิสระ, ข้อความ
  • เลือกหลายชิ้น (Shift+คลิก หรือลากกรอบ), ย่อขยายเป็นกลุ่ม (Shift = ล็อกสัดส่วน)
  • สีพื้น / สีเส้น / ความหนาเส้น / ขนาดตัวอักษร, จานสีด่วน
  • จัดลำดับชั้น, ทำสำเนา, คัดลอก/วาง, Undo/Redo
  • ซูม (Ctrl+ล้อเมาส์), เลื่อนมุมมอง (ล้อเมาส์ / Space+ลาก / ปุ่มกลาง)
  • กริด + Snap, บันทึก/เปิดไฟล์ .json, ส่งออก .svg

คีย์ลัด
  V เลือก   H มือ   R สี่เหลี่ยม   E วงรี   L เส้น   G หลายเหลี่ยม   P ปากกา   T ข้อความ
  Ctrl+Z / Ctrl+Y  ย้อน/ทำซ้ำ     Ctrl+C / Ctrl+V  คัดลอก/วาง     Ctrl+D ทำสำเนา
  Ctrl+A เลือกทั้งหมด   Delete ลบ   ลูกศร ขยับ (Shift = 10)   ] [ เลื่อนชั้น
  Ctrl+S บันทึก   Ctrl+O เปิด   Ctrl+N ใหม่   Ctrl+E ส่งออก SVG   Ctrl+0 ซูมพอดี
  Enter / ดับเบิลคลิก = จบรูปหลายเหลี่ยม   Esc = ยกเลิก
"""

import copy
import json
import math
import os
import sys
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog
from tkinter import font as tkfont
from xml.sax.saxutils import escape

# ──────────────────────────────────────────────────────────────────────────────
#  Theme
# ──────────────────────────────────────────────────────────────────────────────
T = dict(
    bg="#0e1014",
    panel="#16191f",
    panel2="#1f232b",
    border="#2a2f3a",
    text="#e7e9ee",
    muted="#8a92a6",
    accent="#7c5cff",
    accent2="#a48dff",
    hover="#252a34",
    canvas="#0b0d11",
    grid="#151922",
    board_grid="#eef0f5",
    board="#ffffff",
    danger="#ff5c7a",
    shadow="#050609",
)

PALETTE = [
    "#0f172a", "#ffffff", "#f43f5e", "#f97316", "#facc15", "#22c55e",
    "#14b8a6", "#06b6d4", "#3b82f6", "#6366f1", "#7c5cff", "#a855f7",
    "#ec4899", "#64748b", "#cbd5e1", "#78350f",
]

ARTBOARD = (0, 0, 1000, 700)
GRID = 10
IS_MAC = sys.platform == "darwin"

TYPE_TH = {
    "rect": "สี่เหลี่ยม", "ellipse": "วงรี", "line": "เส้นตรง",
    "polygon": "รูปหลายเหลี่ยม", "pen": "เส้นอิสระ", "text": "ข้อความ",
}

TOOLS = [
    ("select", "➤", "เลือก / ย้าย / ย่อขยาย", "V"),
    ("hand", "✋", "เลื่อนมุมมอง", "H"),
    None,
    ("rect", "▢", "สี่เหลี่ยม", "R"),
    ("ellipse", "◯", "วงรี", "E"),
    ("line", "╱", "เส้นตรง", "L"),
    ("polygon", "⬠", "รูปหลายเหลี่ยม", "G"),
    ("pen", "✎", "ปากกาวาดอิสระ", "P"),
    ("text", "T", "ข้อความ", "T"),
]

HINTS = {
    "select": "คลิกเพื่อเลือก · Shift+คลิก เพิ่มการเลือก · ลากพื้นที่ว่างเพื่อเลือกเป็นกรอบ · ดับเบิลคลิกข้อความเพื่อแก้ไข",
    "hand": "ลากเพื่อเลื่อนมุมมอง · Ctrl+ล้อเมาส์ เพื่อซูม",
    "rect": "ลากเพื่อวาดสี่เหลี่ยม · Shift = จัตุรัส · คลิกครั้งเดียว = ขนาดเริ่มต้น",
    "ellipse": "ลากเพื่อวาดวงรี · Shift = วงกลม",
    "line": "ลากเพื่อวาดเส้น · Shift = ล็อกมุม 45°",
    "polygon": "คลิกเพื่อวางจุด · คลิกจุดแรก / ดับเบิลคลิก / Enter เพื่อจบ · Esc ยกเลิก",
    "pen": "กดค้างแล้วลากเพื่อวาดเส้นอิสระ",
    "text": "คลิกตำแหน่งที่ต้องการวางข้อความ",
}

CURSORS = {
    "select": "arrow", "hand": "fleur", "text": "xterm",
}


def pick_font(root):
    fams = set(tkfont.families(root))
    for f in ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", ".AppleSystemUIFont",
              "Helvetica Neue", "Inter", "Noto Sans Thai", "Noto Sans", "Ubuntu",
              "DejaVu Sans", "Helvetica", "Arial"):
        if f in fams:
            return f
    return "TkDefaultFont"


# ──────────────────────────────────────────────────────────────────────────────
#  Small modern widgets
# ──────────────────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text, side="right", font=None):
        self.w, self.text, self.side, self.font = widget, text, side, font
        self.tip = None
        self.job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def _schedule(self, _e=None):
        self.hide()
        self.job = self.w.after(450, self.show)

    def show(self):
        if self.tip:
            return
        self.tip = tk.Toplevel(self.w)
        self.tip.wm_overrideredirect(True)
        try:
            self.tip.attributes("-topmost", True)
        except tk.TclError:
            pass
        lbl = tk.Label(self.tip, text=self.text, bg="#000000", fg="#ffffff",
                       padx=9, pady=5, font=self.font)
        lbl.pack()
        self.tip.update_idletasks()
        if self.side == "right":
            x = self.w.winfo_rootx() + self.w.winfo_width() + 8
            y = self.w.winfo_rooty() + (self.w.winfo_height() - self.tip.winfo_height()) // 2
        else:  # below
            x = self.w.winfo_rootx() + (self.w.winfo_width() - self.tip.winfo_width()) // 2
            y = self.w.winfo_rooty() + self.w.winfo_height() + 6
        self.tip.wm_geometry(f"+{x}+{y}")

    def hide(self, _e=None):
        if self.job:
            self.w.after_cancel(self.job)
            self.job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


class FlatButton(tk.Label):
    """Flat button with hover + active state (Label-based so it themes everywhere)."""

    def __init__(self, master, text, command=None, font=None, bg=None, fg=None,
                 hover=None, active_bg=None, padx=10, pady=6, width=None,
                 tooltip=None, tip_side="below", tip_font=None):
        self.c_bg = bg or T["panel"]
        self.c_fg = fg or T["text"]
        self.c_hover = hover or T["hover"]
        self.c_active = active_bg or T["accent"]
        super().__init__(master, text=text, bg=self.c_bg, fg=self.c_fg, font=font,
                         padx=padx, pady=pady, cursor="hand2", bd=0)
        if width:
            self.config(width=width)
        self.command = command
        self.active = False
        self._hover = False
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._click)
        if tooltip:
            Tooltip(self, tooltip, side=tip_side, font=tip_font)

    def _set_hover(self, h):
        self._hover = h
        self._paint()

    def _paint(self):
        if self.active:
            self.config(bg=self.c_active, fg="#ffffff")
        elif self._hover:
            self.config(bg=self.c_hover, fg="#ffffff")
        else:
            self.config(bg=self.c_bg, fg=self.c_fg)

    def set_active(self, a):
        self.active = a
        self._paint()

    def _click(self, e):
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            if self.command:
                self.command()


class Swatch(tk.Canvas):
    def __init__(self, master, size=30, command=None, bg=None):
        super().__init__(master, width=size, height=size, bg=bg or T["panel"],
                         highlightthickness=0, cursor="hand2")
        self.size = size
        self.color = None
        if command:
            self.bind("<Button-1>", lambda e: command())

    def set(self, color):
        self.color = color
        self.delete("all")
        s = self.size
        self.create_rectangle(2, 2, s - 2, s - 2, outline=T["border"], width=2,
                              fill=color or T["panel2"])
        if not color:
            self.create_line(5, s - 5, s - 5, 5, fill=T["danger"], width=2)


# ──────────────────────────────────────────────────────────────────────────────
#  Editor
# ──────────────────────────────────────────────────────────────────────────────
class VectorEditor:
    def __init__(self, root):
        self.root = root
        root.geometry("1360x840")
        root.minsize(1000, 640)
        root.configure(bg=T["bg"])

        self.ui_font = pick_font(root)
        self.mono = "Consolas" if "Consolas" in tkfont.families(root) else (
            "Menlo" if IS_MAC else "DejaVu Sans Mono")

        # document state
        self.shapes = []
        self.next_id = 1
        self.selected = set()
        self.undo_stack, self.redo_stack = [], []
        self._last_key, self._last_t = None, 0.0
        self.file_path = None
        self.dirty = False
        self.clipboard = []

        # style state (applies to new shapes & selection)
        self.fill = "#7c5cff"
        self.stroke = "#0f172a"
        self.width = 2
        self.font_size = 32

        # view / interaction state
        self.tool = "select"
        self.zoom = 1.0
        self.ox, self.oy = 60.0, 60.0
        self.show_grid = True
        self.snap = False
        self.drag = None
        self.temp = None
        self.poly_pts = []
        self.cursor_w = (0, 0)
        self.hover_id = None
        self.space = False
        self.tool_buttons = {}
        self._flash_job = None

        self.build_ui()
        self.bind_keys()
        self.set_tool("select")
        self.update_title()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(60, self.zoom_fit)

    # ── helpers ──────────────────────────────────────────────────────────────
    def f(self, size=10, weight="normal"):
        return (self.ui_font, size, weight)

    def to_world(self, sx, sy):
        return (sx - self.ox) / self.zoom, (sy - self.oy) / self.zoom

    def to_screen(self, pts):
        z, ox, oy = self.zoom, self.ox, self.oy
        return [v * z + (ox if i % 2 == 0 else oy) for i, v in enumerate(pts)]

    def snapv(self, v):
        return round(v / GRID) * GRID if self.snap else v

    def by_id(self, sid):
        for s in self.shapes:
            if s["id"] == sid:
                return s
        return None

    def selected_shapes(self):
        return [s for s in self.shapes if s["id"] in self.selected]

    # ── UI construction ──────────────────────────────────────────────────────
    def build_ui(self):
        r = self.root
        # top bar
        top = tk.Frame(r, bg=T["panel"], height=54)
        top.pack(side="top", fill="x")
        top.pack_propagate(False)

        logo = tk.Canvas(top, width=30, height=30, bg=T["panel"], highlightthickness=0)
        logo.pack(side="left", padx=(18, 8))
        logo.create_polygon(15, 3, 27, 26, 3, 26, fill=T["accent"], outline="")
        logo.create_oval(10, 13, 20, 23, fill=T["panel"], outline="")
        tk.Label(top, text="Vectra", bg=T["panel"], fg=T["text"],
                 font=self.f(14, "bold")).pack(side="left")
        tk.Label(top, text="Vector Editor", bg=T["panel"], fg=T["muted"],
                 font=self.f(10)).pack(side="left", padx=(6, 22))

        def tb(text, cmd, tip):
            b = FlatButton(top, text, cmd, font=self.f(10), padx=12, pady=7,
                           tooltip=tip, tip_font=self.f(9))
            b.pack(side="left", padx=2, pady=10)
            return b

        def vsep():
            tk.Frame(top, bg=T["border"], width=1).pack(side="left", fill="y", padx=10, pady=14)

        tb("ใหม่", self.new_doc, "เอกสารใหม่  (Ctrl+N)")
        tb("เปิด", self.open_doc, "เปิดไฟล์ .json  (Ctrl+O)")
        tb("บันทึก", self.save, "บันทึก  (Ctrl+S)")
        tb("บันทึกเป็น", lambda: self.save(True), "บันทึกเป็นไฟล์ใหม่  (Ctrl+Shift+S)")
        vsep()
        tb("↶", self.undo, "ย้อนกลับ  (Ctrl+Z)")
        tb("↷", self.redo, "ทำซ้ำ  (Ctrl+Y)")

        export = FlatButton(top, "ส่งออก SVG", self.export_svg, font=self.f(10, "bold"),
                            bg=T["accent"], fg="#ffffff", hover=T["accent2"], padx=16, pady=7,
                            tooltip="ส่งออกเป็นไฟล์ .svg  (Ctrl+E)", tip_font=self.f(9))
        export.pack(side="right", padx=(8, 18), pady=10)

        zf = tk.Frame(top, bg=T["panel2"])
        zf.pack(side="right", pady=12, padx=6)
        FlatButton(zf, "−", lambda: self.zoom_center(1 / 1.2), font=self.f(11), bg=T["panel2"],
                   padx=10, pady=2).pack(side="left")
        self.zoom_lbl = FlatButton(zf, "100%", lambda: self.set_zoom(1.0), font=(self.mono, 10),
                                   bg=T["panel2"], padx=6, pady=2, width=5,
                                   tooltip="คลิกเพื่อซูม 100%", tip_font=self.f(9))
        self.zoom_lbl.pack(side="left")
        FlatButton(zf, "+", lambda: self.zoom_center(1.2), font=self.f(11), bg=T["panel2"],
                   padx=10, pady=2).pack(side="left")
        FlatButton(top, "พอดีจอ", self.zoom_fit, font=self.f(10), padx=10, pady=7,
                   tooltip="ซูมให้พอดีหน้าจอ  (Ctrl+0)", tip_font=self.f(9)).pack(side="right", pady=10)

        tk.Frame(r, bg=T["border"], height=1).pack(side="top", fill="x")

        # status bar
        status = tk.Frame(r, bg=T["panel"], height=28)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)
        tk.Frame(r, bg=T["border"], height=1).pack(side="bottom", fill="x")
        self.status_l = tk.Label(status, text="", bg=T["panel"], fg=T["muted"], font=self.f(9), anchor="w")
        self.status_l.pack(side="left", padx=14)
        self.status_r = tk.Label(status, text="", bg=T["panel"], fg=T["muted"], font=(self.mono, 9))
        self.status_r.pack(side="right", padx=14)

        body = tk.Frame(r, bg=T["bg"])
        body.pack(side="top", fill="both", expand=True)

        # left toolbar
        left = tk.Frame(body, bg=T["panel"], width=64)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Frame(body, bg=T["border"], width=1).pack(side="left", fill="y")
        tk.Frame(left, bg=T["panel"], height=10).pack()
        for item in TOOLS:
            if item is None:
                tk.Frame(left, bg=T["border"], height=1, width=32).pack(pady=8)
                continue
            key, icon, name, sc = item
            b = FlatButton(left, icon, lambda k=key: self.set_tool(k),
                           font=(self.ui_font, 16), width=2, padx=6, pady=6,
                           tooltip=f"{name}   {sc}", tip_side="right", tip_font=self.f(9))
            b.pack(pady=3)
            self.tool_buttons[key] = b

        # right properties panel
        right = tk.Frame(body, bg=T["panel"], width=272)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tk.Frame(body, bg=T["border"], width=1).pack(side="right", fill="y")
        self.build_panel(right)

        # canvas
        self.canvas = tk.Canvas(body, bg=T["canvas"], highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_double)
        c.bind("<Motion>", self.on_motion)
        c.bind("<Leave>", lambda e: self._set_hover(None))
        pan_btn, ctx_btn = ("3", "2") if IS_MAC else ("2", "3")
        c.bind(f"<ButtonPress-{pan_btn}>", self.pan_start)
        c.bind(f"<B{pan_btn}-Motion>", self.pan_move)
        c.bind(f"<ButtonRelease-{pan_btn}>", lambda e: self._end_pan())
        c.bind(f"<ButtonPress-{ctx_btn}>", self.context_menu)
        c.bind("<MouseWheel>", self.on_wheel)
        c.bind("<Shift-MouseWheel>", lambda e: self.on_wheel(e, horizontal=True))
        c.bind("<Control-MouseWheel>", lambda e: self.on_wheel(e, zoom=True))
        if IS_MAC:
            c.bind("<Command-MouseWheel>", lambda e: self.on_wheel(e, zoom=True))
        c.bind("<Button-4>", lambda e: self.on_wheel_linux(e, 1))
        c.bind("<Button-5>", lambda e: self.on_wheel_linux(e, -1))
        c.bind("<Configure>", lambda e: self.render())

        self.menu = tk.Menu(r, tearoff=0, bg=T["panel2"], fg=T["text"], bd=0,
                            activebackground=T["accent"], activeforeground="#ffffff",
                            font=self.f(10), relief="flat")
        for label, cmd, acc in [
            ("คัดลอก", self.copy_sel, "Ctrl+C"), ("วาง", self.paste, "Ctrl+V"),
            ("ทำสำเนา", self.duplicate, "Ctrl+D"), (None, None, None),
            ("ขึ้นหน้าสุด", self.bring_front, "Shift+]"), ("ขึ้น 1 ชั้น", self.bring_forward, "]"),
            ("ลง 1 ชั้น", self.send_backward, "["), ("ส่งไปหลังสุด", self.send_back, "Shift+["),
            (None, None, None), ("ลบ", self.delete_sel, "Del"),
        ]:
            if label is None:
                self.menu.add_separator()
            else:
                self.menu.add_command(label=label, command=cmd, accelerator=acc)

    def build_panel(self, p):
        def section(title, first=False):
            if not first:
                tk.Frame(p, bg=T["border"], height=1).pack(fill="x", pady=(14, 0))
            tk.Label(p, text=title, bg=T["panel"], fg=T["muted"],
                     font=self.f(9, "bold")).pack(anchor="w", padx=18, pady=(14, 8))
            body = tk.Frame(p, bg=T["panel"])
            body.pack(fill="x", padx=18)
            return body

        # Selection info
        s = section("การเลือก", first=True)
        self.info_title = tk.Label(s, text="", bg=T["panel"], fg=T["text"], font=self.f(11, "bold"),
                                   anchor="w")
        self.info_title.pack(fill="x")
        self.info_geo = tk.Label(s, text="", bg=T["panel"], fg=T["muted"], font=(self.mono, 9),
                                 anchor="w", justify="left")
        self.info_geo.pack(fill="x", pady=(4, 0))

        # Appearance
        s = section("ลักษณะ")

        def color_row(label, which):
            row = tk.Frame(s, bg=T["panel"])
            row.pack(fill="x", pady=4)
            sw = Swatch(row, 30, command=lambda: self.pick_color(which))
            sw.pack(side="left")
            col = tk.Frame(row, bg=T["panel"])
            col.pack(side="left", padx=10)
            tk.Label(col, text=label, bg=T["panel"], fg=T["text"], font=self.f(10)).pack(anchor="w")
            hx = tk.Label(col, text="", bg=T["panel"], fg=T["muted"], font=(self.mono, 9))
            hx.pack(anchor="w")
            FlatButton(row, "ไม่มี", lambda: self.set_color(which, None), font=self.f(9),
                       bg=T["panel2"], padx=9, pady=3).pack(side="right")
            return sw, hx

        self.fill_sw, self.fill_hex = color_row("สีพื้น", "fill")
        self.stroke_sw, self.stroke_hex = color_row("สีเส้น", "stroke")

        def slider(label, frm, to, cmd):
            row = tk.Frame(s, bg=T["panel"])
            row.pack(fill="x", pady=(10, 0))
            tk.Label(row, text=label, bg=T["panel"], fg=T["text"], font=self.f(10)).pack(side="left")
            val = tk.Label(row, text="", bg=T["panel"], fg=T["accent2"], font=(self.mono, 10, "bold"))
            val.pack(side="right")
            sc = tk.Scale(s, from_=frm, to=to, orient="horizontal", showvalue=False,
                          bg=T["accent"], fg=T["text"], troughcolor=T["panel2"],
                          activebackground=T["accent2"], highlightthickness=0, bd=0,
                          sliderrelief="flat", sliderlength=16, width=8, command=cmd)
            sc.pack(fill="x", pady=(4, 0))
            return sc, val

        self.width_sc, self.width_val = slider("ความหนาเส้น", 0, 40, self.on_width_change)
        self.size_sc, self.size_val = slider("ขนาดตัวอักษร", 8, 200, self.on_size_change)

        # Palette
        tk.Label(s, text="จานสี  ·  คลิกซ้าย = พื้น  ·  คลิกขวา = เส้น", bg=T["panel"],
                 fg=T["muted"], font=self.f(8)).pack(anchor="w", pady=(14, 6))
        grid = tk.Frame(s, bg=T["panel"])
        grid.pack(anchor="w")
        rbtn = "<Button-2>" if IS_MAC else "<Button-3>"
        for i, col in enumerate(PALETTE):
            cv = tk.Canvas(grid, width=26, height=26, bg=T["panel"], highlightthickness=0, cursor="hand2")
            cv.grid(row=i // 8, column=i % 8, padx=2, pady=2)
            cv.create_rectangle(2, 2, 24, 24, fill=col, outline=T["border"])
            cv.bind("<Button-1>", lambda e, c=col: self.set_color("fill", c))
            cv.bind(rbtn, lambda e, c=col: self.set_color("stroke", c))

        # Arrange
        s = section("จัดเรียง")
        g = tk.Frame(s, bg=T["panel"])
        g.pack(fill="x")
        for i, (txt, cmd, tip) in enumerate([
            ("⤒ หน้าสุด", self.bring_front, "Shift+]"), ("↑ ขึ้น", self.bring_forward, "]"),
            ("↓ ลง", self.send_backward, "["), ("⤓ หลังสุด", self.send_back, "Shift+["),
            ("⧉ ทำสำเนา", self.duplicate, "Ctrl+D"), ("✕ ลบ", self.delete_sel, "Delete"),
        ]):
            b = FlatButton(g, txt, cmd, font=self.f(9), bg=T["panel2"], padx=6, pady=6,
                           tooltip=tip, tip_font=self.f(9),
                           hover=("#3a1f2a" if "ลบ" in txt else None))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=1)

        # View
        s = section("มุมมอง")
        row = tk.Frame(s, bg=T["panel"])
        row.pack(fill="x")
        self.grid_btn = FlatButton(row, "▦ กริด", self.toggle_grid, font=self.f(9), bg=T["panel2"],
                                   padx=8, pady=6, tooltip="แสดง/ซ่อนกริด  (Ctrl+')", tip_font=self.f(9))
        self.grid_btn.pack(side="left", fill="x", expand=True, padx=2)
        self.snap_btn = FlatButton(row, "⌗ Snap", self.toggle_snap, font=self.f(9), bg=T["panel2"],
                                   padx=8, pady=6, tooltip="ยึดตามกริด  (Ctrl+;)", tip_font=self.f(9))
        self.snap_btn.pack(side="left", fill="x", expand=True, padx=2)

        tk.Label(p, text="Ctrl+ล้อเมาส์ = ซูม   ·   Space+ลาก = เลื่อน", bg=T["panel"],
                 fg=T["muted"], font=self.f(8)).pack(side="bottom", pady=12)

    # ── keyboard ─────────────────────────────────────────────────────────────
    def bind_keys(self):
        r = self.root
        mods = ["Control"] + (["Command"] if IS_MAC else [])

        def sc(key, fn):
            for m in mods:
                r.bind(f"<{m}-{key}>", lambda e: (fn(), "break")[1])

        sc("z", self.undo)
        sc("Z", self.redo)
        sc("y", self.redo)
        sc("c", self.copy_sel)
        sc("v", self.paste)
        sc("d", self.duplicate)
        sc("a", self.select_all)
        sc("s", self.save)
        sc("S", lambda: self.save(True))
        sc("o", self.open_doc)
        sc("n", self.new_doc)
        sc("e", self.export_svg)
        sc("0", self.zoom_fit)
        sc("1", lambda: self.set_zoom(1.0))
        sc("equal", lambda: self.zoom_center(1.2))
        sc("plus", lambda: self.zoom_center(1.2))
        sc("minus", lambda: self.zoom_center(1 / 1.2))
        sc("apostrophe", self.toggle_grid)
        sc("semicolon", self.toggle_snap)

        for item in TOOLS:
            if item:
                k = item[3].lower()
                r.bind(f"<KeyPress-{k}>", lambda e, t=item[0]: self.set_tool(t))
                r.bind(f"<KeyPress-{k.upper()}>", lambda e, t=item[0]: self.set_tool(t))

        r.bind("<Delete>", lambda e: self.delete_sel())
        r.bind("<BackSpace>", lambda e: self.delete_sel())
        r.bind("<Escape>", lambda e: self.on_escape())
        r.bind("<Return>", lambda e: self.finish_polygon())
        r.bind("<bracketright>", lambda e: self.bring_forward())
        r.bind("<bracketleft>", lambda e: self.send_backward())
        r.bind("<braceright>", lambda e: self.bring_front())
        r.bind("<braceleft>", lambda e: self.send_back())
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            r.bind(f"<{key}>", lambda e, a=dx, b=dy: self.nudge(a, b))
            r.bind(f"<Shift-{key}>", lambda e, a=dx, b=dy: self.nudge(a * 10, b * 10))
        r.bind("<KeyPress-space>", self._space_down)
        r.bind("<KeyRelease-space>", self._space_up)

    def _space_down(self, _e):
        if not self.space:
            self.space = True
            self.canvas.config(cursor="fleur")

    def _space_up(self, _e):
        self.space = False
        self.canvas.config(cursor=CURSORS.get(self.tool, "crosshair"))

    # ── tool handling ────────────────────────────────────────────────────────
    def set_tool(self, tool):
        if self.tool == "polygon" and tool != "polygon":
            self.finish_polygon()
        self.tool = tool
        for k, b in self.tool_buttons.items():
            b.set_active(k == tool)
        self.canvas.config(cursor=CURSORS.get(tool, "crosshair"))
        self.hover_id = None
        self.render()

    def on_escape(self):
        if self.poly_pts:
            self.poly_pts = []
        elif self.drag:
            self.drag, self.temp = None, None
        else:
            self.selected.clear()
            self.on_selection_changed()
        self.render()

    # ── history ──────────────────────────────────────────────────────────────
    def snapshot(self):
        return (copy.deepcopy(self.shapes), self.next_id)

    def push_undo(self, key=None):
        now = time.time()
        if key and key == self._last_key and now - self._last_t < 1.0:
            self._last_t = now
            return
        self._last_key, self._last_t = key, now
        self.undo_stack.append(self.snapshot())
        if len(self.undo_stack) > 200:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.set_dirty(True)

    def _restore(self, snap):
        self.shapes, self.next_id = copy.deepcopy(snap[0]), snap[1]
        ids = {s["id"] for s in self.shapes}
        self.selected &= ids
        self._last_key = None
        self.set_dirty(True)
        self.on_selection_changed()
        self.render()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.snapshot())
            self._restore(self.undo_stack.pop())
            self.flash("ย้อนกลับ")

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.snapshot())
            self._restore(self.redo_stack.pop())
            self.flash("ทำซ้ำ")

    def set_dirty(self, d):
        if self.dirty != d:
            self.dirty = d
            self.update_title()

    def update_title(self):
        name = os.path.basename(self.file_path) if self.file_path else "ไม่มีชื่อ"
        self.root.title(f"{'● ' if self.dirty else ''}{name} — Vectra")

    # ── geometry ─────────────────────────────────────────────────────────────
    def shape_bbox(self, s):
        if s["type"] == "text":
            b = self.canvas.bbox(f"s{s['id']}")
            if b:
                x0, y0 = self.to_world(b[0], b[1])
                x1, y1 = self.to_world(b[2], b[3])
                return (x0, y0, x1, y1)
            x, y = s["pts"]
            return (x, y, x + s["size"], y + s["size"])
        xs, ys = s["pts"][0::2], s["pts"][1::2]
        return (min(xs), min(ys), max(xs), max(ys))

    def selection_bbox(self):
        bbs = [self.shape_bbox(s) for s in self.selected_shapes()]
        if not bbs:
            return None
        return (min(b[0] for b in bbs), min(b[1] for b in bbs),
                max(b[2] for b in bbs), max(b[3] for b in bbs))

    @staticmethod
    def handle_points(x0, y0, x1, y1):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        return [(x0, y0), (mx, y0), (x1, y0), (x1, my), (x1, y1), (mx, y1), (x0, y1), (x0, my)]

    def handle_at(self, sx, sy):
        bb = self.selection_bbox()
        if not bb:
            return None
        sbb = self.to_screen(list(bb))
        for i, (hx, hy) in enumerate(self.handle_points(*sbb)):
            if abs(sx - hx) <= 7 and abs(sy - hy) <= 7:
                return i
        return None

    def hit(self, sx, sy):
        items = self.canvas.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)
        for it in reversed(items):
            for tag in self.canvas.gettags(it):
                if tag.startswith("s") and tag[1:].isdigit():
                    return int(tag[1:])
        return None

    # ── rendering ────────────────────────────────────────────────────────────
    def grid_step(self):
        g = GRID
        while g * self.zoom < 10:
            g *= 2
        while g * self.zoom > 60 and g > 1:
            g /= 2
        return g * self.zoom

    def render(self):
        c = self.canvas
        c.delete("all")
        W, H = max(1, c.winfo_width()), max(1, c.winfo_height())
        step = self.grid_step()

        # background grid
        if self.show_grid:
            x = self.ox % step
            while x < W:
                c.create_line(x, 0, x, H, fill=T["grid"])
                x += step
            y = self.oy % step
            while y < H:
                c.create_line(0, y, W, y, fill=T["grid"])
                y += step

        # artboard
        ax0, ay0, ax1, ay1 = self.to_screen(list(ARTBOARD))
        c.create_rectangle(ax0 + 5, ay0 + 8, ax1 + 5, ay1 + 8, fill=T["shadow"], outline="")
        c.create_rectangle(ax0, ay0, ax1, ay1, fill=T["board"], outline="")
        if self.show_grid:
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
        c.create_text(ax0, ay0 - 10, anchor="sw", fill=T["muted"], font=self.f(9),
                      text=f"Artboard   {ARTBOARD[2]} × {ARTBOARD[3]}")

        for s in self.shapes:
            self.draw_shape(s)
        if self.temp:
            self.draw_shape(self.temp, temp=True)
        self.draw_polygon_preview()
        self.draw_overlay()
        self.update_status()

    def draw_shape(self, s, temp=False):
        c = self.canvas
        pts = self.to_screen(s["pts"])
        z = self.zoom
        tags = ("temp",) if temp else ("shape", f"s{s['id']}")
        typ = s["type"]
        fill = s.get("fill") or ""
        stroke = s.get("stroke") or ""
        sw = s.get("width", 0)
        outline = stroke if (stroke and sw > 0) else ""
        w = max(1.0, sw * z) if outline else 0
        if typ == "rect":
            c.create_rectangle(*pts, fill=fill, outline=outline, width=w, tags=tags)
        elif typ == "ellipse":
            c.create_oval(*pts, fill=fill, outline=outline, width=w, tags=tags)
        elif typ in ("line", "pen"):
            if len(pts) == 2:
                pts = pts + pts
            col = stroke or fill or "#000000"
            c.create_line(*pts, fill=col, width=max(1.0, max(sw, 1) * z), capstyle="round",
                          joinstyle="round", smooth=(typ == "pen"), tags=tags)
        elif typ == "polygon":
            if len(pts) >= 6:
                c.create_polygon(*pts, fill=fill, outline=outline, width=w, joinstyle="round", tags=tags)
        elif typ == "text":
            size = -max(1, int(round(s.get("size", 24) * z)))
            c.create_text(pts[0], pts[1], text=s.get("text", ""), anchor="nw",
                          fill=fill or stroke or "#000000", font=(self.ui_font, size), tags=tags)

    def draw_polygon_preview(self):
        if self.tool != "polygon" or not self.poly_pts:
            return
        c = self.canvas
        pts = self.to_screen(self.poly_pts + list(self.cursor_w))
        if len(pts) >= 6 and self.fill:
            c.create_polygon(*pts, fill=self.fill, outline="", stipple="gray50" if not IS_MAC else "")
        c.create_line(*pts, fill=T["accent"], width=2, dash=(4, 3))
        sp = self.to_screen(self.poly_pts)
        for i in range(0, len(sp), 2):
            r = 6 if i == 0 else 4
            c.create_oval(sp[i] - r, sp[i + 1] - r, sp[i] + r, sp[i + 1] + r,
                          fill="#ffffff", outline=T["accent"], width=2)

    def draw_overlay(self):
        c = self.canvas
        acc = T["accent"]
        if (self.tool == "select" and self.hover_id and self.hover_id not in self.selected
                and not self.drag):
            s = self.by_id(self.hover_id)
            if s:
                b = self.to_screen(list(self.shape_bbox(s)))
                c.create_rectangle(b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2, outline=T["accent2"], width=1)

        if self.selected and self.tool == "select":
            multi = len(self.selected) > 1
            if multi:
                for s in self.selected_shapes():
                    b = self.to_screen(list(self.shape_bbox(s)))
                    c.create_rectangle(*b, outline=T["accent2"], dash=(3, 3))
            bb = self.selection_bbox()
            sb = self.to_screen(list(bb))
            x0, y0, x1, y1 = sb[0] - 1, sb[1] - 1, sb[2] + 1, sb[3] + 1
            c.create_rectangle(x0, y0, x1, y1, outline=acc, width=1.5)
            if not (self.drag and self.drag["mode"] == "move"):
                for hx, hy in self.handle_points(x0, y0, x1, y1):
                    c.create_rectangle(hx - 4, hy - 4, hx + 4, hy + 4, fill="#ffffff", outline=acc, width=1.5)
            # size pill
            label = f"{bb[2] - bb[0]:.0f} × {bb[3] - bb[1]:.0f}"
            tid = c.create_text((x0 + x1) / 2, y1 + 18, text=label, fill="#ffffff", font=(self.mono, 9))
            tb = c.bbox(tid)
            pill = c.create_rectangle(tb[0] - 7, tb[1] - 3, tb[2] + 7, tb[3] + 3, fill=acc, outline="")
            c.tag_lower(pill, tid)

        if self.drag and self.drag["mode"] == "marquee":
            (sx, sy), (ex, ey) = self.drag["start"], self.drag["cur"]
            c.create_rectangle(sx, sy, ex, ey, outline=acc, dash=(4, 3), width=1)

    def update_status(self):
        self.status_l.config(text=HINTS.get(self.tool, ""))
        x, y = self.cursor_w
        self.status_r.config(text=f"X {x:7.1f}   Y {y:7.1f}    │   {len(self.shapes)} วัตถุ")
        self.zoom_lbl.config(text=f"{self.zoom * 100:.0f}%")

    def flash(self, msg):
        self.status_l.config(text=f"✓  {msg}", fg=T["accent2"])
        if self._flash_job:
            self.root.after_cancel(self._flash_job)

        def back():
            self._flash_job = None
            self.status_l.config(fg=T["muted"], text=HINTS.get(self.tool, ""))
        self._flash_job = self.root.after(1600, back)

    # ── mouse ────────────────────────────────────────────────────────────────
    def on_motion(self, e):
        self.cursor_w = self.to_world(e.x, e.y)
        if self.tool == "polygon" and self.poly_pts:
            self.cursor_w = (self.snapv(self.cursor_w[0]), self.snapv(self.cursor_w[1]))
            self.render()
            return
        if self.tool == "select" and not self.space:
            h = self.handle_at(e.x, e.y) if self.selected else None
            if h is not None:
                self.canvas.config(cursor="sizing")
                self._set_hover(None)
            else:
                sid = self.hit(e.x, e.y)
                self.canvas.config(cursor="fleur" if sid else "arrow")
                self._set_hover(sid)
        x, y = self.cursor_w
        self.status_r.config(text=f"X {x:7.1f}   Y {y:7.1f}    │   {len(self.shapes)} วัตถุ")

    def _set_hover(self, sid):
        if sid != self.hover_id:
            self.hover_id = sid
            self.render()

    def pan_start(self, e):
        self.drag = {"mode": "pan", "last": (e.x, e.y)}
        self.canvas.config(cursor="fleur")

    def pan_move(self, e):
        if self.drag and self.drag["mode"] == "pan":
            lx, ly = self.drag["last"]
            self.ox += e.x - lx
            self.oy += e.y - ly
            self.drag["last"] = (e.x, e.y)
            self.render()

    def _end_pan(self):
        self.drag = None
        self.canvas.config(cursor="fleur" if self.space else CURSORS.get(self.tool, "crosshair"))

    def orig_pts(self):
        return {s["id"]: list(s["pts"]) for s in self.selected_shapes()}

    def on_press(self, e):
        self.canvas.focus_set()
        if self.space or self.tool == "hand":
            self.pan_start(e)
            return
        wx, wy = self.to_world(e.x, e.y)
        sx, sy = self.snapv(wx), self.snapv(wy)
        t = self.tool
        shift = bool(e.state & 0x1)

        if t == "select":
            h = self.handle_at(e.x, e.y)
            if h is not None:
                self.drag = {"mode": "resize", "h": h, "bbox": self.selection_bbox(),
                             "orig": self.orig_pts(), "changed": False}
                return
            sid = self.hit(e.x, e.y)
            if sid:
                if shift:
                    self.selected ^= {sid}
                elif sid not in self.selected:
                    self.selected = {sid}
                self.drag = {"mode": "move", "start": (wx, wy), "orig": self.orig_pts(), "changed": False}
            else:
                if not shift:
                    self.selected = set()
                self.drag = {"mode": "marquee", "start": (e.x, e.y), "cur": (e.x, e.y),
                             "base": set(self.selected)}
            self.on_selection_changed()
            self.render()

        elif t in ("rect", "ellipse", "line"):
            self.drag = {"mode": "draw", "start": (sx, sy)}
            self.temp = self.new_shape(t, [sx, sy, sx, sy])
        elif t == "pen":
            self.drag = {"mode": "pen"}
            self.temp = self.new_shape("pen", [wx, wy])
        elif t == "polygon":
            if len(self.poly_pts) >= 6:
                fx, fy = self.to_screen(self.poly_pts[:2])
                if math.hypot(e.x - fx, e.y - fy) < 9:
                    self.finish_polygon()
                    return
            self.poly_pts += [sx, sy]
            self.cursor_w = (sx, sy)
            self.render()
        elif t == "text":
            self.add_text(sx, sy)

    def on_drag(self, e):
        d = self.drag
        if not d:
            return
        if d["mode"] == "pan":
            self.pan_move(e)
            return
        wx, wy = self.to_world(e.x, e.y)
        self.cursor_w = (wx, wy)
        shift = bool(e.state & 0x1)
        mode = d["mode"]

        if mode == "move":
            dx, dy = wx - d["start"][0], wy - d["start"][1]
            if self.snap:
                dx, dy = round(dx / GRID) * GRID, round(dy / GRID) * GRID
            if shift:  # constrain to axis
                if abs(dx) > abs(dy):
                    dy = 0
                else:
                    dx = 0
            if not d["changed"] and (dx or dy):
                self.push_undo()
                d["changed"] = True
            for sid, orig in d["orig"].items():
                s = self.by_id(sid)
                s["pts"] = [v + (dx if i % 2 == 0 else dy) for i, v in enumerate(orig)]

        elif mode == "resize":
            self.do_resize(d, self.snapv(wx), self.snapv(wy), shift)

        elif mode == "marquee":
            d["cur"] = (e.x, e.y)

        elif mode == "draw":
            x0, y0 = d["start"]
            x1, y1 = self.snapv(wx), self.snapv(wy)
            if shift:
                if self.temp["type"] == "line":
                    ang = math.atan2(y1 - y0, x1 - x0)
                    ang = round(ang / (math.pi / 4)) * (math.pi / 4)
                    ln = math.hypot(x1 - x0, y1 - y0)
                    x1, y1 = x0 + ln * math.cos(ang), y0 + ln * math.sin(ang)
                else:
                    m = max(abs(x1 - x0), abs(y1 - y0))
                    x1 = x0 + math.copysign(m, (x1 - x0) or 1)
                    y1 = y0 + math.copysign(m, (y1 - y0) or 1)
            self.temp["pts"] = [x0, y0, x1, y1]

        elif mode == "pen":
            lx, ly = self.temp["pts"][-2:]
            if math.hypot(wx - lx, wy - ly) * self.zoom > 2:
                self.temp["pts"] += [wx, wy]
        self.render()

    def do_resize(self, d, wx, wy, keep_ratio):
        h = d["h"]
        bx0, by0, bx1, by1 = d["bbox"]
        bw, bh = bx1 - bx0, by1 - by0
        left, right = h in (0, 6, 7), h in (2, 3, 4)
        top, bottom = h in (0, 1, 2), h in (4, 5, 6)
        nx0, ny0, nx1, ny1 = bx0, by0, bx1, by1
        if left:
            nx0 = wx
        if right:
            nx1 = wx
        if top:
            ny0 = wy
        if bottom:
            ny1 = wy
        if keep_ratio and h in (0, 2, 4, 6) and bw and bh:
            nw, nh = nx1 - nx0, ny1 - ny0
            k = max(abs(nw) / bw, abs(nh) / bh)
            nw2 = math.copysign(bw * k, nw or 1)
            nh2 = math.copysign(bh * k, nh or 1)
            if left:
                nx0 = nx1 - nw2
            else:
                nx1 = nx0 + nw2
            if top:
                ny0 = ny1 - nh2
            else:
                ny1 = ny0 + nh2
        kx = (nx1 - nx0) / bw if bw else 1
        ky = (ny1 - ny0) / bh if bh else 1
        if not d["changed"]:
            self.push_undo()
            d["changed"] = True
        for sid, orig in d["orig"].items():
            s = self.by_id(sid)
            s["pts"] = [(nx0 + (v - bx0) * kx) if i % 2 == 0 else (ny0 + (v - by0) * ky)
                        for i, v in enumerate(orig)]

    def on_release(self, e):
        d = self.drag
        if not d:
            return
        mode = d["mode"]
        if mode == "pan":
            self._end_pan()
            return
        if mode == "marquee":
            (sx, sy), (ex, ey) = d["start"], d["cur"]
            if abs(ex - sx) > 2 or abs(ey - sy) > 2:
                x0, y0 = self.to_world(min(sx, ex), min(sy, ey))
                x1, y1 = self.to_world(max(sx, ex), max(sy, ey))
                hits = set()
                for s in self.shapes:
                    b = self.shape_bbox(s)
                    if b[0] <= x1 and b[2] >= x0 and b[1] <= y1 and b[3] >= y0:
                        hits.add(s["id"])
                self.selected = d["base"] | hits
        elif mode == "draw":
            x0, y0, x1, y1 = self.temp["pts"]
            tiny = math.hypot(x1 - x0, y1 - y0) * self.zoom < 4
            if tiny and self.temp["type"] in ("rect", "ellipse"):
                self.temp["pts"] = [x0 - 60, y0 - 60, x0 + 60, y0 + 60]
                tiny = False
            if not tiny:
                self.add_shape(self.temp)
        elif mode == "pen":
            if len(self.temp["pts"]) >= 4:
                self.add_shape(self.temp)
        self.drag, self.temp = None, None
        self.on_selection_changed()
        self.render()

    def on_double(self, e):
        if self.tool == "polygon":
            # the second press of the double-click already added a duplicate point
            if len(self.poly_pts) >= 4 and self.poly_pts[-2:] == self.poly_pts[-4:-2]:
                self.poly_pts = self.poly_pts[:-2]
            self.finish_polygon()
        elif self.tool == "select":
            sid = self.hit(e.x, e.y)
            s = self.by_id(sid) if sid else None
            if s and s["type"] == "text":
                self.drag = None
                txt = simpledialog.askstring("แก้ไขข้อความ", "ข้อความ:", initialvalue=s["text"],
                                             parent=self.root)
                if txt:
                    self.push_undo()
                    s["text"] = txt
                    self.render()

    def on_wheel(self, e, horizontal=False, zoom=False):
        delta = e.delta
        if not IS_MAC:
            delta = delta / 120
        if zoom:
            self.zoom_at(1.1 ** delta, e.x, e.y)
            return
        amount = delta * (12 if IS_MAC else 40)
        if horizontal:
            self.ox += amount
        else:
            self.oy += amount
        self.render()

    def on_wheel_linux(self, e, direction):
        if e.state & 0x4:
            self.zoom_at(1.1 ** direction, e.x, e.y)
        elif e.state & 0x1:
            self.ox += direction * 40
            self.render()
        else:
            self.oy += direction * 40
            self.render()

    def context_menu(self, e):
        sid = self.hit(e.x, e.y)
        if sid and sid not in self.selected:
            self.selected = {sid}
            self.on_selection_changed()
            self.render()
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    # ── zoom ─────────────────────────────────────────────────────────────────
    def zoom_at(self, factor, sx, sy):
        wx, wy = self.to_world(sx, sy)
        self.zoom = min(16.0, max(0.05, self.zoom * factor))
        self.ox = sx - wx * self.zoom
        self.oy = sy - wy * self.zoom
        self.render()

    def zoom_center(self, factor):
        c = self.canvas
        self.zoom_at(factor, c.winfo_width() / 2, c.winfo_height() / 2)

    def set_zoom(self, z):
        self.zoom_center(z / self.zoom)

    def zoom_fit(self):
        c = self.canvas
        W, H = c.winfo_width(), c.winfo_height()
        if W < 10 or H < 10:
            return
        aw, ah = ARTBOARD[2] - ARTBOARD[0], ARTBOARD[3] - ARTBOARD[1]
        self.zoom = min((W - 120) / aw, (H - 120) / ah)
        self.ox = (W - aw * self.zoom) / 2 - ARTBOARD[0] * self.zoom
        self.oy = (H - ah * self.zoom) / 2 - ARTBOARD[1] * self.zoom
        self.render()

    # ── shapes ───────────────────────────────────────────────────────────────
    def new_shape(self, typ, pts):
        s = {"id": 0, "type": typ, "pts": pts, "fill": self.fill, "stroke": self.stroke,
             "width": self.width}
        if typ in ("line", "pen"):
            s["fill"] = None
            s["stroke"] = self.stroke or self.fill or "#000000"
            s["width"] = max(1, self.width)
        if typ == "text":
            s["fill"] = self.fill or self.stroke or "#000000"
            s["stroke"] = None
            s["width"] = 0
            s["size"] = self.font_size
            s["text"] = ""
        return s

    def add_shape(self, s):
        self.push_undo()
        s = copy.deepcopy(s)
        s["id"] = self.next_id
        self.next_id += 1
        self.shapes.append(s)
        self.selected = {s["id"]}
        return s

    def finish_polygon(self):
        pts = self.poly_pts
        self.poly_pts = []
        if len(pts) >= 6:
            self.add_shape(self.new_shape("polygon", pts))
            self.on_selection_changed()
        elif len(pts) == 4:
            self.add_shape(self.new_shape("line", pts))
            self.on_selection_changed()
        self.render()

    def add_text(self, x, y):
        txt = simpledialog.askstring("ข้อความ", "พิมพ์ข้อความ:", parent=self.root)
        if txt:
            s = self.new_shape("text", [x, y])
            s["text"] = txt
            self.add_shape(s)
            self.on_selection_changed()
            self.render()

    # ── edit commands ────────────────────────────────────────────────────────
    def delete_sel(self):
        if not self.selected:
            return
        self.push_undo()
        self.shapes = [s for s in self.shapes if s["id"] not in self.selected]
        self.selected.clear()
        self.on_selection_changed()
        self.render()

    def select_all(self):
        self.set_tool("select")
        self.selected = {s["id"] for s in self.shapes}
        self.on_selection_changed()
        self.render()

    def _insert_copies(self, items, offset):
        self.push_undo()
        new_ids = set()
        for s in items:
            n = copy.deepcopy(s)
            n["id"] = self.next_id
            self.next_id += 1
            n["pts"] = [v + offset for v in n["pts"]]
            self.shapes.append(n)
            new_ids.add(n["id"])
        self.selected = new_ids
        self.on_selection_changed()
        self.render()

    def duplicate(self):
        if self.selected:
            self._insert_copies(self.selected_shapes(), 16)
            self.flash("ทำสำเนาแล้ว")

    def copy_sel(self):
        if self.selected:
            self.clipboard = copy.deepcopy(self.selected_shapes())
            self.flash(f"คัดลอก {len(self.clipboard)} วัตถุ")

    def paste(self):
        if self.clipboard:
            self._insert_copies(self.clipboard, 20)
            self.clipboard = copy.deepcopy(self.selected_shapes())  # cascade next paste

    def nudge(self, dx, dy):
        if not self.selected:
            return
        self.push_undo("nudge")
        for s in self.selected_shapes():
            s["pts"] = [v + (dx if i % 2 == 0 else dy) for i, v in enumerate(s["pts"])]
        self.render()

    def bring_front(self):
        if self.selected:
            self.push_undo()
            self.shapes = ([s for s in self.shapes if s["id"] not in self.selected]
                           + self.selected_shapes())
            self.render()

    def send_back(self):
        if self.selected:
            self.push_undo()
            self.shapes = (self.selected_shapes()
                           + [s for s in self.shapes if s["id"] not in self.selected])
            self.render()

    def bring_forward(self):
        if not self.selected:
            return
        self.push_undo()
        sh = self.shapes
        for i in range(len(sh) - 2, -1, -1):
            if sh[i]["id"] in self.selected and sh[i + 1]["id"] not in self.selected:
                sh[i], sh[i + 1] = sh[i + 1], sh[i]
        self.render()

    def send_backward(self):
        if not self.selected:
            return
        self.push_undo()
        sh = self.shapes
        for i in range(1, len(sh)):
            if sh[i]["id"] in self.selected and sh[i - 1]["id"] not in self.selected:
                sh[i], sh[i - 1] = sh[i - 1], sh[i]
        self.render()

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.refresh_panel()
        self.render()

    def toggle_snap(self):
        self.snap = not self.snap
        self.refresh_panel()
        self.flash("เปิด Snap" if self.snap else "ปิด Snap")

    # ── properties ───────────────────────────────────────────────────────────
    def on_selection_changed(self):
        sel = self.selected_shapes()
        if sel:
            s = sel[0]
            if s["type"] == "text":
                self.fill = s.get("fill")
                self.font_size = s.get("size", self.font_size)
            else:
                self.fill = s.get("fill") if s["type"] not in ("line", "pen") else self.fill
                self.stroke = s.get("stroke")
                self.width = s.get("width", self.width)
        self.refresh_panel()

    def refresh_panel(self):
        self.fill_sw.set(self.fill)
        self.stroke_sw.set(self.stroke)
        self.fill_hex.config(text=(self.fill or "ไม่มี").upper())
        self.stroke_hex.config(text=(self.stroke or "ไม่มี").upper())
        self.width_sc.set(self.width)
        self.width_val.config(text=f"{self.width}px")
        self.size_sc.set(self.font_size)
        self.size_val.config(text=f"{self.font_size}px")
        self.grid_btn.set_active(self.show_grid)
        self.snap_btn.set_active(self.snap)

        sel = self.selected_shapes()
        if not sel:
            self.info_title.config(text="ไม่ได้เลือกวัตถุ")
            self.info_geo.config(text="ค่าด้านล่างจะใช้กับวัตถุที่วาดใหม่")
        else:
            if len(sel) == 1:
                title = TYPE_TH.get(sel[0]["type"], sel[0]["type"])
                if sel[0]["type"] == "text":
                    t = sel[0]["text"]
                    title += f' · "{t[:14]}{"…" if len(t) > 14 else ""}"'
            else:
                title = f"เลือก {len(sel)} วัตถุ"
            self.info_title.config(text=title)
            self.root.after_idle(self._refresh_geo)

    def _refresh_geo(self):
        bb = self.selection_bbox()
        if bb:
            self.info_geo.config(text=f"X {bb[0]:.0f}   Y {bb[1]:.0f}\n"
                                      f"W {bb[2] - bb[0]:.0f}   H {bb[3] - bb[1]:.0f}")

    def apply_prop(self, prop, value, key=None):
        targets = self.selected_shapes()
        if prop == "size":
            targets = [s for s in targets if s["type"] == "text"]
        elif prop == "width":
            targets = [s for s in targets if s["type"] != "text"]
        elif prop == "fill":
            targets = [s for s in targets if s["type"] not in ("line", "pen")]
        elif prop == "stroke":
            targets = [s for s in targets if s["type"] != "text"]
        if prop == "fill" and value is None:
            targets = [s for s in targets if s["type"] != "text"]
        targets = [s for s in targets if s.get(prop) != value]
        if not targets:
            return
        self.push_undo(key)
        for s in targets:
            s[prop] = value
            if s["type"] in ("line", "pen") and prop == "width":
                s["width"] = max(1, value)
        self.render()

    def pick_color(self, which):
        cur = getattr(self, which) or "#ffffff"
        res = colorchooser.askcolor(color=cur, parent=self.root,
                                    title="เลือกสีพื้น" if which == "fill" else "เลือกสีเส้น")
        if res and res[1]:
            self.set_color(which, res[1])

    def set_color(self, which, color):
        setattr(self, which, color)
        self.apply_prop(which, color)
        self.refresh_panel()

    def on_width_change(self, v):
        v = int(float(v))
        self.width_val.config(text=f"{v}px")
        if v == self.width:
            return
        self.width = v
        self.apply_prop("width", v, key="width")

    def on_size_change(self, v):
        v = int(float(v))
        self.size_val.config(text=f"{v}px")
        if v == self.font_size:
            return
        self.font_size = v
        self.apply_prop("size", v, key="size")
        self.root.after_idle(self._refresh_geo)

    # ── files ────────────────────────────────────────────────────────────────
    def confirm_discard(self):
        if not self.dirty or not self.shapes:
            return True
        r = messagebox.askyesnocancel("บันทึกงาน?",
                                      "มีการแก้ไขที่ยังไม่ได้บันทึก\nต้องการบันทึกก่อนหรือไม่?",
                                      parent=self.root)
        if r is None:
            return False
        if r:
            return self.save()
        return True

    def new_doc(self):
        if not self.confirm_discard():
            return
        self.shapes, self.selected = [], set()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.next_id = 1
        self.file_path = None
        self.dirty = False
        self.update_title()
        self.on_selection_changed()
        self.zoom_fit()

    def save(self, save_as=False):
        if save_as or not self.file_path:
            p = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
                                             filetypes=[("Vectra drawing (JSON)", "*.json")],
                                             title="บันทึกงาน")
            if not p:
                return False
            self.file_path = p
        data = {"app": "vectra", "version": 1, "artboard": list(ARTBOARD), "shapes": self.shapes}
        try:
            with open(self.file_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)
        except OSError as ex:
            messagebox.showerror("บันทึกไม่สำเร็จ", str(ex), parent=self.root)
            return False
        self.dirty = False
        self.update_title()
        self.flash(f"บันทึกแล้ว: {os.path.basename(self.file_path)}")
        return True

    def open_doc(self):
        if not self.confirm_discard():
            return
        p = filedialog.askopenfilename(parent=self.root, title="เปิดงาน",
                                       filetypes=[("Vectra drawing (JSON)", "*.json"), ("ทุกไฟล์", "*.*")])
        if not p:
            return
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            shapes = data["shapes"]
            for s in shapes:
                assert s["type"] in TYPE_TH and isinstance(s["pts"], list)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("เปิดไฟล์ไม่สำเร็จ", f"ไฟล์ไม่ถูกต้อง\n{ex}", parent=self.root)
            return
        self.shapes = shapes
        self.next_id = max([s["id"] for s in shapes], default=0) + 1
        self.selected = set()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.file_path = p
        self.dirty = False
        self.update_title()
        self.on_selection_changed()
        self.zoom_fit()
        self.flash(f"เปิด {os.path.basename(p)}")

    def export_svg(self, path=None):
        if path is None:
            path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".svg",
                                                filetypes=[("SVG", "*.svg")], title="ส่งออก SVG")
            if not path:
                return
        x0, y0, x1, y1 = ARTBOARD
        out = ['<?xml version="1.0" encoding="UTF-8"?>',
               f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0}" height="{y1 - y0}" '
               f'viewBox="{x0} {y0} {x1 - x0} {y1 - y0}">',
               f'  <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="#ffffff"/>']
        for s in self.shapes:
            out.append("  " + self.shape_svg(s))
        out.append("</svg>")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))
        self.flash(f"ส่งออก SVG แล้ว: {os.path.basename(path)}")

    def shape_svg(self, s):
        def n(v):
            return f"{v:.2f}".rstrip("0").rstrip(".")
        p = s["pts"]
        fill = s.get("fill") or "none"
        stroke = s.get("stroke") or "none"
        w = s.get("width", 0)
        if not w:
            stroke = "none"
        paint = f'fill="{fill}" stroke="{stroke}" stroke-width="{n(w)}" stroke-linejoin="round"'
        t = s["type"]
        if t == "rect":
            x, y = min(p[0], p[2]), min(p[1], p[3])
            return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(abs(p[2] - p[0]))}" '
                    f'height="{n(abs(p[3] - p[1]))}" {paint}/>')
        if t == "ellipse":
            return (f'<ellipse cx="{n((p[0] + p[2]) / 2)}" cy="{n((p[1] + p[3]) / 2)}" '
                    f'rx="{n(abs(p[2] - p[0]) / 2)}" ry="{n(abs(p[3] - p[1]) / 2)}" {paint}/>')
        if t in ("line", "pen"):
            col = s.get("stroke") or s.get("fill") or "#000000"
            lp = f'fill="none" stroke="{col}" stroke-width="{n(max(1, w))}" stroke-linecap="round" stroke-linejoin="round"'
            if t == "line":
                return f'<line x1="{n(p[0])}" y1="{n(p[1])}" x2="{n(p[2])}" y2="{n(p[3])}" {lp}/>'
            pts = list(zip(p[0::2], p[1::2]))
            d = [f"M{n(pts[0][0])},{n(pts[0][1])}"]
            for i in range(1, len(pts) - 1):
                mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
                d.append(f"Q{n(pts[i][0])},{n(pts[i][1])} {n(mx)},{n(my)}")
            d.append(f"L{n(pts[-1][0])},{n(pts[-1][1])}")
            return f'<path d="{" ".join(d)}" {lp}/>'
        if t == "polygon":
            pts = " ".join(f"{n(x)},{n(y)}" for x, y in zip(p[0::2], p[1::2]))
            return f'<polygon points="{pts}" {paint}/>'
        if t == "text":
            col = s.get("fill") or s.get("stroke") or "#000000"
            return (f'<text x="{n(p[0])}" y="{n(p[1])}" font-family="{escape(self.ui_font)}, sans-serif" '
                    f'font-size="{n(s.get("size", 24))}" fill="{col}" dominant-baseline="text-before-edge">'
                    f'{escape(s.get("text", ""))}</text>')
        return ""

    def on_close(self):
        if self.confirm_discard():
            self.root.destroy()


def main():
    try:  # crisp rendering on Windows HiDPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    root = tk.Tk()
    VectorEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
