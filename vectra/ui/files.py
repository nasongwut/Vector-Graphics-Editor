"""New / open / place / save / export / close."""

import os
from tkinter import filedialog, messagebox

from vectra.fileio import json_io, svg_export
from vectra.fileio.importers import ImportFailed, import_file, is_importable
from vectra.i18n import tr


def _open_filetypes():
    return [(tr("ft_supported"), "*.json *.ai *.eps *.epsf *.ps *.pdf"),
            (tr("ft_json"), "*.json"), (tr("ft_ai"), "*.ai"), (tr("ft_eps"), "*.eps *.epsf *.ps"),
            (tr("ft_pdf"), "*.pdf"), (tr("ft_all"), "*.*")]


class FilesMixin:
    import_name = None

    def confirm_discard(self):
        if not self.dirty or not self.doc.shapes:
            return True
        r = messagebox.askyesnocancel(tr("save_q_title"), tr("save_q_msg"), parent=self.root)
        if r is None:
            return False
        if r:
            return self.save()
        return True

    def _reset(self, shapes, path, artboard=None, import_name=None, layers=None, active=None):
        self.commit_text_edit()
        self.doc.clear()
        if shapes or artboard or layers:
            self.doc.load(shapes or [], artboard, layers)
        if active is not None and self.doc.layer(active) is not None:
            self.doc.active_layer = active
        elif layers:
            self.doc.active_layer = self.doc.layers[-1]["id"]
        self.selected = set()
        self.history.clear()
        self.doc_version += 1
        self.file_path = path
        self.import_name = import_name
        self.dirty = False
        self.update_title()
        self.on_selection_changed()
        self.zoom_fit()

    def new_doc(self):
        if self.confirm_discard():
            self._reset([], None)

    def save(self, save_as=False):
        self.commit_text_edit()
        if save_as or not self.file_path:
            initial = os.path.splitext(self.import_name)[0] + ".json" if self.import_name else ""
            p = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
                                             filetypes=[(tr("ft_json"), "*.json")],
                                             initialfile=initial, title=tr("dlg_save_title"))
            if not p:
                return False
            self.file_path = p
            self.import_name = None
        try:
            json_io.save(self.file_path, self.doc.shapes, self.doc.artboard, self.doc.layers,
                         self.doc.active_layer)
        except OSError as ex:
            messagebox.showerror(tr("save_failed"), str(ex), parent=self.root)
            return False
        self.dirty = False
        self.update_title()
        self.flash(tr("flash_saved", name=os.path.basename(self.file_path)))
        return True

    # ── reading files ───────────────────────────────────────────────────────
    def _read_any(self, path):
        """-> (shapes, artboard, notes, layers, active layer) or None after showing an error."""
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            if is_importable(path):
                res = import_file(path)
                return res.shapes, res.artboard, res.notes, res.layers, None
            shapes, artboard, layers, active = json_io.load_full(path)
            return shapes, artboard, {}, layers, active
        except ImportFailed as ex:
            msg = tr("import_" + ex.reason)
            if ex.reason in ("unsupported", "corrupted") and ex.detail:
                msg += "\n\n" + tr("file_header") + "\n" + ex.detail
            messagebox.showerror(tr("open_failed"), msg, parent=self.root)
        except Exception as ex:  # noqa: BLE001 - any bad file -> friendly message
            messagebox.showerror(tr("open_failed"), f"{tr('invalid_file')}\n{ex}", parent=self.root)
        finally:
            self.root.config(cursor="")
        return None

    def _import_summary(self, name, n, notes):
        msg = tr("flash_imported", name=name, n=n)
        skipped = [tr("skip_" + k, n=notes[k]) for k in ("images", "gradients") if notes.get(k)]
        if notes.get("pages", 1) > 1:
            skipped.append(tr("skip_pages", n=notes["pages"]))
        if skipped:
            msg += "  ·  " + " · ".join(skipped)
        self.flash(msg, ms=7000)

    def open_doc(self, path=None):
        if not self.confirm_discard():
            return
        p = path or filedialog.askopenfilename(parent=self.root, title=tr("dlg_open_title"),
                                               filetypes=_open_filetypes())
        if not p:
            return
        got = self._read_any(p)
        if got is None:
            return
        shapes, artboard, notes, layers, active = got
        name = os.path.basename(p)
        if is_importable(p):
            self._reset(shapes, None, artboard, import_name=name, layers=layers)
            self._import_summary(name, len(shapes), notes)
            if len(self.doc.layers) > 1:
                self.show_panel("layers")
        else:
            self._reset(shapes, p, artboard, layers=layers, active=active)
            self.flash(tr("flash_opened", name=name))

    def place_file(self, path=None):
        """File ▸ Place: add another file's artwork to this document as a group."""
        p = path or filedialog.askopenfilename(parent=self.root, title=tr("m_place"),
                                               filetypes=_open_filetypes())
        if not p:
            return
        got = self._read_any(p)
        if got is None:
            return
        shapes, artboard, notes, layers, _active = got
        hidden = {l["id"] for l in (layers or []) if not l.get("visible", True)}
        shapes = [s for s in shapes if s.get("layer") not in hidden and not s.get("hidden")]
        if not shapes:
            return
        # centre the placed art on the current artboard
        ab, src = self.doc.artboard, artboard or [0, 0, 0, 0]
        dx = (ab[0] + ab[2]) / 2 - (src[0] + src[2]) / 2
        dy = (ab[1] + ab[3]) / 2 - (src[1] + src[3]) / 2
        for s in shapes:
            s["pts"] = [v + (dx if i % 2 == 0 else dy) for i, v in enumerate(s["pts"])]
            if "ctrl" in s:
                s["ctrl"] = [v + (dx if i % 2 == 0 else dy) for i, v in enumerate(s["ctrl"])]
        self.push_undo()
        new_ids = self.doc.insert_copies(shapes, 0, layer=self.doc.active_layer)
        if len(new_ids) > 1:
            self.doc.group(new_ids)
        self.selected = new_ids
        self.set_tool("select")
        self.on_selection_changed()
        self.render()
        self._import_summary(os.path.basename(p), len(shapes), notes)

    def export_svg(self, path=None):
        if path is None:
            path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".svg",
                                                filetypes=[("SVG", "*.svg")], title=tr("dlg_export_title"))
            if not path:
                return
        try:
            svg_export.export(path, self.doc.shapes, self.doc.artboard, self.ui_font, self.doc.layers)
        except OSError as ex:
            messagebox.showerror(tr("export_failed"), str(ex), parent=self.root)
            return
        self.flash(tr("flash_exported", name=os.path.basename(path)))

    def on_close(self):
        if self.confirm_discard():
            self.root.destroy()
