"""Application entry point."""

import tkinter as tk

from vectra import i18n, settings


def main():
    try:  # crisp rendering on Windows HiDPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass

    i18n.set_language(settings.get("language", i18n.DEFAULT_LANGUAGE))

    from vectra.ui.editor import VectorEditor  # imported late so language is set first

    root = tk.Tk()
    VectorEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
