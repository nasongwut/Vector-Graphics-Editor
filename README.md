# Vectra 3.3 — Vector Graphics Editor

โปรแกรมวาดภาพเวกเตอร์ด้วย Python + Tkinter หน้าตาและการใช้งานแบบโปรแกรมออกแบบมืออาชีพ
(แถบเมนู · Control bar · แถบเครื่องมือแบบกลุ่ม · พาเนล Properties/Layers/Swatches · ไม้บรรทัด)
รองรับ 2 ภาษา ไทย / English — ไม่ต้องติดตั้งอะไรเพิ่ม

```bash
python3 main.py                        # หรือ  python3 -m vectra
python3 -m unittest discover tests     # รันเทสต์ (ไม่ต้องเปิดหน้าต่าง)
```

ต้องใช้ Python 3.8+ ที่มี Tk 8.6 (macOS: ใช้ Python จาก python.org หรือ `brew install python-tk`)
กด **F1** ในโปรแกรมเพื่อดูคีย์ลัดทั้งหมด · เปลี่ยนภาษาที่มุมขวาล่าง (TH | EN) หรือ Edit ▸ Language

## ดาวน์โหลด / ติดตั้ง

ไฟล์ติดตั้งสร้างอัตโนมัติด้วย GitHub Actions (`.github/workflows/build.yml`) ทุกครั้งที่ push
ดาวน์โหลดได้จากหน้า **Actions ▸ (รันล่าสุด) ▸ Artifacts** หรือหน้า **Releases** เมื่อ push tag `v*`

| ระบบ | ไฟล์ | หมายเหตุ |
|---|---|---|
| Windows 10 / 11 (64-bit) | `Vectra-Setup-<ver>-win-x64.exe` | ตัวติดตั้งแบบ Wizard (ไทย/อังกฤษ) · เลือกติดตั้งเฉพาะผู้ใช้หรือทั้งเครื่อง · ไอคอนเดสก์ท็อป · เลือกให้เปิด .ai/.eps ด้วย Vectra · ถอนการติดตั้งได้จาก Settings |
| macOS ชิป M (Apple Silicon) | `Vectra-<ver>-macos-apple-silicon.dmg` | macOS 11 ขึ้นไป · ลาก Vectra ไปที่ Applications |
| macOS Intel | `Vectra-<ver>-macos-intel.dmg` | macOS 11 ขึ้นไป |

ไฟล์ยังไม่ได้เซ็นด้วยใบรับรองนักพัฒนา จึงมีคำเตือนตอนเปิดครั้งแรก:
- **Windows:** SmartScreen ขึ้น "Windows protected your PC" → กด *More info* → *Run anyway*
- **macOS:** คลิกขวาที่ Vectra → *Open* → *Open* (หรือ System Settings ▸ Privacy & Security ▸ *Open Anyway*)

### Build เอง
```bash
pip install pyinstaller pillow
bash packaging/macos/build_dmg.sh                                         # macOS → dist/*.dmg
powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1   # Windows (ต้องมี Inno Setup)
git tag v3.3.0 && git push origin v3.3.0                                  # สร้าง Release พร้อมไฟล์ติดตั้งทั้ง 3 ตัว
```

## เครื่องมือ

| กลุ่ม | เครื่องมือ (คีย์ลัด) |
|---|---|
| เลือก | Selection (V) · Direct Selection (A) · Magic Wand (Y) · Lasso (Q) |
| พาธ | Pen (P) · Add Anchor (+) · Delete Anchor (−) · Anchor Point (Shift+C) |
| ข้อความ | Type (T) — พิมพ์บนแคนวาสโดยตรง, Esc = เสร็จ |
| เส้น | Line Segment (\\) · Arc · Spiral |
| รูปทรง | Rectangle (M) · Rounded Rectangle · Ellipse (L) · Polygon · Star |
| วาด/ตัด | Pencil (N) · Scissors (C) |
| แปลงรูป | Rotate (R) · Reflect (O) · Scale (S) — ดับเบิลคลิกไอคอนเพื่อใส่ตัวเลข |
| อื่น ๆ | Artboard (Shift+O) · Eyedropper (I) · Measure · Hand (H / Space) · Zoom (Z) |

