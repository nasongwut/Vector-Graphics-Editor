"""Application entry point."""

import os
import sys
import tkinter as tk

from vectra import i18n, settings

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _set_icon(root):
    try:
        root.iconphoto(True, tk.PhotoImage(file=os.path.join(ASSETS, "icon.png")))
    except Exception:  # noqa: BLE001 — icon is cosmetic
        pass


def _file_args(argv):
    """Document paths given on the command line (Explorer "Open with", drag onto the exe)."""
    return [a for a in argv if not a.startswith("-") and os.path.isfile(a)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:  # crisp rendering on Windows HiDPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass

    i18n.set_language(settings.get("language", i18n.DEFAULT_LANGUAGE))

    from vectra.ui.editor import VectorEditor  # imported late so language is set first

    root = tk.Tk(className="Vectra")
    _set_icon(root)
    ed = VectorEditor(root)

    def open_paths(*paths):
        files = [p for p in paths if os.path.isfile(p)]
        if files:
            root.after(50, lambda: ed.open_doc(files[0]))

    # macOS: Finder double-click / drop on the Dock icon arrives as an Apple Event
    try:
        root.createcommand("::tk::mac::OpenDocument", open_paths)
    except Exception:  # noqa: BLE001
        pass

    files = _file_args(argv)
    if files:
        root.after(200, lambda: ed.open_doc(files[0]))
    root.mainloop()


if __name__ == "__main__":
    main()
