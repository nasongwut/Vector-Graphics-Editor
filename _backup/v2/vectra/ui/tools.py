"""Tool definitions: (key, icon, i18n name key, shortcut). ``None`` = separator."""

TOOLS = [
    ("select", "➤", "tool_select", "V"),
    ("direct", "▷", "tool_direct", "A"),
    ("hand", "✋", "tool_hand", "H"),
    ("zoom", "⊕", "tool_zoom", "Z"),
    None,
    ("rect", "▢", "tool_rect", "R"),
    ("ellipse", "◯", "tool_ellipse", "E"),
    ("line", "╱", "tool_line", "L"),
    ("polygon", "⬠", "tool_polygon", "G"),
    ("star", "☆", "tool_star", "S"),
    ("pen", "✎", "tool_pen", "P"),
    ("text", "T", "tool_text", "T"),
    None,
    ("eyedropper", "◍", "tool_eyedropper", "I"),
]

CURSORS = {
    "select": "arrow", "direct": "arrow", "hand": "fleur", "text": "xterm",
    "zoom": "plus", "eyedropper": "tcross",
}
DEFAULT_CURSOR = "crosshair"


def cursor_for(tool):
    return CURSORS.get(tool, DEFAULT_CURSOR)


def hint_key(tool):
    return "hint_" + tool