กดค้างหรือคลิกขวาที่ปุ่มเครื่องมือที่มี ◢ เพื่อเปิดเครื่องมือย่อย ·
คลิกครั้งเดียวด้วยเครื่องมือรูปทรงเพื่อกรอกขนาด · Alt+ลาก = ทำสำเนา · Shift = ล็อกมุม/สัดส่วน

## คีย์ลัดหลัก

| คีย์ลัด | คำสั่ง | คีย์ลัด | คำสั่ง |
|---|---|---|---|
| Ctrl+Z / Ctrl+Shift+Z | Undo / Redo | Ctrl+G / Ctrl+Shift+G | Group / Ungroup |
| Ctrl+X / C / V | Cut / Copy / Paste | Ctrl+J | Join path |
| Ctrl+F / Ctrl+B | Paste in Front / Back | Ctrl+2 / Ctrl+Alt+2 | Lock / Unlock all |
| Ctrl+Shift+V | Paste in Place | Ctrl+3 / Ctrl+Alt+3 | Hide / Show all |
| Ctrl+D | Transform Again | Ctrl+] / Ctrl+[ (+Shift) | Arrange |
| Ctrl+Shift+M | Move… | Ctrl+A / Ctrl+Shift+A | Select all / Deselect |
| Ctrl+Y | Outline mode | Ctrl+R | Rulers |
| Ctrl+U | Smart Guides | Ctrl+' / Ctrl+Shift+' | Grid / Snap to grid |
| Ctrl+0 / Ctrl+1 | Fit artboard / 100% | Tab | ซ่อน/แสดงพาเนล |
| D / X / Shift+X | สีเริ่มต้น / สลับช่อง / สลับสี | / | ไม่มีสี |
| Ctrl+Alt+E | Export SVG | Ctrl+Alt+P | Document Setup |

## เปิดไฟล์ .ai / .eps / .pdf

**ไฟล์ ▸ เปิด (Ctrl+O)** เปิดไฟล์ `.ai`, `.eps`, `.ps`, `.pdf` เป็นเอกสารใหม่ ·
**ไฟล์ ▸ วางไฟล์ (Ctrl+Shift+P)** นำงานจากไฟล์เหล่านี้มาใส่ในเอกสารปัจจุบันเป็นกลุ่ม

| ไฟล์ | วิธีอ่าน |
|---|---|
| .ai (Illustrator CS ขึ้นไป) | อ่านส่วน PDF ในไฟล์ · ถ้าบันทึกโดยปิด “Create PDF Compatible File” จะอ่านข้อมูล Illustrator ภายในแทน |
| .ai (Illustrator 8 และเก่ากว่า) / .eps / .ps | ตัวแปลภาษา PostScript ในตัว (รองรับ EPS แบบมี preview หัวไฟล์ไบนารี) |
| .pdf | หน้าแรกของไฟล์ |

ได้: เส้นพาธ/เส้นโค้ง, Compound path (รูโหว่), สีพื้น/เส้น (RGB, CMYK, Gray, Spot/Pantone, ICC),
ความหนาเส้น, เส้นประ, ข้อความ (ฟอนต์ ขนาด ตัวหนา/เอียง มุมหมุน), กลุ่ม
ยังไม่ได้: รูปภาพ (ข้าม), Gradient (เป็นสีเรียบสีกลาง), Clipping mask, ความโปร่งใส, เอฟเฟกต์
หลายหน้า/หลาย Artboard ใช้หน้าแรก · บันทึกกลับเป็น .ai ไม่ได้ (บันทึกเป็น .json หรือส่งออก .svg)

ใหม่ในเมนู วัตถุ ▸ Compound Path: สร้าง (Ctrl+8) / แยก (Ctrl+Alt+Shift+8)

## เลเยอร์ (แบบ Illustrator)

- เปิดไฟล์ .ai แล้วได้เลเยอร์ตามชื่อ ลำดับ การซ่อน และการล็อกเดียวกับใน Illustrator
  (เช่น art · cut · fill · mark · size · mark name)
- พาเนล **เลเยอร์** (F7): 👁 ซ่อน/แสดง (Alt+คลิก = แสดงเลเยอร์เดียว) · 🔒 ล็อก · ▸ ขยายดูวัตถุ
  (<พาธ>, <กลุ่ม>, <Compound Path>, ข้อความ) · คลิกเลเยอร์ = เลเยอร์ปัจจุบัน · ดับเบิลคลิก = เปลี่ยนชื่อ ·
  วงกลมด้านขวา = เลือกทุกอย่างในเลเยอร์ · สี่เหลี่ยมสี = มีวัตถุที่เลือกอยู่ในเลเยอร์นั้น
- แถบล่าง: หาวัตถุที่เลือก · ย้ายวัตถุที่เลือกไปเลเยอร์ปัจจุบัน · เลื่อนเลเยอร์ขึ้น/ลง · เลเยอร์ใหม่ (Ctrl+L) · ลบ
- วัตถุใหม่และการวาง (Paste) ไปอยู่ในเลเยอร์ปัจจุบัน · จัดลำดับ (Ctrl+] [) อยู่ภายในเลเยอร์ ·
  กรอบเลือกใช้สีของเลเยอร์
- บันทึก .json เก็บเลเยอร์ · ส่งออก SVG เป็น <g> ตามชื่อเลเยอร์
- ไฟล์ .ai จาก Illustrator CS–2025: อ่านข้อมูลต้นฉบับของ Illustrator ภายในไฟล์ (รวมแบบบีบอัด ZStandard
  ของ Illustrator 2020 ขึ้นไป) จึงได้ <กลุ่ม> ซ้อนกัน, Compound Path และสีเลเยอร์ตรงกับ Illustrator
  (ถ้าอ่านไม่ได้จะใช้ส่วน PDF แทน)

## โครงสร้างโค้ด

```
main.py                     จุดเริ่มโปรแกรม
vectra/
  app.py  config.py  i18n.py (ข้อความ TH/EN)  settings.py (~/.vectra/settings.json)
  model/                    ── ไม่ใช้ Tkinter, เทสต์ได้ ──
    geometry.py             bbox, หมุน, ย่อขยาย, Bézier, ดาว, เกลียว
    shapes.py               ชนิดรูปทรง + แปลงเป็นพาธ + transform
    pathops.py              แก้ไขพาธ: เพิ่ม/ลบจุด, ก้านโค้ง, ตัด, เชื่อม
    document.py  history.py เอกสาร (รูปทรง + artboard) และ Undo/Redo
  fileio/                   json_io.py (บันทึก/เปิด) · svg_export.py
    importers/              pdf.py (อ่าน PDF) · pdf_import.py (.pdf/.ai) · ps_import.py (.eps/.ps/.ai เก่า)
  ui/
    editor.py               ตัวควบคุมหลัก ประกอบหน้าจอ
    menubar.py controlbar.py toolbar.py chrome.py rulers.py   ส่วนของหน้าต่าง
    panels/                 properties · layers · swatches
    tooling/                เครื่องมือ 1 คลาสต่อ 1 เครื่องมือ
    interaction.py commands.py style.py files.py shortcuts.py
    renderer.py smart_guides.py text_editor.py dialogs.py icons.py theme.py widgets.py
  assets/icon.png          ไอคอนหน้าต่าง
packaging/                  vectra.spec (PyInstaller) · windows/vectra.iss (Inno Setup wizard) · macos/build_dmg.sh
.github/workflows/build.yml  CI: เทสต์ + build Windows / macOS Intel / macOS Apple Silicon
tests/test_model.py  tests/test_import.py
```

เพิ่มเครื่องมือใหม่: สร้างคลาสใน `ui/tooling/` (สืบทอด `Tool`), เพิ่มใน `TOOL_CLASSES`/`TOOL_GROUPS`,
วาดไอคอนใน `ui/icons.py` และเพิ่มชื่อ/คำแนะนำใน `i18n.py` (`tool_<key>`, `hint_<key>`)

## ข้อจำกัดของ Tkinter

ยังไม่รองรับ: Gradient, Opacity / Blend mode, Pathfinder / Shape Builder, Brush, Symbol, Mesh,
Perspective Grid, หลาย Artboard และการส่งออก PNG/PDF/AI
ไฟล์งานจาก Vectra 1.x / 2.x / 3.0 เปิดได้ตามปกติ
