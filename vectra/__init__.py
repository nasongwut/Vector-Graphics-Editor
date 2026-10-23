"""Vectra — a small vector graphics editor written with Python + Tkinter.

Package layout
--------------
vectra/
    config.py        app-wide constants (artboard, grid, platform flags)
    i18n.py          Thai / English UI strings and the ``tr()`` lookup
    settings.py      user preferences persisted in ~/.vectra/settings.json
    model/           pure data + geometry, no Tkinter (unit-testable)
    fileio/          JSON documents and SVG export
    ui/              Tkinter widgets, rendering and the editor controller

Run with ``python main.py`` or ``python -m vectra``.
"""

__version__ = "3.3.0"
