# src/renderer.py

import pygame
import os
from common.constants import *
from common.utils import grid_to_screen, screen_to_grid

class RoomRenderer:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def draw_room_on_surface(self, surface, room, camera_offset, is_editor_view=True):
        surface.fill(COLOR_EDITOR_BG if is_editor_view else COLOR_PREVIEW_BG)
        
        if is_editor_view:
            self._draw_iso_grid_on_surface(surface, surface.get_rect(), camera_offset)

        if not room: return
        
        origin_pos = grid_to_screen(0, 0, camera_offset)
        pygame.draw.line(surface, COLOR_ORIGIN, (origin_pos[0] - 10, origin_pos[1]), (origin_pos[0] + 10, origin_pos[1]), 1)
        pygame.draw.line(surface, COLOR_ORIGIN, (origin_pos[0], origin_pos[1] - 10), (origin_pos[0], origin_pos[1] + 10), 1)

        sorted_tiles = sorted(room.tiles.keys(), key=lambda k: (k[1] + k[0], k[1] - k[0]))

        for gx, gy in sorted_tiles:
            screen_pos = grid_to_screen(gx, gy, camera_offset)
            self._draw_tile_shape(surface, screen_pos, room.tiles[(gx, gy)], COLOR_TILE, COLOR_TILE_BORDER)
        for gx, gy in sorted_tiles:
            for pos, edge in room.walls:
                if pos == (gx, gy):
                    screen_pos = grid_to_screen(gx, gy, camera_offset)
                    self._draw_wall(surface, screen_pos, edge)

        for deco in room.get_decorations_sorted_for_render():
            self._draw_decoration(surface, deco, camera_offset)

        if is_editor_view:
            anchor_pos = (room.structure_data["renderAnchor"]["x"] + camera_offset[0], room.structure_data["renderAnchor"]["y"] + camera_offset[1])
            pygame.draw.circle(surface, COLOR_ANCHOR, anchor_pos, 5); pygame.draw.line(surface, COLOR_ANCHOR, (anchor_pos[0] - 8, anchor_pos[1]), (anchor_pos[0] + 8, anchor_pos[1]), 1); pygame.draw.line(surface, COLOR_ANCHOR, (anchor_pos[0], anchor_pos[1] - 8), (anchor_pos[0], anchor_pos[1] + 8), 1)
            ax, ay = room.structure_data["renderAnchor"]["x"], room.structure_data["renderAnchor"]["y"]
            pw, ph = PREVIEW_SIZE
            preview_bounds_rect = pygame.Rect((ax - pw / 2) + camera_offset[0], (ay - ph / 2) + camera_offset[1], pw, ph)
            pygame.draw.rect(surface, COLOR_PREVIEW_OUTLINE, preview_bounds_rect, 1)

    def _draw_iso_grid_on_surface(self, surface, view_rect, offset):
        if not view_rect.w or not view_rect.h: return
        corners_grid = [screen_to_grid(0, 0, offset), screen_to_grid(view_rect.w, 0, offset), screen_to_grid(view_rect.w, view_rect.h, offset), screen_to_grid(0, view_rect.h, offset)]
        min_gx, max_gx = min(c[0] for c in corners_grid) - 1, max(c[0] for c in corners_grid) + 2
        min_gy, max_gy = min(c[1] for c in corners_grid) - 1, max(c[1] for c in corners_grid) + 2
        
        for gy in range(min_gy, max_gy):
            for gx in range(min_gx, max_gx):
                screen_pos = grid_to_screen(gx, gy, offset)
                p = self._get_tile_points(screen_pos)
                points = [p['top'], p['right'], p['bottom'], p['left']]
                pygame.draw.polygon(surface, COLOR_GRID, points, 1)

    def _get_tile_points(self, pos):
        return {"top": (pos[0] + TILE_WIDTH_HALF, pos[1]), "right": (pos[0] + TILE_WIDTH, pos[1] + TILE_HEIGHT_HALF), "bottom": (pos[0] + TILE_WIDTH_HALF, pos[1] + TILE_HEIGHT), "left": (pos[0], pos[1] + TILE_HEIGHT_HALF)}

    def _draw_tile_shape(self, surf, pos, tile_type, fill_color, border_color):
        p = self._get_tile_points(pos)
        points_map = { TILE_TYPE_FULL: [p['top'], p['right'], p['bottom'], p['left']], TILE_TYPE_CORNER_NO_TL: [p['top'], p['right'], p['bottom']], TILE_TYPE_CORNER_NO_TR: [p['top'], p['bottom'], p['left']], TILE_TYPE_CORNER_NO_BR: [p['top'], p['right'], p['left']], TILE_TYPE_CORNER_NO_BL: [p['right'], p['bottom'], p['left']] }
        points = points_map.get(tile_type)
        if points:
            pygame.draw.polygon(surf, fill_color, points)
            pygame.draw.polygon(surf, border_color, points, 2)

    def _draw_wall(self, surf, screen_pos, edge):
        p = self._get_tile_points(screen_pos)
        edge_points = { EDGE_NE: (p['top'], p['right']), EDGE_SE: (p['right'], p['bottom']), EDGE_SW: (p['bottom'], p['left']), EDGE_NW: (p['left'], p['top']), EDGE_DIAG_SW_NE: (p['bottom'], p['top']), EDGE_DIAG_NW_SE: (p['left'], p['right']) }
        p1, p2 = edge_points.get(edge, (None, None))
        if p1 and p2:
            wall_points = [p1, p2, (p2[0], p2[1] - WALL_HEIGHT), (p1[0], p1[1] - WALL_HEIGHT)]
            pygame.draw.polygon(surf, COLOR_WALL, wall_points)
            pygame.draw.polygon(surf, COLOR_WALL_BORDER, wall_points, 2)
            
    def get_rendered_image_and_offset(self, base_id, color_id, rotation):
        if base_id is None or color_id is None or rotation is None: 
            return None, None

        direction = DECO_ROTATION_MAP[rotation % 4]
        render_data = self.data_manager.load_render_data(base_id)

        def get_fallback_offset(image):
            return (image.get_width() // 2, image.get_height())

        def get_data_for_path(filename_base, path):
            image = self.data_manager.get_image(path)
            if image:
                if render_data and filename_base in render_data:
                    offset_data = render_data[filename_base]
                    return image, (offset_data['X'], offset_data['Y'])
                else: 
                    return image, get_fallback_offset(image)
            return None, None

        filename_base_color = f"{base_id}_dir_{direction}_{color_id}_no_sd"
        path_color = os.path.join("furnis", base_id, "rendered", filename_base_color + ".png").replace("\\", "/")
        image, offset = get_data_for_path(filename_base_color, path_color)
        if image:
            return image, offset

        filename_base_default = f"{base_id}_dir_{direction}_no_sd"
        path_default = os.path.join("furnis", base_id, "rendered", filename_base_default + ".png").replace("\\", "/")
        image, offset = get_data_for_path(filename_base_default, path_default)
        if image:
            return image, offset
        
        return None, None

    def _draw_decoration(self, surface, deco_data, camera_offset, is_ghost=False, is_occupied=False):
        base_id, color_id = deco_data.get("base_id"), deco_data.get("color_id", "0")
        grid_pos, rotation = deco_data.get("grid_pos"), deco_data.get("rotation", 0)
        
        image, offset = self.get_rendered_image_and_offset(base_id, color_id, rotation)
        if not image or not offset:
            return

        screen_pos = grid_to_screen(grid_pos[0], grid_pos[1], camera_offset)
        
        anchor_x = screen_pos[0] + TILE_WIDTH_HALF
        # <-- INICIO DE LA CORRECCIÓN -->
        # El ancla es la línea central horizontal de la tile, no su punto más bajo.
        anchor_y = screen_pos[1] + TILE_HEIGHT_HALF
        # <-- FIN DE LA CORRECCIÓN -->

        draw_x = anchor_x - offset[0]
        draw_y = anchor_y - offset[1]

        if is_ghost:
            ghost_image = image.copy()
            alpha = 100 if is_occupied else 150
            ghost_image.set_alpha(alpha)
            if is_occupied:
                red_tint = pygame.Surface(ghost_image.get_size(), pygame.SRCALPHA)
                red_tint.fill((255, 50, 50, 80))
                ghost_image.blit(red_tint, (0, 0))
            surface.blit(ghost_image, (draw_x, draw_y))
        else:
            surface.blit(image, (draw_x, draw_y))