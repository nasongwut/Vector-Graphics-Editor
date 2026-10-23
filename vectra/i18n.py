"""Bilingual UI strings (Thai / English).

Usage::

    from vectra.i18n import tr
    tr("m_save")                   # -> "บันทึก" or "Save"
    tr("flash_copied", n=3)        # -> "คัดลอก 3 วัตถุ" / "Copied 3 objects"

Add a string by adding one entry to ``STRINGS``: ``key: (thai, english)``.
"""

LANGUAGES = {"th": "ไทย", "en": "English"}
DEFAULT_LANGUAGE = "th"
_ORDER = ("th", "en")

_current = DEFAULT_LANGUAGE

STRINGS = {
    # ── general ────────────────────────────────────────────────────────────
    "untitled": ("ไม่มีชื่อ-1", "Untitled-1"),
    "ok": ("ตกลง", "OK"),
    "cancel": ("ยกเลิก", "Cancel"),
    "copy": ("คัดลอก", "Copy"),
    "none": ("ไม่มี", "None"),
    "width": ("กว้าง", "Width"),
    "height": ("สูง", "Height"),
    "radius": ("รัศมี", "Radius"),
    "radius1": ("รัศมี 1 (นอก)", "Radius 1"),
    "radius2": ("รัศมี 2 (ใน)", "Radius 2"),
    "sides": ("จำนวนด้าน", "Sides"),
    "points": ("จำนวนแฉก", "Points"),
    "length": ("ความยาว", "Length"),
    "angle": ("มุม (°)", "Angle (°)"),
    "horizontal": ("แนวนอน", "Horizontal"),
    "vertical": ("แนวตั้ง", "Vertical"),
    "scale_h": ("แนวนอน (%)", "Horizontal (%)"),
    "scale_v": ("แนวตั้ง (%)", "Vertical (%)"),
    "axis_angle": ("มุมแกน (°)", "Axis angle (°)"),
    "note_angle": ("ค่าบวก = หมุนทวนเข็มนาฬิกา", "Positive = counter-clockwise"),
    "note_reflect": ("90° = แกนตั้ง (พลิกซ้าย-ขวา) · 0° = แกนนอน (พลิกบน-ล่าง)",
                     "90° = vertical axis (left-right) · 0° = horizontal axis (top-bottom)"),
    "need_selection": ("เลือกวัตถุก่อน", "Select an object first"),
    "mode_preview": ("Preview", "Preview"),
    "mode_outline": ("Outline", "Outline"),
    "artboard_name": ("Artboard {n}", "Artboard {n}"),
    "tip_lang": ("เปลี่ยนภาษา / Switch language", "Switch language / เปลี่ยนภาษา"),
    "tip_zoom_field": ("พิมพ์ % แล้วกด Enter", "Type a % and press Enter"),
    "measure_info": ("ระยะ {d:.1f}  ·  W {w:.1f}  H {h:.1f}  ·  มุม {a:.1f}°",
                     "D {d:.1f}  ·  W {w:.1f}  H {h:.1f}  ·  Angle {a:.1f}°"),
    "about_text": ("{app} 3.0\n\nโปรแกรมวาดภาพเวกเตอร์ด้วย Python + Tkinter\n"
                   "หน้าตาและการใช้งานแบบโปรแกรมออกแบบมืออาชีพ\n\n"
                   "ไม่มีส่วนเกี่ยวข้องกับ Adobe — เป็นโปรแกรมอิสระ\n\nกด F1 เพื่อดูคีย์ลัดทั้งหมด",
                   "{app} 3.0\n\nA vector graphics editor in Python + Tkinter\n"
                   "with a professional design-app workflow.\n\n"
                   "Independent project — not affiliated with Adobe.\n\nPress F1 for all shortcuts."),

    # ── menus ──────────────────────────────────────────────────────────────
    "menu_file": ("ไฟล์", "File"),
    "menu_edit": ("แก้ไข", "Edit"),
    "menu_object": ("วัตถุ", "Object"),
    "menu_type": ("ตัวอักษร", "Type"),
    "menu_select": ("เลือก", "Select"),
    "menu_view": ("มุมมอง", "View"),
    "menu_window": ("หน้าต่าง", "Window"),
    "menu_help": ("ช่วยเหลือ", "Help"),

    "m_new": ("ใหม่…", "New…"),
    "m_open": ("เปิด…", "Open…"),
    "m_save": ("บันทึก", "Save"),
    "m_save_as": ("บันทึกเป็น…", "Save As…"),
    "m_export_svg": ("ส่งออก SVG…", "Export SVG…"),
    "m_document_setup": ("ตั้งค่าเอกสาร…", "Document Setup…"),
    "m_exit": ("ออก", "Exit"),
    "m_undo": ("ย้อนกลับ", "Undo"),
    "m_redo": ("ทำซ้ำ", "Redo"),
    "m_cut": ("ตัด", "Cut"),
    "m_copy": ("คัดลอก", "Copy"),
    "m_paste": ("วาง", "Paste"),
    "m_paste_front": ("วางด้านหน้า", "Paste in Front"),
    "m_paste_back": ("วางด้านหลัง", "Paste in Back"),
    "m_paste_place": ("วางที่ตำแหน่งเดิม", "Paste in Place"),
    "m_clear": ("ลบ", "Clear"),
    "m_duplicate": ("ทำสำเนา", "Duplicate"),
    "m_language": ("ภาษา (Language)", "Language (ภาษา)"),
    "m_transform": ("แปลงรูป", "Transform"),
    "m_transform_again": ("แปลงรูปซ้ำ", "Transform Again"),
    "m_move": ("ย้าย…", "Move…"),
    "m_rotate": ("หมุน…", "Rotate…"),
    "m_reflect": ("สะท้อน…", "Reflect…"),
    "m_scale": ("ย่อ/ขยาย…", "Scale…"),
    "m_flip_h": ("พลิกแนวนอน", "Flip Horizontal"),
    "m_flip_v": ("พลิกแนวตั้ง", "Flip Vertical"),
    "m_arrange": ("จัดลำดับ", "Arrange"),
    "m_bring_front": ("ไว้หน้าสุด", "Bring to Front"),
    "m_bring_forward": ("ขึ้นหน้า 1 ชั้น", "Bring Forward"),
    "m_send_backward": ("ถอยหลัง 1 ชั้น", "Send Backward"),
    "m_send_back": ("ไว้หลังสุด", "Send to Back"),
    "m_align": ("จัดแนว", "Align"),
    "m_distribute_h": ("กระจายแนวนอน", "Distribute Horizontally"),
    "m_distribute_v": ("กระจายแนวตั้ง", "Distribute Vertically"),
    "m_group": ("จัดกลุ่ม", "Group"),
    "m_ungroup": ("แยกกลุ่ม", "Ungroup"),
    "m_lock": ("ล็อกที่เลือก", "Lock Selection"),
    "m_unlock_all": ("ปลดล็อกทั้งหมด", "Unlock All"),
    "m_hide": ("ซ่อนที่เลือก", "Hide Selection"),
    "m_show_all": ("แสดงทั้งหมด", "Show All"),
    "m_path": ("พาธ", "Path"),
    "m_join": ("เชื่อม (Join)", "Join"),
    "m_close_path": ("ปิดพาธ", "Close Path"),
    "m_reverse_path": ("กลับทิศพาธ", "Reverse Path Direction"),
    "m_convert_path": ("แปลงเป็นพาธ", "Convert to Path"),
    "m_fit_artboard_art": ("ปรับ Artboard ให้พอดีงาน", "Fit Artboard to Artwork Bounds"),
    "m_font_size": ("ขนาดตัวอักษร", "Size"),
    "m_character": ("แผงตัวอักษร", "Character Panel"),
    "m_edit_text": ("แก้ไขข้อความ", "Edit Text"),
    "m_select_all": ("เลือกทั้งหมด", "All"),
    "m_deselect": ("ยกเลิกการเลือก", "Deselect"),
    "m_inverse": ("กลับการเลือก", "Inverse"),
    "m_same": ("เหมือนกัน", "Same"),
    "same_fill": ("สีพื้นเดียวกัน", "Fill Color"),
    "same_stroke": ("สีเส้นเดียวกัน", "Stroke Color"),
    "same_width": ("ความหนาเส้นเดียวกัน", "Stroke Weight"),
    "same_type": ("ชนิดวัตถุเดียวกัน", "Object Type"),
    "m_outline": ("โหมดเส้นโครง (Outline)", "Outline"),
    "m_zoom_in": ("ซูมเข้า", "Zoom In"),
    "m_zoom_out": ("ซูมออก", "Zoom Out"),
    "m_fit_artboard": ("พอดีหน้าต่าง", "Fit Artboard in Window"),
    "m_actual_size": ("ขนาดจริง 100%", "Actual Size"),
    "m_rulers": ("ไม้บรรทัด", "Rulers"),
    "m_smart_guides": ("Smart Guides", "Smart Guides"),
    "m_grid": ("กริด", "Grid"),
    "m_snap_grid": ("ยึดตามกริด", "Snap to Grid"),
    "m_win_tools": ("แถบเครื่องมือ", "Tools"),
    "m_win_control": ("Control bar", "Control"),
    "m_hide_panels": ("ซ่อน/แสดงพาเนลทั้งหมด", "Hide/Show All Panels"),
    "m_shortcuts": ("คีย์ลัดทั้งหมด…", "Keyboard Shortcuts…"),
    "m_about": ("เกี่ยวกับ Vectra…", "About Vectra…"),

    # ── tools ──────────────────────────────────────────────────────────────
    "tool_select": ("เครื่องมือเลือก", "Selection Tool"),
    "tool_direct": ("เลือกจุด (Direct Selection)", "Direct Selection Tool"),
    "tool_magic_wand": ("ไม้กายสิทธิ์", "Magic Wand Tool"),
    "tool_lasso": ("บ่วงบาศ (Lasso)", "Lasso Tool"),
    "tool_pen": ("ปากกา (Pen)", "Pen Tool"),
    "tool_add_anchor": ("เพิ่มจุด Anchor", "Add Anchor Point Tool"),
    "tool_delete_anchor": ("ลบจุด Anchor", "Delete Anchor Point Tool"),
    "tool_anchor_point": ("แปลงจุด Anchor", "Anchor Point Tool"),
    "tool_type": ("ข้อความ (Type)", "Type Tool"),
    "tool_line": ("เส้นตรง", "Line Segment Tool"),
    "tool_arc": ("เส้นโค้ง (Arc)", "Arc Tool"),
    "tool_spiral": ("เกลียว (Spiral)", "Spiral Tool"),
    "tool_rect": ("สี่เหลี่ยม", "Rectangle Tool"),
    "tool_rounded_rect": ("สี่เหลี่ยมมุมมน", "Rounded Rectangle Tool"),
    "tool_ellipse": ("วงรี", "Ellipse Tool"),
    "tool_polygon": ("รูปหลายเหลี่ยม", "Polygon Tool"),
    "tool_star": ("รูปดาว", "Star Tool"),
    "tool_pencil": ("ดินสอ (Pencil)", "Pencil Tool"),
    "tool_scissors": ("กรรไกร", "Scissors Tool"),
    "tool_rotate": ("หมุน", "Rotate Tool"),
    "tool_reflect": ("สะท้อน", "Reflect Tool"),
    "tool_scale": ("ย่อ/ขยาย", "Scale Tool"),
    "tool_artboard": ("Artboard", "Artboard Tool"),
    "tool_eyedropper": ("ดูดสี (Eyedropper)", "Eyedropper Tool"),
    "tool_measure": ("วัดระยะ", "Measure Tool"),
    "tool_hand": ("มือ (เลื่อนมุมมอง)", "Hand Tool"),
    "tool_zoom": ("ซูม", "Zoom Tool"),

    "hint_select": ("คลิก/ลากเพื่อเลือก · Shift เพิ่ม · Alt+ลาก = ทำสำเนา · ลากจุดกลมเพื่อหมุน · "
                    "Enter = ย้ายด้วยตัวเลข",
                    "Click/drag to select · Shift adds · Alt+drag duplicates · drag the round knob to "
                    "rotate · Enter = Move dialog"),
    "hint_direct": ("คลิกจุดเพื่อเลือก · ลากจุด/ก้านโค้งเพื่อแก้รูป · Alt ลากก้าน = หักมุม · "
                    "ดับเบิลคลิกเส้น = เพิ่มจุด · Delete = ลบจุด",
                    "Click anchors to select · drag anchors/handles to reshape · Alt-drag a handle to "
                    "break it · double-click a segment to add · Delete removes anchors"),
    "hint_magic_wand": ("คลิกวัตถุ = เลือกทุกชิ้นที่สีเดียวกัน · Shift เพิ่ม · Alt ลบออก",
                        "Click to select everything with the same colour · Shift adds · Alt subtracts"),
    "hint_lasso": ("ลากวาดรอบวัตถุเพื่อเลือก · Shift เพิ่ม", "Drag around objects to select · Shift adds"),
    "hint_pen": ("คลิก = จุดมุม · คลิกแล้วลาก = จุดโค้ง · คลิกจุดแรก = ปิดรูป · Enter/Esc = จบ · "
                 "Shift = 45°",
                 "Click = corner · click-drag = smooth curve · click the first point to close · "
                 "Enter/Esc to finish · Shift = 45°"),
    "hint_add_anchor": ("คลิกบนเส้นเพื่อเพิ่มจุด", "Click on a path to add an anchor"),
    "hint_delete_anchor": ("คลิกจุดเพื่อลบ", "Click an anchor to delete it"),
    "hint_anchor_point": ("คลิกจุดโค้ง = เปลี่ยนเป็นมุม · ลากจากจุดมุม = ดึงก้านโค้ง",
                          "Click a smooth point to make it a corner · drag from a corner to pull handles"),
    "hint_type": ("คลิกเพื่อพิมพ์ข้อความ · คลิกข้อความเดิมเพื่อแก้ · Esc = เสร็จ",
                  "Click to type · click existing text to edit · Esc to finish"),
    "hint_line": ("ลากเพื่อวาดเส้น · Shift = 45° · Alt = จากกึ่งกลาง · คลิก = ใส่ค่า",
                  "Drag to draw · Shift = 45° · Alt = from centre · click for exact values"),
    "hint_arc": ("ลากเพื่อวาดเส้นโค้ง · Shift = โค้งเท่ากัน", "Drag to draw an arc · Shift = even"),
    "hint_spiral": ("ลากจากจุดกึ่งกลาง · คลิก = ใส่ค่า", "Drag from the centre · click for exact values"),
    "hint_rect": ("ลากเพื่อวาด · Shift = จัตุรัส · Alt = จากกึ่งกลาง · คลิก = ใส่ขนาด",
                  "Drag to draw · Shift = square · Alt = from centre · click for exact size"),
    "hint_rounded_rect": ("ลากเพื่อวาดสี่เหลี่ยมมุมมน · ปรับมุมใน Control bar",
                          "Drag to draw · set corner radius in the Control bar"),
    "hint_ellipse": ("ลากเพื่อวาด · Shift = วงกลม · Alt = จากกึ่งกลาง · คลิก = ใส่ขนาด",
                     "Drag to draw · Shift = circle · Alt = from centre · click for exact size"),
    "hint_polygon": ("ลากจากกึ่งกลาง · ↑/↓ = จำนวนด้าน · Shift = ตั้งตรง · คลิก = ใส่ค่า",
                     "Drag from the centre · ↑/↓ = sides · Shift = upright · click for values"),
    "hint_star": ("ลากจากกึ่งกลาง · ↑/↓ = จำนวนแฉก · Shift = ตั้งตรง · คลิก = ใส่ค่า",
                  "Drag from the centre · ↑/↓ = points · Shift = upright · click for values"),
    "hint_pencil": ("กดค้างแล้วลากเพื่อวาดเส้นอิสระ", "Drag to draw freehand"),
    "hint_scissors": ("คลิกบนเส้นเพื่อตัดพาธ", "Click on a path to cut it"),
    "hint_rotate": ("คลิก = ตั้งจุดหมุน · ลาก = หมุน · Shift = 45° · Alt ตอนปล่อย = สำเนา · "
                    "ดับเบิลคลิกไอคอน = ใส่ค่า",
                    "Click sets the pivot · drag rotates · Shift = 45° · Alt on release = copy · "
                    "double-click the icon for values"),
    "hint_reflect": ("คลิก = ตั้งจุดแกน · ลาก = หมุนแกนสะท้อน · Shift = 45° · Alt ตอนปล่อย = สำเนา",
                     "Click sets the axis point · drag to reflect · Shift = 45° · Alt on release = copy"),
    "hint_scale": ("คลิก = ตั้งจุดอ้างอิง · ลาก = ย่อขยาย · Shift = ตามสัดส่วน · Alt ตอนปล่อย = สำเนา",
                   "Click sets the origin · drag scales · Shift = uniform · Alt on release = copy"),
    "hint_artboard": ("ลากขอบ/มุมเพื่อปรับขนาด Artboard · ลากด้านในเพื่อย้าย · Enter = ตั้งค่า",
                      "Drag edges/corners to resize the artboard · drag inside to move · Enter = setup"),
    "hint_eyedropper": ("คลิกวัตถุเพื่อคัดลอกสี/เส้น/ตัวอักษรไปยังวัตถุที่เลือก",
                        "Click an object to copy its appearance to the selection"),
    "hint_measure": ("ลากเพื่อวัดระยะและมุม", "Drag to measure distance and angle"),
    "hint_hand": ("ลากเพื่อเลื่อนมุมมอง (หรือกด Space ค้าง)", "Drag to pan (or hold Space)"),
    "hint_zoom": ("คลิก = ซูมเข้า · Alt+คลิก = ซูมออก · ลากกรอบ = ซูมพื้นที่",
                  "Click to zoom in · Alt+click to zoom out · drag a box to zoom to it"),

    # ── shape types ────────────────────────────────────────────────────────
    "type_rect": ("สี่เหลี่ยม", "Rectangle"),
    "type_ellipse": ("วงรี", "Ellipse"),
    "type_line": ("เส้นตรง", "Line"),
    "type_polygon": ("รูปหลายเหลี่ยม", "Polygon"),
    "type_pen": ("เส้นดินสอ", "Pencil Path"),
    "type_path": ("พาธ", "Path"),
    "type_text": ("ข้อความ", "Text"),

    # ── panels / control bar ───────────────────────────────────────────────
    "tab_props": ("คุณสมบัติ", "Properties"),
    "tab_layers": ("เลเยอร์", "Layers"),
    "tab_swatches": ("แถบสี", "Swatches"),
    "sec_document": ("เอกสาร", "Document"),
    "sec_transform": ("แปลงรูป", "Transform"),
    "sec_appearance": ("ลักษณะ", "Appearance"),
    "sec_character": ("ตัวอักษร", "Character"),
    "sec_align": ("จัดแนว", "Align"),
    "sec_quick": ("คำสั่งด่วน", "Quick Actions"),
    "sec_layers": ("วัตถุทั้งหมด (บนสุดอยู่ด้านบน)", "All objects (top first)"),
    "rulers_grids": ("ไม้บรรทัด / กริด / Guides", "Rulers, Grids & Guides"),
    "no_selection": ("ไม่ได้เลือกวัตถุ", "No Selection"),
    "mixed_objects": ("หลายวัตถุ", "Mixed Objects"),
    "group": ("กลุ่ม", "Group"),
    "n_selected": ("เลือก {n} วัตถุ", "{n} objects selected"),
    "group_of": ("กลุ่ม ({n} วัตถุ)", "Group ({n} objects)"),
    "fill": ("สีพื้น", "Fill"),
    "stroke": ("สีเส้น", "Stroke"),
    "stroke_width": ("ความหนาเส้น (px)", "Stroke weight (px)"),
    "font_size": ("ขนาด (px)", "Size (px)"),
    "corner": ("มุม", "Corner"),
    "corner_radius": ("มุมมน (px)", "Corner radius (px)"),
    "character": ("ตัวอักษร", "Character"),
    "dashed": ("เส้นประ", "Dashed"),
    "swap": ("⇄ สลับ", "⇄ Swap"),
    "tip_swap": ("สลับสีพื้นกับสีเส้น  (Shift+X)", "Swap fill and stroke  (Shift+X)"),
    "default_colors": ("ค่าเริ่มต้น", "Default"),
    "tip_default_colors": ("พื้นขาว เส้นดำ  (D)", "White fill, black stroke  (D)"),
    "tip_keep_ratio": ("ล็อกสัดส่วน W/H", "Constrain width and height proportions"),
    "align_left": ("ชิดซ้าย", "Horizontal Align Left"),
    "align_hcenter": ("กึ่งกลางแนวนอน", "Horizontal Align Center"),
    "align_right": ("ชิดขวา", "Horizontal Align Right"),
    "align_top": ("ชิดบน", "Vertical Align Top"),
    "align_vcenter": ("กึ่งกลางแนวตั้ง", "Vertical Align Center"),
    "align_bottom": ("ชิดล่าง", "Vertical Align Bottom"),
    "align_to": ("จัดตาม:", "Align to:"),
    "align_to_selection": ("การเลือก", "Selection"),
    "align_to_artboard": ("Artboard", "Artboard"),
    "tip_distribute": ("ต้องเลือกอย่างน้อย 3 ชิ้น", "Select 3 or more objects"),
    "tip_fill_stroke": ("คลิก = เลือกช่องที่ใช้งาน · ดับเบิลคลิก = เลือกสี · ⇄ = สลับ (Shift+X) · "
                        "▪ = ค่าเริ่มต้น (D) · X = สลับช่อง",
                        "Click to make active · double-click to pick colour · ⇄ swaps (Shift+X) · "
                        "▪ default (D) · X toggles"),
    "tip_color_btn": ("ใช้สีล่าสุด  (,)", "Last colour  (,)"),
    "tip_none_btn": ("ไม่มีสี  (/)", "None  (/)"),
    "swatches_hint": ("คลิก = ใช้กับช่อง Fill/Stroke ที่ใช้งานอยู่ · คลิกขวา = สีเส้น · "
                      "Ctrl+ดับเบิลคลิก = ลบแถบสี",
                      "Click = apply to the active Fill/Stroke · right-click = stroke · "
                      "Ctrl+double-click = delete swatch"),
    "new_swatch": ("เพิ่มแถบสี", "New Swatch"),
    "reset_swatches": ("คืนค่าเริ่มต้น", "Reset"),
    "layers_empty": ("ยังไม่มีวัตถุ", "No objects yet"),
    "tip_eye": ("แสดง / ซ่อน", "Toggle visibility"),
    "tip_lock": ("ล็อก / ปลดล็อก", "Toggle lock"),
    "rename_title": ("เปลี่ยนชื่อ", "Rename"),
    "rename_prompt": ("ชื่อวัตถุ:", "Object name:"),
    "layers_hint": ("คลิก = เลือก · Shift+คลิก = เพิ่ม · ดับเบิลคลิก = เปลี่ยนชื่อ",
                    "Click = select · Shift+click = add · double-click = rename"),

    # ── shortcut list (Help) ───────────────────────────────────────────────
    "k_default_colors": ("สีเริ่มต้น", "Default fill & stroke"),
    "k_toggle_focus": ("สลับช่อง Fill/Stroke", "Toggle fill / stroke focus"),
    "k_swap": ("สลับสีพื้น-เส้น", "Swap fill & stroke"),
    "k_none": ("ไม่มีสี", "None"),
    "k_nudge": ("ขยับ", "Nudge"),
    "k_alt_drag": ("ลากเพื่อทำสำเนา", "Duplicate while dragging"),

    # ── dialogs ────────────────────────────────────────────────────────────
    "save_q_title": ("บันทึกงาน?", "Save changes?"),
    "save_q_msg": ("มีการแก้ไขที่ยังไม่ได้บันทึก\nต้องการบันทึกก่อนหรือไม่?",
                   "You have unsaved changes.\nSave them first?"),
    "save_failed": ("บันทึกไม่สำเร็จ", "Could not save"),
    "open_failed": ("เปิดไฟล์ไม่สำเร็จ", "Could not open file"),
    "invalid_file": ("ไฟล์ไม่ถูกต้อง", "The file is not a valid Vectra drawing"),
    "export_failed": ("ส่งออกไม่สำเร็จ", "Could not export"),
    "dlg_save_title": ("บันทึกงาน", "Save drawing"),
    "dlg_open_title": ("เปิดงาน", "Open drawing"),
    "dlg_export_title": ("ส่งออก SVG", "Export SVG"),
    "ft_json": ("ไฟล์งาน Vectra (.json)", "Vectra drawing (.json)"),
    "ft_all": ("ทุกไฟล์", "All files"),
    "pick_fill": ("เลือกสีพื้น", "Choose fill colour"),
    "pick_stroke": ("เลือกสีเส้น", "Choose stroke colour"),

    # ── import (.ai / .eps / .pdf) ─────────────────────────────────────────
    "m_place": ("วางไฟล์ (Place)…", "Place…"),
    "m_compound": ("Compound Path", "Compound Path"),
    "m_make_compound": ("สร้าง Compound Path", "Make Compound Path"),
    "m_release_compound": ("แยก Compound Path", "Release Compound Path"),
    "compound_no_cut": ("ตัด Compound Path ไม่ได้ — แยกก่อน (Ctrl+Alt+Shift+8)",
                        "Can't cut a compound path — release it first (Ctrl+Alt+Shift+8)"),
    "flash_compound": ("สร้าง Compound Path แล้ว", "Compound path made"),
    "flash_released": ("แยก Compound Path แล้ว", "Compound path released"),
    "ft_supported": ("ไฟล์ที่รองรับ", "All supported files"),
    "ft_ai": ("Adobe Illustrator (.ai)", "Adobe Illustrator (.ai)"),
    "ft_eps": ("EPS / PostScript", "EPS / PostScript"),
    "ft_pdf": ("PDF", "PDF"),
    "flash_imported": ("นำเข้า {name}: {n} วัตถุ", "Imported {name}: {n} objects"),
    "skip_images": ("ข้ามรูปภาพ {n}", "{n} images skipped"),
    "skip_gradients": ("Gradient {n} เป็นสีเรียบ", "{n} gradients as solid colour"),
    "skip_pages": ("ใช้หน้าแรกจาก {n} หน้า", "first of {n} pages"),
    "import_unsupported": ("ไม่รู้จักรูปแบบไฟล์นี้ (รองรับ .ai, .eps, .ps, .pdf, .json)",
                           "Unrecognised file format (supported: .ai, .eps, .ps, .pdf, .json)"),
    "file_header": ("ข้อมูลต้นไฟล์ (ช่วยวิเคราะห์):", "File header (for diagnosis):"),
    "import_corrupted": ("ไฟล์นี้เสียหาย: ข้อมูลไบนารีถูกแปลงเป็นข้อความ (เจออักขระ � จำนวนมาก)\n"
                         "มักเกิดจากการคัดลอก/อัปโหลด/ส่งไฟล์ผ่านช่องทางที่แปลงไฟล์เป็นข้อความ\n"
                         "ลองใช้ไฟล์ต้นฉบับจาก Illustrator อีกครั้ง หรือ Save As ใหม่",
                         "This file is damaged: its binary data was converted to text (many � characters).\n"
                         "This usually happens when a file is copied, uploaded or sent through a text-only channel.\n"
                         "Use the original file from Illustrator, or re-save it."),
    "import_encrypted": ("ไฟล์นี้ถูกเข้ารหัส/ป้องกันไว้ เปิดไม่ได้", "This file is encrypted and can't be opened"),
    "import_empty": ("ไม่พบงานเวกเตอร์ในไฟล์นี้", "No vector artwork found in this file"),
    "import_no_pdf_content": ("ไฟล์ .ai นี้บันทึกโดยไม่ได้เปิด “Create PDF Compatible File” "
                              "และใช้การบีบอัดแบบใหม่ที่อ่านไม่ได้\nกรุณาบันทึกใหม่ใน Illustrator โดยเปิดตัวเลือกนั้น "
                              "หรือ Save As เป็น .eps / .pdf",
                              "This .ai was saved without “Create PDF Compatible File” using a compression "
                              "Vectra can't read.\nRe-save it in Illustrator with that option on, "
                              "or save as .eps / .pdf."),

    # ── layers ─────────────────────────────────────────────────────────────
    "n_layers": ("{n} เลเยอร์", "{n} Layers"),
    "more_objects": ("… อีก {n} วัตถุ", "… {n} more objects"),
    "obj_path": ("<พาธ>", "<Path>"),
    "obj_pen": ("<พาธ>", "<Path>"),
    "obj_compound": ("<Compound Path>", "<Compound Path>"),
    "obj_group": ("<กลุ่ม>", "<Group>"),
    "obj_rect": ("<สี่เหลี่ยม>", "<Rectangle>"),
    "obj_ellipse": ("<วงรี>", "<Ellipse>"),
    "obj_polygon": ("<รูปหลายเหลี่ยม>", "<Polygon>"),
    "obj_line": ("<เส้น>", "<Line>"),
    "obj_text": ("<ข้อความ>", "<Text>"),
    "tip_target": ("เลือกทั้งหมดใน (Shift = เพิ่ม)", "Select (Shift = add)"),
    "tip_new_layer": ("สร้างเลเยอร์ใหม่  (Ctrl+L)", "Create New Layer  (Ctrl+L)"),
    "tip_delete_layer": ("ลบเลเยอร์ปัจจุบัน", "Delete current layer"),
    "tip_layer_up": ("ย้ายเลเยอร์ขึ้น", "Move layer up"),
    "tip_layer_down": ("ย้ายเลเยอร์ลง", "Move layer down"),
    "tip_move_to_layer": ("ย้ายวัตถุที่เลือกไปเลเยอร์ปัจจุบัน", "Move selection to current layer"),
    "tip_locate": ("หาตำแหน่งวัตถุที่เลือกในรายการ", "Locate object"),
    "m_new_layer": ("เลเยอร์ใหม่", "New Layer"),
    "m_send_to_layer": ("ส่งไปเลเยอร์ปัจจุบัน", "Send to Current Layer"),
    "rename_layer_title": ("ตั้งชื่อเลเยอร์", "Layer Options"),
    "rename_layer_prompt": ("ชื่อเลเยอร์:", "Name:"),
    "delete_layer_title": ("ลบเลเยอร์", "Delete layer"),
    "delete_layer_msg": ("ลบเลเยอร์ “{name}” และงาน {n} ชิ้นในเลเยอร์?", "Delete layer “{name}” and its {n} objects?"),
    "flash_new_layer": ("สร้าง {name}", "Created {name}"),
    "flash_layer_deleted": ("ลบเลเยอร์ {name}", "Deleted layer {name}"),
    "flash_moved_to_layer": ("ย้ายไปเลเยอร์ {name}", "Moved to {name}"),

    # ── status / flash messages ────────────────────────────────────────────
    "status_objects": ("{n} วัตถุ", "{n} objects"),
    "flash_undo": ("ย้อนกลับ", "Undo"),
    "flash_redo": ("ทำซ้ำ", "Redo"),
    "flash_duplicated": ("ทำสำเนาแล้ว", "Duplicated"),
    "flash_copied": ("คัดลอก {n} วัตถุ", "Copied {n} objects"),
    "flash_saved": ("บันทึกแล้ว: {name}", "Saved: {name}"),
    "flash_opened": ("เปิด {name}", "Opened {name}"),
    "flash_exported": ("ส่งออก SVG แล้ว: {name}", "Exported SVG: {name}"),
    "flash_snap_on": ("เปิด Snap to Grid", "Snap to grid on"),
    "flash_snap_off": ("ปิด Snap to Grid", "Snap to grid off"),
    "flash_smart_on": ("เปิด Smart Guides", "Smart Guides on"),
    "flash_smart_off": ("ปิด Smart Guides", "Smart Guides off"),
    "flash_grouped": ("จัดกลุ่ม {n} วัตถุ", "Grouped {n} objects"),
    "flash_ungrouped": ("แยกกลุ่มแล้ว", "Ungrouped"),
    "flash_locked": ("ล็อก {n} วัตถุ", "Locked {n} objects"),
    "flash_unlocked": ("ปลดล็อกทั้งหมด", "Unlocked all"),
    "flash_hidden": ("ซ่อน {n} วัตถุ", "Hid {n} objects"),
    "flash_shown": ("แสดงทั้งหมด", "Showing all"),
    "flash_count": ("จำนวน: {n}", "Count: {n}"),
    "flash_appearance": ("คัดลอกลักษณะแล้ว", "Appearance copied"),
    "flash_converted": ("แปลง {n} วัตถุเป็นพาธ", "Converted {n} objects to paths"),
    "flash_joined": ("เชื่อมพาธแล้ว", "Paths joined"),
    "flash_closed": ("ปิดพาธแล้ว", "Path closed"),
    "flash_lang": ("ภาษา: ไทย", "Language: English"),
}


def set_language(lang):
    global _current
    _current = lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def get_language():
    return _current


def next_language():
    i = _ORDER.index(_current)
    return _ORDER[(i + 1) % len(_ORDER)]


def tr(key, **kwargs):
    """Translate ``key`` into the current language; unknown keys return the key."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry[_ORDER.index(_current)]
    return text.format(**kwargs) if kwargs else text
