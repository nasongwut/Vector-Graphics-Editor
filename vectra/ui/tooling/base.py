"""Base class and helpers shared by all tools."""

import math

from vectra.config import ALT_MASK, SHIFT_MASK
from vectra.i18n import tr


def shift(e):
    return bool(e.state & SHIFT_MASK)


def alt(e):
    return bool(e.state & ALT_MASK)


def snap_angle(deg, step):
    return round(deg / step) * step


class Tool:
    key = ""
    cursor = "crosshair"
    box = None          # selection box style the renderer draws: "full", "plain" or None
    hover = False       # renderer highlights the object under the cursor

    def __init__(self, ed):
        self.ed = ed
        self.press_screen = (0, 0)

    # ── lifecycle ───────────────────────────────────────────────────────────
    def name(self):
        return tr("tool_" + self.key)

    def hint(self):
        return tr("hint_" + self.key)

    def activate(self):
        pass

    def deactivate(self):
        pass

    # ── events (world coordinates) ──────────────────────────────────────────
    def press(self, e, wx, wy):
        pass

    def drag(self, e, wx, wy):
        pass

    def release(self, e, wx, wy):
        pass

    def motion(self, e, wx, wy):
        pass

    def double(self, e, wx, wy):
        """Return True if the double-click was handled (otherwise it acts as a press)."""
        return False

    def on_key(self, keysym):
        """Return True if the key was handled (Return, Escape, Delete, arrows)."""
        return False

    def overlay(self, renderer):
        pass

    # ── helpers ─────────────────────────────────────────────────────────────
    def moved(self, e, px=3):
        return math.hypot(e.x - self.press_screen[0], e.y - self.press_screen[1]) > px

    def snap_point(self, x, y):
        """Grid snap, then smart-guide snap to other objects."""
        ed = self.ed
        x, y = ed.snapv(x), ed.snapv(y)
        return ed.guides.snap_point(x, y)
