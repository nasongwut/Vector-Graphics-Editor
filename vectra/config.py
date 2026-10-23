"""App-wide constants."""

import sys

APP_NAME = "Vectra"
APP_ID = "vectra"           # written into saved files
FILE_VERSION = 3            # v1/v2 files still load fine

ARTBOARD = (0, 0, 1000, 700)
GRID = 10
UNDO_LIMIT = 200
UNDO_COALESCE_SECONDS = 1.0

MIN_ZOOM = 0.05
MAX_ZOOM = 16.0

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

# Modifier bits in a Tk event.state
SHIFT_MASK = 0x1
CONTROL_MASK = 0x4
if IS_MAC:
    ALT_MASK = 0x10          # Option
elif IS_WIN:
    ALT_MASK = 0x20000
else:
    ALT_MASK = 0x8           # Mod1

# Default style for new shapes
DEFAULT_FILL = "#7c5cff"
DEFAULT_STROKE = "#0f172a"
DEFAULT_WIDTH = 2
DEFAULT_FONT_SIZE = 32
DEFAULT_STAR_POINTS = 5
STAR_INNER_RATIO = 0.5
