# src/common/constants.py

# --- Window and Layout ---
INITIAL_WIN_WIDTH, INITIAL_WIN_HEIGHT = 1280, 720
TOP_BAR_HEIGHT = 40
TOOLBAR_HEIGHT = 0 # Second toolbar removed
RIGHT_PANEL_WIDTH = 280
PREVIEW_SIZE = (240, 240)

# --- Isometric Grid ---
TILE_WIDTH, TILE_HEIGHT = 64, 32
TILE_WIDTH_HALF, TILE_HEIGHT_HALF = TILE_WIDTH // 2, TILE_HEIGHT // 2
WALL_HEIGHT = 96

# --- Colors ---
COLOR_BG = (20, 30, 40)
COLOR_TOP_BAR = (30, 40, 50)
COLOR_PANEL_BG = (35, 45, 55)
COLOR_EDITOR_BG = (45, 55, 65)
COLOR_PREVIEW_BG = (0, 0, 0)
COLOR_BORDER = (80, 90, 100)
COLOR_BUTTON = (70, 80, 90)
COLOR_BUTTON_HOVER = (100, 110, 120)
COLOR_BUTTON_ACTIVE = (120, 130, 140)
COLOR_TEXT = (200, 200, 210)
COLOR_INFO_TEXT = (130, 140, 150)
COLOR_TITLE_TEXT = (150, 160, 170)
COLOR_ANCHOR = (255, 100, 100)
COLOR_INPUT_ACTIVE = (230, 230, 230)
COLOR_INPUT_INACTIVE = (150, 150, 150)
COLOR_TILE = (180, 140, 100)
COLOR_TILE_BORDER = (100, 100, 100)
COLOR_ORIGIN = (100, 120, 140)
COLOR_HOVER_BORDER = (255, 255, 0)
COLOR_WALL = (200, 120, 50)
COLOR_WALL_BORDER = (140, 80, 30)
COLOR_PREVIEW_OUTLINE = (220, 220, 220)
COLOR_SAVE_CONFIRM_BG = (50, 60, 70, 220)
COLOR_GRID = (60, 70, 80)
COLOR_SCROLLBAR_BG = (25, 35, 45)
COLOR_SCROLLBAR_THUMB = (70, 80, 90)
COLOR_SCROLLBAR_THUMB_HOVER = (100, 110, 120)

# --- UI Element States ---
COLOR_TOGGLE_ON = (50, 160, 50)
COLOR_TOGGLE_ON_HOVER = (70, 180, 70)

# --- Walkable Overlay Colors ---
COLOR_WALKABLE_OVERLAY = (50, 200, 50, 128)
COLOR_NON_WALKABLE_OVERLAY = (200, 50, 50, 128)

# --- Tile Types ---
TILE_TYPE_FULL = 1
TILE_TYPE_CORNER_NO_TL = 2
TILE_TYPE_CORNER_NO_TR = 3
TILE_TYPE_CORNER_NO_BR = 4
TILE_TYPE_CORNER_NO_BL = 5
TILE_TYPES = [TILE_TYPE_FULL, TILE_TYPE_CORNER_NO_TL, TILE_TYPE_CORNER_NO_TR, TILE_TYPE_CORNER_NO_BR, TILE_TYPE_CORNER_NO_BL]

# --- Structure Edit Modes ---
MODE_TILES = 0
MODE_WALLS = 1
MODE_WALKABLE = 2
MODE_LAYERS = 3

# --- Layer System ---
# Defines the rendering order for decorations. Lower IDs are rendered first.
# "Tile Layers" can be painted on the grid (Structure Editor) and saved in structure.json as a default.
# "Decoration Layers" can be assigned to individual decoration items. All layers are valid as Decoration Layers.
LAYER_WALL = 0
LAYER_FLOOR = 1
LAYER_BACKGROUND = 2
LAYER_MAIN = 3
LAYER_FOREGROUND = 4

LAYER_DATA = {
    # Calculated dynamically based on wall positions. Cannot be painted as a Tile Layer.
    LAYER_WALL:       {"name": "Wall",       "char": "w", "color": (150, 100, 255, 77)},
    
    # Decoration-only layer (e.g., carpets). Cannot be painted as a Tile Layer, but can be assigned to decorations.
    LAYER_FLOOR:      {"name": "Floor",      "char": "f", "color": (255, 255, 100, 128)},
    
    # Standard Tile & Decoration layer for items behind the Main layer.
    LAYER_BACKGROUND: {"name": "Background", "char": "b", "color": (100, 150, 255, 128)},
    
    # Standard Tile & Decoration layer. Default for most furniture and characters.
    LAYER_MAIN:       {"name": "Main",       "char": "m", "color": (100, 255, 150, 128)},
    
    # Standard Tile & Decoration layer for items in front of the Main layer.
    # Note: 'f' char is reused, but in structure.json it always means Foreground, as Floor layer is never saved.
    LAYER_FOREGROUND: {"name": "Foreground", "char": "f", "color": (255, 150, 100, 128)},
}

LAYER_CHARS_TO_ID = {data["char"]: layer_id for layer_id, data in LAYER_DATA.items()}
DEFAULT_LAYER = LAYER_MAIN

# --- Wall Edges ---
EDGE_NE = "ne"; EDGE_SE = "se"; EDGE_SW = "sw"; EDGE_NW = "nw"
EDGE_DIAG_SW_NE = "diag_sw_ne"
EDGE_DIAG_NW_SE = "diag_nw_se"

# --- MAPPING TILE TYPES TO THEIR VALID EDGES ---
TILE_TYPE_EDGES = {
    TILE_TYPE_FULL: [EDGE_NE, EDGE_SE, EDGE_SW, EDGE_NW],
    TILE_TYPE_CORNER_NO_TL: [EDGE_NE, EDGE_SE, EDGE_DIAG_SW_NE],
    TILE_TYPE_CORNER_NO_TR: [EDGE_NW, EDGE_SW, EDGE_DIAG_SW_NE],
    TILE_TYPE_CORNER_NO_BR: [EDGE_NW, EDGE_NE, EDGE_DIAG_NW_SE],
    TILE_TYPE_CORNER_NO_BL: [EDGE_SE, EDGE_SW, EDGE_DIAG_NW_SE],
}

# --- Main Editor Modes ---
EDITOR_MODE_STRUCTURE = 0
EDITOR_MODE_DECORATIONS = 1

# --- Decoration ---
DECO_ROTATION_MAP = [2, 4, 6, 0]