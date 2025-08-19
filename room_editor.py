import pygame
import json
import sys
import os
import tkinter as tk
from tkinter import filedialog
import math

# --- Constants and Configuration ---
INITIAL_WIN_WIDTH, INITIAL_WIN_HEIGHT = 1280, 720
TOOLBAR_HEIGHT = 40
RIGHT_PANEL_WIDTH = 280
PREVIEW_SIZE = (240, 240)
TILE_WIDTH, TILE_HEIGHT = 64, 32
TILE_WIDTH_HALF, TILE_HEIGHT_HALF = TILE_WIDTH // 2, TILE_HEIGHT // 2
WALL_HEIGHT = 96 # 3 * TILE_HEIGHT

COLOR_BG = (20, 30, 40)
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

# --- Tile Types ---
TILE_TYPE_FULL = 1; TILE_TYPE_CORNER_NO_TL = 2; TILE_TYPE_CORNER_NO_TR = 3
TILE_TYPE_CORNER_NO_BR = 4; TILE_TYPE_CORNER_NO_BL = 5
TILE_TYPES = [TILE_TYPE_FULL, TILE_TYPE_CORNER_NO_TL, TILE_TYPE_CORNER_NO_TR, TILE_TYPE_CORNER_NO_BR, TILE_TYPE_CORNER_NO_BL]

# --- Edit Modes ---
MODE_TILES = 0; MODE_WALLS = 1

# --- Wall Edges ---
EDGE_NE = "ne"; EDGE_SE = "se"; EDGE_SW = "sw"; EDGE_NW = "nw"
EDGE_DIAG_SW_NE = "diag_sw_ne"
EDGE_DIAG_NW_SE = "diag_nw_se"

# --- MAPPING TILE TYPES TO THEIR VALID EDGES ---
TILE_TYPE_EDGES = {
    TILE_TYPE_FULL: [EDGE_NE, EDGE_SE, EDGE_SW, EDGE_NW],
    TILE_TYPE_CORNER_NO_TL: [EDGE_NE, EDGE_SE, EDGE_DIAG_SW_NE],
    TILE_TYPE_CORNER_NO_TR: [EDGE_NW, EDGE_SW, EDGE_DIAG_NW_SE],
    TILE_TYPE_CORNER_NO_BR: [EDGE_NW, EDGE_NE, EDGE_DIAG_SW_NE],
    TILE_TYPE_CORNER_NO_BL: [EDGE_SE, EDGE_SW, EDGE_DIAG_NW_SE],
}

NEW_ROOM_TEMPLATE = {
    "name": "New Room", "id": "new_room_01",
    "dimensions": {"width": 0, "depth": 0, "origin_x": 0, "origin_y": 0},
    "renderAnchor": {"x": 0, "y": 0}, "tiles": [], "walls": []
}

# --- Helper Classes ---
class Button:
    def __init__(self, x, y, w, h, text, font): self.rect = pygame.Rect(x, y, w, h); self.text = text; self.font = font; self.is_hovered = False
    def draw(self, screen, is_active=False):
        color = COLOR_BUTTON_ACTIVE if is_active else (COLOR_BUTTON_HOVER if self.is_hovered else COLOR_BUTTON)
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        if self.text:
            ts = self.font.render(self.text, True, COLOR_TEXT)
            tr = ts.get_rect(center=self.rect.center)
            screen.blit(ts, tr)
    def check_hover(self, m_pos): self.is_hovered = self.rect.collidepoint(m_pos)
    def is_clicked(self, event): return self.is_hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

