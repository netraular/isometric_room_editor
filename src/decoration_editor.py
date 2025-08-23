# src/decoration_editor.py
import pygame
import math
import os
from common.constants import *
from common.ui import Button, TextInputBox
from common.utils import grid_to_screen, screen_to_grid

class DecorationEditor:
    SCROLL_SPEED = 30

    def __init__(self, app_ref):
        self.app = app_ref
        self.font_ui = self.app.font_ui
        self.font_title = self.app.font_title
        self.font_desc = pygame.font.SysFont("Arial", 12)
        self.catalog_data = self.app.data_manager.load_catalog()
        self.open_main_cat_indices = set()
        self.selected_deco_item = None
        self.clickable_elements = []
        self.scroll_y = 0
        self.content_height = 0
        self.is_scrolling_with_thumb = False
        self.scroll_start_y = 0
        self.scroll_start_scroll_y = 0
        self.active_search_term = ""
        self.search_input = None
        self.search_button = None
        self.ghost_pos = (0, 0)
        self.hover_grid_pos = None 
        self.ghost_rotation = 0
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.content_surface = None
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None

    def update_layout(self):
        self.panel_rect = self.app.right_panel_rect
        margin, input_height = 10, 28
        button_size = input_height
        button_padding = 5
        self.search_button = Button(self.panel_rect.x + margin, self.panel_rect.y + margin, button_size, button_size, "", self.app.font_ui)
        input_x = self.search_button.rect.right + button_padding
        input_width = self.panel_rect.width - (margin * 2) - button_size - button_padding
        self.search_input = TextInputBox(input_x, self.panel_rect.y + margin, input_width, input_height, self.app.font_ui, input_type='text')
        self.content_surface = pygame.Surface((self.panel_rect.width, 8000), pygame.SRCALPHA)
        scrollbar_width = 15
        self.scrollbar_track_rect = pygame.Rect(self.panel_rect.right - scrollbar_width, self.panel_rect.top, scrollbar_width, self.panel_rect.height)
        self.update_scrollbar_thumb()

    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        if self.search_input.handle_event(event) is not None:
            self.perform_search()
            self.search_input.active = False
        self.search_button.check_hover(mouse_pos)
        if self.search_button.is_clicked(event):
            self.perform_search()
            self.search_input.active = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.scrollbar_thumb_rect and self.scrollbar_thumb_rect.collidepoint(mouse_pos):
                self.is_scrolling_with_thumb = True
                self.scroll_start_y = mouse_pos[1]
                self.scroll_start_scroll_y = self.scroll_y
            if self.panel_rect.collidepoint(mouse_pos):
                if event.button == 4: self.scroll_y -= self.SCROLL_SPEED
                elif event.button == 5: self.scroll_y += self.SCROLL_SPEED
                self.clamp_scroll()
            if event.button == 1:
                is_on_content = self.panel_rect.collidepoint(mouse_pos) and not self.scrollbar_track_rect.collidepoint(mouse_pos) and not self.search_input.rect.collidepoint(mouse_pos) and not self.search_button.rect.collidepoint(mouse_pos)
                if is_on_content:
                    self.handle_panel_click(mouse_pos)
                elif self.selected_deco_item and self.app.editor_rect.collidepoint(mouse_pos):
                    self.place_decoration(self.ghost_pos)
            if event.button == 3 and self.app.editor_rect.collidepoint(mouse_pos):
                clicked_grid_pos = screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera.offset, self.app.camera.zoom)
                self.delete_decoration_at(clicked_grid_pos)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_scrolling_with_thumb = False
        if event.type == pygame.MOUSEMOTION:
            if self.is_scrolling_with_thumb:
                delta_y = mouse_pos[1] - self.scroll_start_y
                scrollable_px_range = self.scrollbar_track_rect.height - self.scrollbar_thumb_rect.height
                scrollable_content_range = self.content_height - self.panel_rect.height
                if scrollable_px_range > 0:
                    self.scroll_y = self.scroll_start_scroll_y + delta_y * (scrollable_content_range / scrollable_px_range)
                    self.clamp_scroll()
            
            if self.app.editor_rect.collidepoint(mouse_pos) and not self.app.camera.is_panning:
                self.hover_grid_pos = screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera.offset, self.app.camera.zoom)
                if self.selected_deco_item:
                    self.ghost_pos = self.hover_grid_pos
            else:
                self.hover_grid_pos = None
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.selected_deco_item = None
            elif event.key == pygame.K_r and self.selected_deco_item:
                self.rotate_ghost_to_next_valid()

    def rotate_ghost_to_next_valid(self):
        base_id = self.selected_deco_item.get("base_id")
        variant_id = self.selected_deco_item.get("variant_id", "0")
        for i in range(1, 5):
            next_rotation_idx = (self.ghost_rotation + i) % 4
            image, _ = self.app.renderer.get_rendered_image_and_offset(base_id, variant_id, next_rotation_idx)
            if image is not None:
                self.ghost_rotation = next_rotation_idx
                return
    
    def delete_decoration_at(self, grid_pos):
        if self.app.current_room:
            self.app.current_room.remove_decoration_at(grid_pos)

    def place_decoration(self, grid_pos):
        if not self.selected_deco_item or not self.app.current_room:
            return
            
        # --- LÍNEA CORREGIDA ---
        # Se ha reemplazado 'color_id' por 'variant_id' para que coincida con la nueva estructura de datos.
        self.app.current_room.add_decoration(self.selected_deco_item['base_id'], self.selected_deco_item['variant_id'], grid_pos, self.ghost_rotation)
        
    def perform_search(self):
        self.active_search_term = self.search_input.text.lower().strip()
        self.scroll_y = 0

    def clamp_scroll(self):
        max_scroll = self.content_height - (self.panel_rect.height - self.search_input.rect.height - 20)
        self.scroll_y = max(0, min(self.scroll_y, max(0, max_scroll)))

    def handle_panel_click(self, mouse_pos):
        content_y_start = self.search_input.rect.bottom + 10
        local_x = mouse_pos[0] - self.panel_rect.x
        local_y = mouse_pos[1] - content_y_start + self.scroll_y
        for element in self.clickable_elements:
            if element['rect'].collidepoint(local_x, local_y):
                elem_type, elem_id = element['type'], element['id']
                if elem_type == 'main_cat':
                    if elem_id in self.open_main_cat_indices:
                        self.open_main_cat_indices.remove(elem_id)
                    else:
                        self.open_main_cat_indices.add(elem_id)
                elif elem_type == 'item':
                    self.selected_deco_item = elem_id
                    self.ghost_rotation = 0
                return

    def get_selected_item_image(self):
        if not self.selected_deco_item:
            return None, None
        image, offset = self.app.renderer.get_rendered_image_and_offset(self.selected_deco_item.get("base_id"), self.selected_deco_item.get("variant_id"), self.ghost_rotation)
        return image, offset

    def draw_on_editor(self, surface):
        if self.hover_grid_pos:
            hover_screen_pos = grid_to_screen(*self.hover_grid_pos, self.app.camera.offset, self.app.camera.zoom)
            p = self.app.renderer._get_tile_points(hover_screen_pos, self.app.camera.zoom)
            pygame.draw.polygon(surface, COLOR_HOVER_BORDER, [p['top'], p['right'], p['bottom'], p['left']], 3)

        if self.selected_deco_item and self.app.current_room and self.hover_grid_pos:
            ghost_data = {
                "base_id": self.selected_deco_item.get("base_id"),
                "variant_id": self.selected_deco_item.get("variant_id", "0"),
                "grid_pos": self.ghost_pos,
                "rotation": self.ghost_rotation
            }
            is_occupied = tuple(self.ghost_pos) in self.app.current_room.occupied_tiles
            self.app.renderer._draw_decoration(surface, ghost_data, self.app.camera.offset, self.app.camera.zoom, is_ghost=True, is_occupied=is_occupied)

    def get_info_lines(self):
        return ["[Left Click] Place Item", "[Right Click] Delete Item", "[R] Rotate Ghost", "[Esc] Deselect"]

    def draw_ui_on_panel(self, screen):
        pygame.draw.rect(screen, COLOR_PANEL_BG, self.panel_rect)
        self.draw_content()
        content_y_start = self.search_input.rect.bottom + 10
        draw_area = pygame.Rect(self.panel_rect.x, content_y_start, self.panel_rect.width, self.panel_rect.height - (content_y_start - self.panel_rect.top))
        screen.blit(self.content_surface, draw_area, pygame.Rect(0, self.scroll_y, draw_area.width, draw_area.height))
        bg_rect = self.search_button.rect.union(self.search_input.rect).inflate(20, 20)
        pygame.draw.rect(screen, COLOR_PANEL_BG, bg_rect)
        self.search_button.draw(screen)
        self.draw_search_icon(screen, self.search_button.rect)
        self.search_input.update()
        self.search_input.draw(screen)
        if not self.search_input.text and not self.search_input.active:
            screen.blit(self.app.font_ui.render("Search items...", True, COLOR_INFO_TEXT), (self.search_input.rect.x + 8, self.search_input.rect.y + 6))
        pygame.draw.rect(screen, COLOR_BORDER, self.panel_rect, 1)
        self.draw_scrollbar(screen)

    def draw_search_icon(self, screen, rect):
        center = rect.center
        radius = min(rect.width, rect.height) // 4
        pygame.draw.circle(screen, COLOR_TEXT, center, radius, 2)
        angle = math.radians(135)
        start_pos = (center[0] + radius * math.cos(angle), center[1] - radius * math.sin(angle))
        end_pos = (center[0] + radius * 2 * math.cos(angle), center[1] - radius * 2 * math.sin(angle))
        pygame.draw.line(screen, COLOR_TEXT, start_pos, end_pos, 3)

    def draw_content(self):
        self.content_surface.fill((0, 0, 0, 0))
        self.clickable_elements.clear()
        self.content_height = self.draw_search_results_view() if self.active_search_term else self.draw_catalog_view()

    def draw_search_results_view(self):
        search_results = []
        processed_ids = set()
        for category in self.catalog_data.get("categories", []):
            for item in category.get("items", []):
                if self.active_search_term in item['name'].lower() and item['id'] not in processed_ids:
                    search_results.append(item)
                    processed_ids.add(item['id'])
        margin = 10
        has_scrollbar = self.content_height > self.panel_rect.height
        content_width = self.panel_rect.width - margin * 2 - (self.scrollbar_track_rect.width if has_scrollbar else 0)
        if not search_results:
            msg_surf = self.font_ui.render(f"No results for '{self.active_search_term}'", True, COLOR_INFO_TEXT)
            self.content_surface.blit(msg_surf, msg_surf.get_rect(centerx=self.panel_rect.width / 2, y=20))
            return 60
        return self.draw_item_grid(search_results, margin, 10, content_width)

    def draw_catalog_view(self):
        y_pos, margin = 0, 10
        has_scrollbar = self.content_height > self.panel_rect.height
        content_width = self.panel_rect.width - margin * 2 - (self.scrollbar_track_rect.width if has_scrollbar else 0)
        
        # The structure is now flat: just iterate through the main categories
        for i, category in enumerate(self.catalog_data.get("categories", [])):
            is_open = i in self.open_main_cat_indices
            
            # Draw the category button
            rect = pygame.Rect(margin, y_pos, content_width, 28)
            pygame.draw.rect(self.content_surface, COLOR_BUTTON_ACTIVE if is_open else COLOR_BUTTON, rect, border_radius=5)
            self.clickable_elements.append({'rect': rect, 'type': 'main_cat', 'id': i})
            
            title_text = ("v " if is_open else "> ") + category["name"]
            title = self.font_ui.render(title_text, True, COLOR_TEXT)
            self.content_surface.blit(title, (rect.x + 10, rect.centery - title.get_height() // 2))
            y_pos += rect.height + 5

            # If the category is open, draw its items
            if is_open and category["items"]:
                # The item grid is drawn directly under the main category, slightly indented
                y_pos += self.draw_item_grid(category["items"], margin + 15, y_pos, content_width - 15)
        
        return y_pos

    def draw_item_grid(self, items, start_x, start_y, width):
        icon_size, padding = 60, 10
        cols = max(1, (width + padding) // (icon_size + padding))
        for k, item in enumerate(items):
            item_rect = pygame.Rect(start_x + (k % cols) * (icon_size + padding), start_y + (k // cols) * (icon_size + 30 + padding), icon_size, icon_size)
            self.clickable_elements.append({'rect': pygame.Rect(item_rect.x, item_rect.y, icon_size, icon_size + 30), 'type': 'item', 'id': item})
            
            icon_img = self.app.data_manager.get_image(item['base_id'], item['icon_path'])
            
            if icon_img:
                pygame.draw.rect(self.content_surface, COLOR_EDITOR_BG, item_rect, border_radius=5)
                max_size = icon_size - 8
                img_w, img_h = icon_img.get_size()
                
                final_img = icon_img
                # Only scale down if necessary to avoid distortion
                if img_w > max_size or img_h > max_size:
                    scale = min(max_size / img_w, max_size / img_h)
                    scaled_size = (int(img_w * scale), int(img_h * scale))
                    final_img = pygame.transform.smoothscale(icon_img, scaled_size)

                self.content_surface.blit(final_img, final_img.get_rect(center=item_rect.center))
            
            is_selected = self.selected_deco_item and self.selected_deco_item['id'] == item['id']
            pygame.draw.rect(self.content_surface, COLOR_HOVER_BORDER if is_selected else COLOR_BORDER, item_rect, 2 if is_selected else 1, border_radius=5)
            
            item_name_y = item_rect.bottom + 4
            words = item['name'].split(' ')
            line = ""
            for word in words:
                if self.font_desc.size(line + word + " ")[0] <= icon_size:
                    line += word + " "
                else:
                    surf = self.font_desc.render(line.strip(), True, COLOR_TEXT)
                    self.content_surface.blit(surf, surf.get_rect(centerx=item_rect.centerx, top=item_name_y))
                    item_name_y += self.font_desc.get_linesize()
                    line = word + " "
            if line:
                surf = self.font_desc.render(line.strip(), True, COLOR_TEXT)
                self.content_surface.blit(surf, surf.get_rect(centerx=item_rect.centerx, top=item_name_y))
                
        return (-(-len(items) // cols) if items else 0) * (icon_size + 30 + padding) + 10

    def update_scrollbar_thumb(self):
        content_visible_h = self.panel_rect.height - (self.search_input.rect.height if self.search_input else 0) - 20
        if self.content_height > content_visible_h:
            thumb_h = max(20, content_visible_h * (content_visible_h / self.content_height))
            scroll_ratio = self.scroll_y / max(1, self.content_height - content_visible_h)
            thumb_y = self.scrollbar_track_rect.y + scroll_ratio * (self.scrollbar_track_rect.height - thumb_h)
            self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_track_rect.x, thumb_y, self.scrollbar_track_rect.width, thumb_h)
        else:
            self.scrollbar_thumb_rect = None

    def draw_scrollbar(self, screen):
        self.update_scrollbar_thumb()
        if self.scrollbar_thumb_rect:
            pygame.draw.rect(screen, COLOR_SCROLLBAR_BG, self.scrollbar_track_rect)
            color = COLOR_SCROLLBAR_THUMB_HOVER if self.scrollbar_thumb_rect.collidepoint(pygame.mouse.get_pos()) or self.is_scrolling_with_thumb else COLOR_SCROLLBAR_THUMB
            pygame.draw.rect(screen, color, self.scrollbar_thumb_rect, border_radius=4)