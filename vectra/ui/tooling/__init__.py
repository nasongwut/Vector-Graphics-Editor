"""Tools: one class per tool, grouped in the tool bar like a pro vector editor.

Each tool receives canvas events from the editor (``press``/``drag``/``release``/
``motion``/``double``) already converted to world coordinates, plus a few keys
(``on_key``). Tools may draw their own overlay (``overlay``).
"""

from vectra.ui.tooling.misc import (ArtboardTool, EyedropperTool, HandTool, LassoTool,
                                    MagicWandTool, MeasureTool, ScissorsTool, TypeTool, ZoomTool)
from vectra.ui.tooling.pen import AddAnchorTool, AnchorPointTool, DeleteAnchorTool, PenTool
from vectra.ui.tooling.select import DirectSelectTool, SelectTool
from vectra.ui.tooling.shape_tools import (ArcTool, EllipseTool, LineTool, PencilTool, PolygonTool,
                                           RectTool, RoundedRectTool, SpiralTool, StarTool)
from vectra.ui.tooling.transform_tools import ReflectTool, RotateTool, ScaleTool

TOOL_CLASSES = [
    SelectTool, DirectSelectTool, MagicWandTool, LassoTool,
    PenTool, AddAnchorTool, DeleteAnchorTool, AnchorPointTool,
    TypeTool, LineTool, ArcTool, SpiralTool,
    RectTool, RoundedRectTool, EllipseTool, PolygonTool, StarTool,
    PencilTool, ScissorsTool, RotateTool, ReflectTool, ScaleTool,
    ArtboardTool, EyedropperTool, MeasureTool, HandTool, ZoomTool,
]

# Tool-bar layout: each inner list is one button with a fly-out of alternatives.
TOOL_GROUPS = [
    ["select"], ["direct"], ["magic_wand", "lasso"],
    ["pen", "add_anchor", "delete_anchor", "anchor_point"],
    ["type"], ["line", "arc", "spiral"],
    ["rect", "rounded_rect", "ellipse", "polygon", "star"],
    ["pencil"], ["scissors"], ["rotate", "reflect"], ["scale"], ["artboard"],
    ["eyedropper", "measure"], ["hand"], ["zoom"],
]

# Shortcut label shown in tooltips / menus, and the Tk keysyms that trigger it.
SHORTCUTS = {
    "select": ("V", ["v"]), "direct": ("A", ["a"]), "magic_wand": ("Y", ["y"]),
    "lasso": ("Q", ["q"]), "pen": ("P", ["p"]), "add_anchor": ("+", ["plus", "KP_Add"]),
    "delete_anchor": ("-", ["minus", "KP_Subtract"]), "anchor_point": ("Shift+C", ["C"]),
    "type": ("T", ["t"]), "line": ("\\", ["backslash"]), "rect": ("M", ["m"]),
    "ellipse": ("L", ["l"]), "pencil": ("N", ["n"]), "scissors": ("C", ["c"]),
    "rotate": ("R", ["r"]), "reflect": ("O", ["o"]), "scale": ("S", ["s"]),
    "artboard": ("Shift+O", ["O"]), "eyedropper": ("I", ["i"]), "hand": ("H", ["h"]),
    "zoom": ("Z", ["z"]),
}


def create_tools(ed):
    return {cls.key: cls(ed) for cls in TOOL_CLASSES}


def group_of(key):
    for i, grp in enumerate(TOOL_GROUPS):
        if key in grp:
            return i
    return None


def shortcut_label(key):
    return SHORTCUTS.get(key, ("", []))[0]
