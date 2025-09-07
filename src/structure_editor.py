# src/structure_editor.py

import pygame
import math
from common.constants import *
from common.ui import Button, TextInputBox
from common.utils import grid_to_screen, screen_to_grid

class StructureEditor:
    def __init__(self, app_ref):
        self.app = app_ref
        self.font_ui = self.app.font_ui; self.font_info = self.app.font_info
        self.edit_mode = MODE_TILES; self.is_painting = False; self.is_erasing = False
        self.hover_grid_pos = None; self.hover_wall_edge = None
        self.buttons = {}

    def setup_ui(self):
        center_btn_y = self.app.anchor_offset_input_x.rect.bottom + 20; margin = 15
        self.buttons = {"center_anchor": Button(self.app.right_panel_rect.centerx - 60, center_btn_y, 120, 22, "Center Anchor", self.font_ui)}
        mode_btn_y = self.buttons["center_anchor"].rect.bottom + 20
        self.buttons.update({"mode_tile": Button(self.app.right_panel_rect.left + margin, mode_btn_y, 100, 55, "", self.font_ui), "mode_wall": Button(self.app.right_panel_rect.right - 100 - margin, mode_btn_y, 100, 55, "", self.font_ui)})
    
    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]; alt = keys[pygame.K_LALT] or keys[pygame.K_RALT]
        for btn in self.buttons.values(): btn.check_hover(mouse_pos)
            
        if self.buttons['mode_tile'].is_clicked(event): self.edit_mode = MODE_TILES
        elif self.buttons['mode_wall'].is_clicked(event): self.edit_mode = MODE_WALLS
        elif self.buttons['center_anchor'].is_clicked(event) and self.app.current_room:
            center_wx, center_wy = self.app.current_room.calculate_center_world_coords()
            self.app.current_room.structure_data['renderAnchor']['x'] = center_wx
            self.app.current_room.structure_data['renderAnchor']['y'] = center_wy
            self.app.update_anchor_offset_inputs()

        self.hover_grid_pos = None; self.hover_wall_edge = None
        if self.app.editor_rect.collidepoint(mouse_pos) and not self.app.camera.is_panning:
            self.hover_grid_pos = screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera.offset, self.app.camera.zoom)
            if self.edit_mode == MODE_WALLS: self.hover_wall_edge = self.get_hovered_edge(self.hover_grid_pos, local_mouse_pos)

        if event.type == pygame.MOUSEBUTTONDOWN and self.hover_grid_pos and self.app.current_room:
            if self.edit_mode == MODE_WALLS and event.button == 1 and self.hover_wall_edge:
                wall_tuple = (self.hover_wall_edge[0], self.hover_wall_edge[1])
                if wall_tuple in self.app.current_room.walls: self.app.current_room.walls.remove(wall_tuple)
                else: self.app.current_room.walls.add(wall_tuple)
            elif self.edit_mode == MODE_TILES:
                if event.button == 1:
                    if shift:
                        # Convert screen mouse pos to world pos to set the anchor
                        w_mouse_x = (local_mouse_pos[0] - self.app.camera.offset[0]) / self.app.camera.zoom
                        w_mouse_y = (local_mouse_pos[1] - self.app.camera.offset[1]) / self.app.camera.zoom
                        self.app.current_room.structure_data["renderAnchor"]["x"], self.app.current_room.structure_data["renderAnchor"]["y"] = w_mouse_x, w_mouse_y
                        self.app.update_anchor_offset_inputs()
                    elif alt:
                        self.app.current_room.tiles[self.hover_grid_pos] = TILE_TYPES[(TILE_TYPES.index(self.app.current_room.tiles.get(self.hover_grid_pos, TILE_TYPE_FULL)) + 1) % len(TILE_TYPES)]
                        self.app.update_anchor_offset_inputs()
                    else:
                        self.is_painting = True; self.app.current_room.tiles[self.hover_grid_pos] = TILE_TYPE_FULL; self.app.update_anchor_offset_inputs()
                elif event.button == 3: self.is_erasing = True; self.delete_tile(self.hover_grid_pos)
        
        if event.type == pygame.MOUSEBUTTONUP: self.is_painting = False; self.is_erasing = False
        if event.type == pygame.MOUSEMOTION:
             if self.edit_mode == MODE_TILES and self.hover_grid_pos and not shift and not alt and self.app.current_room:
                if self.is_painting: self.app.current_room.tiles[self.hover_grid_pos] = TILE_TYPE_FULL; self.app.update_anchor_offset_inputs()
                elif self.is_erasing: self.delete_tile(self.hover_grid_pos)

    def draw_on_editor(self, surface):
        if self.edit_mode == MODE_TILES and self.hover_grid_pos:
            hover_screen_pos = grid_to_screen(*self.hover_grid_pos, self.app.camera.offset, self.app.camera.zoom)
            p = self.app.renderer._get_tile_points(hover_screen_pos, self.app.camera.zoom)
            pygame.draw.polygon(surface, COLOR_HOVER_BORDER, [p['top'], p['right'], p['bottom'], p['left']], 3)
        elif self.edit_mode == MODE_WALLS and self.hover_wall_edge:
            pos, edge = self.hover_wall_edge
            hover_screen_pos = grid_to_screen(*pos, self.app.camera.offset, self.app.camera.zoom)
            p = self.app.renderer._get_tile_points(hover_screen_pos, self.app.camera.zoom)
            edge_points = { EDGE_NE: (p['top'], p['right']), EDGE_SE: (p['right'], p['bottom']), EDGE_SW: (p['bottom'], p['left']), EDGE_NW: (p['left'], p['top']), EDGE_DIAG_SW_NE: (p['bottom'], p['top']), EDGE_DIAG_NW_SE: (p['left'], p['right']) }
            p1, p2 = edge_points.get(edge, (None, None))
            if p1 and p2: pygame.draw.line(surface, COLOR_HOVER_BORDER, p1, p2, 4)

    def draw_ui_on_panel(self, screen):
        for name, btn in self.buttons.items():
            is_active = (name == 'mode_tile' and self.edit_mode == MODE_TILES) or (name == 'mode_wall' and self.edit_mode == MODE_WALLS)
            btn.draw(screen, is_active)
            if name in ['mode_tile', 'mode_wall']:
                self.app.draw_mode_button_icon(screen, name, btn.rect); text_str = "Tiles" if name == 'mode_tile' else "Walls"
                ts = self.font_ui.render(text_str, True, COLOR_TEXT); tr = ts.get_rect(centerx=btn.rect.centerx, bottom=btn.rect.bottom - 8); screen.blit(ts, tr)

    def get_info_lines(self): return ["[Click] Paint Tile", "[Drag] Paint/Erase", "[Alt+Click] Cycle Corner"] if self.edit_mode == MODE_TILES else ["[Click Edge] Toggle Wall"]
    
    def point_to_line_segment_dist(self, p, a, b):
        px, py = p; ax, ay = a; bx, by = b; line_mag_sq = (bx - ax)**2 + (by - ay)**2
        if line_mag_sq == 0: return math.hypot(px - ax, py - ay)
        u = max(0, min(1, (((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / line_mag_sq)))
        ix = ax + u * (bx - ax); iy = ay + u * (by - ay); return math.hypot(px - ix, py - iy)

    def get_hovered_edge(self, grid_pos, screen_mouse_pos):
        if not self.app.current_room or grid_pos not in self.app.current_room.tiles: return None
        tile_screen_pos = grid_to_screen(*grid_pos, self.app.camera.offset, self.app.camera.zoom)
        p = self.app.renderer._get_tile_points(tile_screen_pos, self.app.camera.zoom)
        
        tile_type = self.app.current_room.tiles[grid_pos]
        edge_definitions = { EDGE_NE: {'seg': (p['top'], p['right']), 'neighbor': (grid_pos[0], grid_pos[1] - 1)}, EDGE_SE: {'seg': (p['right'], p['bottom']), 'neighbor': (grid_pos[0] + 1, grid_pos[1])}, EDGE_SW: {'seg': (p['bottom'], p['left']), 'neighbor': (grid_pos[0], grid_pos[1] + 1)}, EDGE_NW: {'seg': (p['left'], p['top']), 'neighbor': (grid_pos[0] - 1, grid_pos[1])}, EDGE_DIAG_SW_NE: {'seg': (p['bottom'], p['top']), 'neighbor': None}, EDGE_DIAG_NW_SE: {'seg': (p['left'], p['right']), 'neighbor': None}, }
        best_edge = None; min_dist = 15; valid_edges_for_shape = TILE_TYPE_EDGES.get(tile_type, [])
        for edge_name in valid_edges_for_shape:
            data = edge_definitions[edge_name]
            if (data['neighbor'] is None) or (data['neighbor'] not in self.app.current_room.tiles):
                if (dist := self.point_to_line_segment_dist(screen_mouse_pos, *data['seg'])) < min_dist: min_dist = dist; best_edge = (grid_pos, edge_name)
        return best_edge

    def delete_tile(self, grid_pos):
        if not self.app.current_room or not grid_pos or grid_pos not in self.app.current_room.tiles: return
        self.app.current_room.tiles.pop(grid_pos, None)
        self.app.current_room.walls = {wall for wall in self.app.current_room.walls if wall[0] != grid_pos}
        self.app.update_anchor_offset_inputs()