class TextInputBox:
    def __init__(self, x, y, w, h, font, text=''): self.rect = pygame.Rect(x, y, w, h); self.color = COLOR_INPUT_INACTIVE; self.text = text; self.font = font; self.txt_surface = self.font.render(text, True, self.color); self.active = False; self.cursor_visible = True; self.cursor_timer = 0
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN: self.active = self.rect.collidepoint(event.pos); self.color = COLOR_TEXT if self.active else COLOR_INPUT_INACTIVE
        if event.type == pygame.KEYDOWN and self.active:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): return self.text
            elif event.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            elif event.unicode.isdigit() or (event.unicode == '.' and '.' not in self.text) or (event.unicode == '-' and not self.text): self.text += event.unicode
            self.txt_surface = self.font.render(self.text, True, COLOR_TEXT)
        return None
    def update(self):
        if self.active: self.cursor_timer = (self.cursor_timer + 1) % 60; self.cursor_visible = self.cursor_timer < 30
    def draw(self, screen):
        pygame.draw.rect(screen, COLOR_EDITOR_BG, self.rect); pygame.draw.rect(screen, COLOR_INPUT_ACTIVE if self.active else self.color, self.rect, 2); screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        if self.active and self.cursor_visible: c_pos = self.rect.x + 5 + self.txt_surface.get_width(); pygame.draw.line(screen, COLOR_TEXT, (c_pos, self.rect.y + 5), (c_pos, self.rect.y + self.rect.h - 5))
    def set_text(self, text): self.text = str(text); self.txt_surface = self.font.render(self.text, True, COLOR_TEXT)

