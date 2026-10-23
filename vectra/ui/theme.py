"""Colours and fonts — a neutral dark-grey workspace in the style of pro vector apps."""

from tkinter import font as tkfont

from vectra.config import IS_MAC

T = dict(
    bg="#262626",           # app background / gaps between panels
    panel="#323232",        # panels, tool bar, control bar
    panel2="#3c3c3c",       # inputs, buttons inside panels
    panel3="#2b2b2b",       # tab strips, headers
    border="#1e1e1e",
    divider="#454545",
    text="#e0e0e0",
    muted="#a0a0a0",
    dim="#6e6e6e",
    accent="#378ef0",       # active tool, focused tab, primary button
    accent2="#5aa2f5",
    hover="#454545",
    tool_active="#505050",
    selection="#4a7dff",    # selection boxes, anchors (layer colour)
    smart="#ff3ec9",        # smart guides (magenta)
    canvas="#535353",       # pasteboard
    grid="#5c5c5c",
    board="#ffffff",
    board_grid="#ececf2",
    ruler="#2b2b2b",
    ruler_text="#9a9a9a",
    danger="#ff5c5c",
    danger_hover="#5a2a2a",
    shadow="#3a3a3a",
    entry="#262626",
    menu="#3c3c3c",
)

# Swatches panel defaults (rows of 10)
PALETTE = [
    "#ffffff", "#000000", "#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff", "#7c5cff", "#f97316",
    "#ed1c24", "#f15a24", "#f7931e", "#fbb03b", "#fcee21", "#d9e021", "#8cc63f", "#39b54a", "#009245", "#006837",
    "#22b573", "#00a99d", "#29abe2", "#0071bc", "#2e3192", "#1b1464", "#662d91", "#93278f", "#9e005d", "#d4145a",
    "#ed1e79", "#c7b299", "#998675", "#736357", "#534741", "#c69c6d", "#a67c52", "#8c6239", "#754c24", "#603813",
    "#f2f2f2", "#e6e6e6", "#cccccc", "#b3b3b3", "#999999", "#808080", "#666666", "#4d4d4d", "#333333", "#1a1a1a",
]

_UI_FONTS = ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", ".AppleSystemUIFont",
             "Helvetica Neue", "Inter", "Noto Sans Thai", "Noto Sans", "Ubuntu",
             "DejaVu Sans", "Helvetica", "Arial")


def pick_font(root):
    fams = set(tkfont.families(root))
    for f in _UI_FONTS:
        if f in fams:
            return f
    return "TkDefaultFont"


def pick_mono_font(root):
    if "Consolas" in tkfont.families(root):
        return "Consolas"
    return "Menlo" if IS_MAC else "DejaVu Sans Mono"


def font_families(root):
    return sorted({f for f in tkfont.families(root) if not f.startswith("@")}, key=str.lower)
