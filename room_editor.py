import pygame
import json
import sys
import os
import tkinter as tk
from tkinter import filedialog

# --- Constants and Configuration ---
INITIAL_WIN_WIDTH, INITIAL_WIN_HEIGHT = 1280, 720
TOOLBAR_HEIGHT = 40
RIGHT_PANEL_WIDTH = 280
PREVIEW_SIZE = (240, 240)
TILE_WIDTH, TILE_HEIGHT = 64, 32
TILE_WIDTH_HALF, TILE_HEIGHT_HALF = TILE_WIDTH // 2, TILE_HEIGHT // 2

COLOR_BG = (20, 30, 40)
COLOR_PANEL_BG = (35, 45, 55)
COLOR_EDITOR_BG = (45, 55, 65)
COLOR_PREVIEW_BG = (0, 0, 0)
COLOR_BORDER = (80, 90, 100)
COLOR_BUTTON = (70, 80, 90)
COLOR_BUTTON_HOVER = (100, 110, 120)
COLOR_TEXT = (200, 200, 210)
COLOR_INFO_TEXT = (130, 140, 150)
COLOR_TITLE_TEXT = (150, 160, 170)
COLOR_ANCHOR = (255, 100, 100)
COLOR_INPUT_ACTIVE = (230, 230, 230)
COLOR_INPUT_INACTIVE = (150, 150, 150)
COLOR_TILE = (180, 140, 100)
COLOR_TILE_BORDER = (100, 100, 100)
COLOR_TILE_HOVER = (210, 170, 130)
COLOR_ORIGIN = (100, 120, 140)
COLOR_HOVER_BORDER = (255, 255, 0)  # Bright Yellow

# --- Tile Types ---
TILE_TYPE_FULL = 1
TILE_TYPE_CORNER_NO_TL = 2  # Triangle pointing Down-Right
TILE_TYPE_CORNER_NO_TR = 3  # Triangle pointing Down-Left
TILE_TYPE_CORNER_NO_BR = 4  # Triangle pointing Up-Left
TILE_TYPE_CORNER_NO_BL = 5  # Triangle pointing Up-Right
TILE_TYPES = [TILE_TYPE_FULL, TILE_TYPE_CORNER_NO_TL, TILE_TYPE_CORNER_NO_TR, TILE_TYPE_CORNER_NO_BR, TILE_TYPE_CORNER_NO_BL]
NUM_TILE_TYPES = len(TILE_TYPES)

NEW_ROOM_TEMPLATE = {
    "name": "New Room",
    "id": "new_room_01",
    "dimensions": {"width": 0, "depth": 0, "origin_x": 0, "origin_y": 0},
    "renderAnchor": {"x": 0, "y": 0},
    "tiles": []
}

