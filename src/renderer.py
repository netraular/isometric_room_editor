# src/renderer.py
import pygame
import os
from common.constants import *
from common.utils import grid_to_screen, screen_to_grid

class RoomRenderer:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def draw_room_on_surface(self, surface, room, camera_offset, zoom=1.0, is_editor_view=True, 
                             draw_walkable_overlay=False, draw_layer_overlay=False, draw_decorations=True, 
                             walkable_view_filter=False, hovered_decoration_layer=None, filter_by_layer=None):
        surface.fill(COLOR_EDITOR_BG if is_editor_view else COLOR_PREVIEW_BG)
        if is_editor_view and not filter_by_layer:
            self._draw_iso_grid_on_surface(surface, surface.get_rect(), camera_offset, zoom)

        if not room: return
        origin_pos = grid_to_screen(0, 0, camera_offset, zoom)
        pygame.draw.line(surface, COLOR_ORIGIN, (origin_pos[0] - 10, origin_pos[1]), (origin_pos[0] + 10, origin_pos[1]), 1)
        pygame.draw.line(surface, COLOR_ORIGIN, (origin_pos[0], origin_pos[1] - 10), (origin_pos[0], origin_pos[1] + 10), 1)
        
        tiles_to_draw = []
        if filter_by_layer is not None:
            # Special case: Floor layer shows ALL tiles.
            if filter_by_layer == LAYER_FLOOR:
                tiles_to_draw = room.tiles.keys()
            # Other layers only show tiles assigned to them.
            else:
                for pos, layer_id in room.layer_map.items():
                    if layer_id == filter_by_layer and pos in room.tiles:
                        tiles_to_draw.append(pos)
        else:
            tiles_to_draw = room.tiles.keys()
        
        sorted_tiles = sorted(tiles_to_draw, key=lambda k: (k[1] + k[0], k[1] - k[0]))

        for gx, gy in sorted_tiles:
            screen_pos = grid_to_screen(gx, gy, camera_offset, zoom)
            self._draw_tile_shape(surface, screen_pos, room.tiles[(gx, gy)], COLOR_TILE, COLOR_TILE_BORDER, zoom)

        if is_editor_view and (draw_walkable_overlay or draw_layer_overlay):
            overlay_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            if draw_layer_overlay:
                for (gx, gy), layer_id in room.layer_map.items():
                    tile_type = room.tiles.get((gx, gy), TILE_TYPE_FULL)
                    screen_pos = grid_to_screen(gx, gy, camera_offset, zoom)
                    points = self._get_tile_points_from_type(screen_pos, tile_type, zoom)
                    if points: pygame.draw.polygon(overlay_surface, LAYER_DATA[layer_id]['color'], points)
            elif draw_walkable_overlay:
                for (gx, gy), tile_type in room.tiles.items():
                    screen_pos = grid_to_screen(gx, gy, camera_offset, zoom)
                    points = self._get_tile_points_from_type(screen_pos, tile_type, zoom)
                    if points:
                        color = COLOR_WALKABLE_OVERLAY if room.walkable_map.get((gx, gy), 0) else COLOR_NON_WALKABLE_OVERLAY
                        pygame.draw.polygon(overlay_surface, color, points)
            surface.blit(overlay_surface, (0, 0))

        if filter_by_layer is None or filter_by_layer == LAYER_WALL:
            for gx, gy in sorted(room.tiles.keys(), key=lambda k: (k[1] + k[0], k[1] - k[0])):
                for pos, edge in room.walls:
                    if pos == (gx, gy):
                        screen_pos = grid_to_screen(gx, gy, camera_offset, zoom)
                        self._draw_wall(surface, screen_pos, edge, zoom)
        
        if draw_decorations:
            for deco in room.get_decorations_sorted_for_render():
                opacity_ratio = None
                if hovered_decoration_layer is not None:
                    if deco.get('layer', DEFAULT_LAYER) != hovered_decoration_layer: opacity_ratio = 0.1
                elif filter_by_layer is not None:
                    if deco.get('layer', DEFAULT_LAYER) != filter_by_layer: opacity_ratio = 0.1
                elif walkable_view_filter:
                    is_walkable = room.walkable_map.get(tuple(deco.get("grid_pos", ())), 0) == 1
                    if not is_walkable: opacity_ratio = 0.1
                self._draw_decoration(surface, deco, camera_offset, zoom, custom_opacity_ratio=opacity_ratio)

        if is_editor_view and not filter_by_layer:
            anchor_world_x, anchor_world_y = room.structure_data["renderAnchor"]["x"], room.structure_data["renderAnchor"]["y"]
            anchor_pos = (anchor_world_x * zoom + camera_offset[0], anchor_world_y * zoom + camera_offset[1])
            pygame.draw.circle(surface, COLOR_ANCHOR, anchor_pos, 5); pygame.draw.line(surface, COLOR_ANCHOR, (anchor_pos[0] - 8, anchor_pos[1]), (anchor_pos[0] + 8, anchor_pos[1]), 1); pygame.draw.line(surface, COLOR_ANCHOR, (anchor_pos[0], anchor_pos[1] - 8), (anchor_pos[0], anchor_pos[1] + 8), 1)
            pw, ph = PREVIEW_SIZE
            scaled_pw, scaled_ph = pw * zoom, ph * zoom
            preview_bounds_rect = pygame.Rect(anchor_pos[0] - scaled_pw / 2, anchor_pos[1] - scaled_ph / 2, scaled_pw, scaled_ph)
            pygame.draw.rect(surface, COLOR_PREVIEW_OUTLINE, preview_bounds_rect, 1)

    def _draw_iso_grid_on_surface(self, surface, view_rect, offset, zoom=1.0):
        if not view_rect.w or not view_rect.h: return
        corners_grid = [screen_to_grid(0, 0, offset, zoom), screen_to_grid(view_rect.w, 0, offset, zoom), screen_to_grid(view_rect.w, view_rect.h, offset, zoom), screen_to_grid(0, view_rect.h, offset, zoom)]
        min_gx, max_gx = min(c[0] for c in corners_grid) - 1, max(c[0] for c in corners_grid) + 2
        min_gy, max_gy = min(c[1] for c in corners_grid) - 1, max(c[1] for c in corners_grid) + 2
        for gy in range(min_gy, max_gy):
            for gx in range(min_gx, max_gx):
                screen_pos = grid_to_screen(gx, gy, offset, zoom)
                p = self._get_tile_points(screen_pos, zoom)
                pygame.draw.aalines(surface, COLOR_GRID, True, [p['top'], p['right'], p['bottom'], p['left']])

    def _get_tile_points(self, pos, zoom=1.0):
        scaled_twh = TILE_WIDTH_HALF * zoom; scaled_thh = TILE_HEIGHT_HALF * zoom
        scaled_tw = TILE_WIDTH * zoom; scaled_th = TILE_HEIGHT * zoom
        return {"top": (pos[0] + scaled_twh, pos[1]), "right": (pos[0] + scaled_tw, pos[1] + scaled_thh), "bottom": (pos[0] + scaled_twh, pos[1] + scaled_th), "left": (pos[0], pos[1] + scaled_thh)}

    def _get_tile_points_from_type(self, pos, tile_type, zoom):
        p = self._get_tile_points(pos, zoom)
        points_map = { TILE_TYPE_FULL: [p['top'], p['right'], p['bottom'], p['left']], TILE_TYPE_CORNER_NO_TL: [p['top'], p['right'], p['bottom']], TILE_TYPE_CORNER_NO_TR: [p['top'], p['bottom'], p['left']], TILE_TYPE_CORNER_NO_BR: [p['top'], p['right'], p['left']], TILE_TYPE_CORNER_NO_BL: [p['right'], p['bottom'], p['left']] }
        return points_map.get(tile_type)

    def _draw_tile_shape(self, surf, pos, tile_type, fill_color, border_color, zoom=1.0):
        points = self._get_tile_points_from_type(pos, tile_type, zoom)
        if points:
            pygame.draw.polygon(surf, fill_color, points); pygame.draw.aalines(surf, border_color, True, points)

    def _draw_wall(self, surf, screen_pos, edge, zoom=1.0):
        p = self._get_tile_points(screen_pos, zoom); scaled_wall_h = WALL_HEIGHT * zoom
        edge_points = { EDGE_NE: (p['top'], p['right']), EDGE_SE: (p['right'], p['bottom']), EDGE_SW: (p['bottom'], p['left']), EDGE_NW: (p['left'], p['top']), EDGE_DIAG_SW_NE: (p['bottom'], p['top']), EDGE_DIAG_NW_SE: (p['left'], p['right']) }
        p1, p2 = edge_points.get(edge, (None, None))
        if p1 and p2:
            wall_points = [p1, p2, (p2[0], p2[1] - scaled_wall_h), (p1[0], p1[1] - scaled_wall_h)]
            pygame.draw.polygon(surf, COLOR_WALL, wall_points); pygame.draw.polygon(surf, COLOR_WALL_BORDER, wall_points, 2)

    def get_rendered_image_and_offset(self, base_id, variant_id, rotation):
        if not all((base_id, variant_id, rotation is not None)): return None, None
        furni_data = self.data_manager.get_furni_data(base_id)
        if not furni_data: return None, None
        try:
            variant = furni_data["variants"][str(variant_id)]; render_info = variant["renders"][str(rotation)]
            image = self.data_manager.get_image(base_id, render_info["path"])
            if image: return image, (render_info["offset"]['x'], render_info["offset"]['y'])
        except KeyError: pass
        return None, None
        
    def get_decoration_render_details(self, deco_data, camera_offset, zoom=1.0):
        base_id, variant_id = deco_data.get("base_id"), deco_data.get("variant_id", "0")
        grid_pos, rotation = deco_data.get("grid_pos"), deco_data.get("rotation", 0)
        image, offset = self.get_rendered_image_and_offset(base_id, variant_id, rotation)
        if not image or not offset or not grid_pos: return None, None
        screen_pos = grid_to_screen(grid_pos[0], grid_pos[1], camera_offset, zoom)
        img_w, img_h = image.get_size()
        scaled_size = (int(img_w * zoom), int(img_h * zoom))
        if scaled_size[0] <= 0 or scaled_size[1] <= 0: return None, None
        final_image = pygame.transform.scale(image, scaled_size)
        scaled_offset = (offset[0] * zoom, offset[1] * zoom)
        anchor_x = screen_pos[0] + (TILE_WIDTH_HALF * zoom); anchor_y = screen_pos[1] + (TILE_HEIGHT_HALF * zoom)
        draw_x = anchor_x - scaled_offset[0]; draw_y = anchor_y - scaled_offset[1]
        return final_image, (draw_x, draw_y)

    def _draw_decoration(self, surface, deco_data, camera_offset, zoom=1.0, is_ghost=False, is_occupied=False, custom_opacity_ratio=None):
        render_details = self.get_decoration_render_details(deco_data, camera_offset, zoom)
        if not render_details or not render_details[0]:
            if grid_pos := deco_data.get("grid_pos"):
                screen_pos = grid_to_screen(grid_pos[0], grid_pos[1], camera_offset, zoom)
                center_x, center_y = screen_pos[0] + (TILE_WIDTH_HALF * zoom), screen_pos[1] + (TILE_HEIGHT_HALF * zoom)
                pygame.draw.circle(surface, (255, 0, 255), (center_x, center_y), 8)
            return
        final_image, (draw_x, draw_y) = render_details
        if is_ghost:
            ghost_image = final_image.copy()
            alpha = 100 if is_occupied else 150
            ghost_image.set_alpha(alpha)
            if is_occupied:
                red_tint = pygame.Surface(ghost_image.get_size(), pygame.SRCALPHA); red_tint.fill((255, 50, 50, 80))
                ghost_image.blit(red_tint, (0, 0))
            surface.blit(ghost_image, (draw_x, draw_y))
        elif custom_opacity_ratio is not None:
            faded_image = final_image.copy()
            faded_image.set_alpha(int(255 * custom_opacity_ratio))
            surface.blit(faded_image, (draw_x, draw_y))
        else:
            surface.blit(final_image, (draw_x, draw_y))