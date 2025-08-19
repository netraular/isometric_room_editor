# src/app.py

import pygame
import json
import sys
import os
from common.constants import *
from common.ui import Button, TextInputBox
from common.utils import grid_to_screen, screen_to_grid
from data_manager import DataManager
from structure_editor import StructureEditor
from decoration_editor import DecorationEditor

class App:
    def __init__(self, project_root):
        pygame.init()
        self.project_root = project_root
        self.win_width, self.win_height = INITIAL_WIN_WIDTH, INITIAL_WIN_HEIGHT
        self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
        pygame.display.set_caption("Isometric Room Editor")
        self.clock = pygame.time.Clock()
        self.font_ui = pygame.font.SysFont("Arial", 14); self.font_title = pygame.font.SysFont("Arial", 18, bold=True); self.font_info = pygame.font.SysFont("Consolas", 12)
        
        self.data_manager = DataManager(self.project_root)

        self.structure_data, self.decoration_set_data = None, None
        self.tiles, self.walls, self.placed_decorations = {}, set(), []
        self.is_panning, self.pan_start_pos = False, (0, 0)
        self.camera_offset, self.save_confirmation_timer = [0, 0], 0
        
        self.main_mode = EDITOR_MODE_STRUCTURE
        # --- Importante: Inicializar los editores ANTES de llamar a update_layout ---
        self.structure_editor = StructureEditor(self)
        self.decoration_editor = DecorationEditor(self)
        self.active_editor = self.structure_editor
        
        self.update_layout() # Llama al layout una vez que todo está inicializado
        self.load_initial_room()

    def update_layout(self):
        margin = 15
        btn_y = 5
        btn_height = 30
        
        # --- LÍNEAS MODIFICADAS: PANEL DERECHO DINÁMICO ---
        # El panel derecho ahora ocupa 1/3 del ancho de la ventana.
        right_panel_width = self.win_width // 3 
        self.top_bar_rect = pygame.Rect(0, 0, self.win_width, TOP_BAR_HEIGHT)
        self.right_panel_rect = pygame.Rect(self.win_width - right_panel_width, TOP_BAR_HEIGHT, right_panel_width, self.win_height - TOP_BAR_HEIGHT)
        self.editor_rect = pygame.Rect(0, TOP_BAR_HEIGHT, self.win_width - right_panel_width, self.win_height - TOP_BAR_HEIGHT)
        # --- FIN DE LÍNEAS MODIFICADAS ---
        
        self.editor_surface = pygame.Surface(self.editor_rect.size, pygame.SRCALPHA)
        
        self.main_buttons = {
            "structure": Button(margin, btn_y, 140, btn_height, "Structure Editor", self.font_ui),
            "decorations": Button(margin + 150, btn_y, 140, btn_height, "Decorations Editor", self.font_ui)
        }
        
        btn_file_h = 25
        btn_file_y = (TOP_BAR_HEIGHT - btn_file_h) // 2
        btn_save_as = Button(self.win_width - margin - 90, btn_file_y, 90, btn_file_h, "Save As...", self.font_ui)
        btn_save = Button(btn_save_as.rect.left - 10 - 60, btn_file_y, 60, btn_file_h, "Save", self.font_ui)
        btn_load = Button(btn_save.rect.left - 10 - 60, btn_file_y, 60, btn_file_h, "Load", self.font_ui)
        btn_new = Button(btn_load.rect.left - 10 - 60, btn_file_y, 60, btn_file_h, "New", self.font_ui)
        self.file_buttons = {"new": btn_new, "load": btn_load, "save": btn_save, "save_as": btn_save_as}

        self.preview_rect = pygame.Rect(0, 0, PREVIEW_SIZE[0], PREVIEW_SIZE[1])
        self.preview_rect.topright = (self.editor_rect.right - margin, self.editor_rect.top + margin)
        self.preview_surface = pygame.Surface(PREVIEW_SIZE)

        input_y = self.right_panel_rect.y + margin + 20
        self.anchor_offset_input_x = TextInputBox(self.right_panel_rect.left + margin, input_y, 100, 25, self.font_ui)
        self.anchor_offset_input_y = TextInputBox(self.right_panel_rect.right - 100 - margin, input_y, 100, 25, self.font_ui)
        self.input_boxes = [self.anchor_offset_input_x, self.anchor_offset_input_y]
        
        if hasattr(self, 'structure_editor'): self.structure_editor.setup_ui()
        # --- LÍNEA AÑADIDA: Notificar al decoration_editor que el layout ha cambiado ---
        if hasattr(self, 'decoration_editor'): self.decoration_editor.update_layout()

    def load_initial_room(self):
        s_path = os.path.join(self.project_root, "rooms", "structures", "new_room_01.json")
        d_path = os.path.join(self.project_root, "rooms", "decoration_sets", "new_room_01_decoration_set.json")
        if os.path.exists(s_path) and os.path.exists(d_path):
            with open(s_path, 'r') as f: self.structure_data = json.load(f)
            with open(d_path, 'r') as f: self.decoration_set_data = json.load(f)
            self.data_manager.current_structure_path = s_path
            self.data_manager.current_decoration_set_path = d_path
            self.set_new_room_data(self.structure_data, self.decoration_set_data)
        else: self.create_new_room()

    def set_new_room_data(self, structure_data, decoration_set_data):
        self.structure_data = structure_data
        self.decoration_set_data = decoration_set_data
        self.populate_internal_data()
        self.center_camera_on_room()
        self.update_anchor_offset_inputs()
        decoration_set_name = os.path.basename(self.data_manager.current_decoration_set_path or "Untitled Decoration Set")
        pygame.display.set_caption(f"Editor - {decoration_set_name}")

    def populate_internal_data(self):
        self.tiles.clear(); self.walls.clear()
        dims = self.structure_data.get('dimensions', {}); ox, oy = dims.get('origin_x', 0), dims.get('origin_y', 0)
        for y, row in enumerate(self.structure_data.get('tiles', [])):
            for x, char_val in enumerate(row):
                if char_val != '0': self.tiles[(x + ox, y + oy)] = int(char_val)
        for wall_data in self.structure_data.get('walls', []):
            self.walls.add((tuple(wall_data['grid_pos']), wall_data['edge']))
        self.placed_decorations = self.decoration_set_data.get("decorations", [])

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()
        local_mouse_pos = (mouse_pos[0] - self.editor_rect.x, mouse_pos[1] - self.editor_rect.y)
        
        for btn in list(self.main_buttons.values()) + list(self.file_buttons.values()): btn.check_hover(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.VIDEORESIZE: 
                self.win_width, self.win_height = event.size
                self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
                self.update_layout() # Esencial para que el layout se adapte
            
            if self.main_mode == EDITOR_MODE_STRUCTURE:
                for box in self.input_boxes:
                    if box.handle_event(event) is not None: self.apply_anchor_offset(); box.active = False
            
            if self.main_buttons['structure'].is_clicked(event): self.main_mode = EDITOR_MODE_STRUCTURE; self.active_editor = self.structure_editor
            if self.main_buttons['decorations'].is_clicked(event): self.main_mode = EDITOR_MODE_DECORATIONS; self.active_editor = self.decoration_editor
            
            if self.file_buttons['new'].is_clicked(event): self.create_new_room()
            if self.file_buttons['load'].is_clicked(event): self.load_file_for_current_mode()
            if self.file_buttons['save'].is_clicked(event): self.save_all(save_as=False)
            if self.file_buttons['save_as'].is_clicked(event): self.save_all(save_as=True)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2 and self.editor_rect.collidepoint(mouse_pos): self.is_panning = True; self.pan_start_pos = event.pos
            if event.type == pygame.MOUSEBUTTONUP and event.button == 2: self.is_panning = False
            if event.type == pygame.MOUSEMOTION and self.is_panning:
                delta = (event.pos[0] - self.pan_start_pos[0], event.pos[1] - self.pan_start_pos[1]); self.camera_offset[0] += delta[0]; self.camera_offset[1] += delta[1]; self.pan_start_pos = event.pos
            
            self.active_editor.handle_events(event, mouse_pos, local_mouse_pos, keys)
        return True

    def draw(self):
        self.screen.fill(COLOR_BG)
        pygame.draw.rect(self.screen, COLOR_TOP_BAR, self.top_bar_rect)
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, self.right_panel_rect)
        
        self.draw_room_on_surface(self.editor_surface, self.camera_offset, True)
        self.screen.blit(self.editor_surface, self.editor_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.editor_rect, 1)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.right_panel_rect, 1)

        self.draw_room_on_surface(self.preview_surface, self.calculate_preview_offset(PREVIEW_SIZE), False)
        self.screen.blit(self.preview_surface, self.preview_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.preview_rect, 1)
        
        title_surf = self.font_title.render("Preview", True, COLOR_TITLE_TEXT)
        title_rect = title_surf.get_rect(topright=(self.preview_rect.right, self.preview_rect.bottom + 5))
        self.screen.blit(title_surf, title_rect)

        self.draw_info_box(self.active_editor.get_info_lines())

        for name, btn in self.main_buttons.items(): btn.draw(self.screen, (name == 'structure' and self.main_mode == EDITOR_MODE_STRUCTURE) or (name == 'decorations' and self.main_mode == EDITOR_MODE_DECORATIONS))
        for btn in self.file_buttons.values(): btn.draw(self.screen)
        
        if self.main_mode == EDITOR_MODE_STRUCTURE:
            self.screen.blit(self.font_info.render("Offset X:", True, COLOR_INFO_TEXT), (self.anchor_offset_input_x.rect.left, self.anchor_offset_input_x.rect.top - 15))
            self.screen.blit(self.font_info.render("Offset Y:", True, COLOR_INFO_TEXT), (self.anchor_offset_input_y.rect.left, self.anchor_offset_input_y.rect.top - 15))
            for box in self.input_boxes: box.update(); box.draw(self.screen)
        
        self.active_editor.draw_ui_on_panel(self.screen)
        
        self.draw_save_confirmation()
        pygame.display.flip()

    def run(self):
        running = True
        try:
            while running:
                running = self.handle_events()
                self.draw()
                self.clock.tick(60)
        except KeyboardInterrupt:
            print("\nEditor closed via Ctrl+C.")
        finally:
            pygame.quit()
    
    def create_new_room(self):
        new_structure = {"name": "New Structure", "id": "new_structure", "dimensions": {"width": 0, "depth": 0, "origin_x": 0, "origin_y": 0}, "renderAnchor": {"x": 0, "y": 0}, "tiles": [], "walls": []}
        new_decoration_set = {"decoration_set_name": "New Decoration Set", "structure_id": "new_structure", "decorations": []}
        self.data_manager.current_decoration_set_path = None
        self.data_manager.current_structure_path = None
        self.set_new_room_data(new_structure, new_decoration_set)

    def load_file_for_current_mode(self):
        if self.main_mode == EDITOR_MODE_STRUCTURE:
            start_dir = os.path.join(self.project_root, "rooms", "structures")
        else:
            start_dir = os.path.join(self.project_root, "rooms", "decoration_sets")
        s_data, d_data = self.data_manager.load_decoration_set_and_structure(initial_dir=start_dir)
        if s_data and d_data:
            self.set_new_room_data(s_data, d_data)

    def save_all(self, save_as=False):
        if not self.structure_data or not self.decoration_set_data: return
        
        if not self.tiles: min_x, min_y, max_x, max_y = 0, 0, 0, 0
        else: all_x = [p[0] for p in self.tiles.keys()]; all_y = [p[1] for p in self.tiles.keys()]; min_x, max_x = min(all_x), max(all_x); min_y, max_y = min(all_y), max(all_y)
        new_w = max_x - min_x + 1 if self.tiles else 0; new_d = max_y - min_y + 1 if self.tiles else 0
        new_grid = [['0'] * new_w for _ in range(new_d)]
        for (gx, gy), tile_type in self.tiles.items(): new_grid[gy - min_y][gx - min_x] = str(tile_type)
        
        self.structure_data['dimensions'] = {'width': new_w, 'depth': new_d, 'origin_x': min_x, 'origin_y': min_y}
        self.structure_data['tiles'] = ["".join(row) for row in new_grid]
        self.structure_data['walls'] = [{"grid_pos": list(pos), "edge": edge} for pos, edge in sorted(list(self.walls))]
        self.decoration_set_data["decorations"] = self.placed_decorations

        s_ok = self.data_manager.save_structure(self.structure_data, save_as)
        if s_ok:
            self.decoration_set_data['structure_id'] = self.structure_data['id']
            d_ok, new_name = self.data_manager.save_decoration_set(self.decoration_set_data, save_as)
            if d_ok: self.save_confirmation_timer = 120; pygame.display.set_caption(f"Editor - {new_name}")

    def draw_room_on_surface(self, surf, offset, is_editor):
        surf.fill(COLOR_EDITOR_BG if is_editor else COLOR_PREVIEW_BG)
        if not self.structure_data: return
        
        origin_pos = grid_to_screen(0, 0, offset)
        pygame.draw.line(surf, COLOR_ORIGIN, (origin_pos[0] - 10, origin_pos[1]), (origin_pos[0] + 10, origin_pos[1]), 1)
        pygame.draw.line(surf, COLOR_ORIGIN, (origin_pos[0], origin_pos[1] - 10), (origin_pos[0], origin_pos[1] + 10), 1)

        sorted_tiles = sorted(self.tiles.keys(), key=lambda k: (k[1] + k[0], k[1] - k[0]))

        for gx, gy in sorted_tiles:
            screen_pos = grid_to_screen(gx, gy, offset)
            self.draw_tile_shape(surf, screen_pos, self.tiles[(gx, gy)], COLOR_TILE, COLOR_TILE_BORDER)
        for gx, gy in sorted_tiles:
            for pos, edge in self.walls:
                if pos == (gx, gy):
                    screen_pos = grid_to_screen(gx, gy, offset)
                    self.draw_wall(surf, screen_pos, edge)

        if is_editor:
            anchor_pos = (self.structure_data["renderAnchor"]["x"] + offset[0], self.structure_data["renderAnchor"]["y"] + offset[1])
            pygame.draw.circle(surf, COLOR_ANCHOR, anchor_pos, 5); pygame.draw.line(surf, COLOR_ANCHOR, (anchor_pos[0] - 8, anchor_pos[1]), (anchor_pos[0] + 8, anchor_pos[1]), 1); pygame.draw.line(surf, COLOR_ANCHOR, (anchor_pos[0], anchor_pos[1] - 8), (anchor_pos[0], anchor_pos[1] + 8), 1)
            ax, ay = self.structure_data["renderAnchor"]["x"], self.structure_data["renderAnchor"]["y"]
            pw, ph = PREVIEW_SIZE
            preview_bounds_rect = pygame.Rect((ax - pw / 2) + offset[0], (ay - ph / 2) + offset[1], pw, ph)
            pygame.draw.rect(surf, COLOR_PREVIEW_OUTLINE, preview_bounds_rect, 1)
            self.active_editor.draw_on_editor(surf)

    def center_camera_on_room(self):
        if not self.editor_rect.w or not self.editor_rect.h: return
        center_world_coords = self.calculate_room_center()
        editor_center_screen = (self.editor_rect.w / 2, self.editor_rect.h / 2)
        self.camera_offset = [editor_center_screen[0] - center_world_coords[0], editor_center_screen[1] - center_world_coords[1]]

    def draw_info_box(self, mode_specific_lines):
        margin, padding, line_height = 15, 8, 15
        base_lines = ["Controls:", "[Middle Mouse] Pan View"]
        if self.main_mode == EDITOR_MODE_STRUCTURE: base_lines.append("[Shift+Click] Set Anchor")
        info_lines = base_lines[:1] + mode_specific_lines + base_lines[1:]
        rendered_lines = [self.font_info.render(line, True, COLOR_INFO_TEXT) for line in info_lines]
        box_w = max(line.get_width() for line in rendered_lines) + padding * 2; box_h = len(info_lines) * line_height + padding * 2
        
        box_rect = pygame.Rect(0, 0, box_w, box_h)
        box_rect.bottomright = (self.editor_rect.right - margin, self.editor_rect.bottom - margin)
        
        pygame.draw.rect(self.screen, COLOR_EDITOR_BG, box_rect, border_radius=5); pygame.draw.rect(self.screen, COLOR_BORDER, box_rect, 1, border_radius=5)
        for i, line_surf in enumerate(rendered_lines): self.screen.blit(line_surf, (box_rect.left + padding, box_rect.top + padding + i * line_height))
    
    def draw_save_confirmation(self):
        if self.save_confirmation_timer > 0:
            self.save_confirmation_timer -= 1
            surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            text_surf = self.font_title.render("Files Saved!", True, COLOR_TEXT)
            bg_rect = text_surf.get_rect(center=self.editor_rect.center).inflate(30, 20)
            pygame.draw.rect(surf, COLOR_SAVE_CONFIRM_BG, bg_rect, border_radius=8)
            self.screen.blit(surf, (0, 0))
            self.screen.blit(text_surf, text_surf.get_rect(center=self.editor_rect.center))

    def calculate_room_center(self):
        if not self.tiles: return grid_to_screen(0, 0, (0,0))
        all_x = [p[0] for p in self.tiles.keys()]; all_y = [p[1] for p in self.tiles.keys()]
        center_gx = (min(all_x) + max(all_x)) / 2; center_gy = (min(all_y) + max(all_y)) / 2
        return grid_to_screen(center_gx, center_gy, (TILE_WIDTH_HALF, TILE_HEIGHT_HALF))

    def update_anchor_offset_inputs(self):
        if self.structure_data and 'renderAnchor' in self.structure_data:
            center_wx, center_wy = self.calculate_room_center()
            offset_x = self.structure_data['renderAnchor']['x'] - center_wx; offset_y = self.structure_data['renderAnchor']['y'] - center_wy
            self.anchor_offset_input_x.set_text(f"{offset_x:.0f}"); self.anchor_offset_input_y.set_text(f"{offset_y:.0f}")

    def apply_anchor_offset(self):
        try:
            offset_x = float(self.anchor_offset_input_x.text); offset_y = float(self.anchor_offset_input_y.text)
            center_wx, center_wy = self.calculate_room_center()
            self.structure_data['renderAnchor']['x'] = center_wx + offset_x; self.structure_data['renderAnchor']['y'] = center_wy + offset_y
        except (ValueError, KeyError): self.update_anchor_offset_inputs()

    def get_tile_points(self, pos): return {"top": (pos[0] + TILE_WIDTH_HALF, pos[1]), "right": (pos[0] + TILE_WIDTH, pos[1] + TILE_HEIGHT_HALF), "bottom": (pos[0] + TILE_WIDTH_HALF, pos[1] + TILE_HEIGHT), "left": (pos[0], pos[1] + TILE_HEIGHT_HALF)}
    
    def draw_tile_shape(self, surf, pos, tile_type, fill_color, border_color):
        p = self.get_tile_points(pos)
        points_map = {
            TILE_TYPE_FULL: [p['top'], p['right'], p['bottom'], p['left']],
            TILE_TYPE_CORNER_NO_TL: [p['top'], p['right'], p['bottom']],
            TILE_TYPE_CORNER_NO_TR: [p['top'], p['bottom'], p['left']],
            TILE_TYPE_CORNER_NO_BR: [p['top'], p['right'], p['left']],
            TILE_TYPE_CORNER_NO_BL: [p['right'], p['bottom'], p['left']]
        }
        points = points_map.get(tile_type)
        if points:
            pygame.draw.polygon(surf, fill_color, points)
            pygame.draw.polygon(surf, border_color, points, 2)
        
    def draw_wall(self, surf, screen_pos, edge):
        p = self.get_tile_points(screen_pos)
        edge_points = {
            EDGE_NE: (p['top'], p['right']), EDGE_SE: (p['right'], p['bottom']),
            EDGE_SW: (p['bottom'], p['left']), EDGE_NW: (p['left'], p['top']),
            EDGE_DIAG_SW_NE: (p['bottom'], p['top']),
            EDGE_DIAG_NW_SE: (p['left'], p['right'])
        }
        p1, p2 = edge_points.get(edge, (None, None))
        if p1 and p2:
            wall_points = [p1, p2, (p2[0], p2[1] - WALL_HEIGHT), (p1[0], p1[1] - WALL_HEIGHT)]
            pygame.draw.polygon(surf, COLOR_WALL, wall_points)
            pygame.draw.polygon(surf, COLOR_WALL_BORDER, wall_points, 2)

    def calculate_preview_offset(self, surface_size):
        if self.structure_data and "renderAnchor" in self.structure_data:
            ax, ay = self.structure_data["renderAnchor"]["x"], self.structure_data["renderAnchor"]["y"]
            return (surface_size[0] / 2 - ax, surface_size[1] / 2 - ay)
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