# --- Main Editor Class ---
class RoomEditor:
    def __init__(self):
        pygame.init()
        self.root = tk.Tk()
        self.root.withdraw()

        self.win_width, self.win_height = INITIAL_WIN_WIDTH, INITIAL_WIN_HEIGHT
        self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
        pygame.display.set_caption("Isometric Room Editor")
        self.clock = pygame.time.Clock()
        self.font_ui = pygame.font.SysFont("Arial", 14); self.font_title = pygame.font.SysFont("Arial", 18, bold=True); self.font_info = pygame.font.SysFont("Consolas", 12)
        self.is_panning = False; self.pan_start_pos = (0, 0); self.camera_offset = [0, 0]
        self.is_painting = False; self.is_erasing = False
        self.room_data = None; self.current_filepath = None
        self.hover_grid_pos = None; self.hover_wall_edge = None
        self.tiles = {}; self.walls = set()
        self.edit_mode = MODE_TILES
        self.save_confirmation_timer = 0
        self.update_layout()
        self.create_new_room()

    def update_layout(self):
        margin = 15
        self.toolbar_rect = pygame.Rect(0, 0, self.win_width, TOOLBAR_HEIGHT)
        self.buttons = {"new": Button(margin, 8, 60, 25, "New", self.font_ui), "load": Button(margin + 70, 8, 60, 25, "Load", self.font_ui), "save": Button(margin + 140, 8, 60, 25, "Save", self.font_ui), "save_as": Button(margin + 210, 8, 90, 25, "Save As...", self.font_ui)}
        self.right_panel_rect = pygame.Rect(self.win_width - RIGHT_PANEL_WIDTH, TOOLBAR_HEIGHT, RIGHT_PANEL_WIDTH, self.win_height - TOOLBAR_HEIGHT)
        self.editor_rect = pygame.Rect(0, TOOLBAR_HEIGHT, self.win_width - RIGHT_PANEL_WIDTH, self.win_height - TOOLBAR_HEIGHT)
        self.editor_surface = pygame.Surface(self.editor_rect.size, pygame.SRCALPHA)
        self.preview_rect = pygame.Rect(self.right_panel_rect.x + (RIGHT_PANEL_WIDTH - PREVIEW_SIZE[0]) // 2, self.right_panel_rect.y + margin + 20, PREVIEW_SIZE[0], PREVIEW_SIZE[1])
        self.preview_surface = pygame.Surface(PREVIEW_SIZE)
        input_y = self.preview_rect.bottom + 35
        self.anchor_offset_input_x = TextInputBox(self.preview_rect.left, input_y, 100, 25, self.font_ui)
        self.anchor_offset_input_y = TextInputBox(self.preview_rect.right - 100, input_y, 100, 25, self.font_ui)
        self.input_boxes = [self.anchor_offset_input_x, self.anchor_offset_input_y]
        center_btn_y = self.anchor_offset_input_x.rect.bottom + 5
        self.buttons["center_anchor"] = Button(self.preview_rect.centerx - 60, center_btn_y, 120, 22, "Center Anchor", self.font_ui)
        mode_btn_y = self.buttons["center_anchor"].rect.bottom + 20
        self.buttons["mode_tile"] = Button(self.preview_rect.left, mode_btn_y, 100, 55, "", self.font_ui)
        self.buttons["mode_wall"] = Button(self.preview_rect.right - 100, mode_btn_y, 100, 55, "", self.font_ui)
        if hasattr(self, 'room_data') and self.room_data: self.update_anchor_offset_inputs()

    def grid_to_screen(self, grid_x, grid_y, offset): sx = (grid_x - grid_y) * TILE_WIDTH_HALF + offset[0]; sy = (grid_x + grid_y) * TILE_HEIGHT_HALF + offset[1]; return int(sx), int(sy)
    def screen_to_grid(self, screen_x, screen_y, offset): wx = screen_x - offset[0] - TILE_WIDTH_HALF; wy = screen_y - offset[1] - TILE_HEIGHT_HALF; gx = round((wx / TILE_WIDTH_HALF + wy / TILE_HEIGHT_HALF) / 2); gy = round((wy / TILE_HEIGHT_HALF - wx / TILE_WIDTH_HALF) / 2); return int(gx), int(gy)

    def _populate_internal_data_from_json(self):
        self.tiles.clear(); self.walls.clear()
        dims = self.room_data['dimensions']; ox, oy = dims.get('origin_x', 0), dims.get('origin_y', 0)
        for y, row in enumerate(self.room_data.get('tiles', [])):
            for x, char_val in enumerate(row):
                if char_val != '0': self.tiles[(x + ox, y + oy)] = int(char_val)
        for wall_data in self.room_data.get('walls', []):
            self.walls.add((tuple(wall_data['grid_pos']), wall_data['edge']))

    def calculate_room_center(self):
        if not self.tiles: return (0, 0)
        all_x = [p[0] for p in self.tiles.keys()]; all_y = [p[1] for p in self.tiles.keys()]
        center_gx = (min(all_x) + max(all_x)) / 2; center_gy = (min(all_y) + max(all_y)) / 2
        return self.grid_to_screen(center_gx, center_gy, (TILE_WIDTH_HALF, TILE_HEIGHT_HALF))

    def update_anchor_offset_inputs(self):
        center_wx, center_wy = self.calculate_room_center()
        offset_x = self.room_data['renderAnchor']['x'] - center_wx; offset_y = self.room_data['renderAnchor']['y'] - center_wy
        self.anchor_offset_input_x.set_text(f"{offset_x:.0f}"); self.anchor_offset_input_y.set_text(f"{offset_y:.0f}")

    def apply_anchor_offset(self):
        try:
            offset_x = float(self.anchor_offset_input_x.text); offset_y = float(self.anchor_offset_input_y.text)
            center_wx, center_wy = self.calculate_room_center()
            self.room_data['renderAnchor']['x'] = center_wx + offset_x; self.room_data['renderAnchor']['y'] = center_wy + offset_y
        except ValueError: print(f"Invalid offset input."); self.update_anchor_offset_inputs()

    def reset_camera(self): self.camera_offset = [self.editor_surface.get_width() / 2, self.editor_surface.get_height() / 2]
    def create_new_room(self): self.room_data = json.loads(json.dumps(NEW_ROOM_TEMPLATE)); self._populate_internal_data_from_json(); self.current_filepath = None; pygame.display.set_caption("Editor - Untitled"); self.reset_camera(); self.update_anchor_offset_inputs()
    
    def load_room(self):
        initial_dir = os.path.join(os.getcwd(), "rooms"); os.makedirs(initial_dir, exist_ok=True)
        fp = filedialog.askopenfilename(parent=self.root, initialdir=initial_dir, title="Load Room", filetypes=(("JSON files", "*.json"),))
        self.root.update() # Force Tkinter to process events and release focus
        if not fp: return
        try:
            with open(fp, 'r') as f: self.room_data = json.load(f)
            self._populate_internal_data_from_json(); self.current_filepath = fp; pygame.display.set_caption(f"Editor - {os.path.basename(fp)}"); self.reset_camera(); self.update_anchor_offset_inputs()
        except Exception as e: print(f"Error loading file: {e}")

    def save_room(self, save_as=False):
        if not self.room_data: return
        fp = self.current_filepath
        if save_as or not fp:
            initial_dir = os.path.join(os.getcwd(), "rooms"); os.makedirs(initial_dir, exist_ok=True)
            fp = filedialog.asksaveasfilename(parent=self.root, initialdir=initial_dir, title="Save Room As", defaultextension=".json", filetypes=(("JSON files", "*.json"),))
            self.root.update() # Force Tkinter to process events and release focus
        if not fp: return

        if not self.tiles: min_x, min_y, max_x, max_y = 0, 0, 0, 0
        else: all_x = [p[0] for p in self.tiles.keys()]; all_y = [p[1] for p in self.tiles.keys()]; min_x, max_x = min(all_x), max(all_x); min_y, max_y = min(all_y), max(all_y)
        new_w = max_x - min_x + 1; new_d = max_y - min_y + 1; new_grid = [['0'] * new_w for _ in range(new_d)]
        for (gx, gy), tile_type in self.tiles.items(): new_grid[gy - min_y][gx - min_x] = str(tile_type)
        dts = self.room_data.copy(); dts['dimensions'] = {'width': new_w, 'depth': new_d, 'origin_x': min_x, 'origin_y': min_y}; dts['tiles'] = ["".join(row) for row in new_grid]
        dts['walls'] = [{"grid_pos": list(pos), "edge": edge} for pos, edge in sorted(list(self.walls))]
        try:
            with open(fp, 'w') as f: json.dump(dts, f, indent=2)
            self.current_filepath = fp; pygame.display.set_caption(f"Editor - {os.path.basename(fp)}")
            self.save_confirmation_timer = 120
        except Exception as e: print(f"Error saving file: {e}")

    def point_to_line_segment_dist(self, p, a, b):
        px, py = p; ax, ay = a; bx, by = b
        line_mag_sq = (bx - ax)**2 + (by - ay)**2
        if line_mag_sq == 0: return math.hypot(px - ax, py - ay)
        u = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / line_mag_sq
        u = max(0, min(1, u))
        ix = ax + u * (bx - ax); iy = ay + u * (by - ay)
        return math.hypot(px - ix, py - iy)

    def get_hovered_edge(self, grid_pos, screen_mouse_pos):
        if grid_pos not in self.tiles: return None
        tile_type = self.tiles[grid_pos]
        tile_screen_pos = self.grid_to_screen(*grid_pos, self.camera_offset)
        p = self.get_tile_points(tile_screen_pos)
        gx, gy = grid_pos
        edge_definitions = {
            EDGE_NE: {'seg': (p['top'], p['right']), 'neighbor': (gx, gy - 1)},
            EDGE_SE: {'seg': (p['right'], p['bottom']), 'neighbor': (gx + 1, gy)},
            EDGE_SW: {'seg': (p['bottom'], p['left']), 'neighbor': (gx, gy + 1)},
            EDGE_NW: {'seg': (p['left'], p['top']), 'neighbor': (gx - 1, gy)},
            EDGE_DIAG_SW_NE: {'seg': (p['bottom'], p['top']), 'neighbor': None},
            EDGE_DIAG_NW_SE: {'seg': (p['left'], p['right']), 'neighbor': None},
        }
        best_edge = None; min_dist = 15
        valid_edges_for_shape = TILE_TYPE_EDGES.get(tile_type, [])
        for edge_name in valid_edges_for_shape:
            data = edge_definitions[edge_name]
            is_valid_to_place = (data['neighbor'] is None) or (data['neighbor'] not in self.tiles)
            if is_valid_to_place:
                dist = self.point_to_line_segment_dist(screen_mouse_pos, *data['seg'])
                if dist < min_dist:
                    min_dist = dist
                    best_edge = (grid_pos, edge_name)
        return best_edge

    def delete_tile(self, grid_pos):
        if not grid_pos or grid_pos not in self.tiles: return
        self.tiles.pop(grid_pos, None)
        self.walls = {wall for wall in self.walls if wall[0] != grid_pos}
        self.update_anchor_offset_inputs()

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed(); shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]; alt = keys[pygame.K_LALT] or keys[pygame.K_RALT]
        local_mouse_pos = (mouse_pos[0] - self.editor_rect.x, mouse_pos[1] - self.editor_rect.y)
        
        self.hover_grid_pos = None; self.hover_wall_edge = None
        if self.editor_rect.collidepoint(mouse_pos) and not self.is_panning:
            self.hover_grid_pos = self.screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.camera_offset)
            if self.edit_mode == MODE_WALLS:
                self.hover_wall_edge = self.get_hovered_edge(self.hover_grid_pos, local_mouse_pos)

        for btn in self.buttons.values(): btn.check_hover(mouse_pos)
        
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE: self.win_width, self.win_height = event.size; self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE); self.update_layout()
            if event.type == pygame.QUIT: return False
            for box in self.input_boxes:
                if box.handle_event(event) is not None: self.apply_anchor_offset(); box.active = False
            
            if self.buttons['new'].is_clicked(event): self.create_new_room()
            elif self.buttons['load'].is_clicked(event): self.load_room()
            elif self.buttons['save'].is_clicked(event): self.save_room()
            elif self.buttons['save_as'].is_clicked(event): self.save_room(save_as=True)
            elif self.buttons['center_anchor'].is_clicked(event): center_wx, center_wy = self.calculate_room_center(); self.room_data['renderAnchor']['x'], self.room_data['renderAnchor']['y'] = center_wx, center_wy; self.update_anchor_offset_inputs()
            elif self.buttons['mode_tile'].is_clicked(event): self.edit_mode = MODE_TILES
            elif self.buttons['mode_wall'].is_clicked(event): self.edit_mode = MODE_WALLS

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2 and self.editor_rect.collidepoint(mouse_pos): self.is_panning = True; self.pan_start_pos = event.pos
                elif self.hover_grid_pos and not any(b.active for b in self.input_boxes):
                    if self.edit_mode == MODE_WALLS and event.button == 1 and self.hover_wall_edge:
                        if self.hover_wall_edge in self.walls: self.walls.remove(self.hover_wall_edge)
                        else: self.walls.add(self.hover_wall_edge)
                    elif self.edit_mode == MODE_TILES:
                        if event.button == 1:
                            if shift: w_mouse_x = local_mouse_pos[0] - self.camera_offset[0]; w_mouse_y = local_mouse_pos[1] - self.camera_offset[1]; self.room_data["renderAnchor"]["x"], self.room_data["renderAnchor"]["y"] = w_mouse_x, w_mouse_y; self.update_anchor_offset_inputs()
                            elif alt: self.tiles[self.hover_grid_pos] = TILE_TYPES[(TILE_TYPES.index(self.tiles.get(self.hover_grid_pos, TILE_TYPE_FULL)) + 1) % len(TILE_TYPES)]; self.update_anchor_offset_inputs()
                            else: self.is_painting = True; self.tiles[self.hover_grid_pos] = TILE_TYPE_FULL; self.update_anchor_offset_inputs()
                        elif event.button == 3: 
                            self.is_erasing = True
                            self.delete_tile(self.hover_grid_pos)

            if event.type == pygame.MOUSEBUTTONUP: self.is_painting = False; self.is_erasing = False; self.is_panning = False
            if event.type == pygame.MOUSEMOTION:
                if self.is_panning: delta = (event.pos[0] - self.pan_start_pos[0], event.pos[1] - self.pan_start_pos[1]); self.camera_offset[0] += delta[0]; self.camera_offset[1] += delta[1]; self.pan_start_pos = event.pos
                elif self.edit_mode == MODE_TILES and self.hover_grid_pos and not shift and not alt:
                    if self.is_painting: self.tiles[self.hover_grid_pos] = TILE_TYPE_FULL; self.update_anchor_offset_inputs()
                    elif self.is_erasing:
                        self.delete_tile(self.hover_grid_pos)

        if not any(b.active for b in self.input_boxes):
            nudge = 10 if shift else 1; moved = False
            if keys[pygame.K_LEFT]: self.room_data["renderAnchor"]["x"] -= nudge; moved = True
            if keys[pygame.K_RIGHT]: self.room_data["renderAnchor"]["x"] += nudge; moved = True
            if keys[pygame.K_UP]: self.room_data["renderAnchor"]["y"] -= nudge; moved = True
            if keys[pygame.K_DOWN]: self.room_data["renderAnchor"]["y"] += nudge; moved = True
            if moved: self.update_anchor_offset_inputs()
        return True

    def get_tile_points(self, pos): return {"top": (pos[0] + TILE_WIDTH_HALF, pos[1]), "right": (pos[0] + TILE_WIDTH, pos[1] + TILE_HEIGHT_HALF), "bottom": (pos[0] + TILE_WIDTH_HALF, pos[1] + TILE_HEIGHT), "left": (pos[0], pos[1] + TILE_HEIGHT_HALF)}

    def draw_tile_shape(self, surf, pos, tile_type, fill_color, border_color):
        p = self.get_tile_points(pos)
        points_map = {
            TILE_TYPE_FULL: [p['top'], p['right'], p['bottom'], p['left']], TILE_TYPE_CORNER_NO_TL: [p['top'], p['right'], p['bottom']],
            TILE_TYPE_CORNER_NO_TR: [p['top'], p['bottom'], p['left']], TILE_TYPE_CORNER_NO_BR: [p['top'], p['right'], p['left']],
            TILE_TYPE_CORNER_NO_BL: [p['right'], p['bottom'], p['left']]
        }
        points = points_map.get(tile_type)
        if points: pygame.draw.polygon(surf, fill_color, points); pygame.draw.polygon(surf, border_color, points, 2)
            
    def draw_wall(self, surf, screen_pos, edge):
        p = self.get_tile_points(screen_pos)
        edge_points = {
            EDGE_NE: (p['top'], p['right']), EDGE_SE: (p['right'], p['bottom']),
            EDGE_SW: (p['bottom'], p['left']), EDGE_NW: (p['left'], p['top']),
            EDGE_DIAG_SW_NE: (p['bottom'], p['top']), EDGE_DIAG_NW_SE: (p['left'], p['right'])
        }
        p1, p2 = edge_points.get(edge, (None, None))
        if p1 and p2:
            wall_points = [p1, p2, (p2[0], p2[1] - WALL_HEIGHT), (p1[0], p1[1] - WALL_HEIGHT)]
            pygame.draw.polygon(surf, COLOR_WALL, wall_points); pygame.draw.polygon(surf, COLOR_WALL_BORDER, wall_points, 2)
    
    def draw_room_on_surface(self, surf, offset, is_editor):
        surf.fill(COLOR_EDITOR_BG if is_editor else COLOR_PREVIEW_BG)
        if not self.room_data: return
        origin_pos = self.grid_to_screen(0, 0, offset)
        pygame.draw.line(surf, COLOR_ORIGIN, (origin_pos[0] - 10, origin_pos[1]), (origin_pos[0] + 10, origin_pos[1]), 1)
        pygame.draw.line(surf, COLOR_ORIGIN, (origin_pos[0], origin_pos[1] - 10), (origin_pos[0], origin_pos[1] + 10), 1)
        
        sorted_items = sorted(self.tiles.keys(), key=lambda k: (k[1], k[0]))
        for gx, gy in sorted_items:
            screen_pos = self.grid_to_screen(gx, gy, offset)
            self.draw_tile_shape(surf, screen_pos, self.tiles[(gx, gy)], COLOR_TILE, COLOR_TILE_BORDER)
            for pos, edge in self.walls:
                if pos == (gx, gy):
                    self.draw_wall(surf, screen_pos, edge)

        anchor_pos = (self.room_data["renderAnchor"]["x"] + offset[0], self.room_data["renderAnchor"]["y"] + offset[1])
        pygame.draw.circle(surf, COLOR_ANCHOR, anchor_pos, 5); pygame.draw.line(surf, COLOR_ANCHOR, (anchor_pos[0] - 8, anchor_pos[1]), (anchor_pos[0] + 8, anchor_pos[1]), 1); pygame.draw.line(surf, COLOR_ANCHOR, (anchor_pos[0], anchor_pos[1] - 8), (anchor_pos[0], anchor_pos[1] + 8), 1)

        if is_editor:
            ax, ay = self.room_data["renderAnchor"]["x"], self.room_data["renderAnchor"]["y"]
            pw, ph = PREVIEW_SIZE
            screen_x = (ax - pw / 2) + offset[0]
            screen_y = (ay - ph / 2) + offset[1]
            preview_bounds_rect = pygame.Rect(screen_x, screen_y, pw, ph)
            pygame.draw.rect(surf, COLOR_PREVIEW_OUTLINE, preview_bounds_rect, 1)

        if is_editor and self.edit_mode == MODE_TILES and self.hover_grid_pos:
            hover_screen_pos = self.grid_to_screen(*self.hover_grid_pos, offset)
            p = self.get_tile_points(hover_screen_pos)
            pygame.draw.polygon(surf, COLOR_HOVER_BORDER, [p['top'], p['right'], p['bottom'], p['left']], 3)
        elif is_editor and self.edit_mode == MODE_WALLS and self.hover_wall_edge:
            pos, edge = self.hover_wall_edge
            hover_screen_pos = self.grid_to_screen(*pos, offset)
            p = self.get_tile_points(hover_screen_pos)
            edge_points = {
                EDGE_NE: (p['top'], p['right']), EDGE_SE: (p['right'], p['bottom']),
                EDGE_SW: (p['bottom'], p['left']), EDGE_NW: (p['left'], p['top']),
                EDGE_DIAG_SW_NE: (p['bottom'], p['top']), EDGE_DIAG_NW_SE: (p['left'], p['right'])
            }
            p1, p2 = edge_points.get(edge, (None, None))
            if p1 and p2: pygame.draw.line(surf, COLOR_HOVER_BORDER, p1, p2, 4)

    def calculate_preview_offset(self, surface_size):
        if self.room_data and "renderAnchor" in self.room_data: ax, ay = self.room_data["renderAnchor"]["x"], self.room_data["renderAnchor"]["y"]; return (surface_size[0] / 2 - ax, surface_size[1] / 2 - ay)
        return (0, 0)

    def draw_mode_button_icon(self, screen, button_name, rect):
        center_x, top_y = rect.centerx, rect.top + 12
        if button_name == "mode_tile":
            points = [(center_x, top_y - 8), (center_x + 16, top_y), (center_x, top_y + 8), (center_x - 16, top_y)]
            pygame.draw.polygon(screen, COLOR_TILE, points); pygame.draw.polygon(screen, COLOR_TILE_BORDER, points, 1)
        elif button_name == "mode_wall":
            t_center_x, t_center_y = center_x, top_y + 8
            t_points = [(t_center_x, t_center_y - 4), (t_center_x + 8, t_center_y), (t_center_x, t_center_y + 4), (t_center_x - 8, t_center_y)]
            pygame.draw.polygon(screen, COLOR_TILE, t_points)
            p1, p2 = t_points[3], t_points[0]
            wall_points = [p1, p2, (p2[0], p2[1] - 12), (p1[0], p1[1] - 12)]
            pygame.draw.polygon(screen, COLOR_WALL, wall_points); pygame.draw.polygon(screen, COLOR_WALL_BORDER, wall_points, 1)

    def draw(self):
        self.screen.fill(COLOR_BG)
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, self.toolbar_rect); pygame.draw.rect(self.screen, COLOR_PANEL_BG, self.right_panel_rect)
        preview_offset = self.calculate_preview_offset(self.preview_surface.get_size())
        self.draw_room_on_surface(self.editor_surface, self.camera_offset, True); self.draw_room_on_surface(self.preview_surface, preview_offset, False)
        self.screen.blit(self.editor_surface, self.editor_rect); self.screen.blit(self.preview_surface, self.preview_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.editor_rect, 1); pygame.draw.rect(self.screen, COLOR_BORDER, self.right_panel_rect, 1); pygame.draw.rect(self.screen, COLOR_BORDER, self.preview_rect, 1)
        self.screen.blit(self.font_title.render("Preview", True, COLOR_TITLE_TEXT), (self.preview_rect.x, self.preview_rect.y - 22))
        
        for name, btn in self.buttons.items():
            is_active = (name == 'mode_tile' and self.edit_mode == MODE_TILES) or (name == 'mode_wall' and self.edit_mode == MODE_WALLS)
            btn.draw(self.screen, is_active)
            if name in ['mode_tile', 'mode_wall']:
                self.draw_mode_button_icon(self.screen, name, btn.rect)
                text_str = "Tiles" if name == 'mode_tile' else "Walls"
                ts = self.font_ui.render(text_str, True, COLOR_TEXT)
                tr = ts.get_rect(centerx=btn.rect.centerx, bottom=btn.rect.bottom - 8)
                self.screen.blit(ts, tr)

        self.screen.blit(self.font_info.render("Offset X:", True, COLOR_INFO_TEXT), (self.anchor_offset_input_x.rect.left, self.anchor_offset_input_x.rect.top - 15))
        self.screen.blit(self.font_info.render("Offset Y:", True, COLOR_INFO_TEXT), (self.anchor_offset_input_y.rect.left, self.anchor_offset_input_y.rect.top - 15))
        for box in self.input_boxes: box.update(); box.draw(self.screen)
        
        margin, padding, line_height = 15, 8, 15
        info_lines_base = ["Controls:", "[Middle Mouse] Pan View", "[Shift+Click] Set Anchor", "[Arrow Keys] Nudge Anchor (Shift+)"]
        info_lines_mode = ["[Click] Paint Tile", "[Drag] Paint/Erase", "[Alt+Click] Cycle Corner"] if self.edit_mode == MODE_TILES else ["[Click Edge] Toggle Wall"]
        info_lines = info_lines_base[:1] + info_lines_mode + info_lines_base[1:]
        rendered_lines = [self.font_info.render(line, True, COLOR_INFO_TEXT) for line in info_lines]
        box_w = max(line.get_width() for line in rendered_lines) + padding * 2; box_h = len(info_lines) * line_height + padding * 2
        box_rect = pygame.Rect(0, 0, box_w, box_h); box_rect.bottomright = (self.right_panel_rect.right - margin, self.right_panel_rect.bottom - margin)
        pygame.draw.rect(self.screen, COLOR_EDITOR_BG, box_rect, border_radius=5); pygame.draw.rect(self.screen, COLOR_BORDER, box_rect, 1, border_radius=5)
        for i, line_surf in enumerate(rendered_lines): self.screen.blit(line_surf, (box_rect.left + padding, box_rect.top + padding + i * line_height))
        
        if self.save_confirmation_timer > 0:
            self.save_confirmation_timer -= 1
            save_text_surf = self.font_title.render("File Saved!", True, COLOR_TEXT)
            text_rect = save_text_surf.get_rect()
            
            bg_rect = text_rect.inflate(30, 20)
            bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, COLOR_SAVE_CONFIRM_BG, bg_surf.get_rect(), border_radius=8)
            
            bg_rect.center = self.editor_rect.center
            text_rect.center = bg_rect.center
            
            self.screen.blit(bg_surf, bg_rect)
            self.screen.blit(save_text_surf, text_rect)

        pygame.display.flip()

    def run(self):
        running = True
        try:
            while running: running = self.handle_events(); self.draw(); self.clock.tick(60)
        except KeyboardInterrupt: print("\nClosing editor.")
        finally:
            pygame.quit()
            sys.exit()

if __name__ == "__main__":
    try: os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except NameError: pass
    RoomEditor().run()