# --- Helper Classes ---
class Button:
    def __init__(self, x, y, w, h, text, font): self.rect = pygame.Rect(x, y, w, h); self.text = text; self.font = font; self.is_hovered = False
    def draw(self, screen): color = COLOR_BUTTON_HOVER if self.is_hovered else COLOR_BUTTON; pygame.draw.rect(screen, color, self.rect, border_radius=5); ts = self.font.render(self.text, True, COLOR_TEXT); tr = ts.get_rect(center=self.rect.center); screen.blit(ts, tr)
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
        self.win_width, self.win_height = INITIAL_WIN_WIDTH, INITIAL_WIN_HEIGHT
        self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
        pygame.display.set_caption("Isometric Room Editor")
        self.clock = pygame.time.Clock()
        self.font_ui = pygame.font.SysFont("Arial", 14)
        self.font_title = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_info = pygame.font.SysFont("Consolas", 12)
        self.is_panning = False
        self.pan_start_pos = (0, 0)
        self.camera_offset = [0, 0]
        self.is_painting = False
        self.is_erasing = False
        self.room_data = None
        self.current_filepath = None
        self.hover_grid_pos = None
        self.tiles = {}
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
        if hasattr(self, 'room_data') and self.room_data: self.update_anchor_offset_inputs()

    def grid_to_screen(self, grid_x, grid_y, offset): sx = (grid_x - grid_y) * TILE_WIDTH_HALF + offset[0]; sy = (grid_x + grid_y) * TILE_HEIGHT_HALF + offset[1]; return int(sx), int(sy)
    def screen_to_grid(self, screen_x, screen_y, offset): wx = screen_x - offset[0] - TILE_WIDTH_HALF; wy = screen_y - offset[1] - TILE_HEIGHT_HALF; gx = round((wx / TILE_WIDTH_HALF + wy / TILE_HEIGHT_HALF) / 2); gy = round((wy / TILE_HEIGHT_HALF - wx / TILE_WIDTH_HALF) / 2); return int(gx), int(gy)

    def _populate_internal_tiles_from_json(self):
        self.tiles.clear()
        dims = self.room_data['dimensions']
        ox, oy = dims.get('origin_x', 0), dims.get('origin_y', 0)
        for y, row in enumerate(self.room_data['tiles']):
            for x, char_val in enumerate(row):
                if char_val != '0':
                    tile_type = TILE_TYPE_FULL if char_val == '1' else int(char_val)
                    self.tiles[(x + ox, y + oy)] = tile_type

    def calculate_room_center(self):
        if not self.tiles: return (0, 0)
        all_x = [p[0] for p in self.tiles.keys()]; all_y = [p[1] for p in self.tiles.keys()]
        center_gx = (min(all_x) + max(all_x)) / 2; center_gy = (min(all_y) + max(all_y)) / 2
        center_wx, center_wy = self.grid_to_screen(center_gx, center_gy, (0, 0))
        return (center_wx + TILE_WIDTH_HALF, center_wy + TILE_HEIGHT_HALF)

    def update_anchor_offset_inputs(self):
        center_wx, center_wy = self.calculate_room_center()
        offset_x = self.room_data['renderAnchor']['x'] - center_wx
        offset_y = self.room_data['renderAnchor']['y'] - center_wy
        self.anchor_offset_input_x.set_text(f"{offset_x:.0f}")
        self.anchor_offset_input_y.set_text(f"{offset_y:.0f}")

    def apply_anchor_offset(self):
        try:
            offset_x = float(self.anchor_offset_input_x.text)
            offset_y = float(self.anchor_offset_input_y.text)
            center_wx, center_wy = self.calculate_room_center()
            self.room_data['renderAnchor']['x'] = center_wx + offset_x
            self.room_data['renderAnchor']['y'] = center_wy + offset_y
        except ValueError:
            print(f"Invalid offset input."); self.update_anchor_offset_inputs()

    def reset_camera(self): self.camera_offset = [self.editor_surface.get_width() / 2, self.editor_surface.get_height() / 2]
    def create_new_room(self): self.room_data = json.loads(json.dumps(NEW_ROOM_TEMPLATE)); self._populate_internal_tiles_from_json(); self.current_filepath = None; pygame.display.set_caption("Editor - Untitled"); self.reset_camera(); self.update_anchor_offset_inputs()
    def load_room(self):
        root = tk.Tk(); root.withdraw(); initial_dir = os.path.join(os.getcwd(), "rooms"); os.makedirs(initial_dir, exist_ok=True); fp = filedialog.askopenfilename(initialdir=initial_dir, title="Load Room", filetypes=(("JSON files", "*.json"),))
        if not fp: return
        try:
            with open(fp, 'r') as f: data = json.load(f)
            if "defaultSpawnPoint" in data: gx, gy = data["defaultSpawnPoint"]["x"], data["defaultSpawnPoint"]["y"]; data["renderAnchor"] = {"x": (gx - gy) * TILE_WIDTH_HALF + TILE_WIDTH_HALF, "y": (gx + gy) * TILE_HEIGHT_HALF + TILE_HEIGHT_HALF}; del data["defaultSpawnPoint"]
            self.room_data = data; self._populate_internal_tiles_from_json(); self.current_filepath = fp; pygame.display.set_caption(f"Editor - {os.path.basename(fp)}"); self.reset_camera(); self.update_anchor_offset_inputs()
        except Exception as e:
            print(f"Error loading file: {e}")

    def save_room(self, save_as=False):
        if not self.room_data: return
        fp = self.current_filepath
        if save_as or not fp: root = tk.Tk(); root.withdraw(); initial_dir = os.path.join(os.getcwd(), "rooms"); os.makedirs(initial_dir, exist_ok=True); fp = filedialog.asksaveasfilename(initialdir=initial_dir, title="Save Room As", defaultextension=".json", filetypes=(("JSON files", "*.json"),))
        if not fp: return
        if not self.tiles: min_x, min_y, max_x, max_y = 0, 0, 0, 0
        else: all_x = [p[0] for p in self.tiles.keys()]; all_y = [p[1] for p in self.tiles.keys()]; min_x, max_x = min(all_x), max(all_x); min_y, max_y = min(all_y), max(all_y)
        new_w = max_x - min_x + 1; new_d = max_y - min_y + 1; new_grid = [['0'] * new_w for _ in range(new_d)]
        for (gx, gy), tile_type in self.tiles.items():
            new_grid[gy - min_y][gx - min_x] = str(tile_type)
        dts = json.loads(json.dumps(self.room_data)); dts['dimensions'] = {'width': new_w, 'depth': new_d, 'origin_x': min_x, 'origin_y': min_y}; dts['tiles'] = ["".join(row) for row in new_grid]
        try:
            with open(fp, 'w') as f: json.dump(dts, f, indent=2)
            self.current_filepath = fp; pygame.display.set_caption(f"Editor - {os.path.basename(fp)}")
        except Exception as e:
            print(f"Error saving file: {e}")

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        alt = keys[pygame.K_LALT] or keys[pygame.K_RALT]
        local_mouse_pos = (mouse_pos[0] - self.editor_rect.x, mouse_pos[1] - self.editor_rect.y)
        self.hover_grid_pos = None
        if self.editor_rect.collidepoint(mouse_pos) and not self.is_panning: self.hover_grid_pos = self.screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.camera_offset)
        for btn in self.buttons.values(): btn.check_hover(mouse_pos)
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE: self.win_width, self.win_height = event.size; self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE); self.update_layout()
            if event.type == pygame.QUIT: return False
            for box in self.input_boxes:
                res = box.handle_event(event)
                if res is not None: self.apply_anchor_offset(); box.active = False
            if self.buttons['new'].is_clicked(event): self.create_new_room()
            elif self.buttons['load'].is_clicked(event): self.load_room()
            elif self.buttons['save'].is_clicked(event): self.save_room()
            elif self.buttons['save_as'].is_clicked(event): self.save_room(save_as=True)
            elif self.buttons['center_anchor'].is_clicked(event): center_wx, center_wy = self.calculate_room_center(); self.room_data['renderAnchor']['x'], self.room_data['renderAnchor']['y'] = center_wx, center_wy; self.update_anchor_offset_inputs()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2 and self.editor_rect.collidepoint(mouse_pos): self.is_panning = True; self.pan_start_pos = event.pos
                elif self.hover_grid_pos and not any(b.active for b in self.input_boxes):
                    if event.button == 1:
                        if shift:
                            w_mouse_x = local_mouse_pos[0] - self.camera_offset[0]; w_mouse_y = local_mouse_pos[1] - self.camera_offset[1]
                            self.room_data["renderAnchor"]["x"], self.room_data["renderAnchor"]["y"] = w_mouse_x, w_mouse_y
                            self.update_anchor_offset_inputs()
                        elif alt:
                            if self.hover_grid_pos in self.tiles:
                                current_type = self.tiles[self.hover_grid_pos]
                                current_index = TILE_TYPES.index(current_type)
                                next_index = (current_index + 1) % NUM_TILE_TYPES
                                self.tiles[self.hover_grid_pos] = TILE_TYPES[next_index]
                            else:
                                self.tiles[self.hover_grid_pos] = TILE_TYPE_CORNER_NO_TL
                                self.update_anchor_offset_inputs()
                        else:
                            self.is_painting = True
                            self.tiles[self.hover_grid_pos] = TILE_TYPE_FULL
                            self.update_anchor_offset_inputs()
                    elif event.button == 3: self.is_erasing = True; self.tiles.pop(self.hover_grid_pos, None); self.update_anchor_offset_inputs()
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: self.is_painting = False
                elif event.button == 3: self.is_erasing = False
                elif event.button == 2: self.is_panning = False
            if event.type == pygame.MOUSEMOTION:
                if self.is_panning: delta = (event.pos[0] - self.pan_start_pos[0], event.pos[1] - self.pan_start_pos[1]); self.camera_offset[0] += delta[0]; self.camera_offset[1] += delta[1]; self.pan_start_pos = event.pos
                elif self.hover_grid_pos and not shift and not alt:
                    if self.is_painting: self.tiles[self.hover_grid_pos] = TILE_TYPE_FULL; self.update_anchor_offset_inputs()
                    elif self.is_erasing: self.tiles.pop(self.hover_grid_pos, None); self.update_anchor_offset_inputs()
        if not any(b.active for b in self.input_boxes):
            nudge = 10 if shift else 1; moved = False
            if keys[pygame.K_LEFT]: self.room_data["renderAnchor"]["x"] -= nudge; moved = True
            if keys[pygame.K_RIGHT]: self.room_data["renderAnchor"]["x"] += nudge; moved = True
            if keys[pygame.K_UP]: self.room_data["renderAnchor"]["y"] -= nudge; moved = True
            if keys[pygame.K_DOWN]: self.room_data["renderAnchor"]["y"] += nudge; moved = True
            if moved: self.update_anchor_offset_inputs()
        return True

    def draw_tile_shape(self, surf, pos, tile_type, fill_color, border_color):
        p_top = (pos[0] + TILE_WIDTH_HALF, pos[1])
        p_right = (pos[0] + TILE_WIDTH, pos[1] + TILE_HEIGHT_HALF)
        p_bottom = (pos[0] + TILE_WIDTH_HALF, pos[1] + TILE_HEIGHT)
        p_left = (pos[0], pos[1] + TILE_HEIGHT_HALF)
        points = []
        if tile_type == TILE_TYPE_FULL: points = [p_top, p_right, p_bottom, p_left]
        elif tile_type == TILE_TYPE_CORNER_NO_TL: points = [p_top, p_right, p_bottom]
        elif tile_type == TILE_TYPE_CORNER_NO_TR: points = [p_top, p_bottom, p_left]
        elif tile_type == TILE_TYPE_CORNER_NO_BR: points = [p_top, p_right, p_left]
        elif tile_type == TILE_TYPE_CORNER_NO_BL: points = [p_right, p_bottom, p_left]
        if points:
            pygame.draw.polygon(surf, fill_color, points)
            pygame.draw.polygon(surf, border_color, points, 2)

    def draw_hover_indicator(self, surf, pos, tile_type):
        p_top = (pos[0] + TILE_WIDTH_HALF, pos[1])
        p_right = (pos[0] + TILE_WIDTH, pos[1] + TILE_HEIGHT_HALF)
        p_bottom = (pos[0] + TILE_WIDTH_HALF, pos[1] + TILE_HEIGHT)
        p_left = (pos[0], pos[1] + TILE_HEIGHT_HALF)
        points = []
        if tile_type == TILE_TYPE_FULL: points = [p_top, p_right, p_bottom, p_left]
        elif tile_type == TILE_TYPE_CORNER_NO_TL: points = [p_top, p_right, p_bottom]
        elif tile_type == TILE_TYPE_CORNER_NO_TR: points = [p_top, p_bottom, p_left]
        elif tile_type == TILE_TYPE_CORNER_NO_BR: points = [p_top, p_right, p_left]
        elif tile_type == TILE_TYPE_CORNER_NO_BL: points = [p_right, p_bottom, p_left]
        if points:
            pygame.draw.polygon(surf, COLOR_HOVER_BORDER, points, 3)

    def draw_room_on_surface(self, surf, offset, is_editor, hover_pos=None):
        surf.fill(COLOR_EDITOR_BG if is_editor else COLOR_PREVIEW_BG)
        if not self.room_data: return
        origin_pos = self.grid_to_screen(0, 0, offset)
        pygame.draw.line(surf, COLOR_ORIGIN, (origin_pos[0] - 10, origin_pos[1]), (origin_pos[0] + 10, origin_pos[1]), 1)
        pygame.draw.line(surf, COLOR_ORIGIN, (origin_pos[0], origin_pos[1] - 10), (origin_pos[0], origin_pos[1] + 10), 1)
        for (gx, gy), tile_type in self.tiles.items():
            self.draw_tile_shape(surf, self.grid_to_screen(gx, gy, offset), tile_type, COLOR_TILE, COLOR_TILE_BORDER)
        anchor_pos = (self.room_data["renderAnchor"]["x"] + offset[0], self.room_data["renderAnchor"]["y"] + offset[1])
        pygame.draw.circle(surf, COLOR_ANCHOR, anchor_pos, 5)
        pygame.draw.line(surf, COLOR_ANCHOR, (anchor_pos[0] - 8, anchor_pos[1]), (anchor_pos[0] + 8, anchor_pos[1]), 1)
        pygame.draw.line(surf, COLOR_ANCHOR, (anchor_pos[0], anchor_pos[1] - 8), (anchor_pos[0], anchor_pos[1] + 8), 1)
        # Draw hover indicator if a position is provided
        if hover_pos:
            hover_tile_type = self.tiles.get(hover_pos, TILE_TYPE_FULL)
            hover_screen_pos = self.grid_to_screen(*hover_pos, offset)
            self.draw_hover_indicator(surf, hover_screen_pos, hover_tile_type)

    def calculate_preview_offset(self, surface_size):
        if self.room_data and "renderAnchor" in self.room_data: ax, ay = self.room_data["renderAnchor"]["x"], self.room_data["renderAnchor"]["y"]; return (surface_size[0] / 2 - ax, surface_size[1] / 2 - ay)
        return (0, 0)

    def draw(self):
        self.screen.fill(COLOR_BG)
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, self.toolbar_rect); pygame.draw.rect(self.screen, COLOR_PANEL_BG, self.right_panel_rect)
        preview_offset = self.calculate_preview_offset(self.preview_surface.get_size())
        # Call the draw functions, passing the cursor position (hover_grid_pos)
        self.draw_room_on_surface(self.editor_surface, self.camera_offset, True, self.hover_grid_pos)
        self.draw_room_on_surface(self.preview_surface, preview_offset, False, self.hover_grid_pos)
        self.screen.blit(self.editor_surface, self.editor_rect); self.screen.blit(self.preview_surface, self.preview_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.editor_rect, 1); pygame.draw.rect(self.screen, COLOR_BORDER, self.right_panel_rect, 1); pygame.draw.rect(self.screen, COLOR_BORDER, self.preview_rect, 1)
        self.screen.blit(self.font_title.render("Preview", True, COLOR_TITLE_TEXT), (self.preview_rect.x, self.preview_rect.y - 22))
        for btn in self.buttons.values(): btn.draw(self.screen)
        self.screen.blit(self.font_info.render("Offset X:", True, COLOR_INFO_TEXT), (self.anchor_offset_input_x.rect.left, self.anchor_offset_input_x.rect.top - 15))
        self.screen.blit(self.font_info.render("Offset Y:", True, COLOR_INFO_TEXT), (self.anchor_offset_input_y.rect.left, self.anchor_offset_input_y.rect.top - 15))
        for box in self.input_boxes: box.update(); box.draw(self.screen)
        margin, padding, line_height = 15, 8, 15
        info_lines = ["Controls:", "[Click] Paint Tile", "[Drag] Paint/Erase", "[Alt+Click] Place/Cycle Corner", "[Middle Mouse] Pan View", "[Shift+Click] Set Anchor", "[Arrow Keys] Nudge Anchor (Shift+)"]
        rendered_lines = [self.font_info.render(line, True, COLOR_INFO_TEXT) for line in info_lines]
        box_w = max(line.get_width() for line in rendered_lines) + padding * 2; box_h = len(info_lines) * line_height + padding * 2
        box_rect = pygame.Rect(0, 0, box_w, box_h); box_rect.bottomright = (self.right_panel_rect.right - margin, self.right_panel_rect.bottom - margin)
        pygame.draw.rect(self.screen, COLOR_EDITOR_BG, box_rect, border_radius=5); pygame.draw.rect(self.screen, COLOR_BORDER, box_rect, 1, border_radius=5)
        for i, line_surf in enumerate(rendered_lines): self.screen.blit(line_surf, (box_rect.left + padding, box_rect.top + padding + i * line_height))
        pygame.display.flip()

    def run(self):
        running = True
        try:
            while running:
                running = self.handle_events()
                self.draw()
                self.clock.tick(60)
        except KeyboardInterrupt:
            print("\nClosing editor due to keyboard interrupt (Ctrl+C).")
        finally:
            pygame.quit()
            sys.exit()

if __name__ == "__main__":
    try:
        # Move to the script's directory to ensure relative paths work
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        # __file__ is not defined in some environments (like interactive interpreters)
        pass
    editor = RoomEditor()
    editor.run()