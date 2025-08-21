# src/decoration_editor.py

import pygame
import math
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

        # --- ESTADO DE LA UI ---
        self.open_main_cat_indices = set()
        self.open_sub_cat_indices = set()
        self.selected_deco_item = None
        self.clickable_elements = []

        # --- ESTADO DE SCROLL ---
        self.scroll_y = 0
        self.content_height = 0
        self.is_scrolling_with_thumb = False
        self.scroll_start_y = 0
        self.scroll_start_scroll_y = 0

        # --- ESTADO DE BÚSQUEDA ---
        # active_search_term solo se actualiza cuando se realiza una búsqueda
        self.active_search_term = "" 
        self.search_input = None
        self.search_button = None

        # --- ESTADO DEL EDITOR (GHOST) ---
        self.ghost_image = None
        self.ghost_pos = (0, 0)

        # --- RECTS Y SURFACES ---
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.content_surface = None
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None

    def update_layout(self):
        self.panel_rect = self.app.right_panel_rect
        margin, input_height = 10, 28
        
        # --- LÓGICA DE LAYOUT MODIFICADA PARA EL BOTÓN ---
        button_size = input_height
        button_padding = 5
        
        self.search_button = Button(
            self.panel_rect.x + margin, self.panel_rect.y + margin,
            button_size, button_size, "", self.app.font_ui
        )
        
        input_x = self.search_button.rect.right + button_padding
        input_width = self.panel_rect.width - (margin * 2) - button_size - button_padding

        self.search_input = TextInputBox(
            input_x, self.panel_rect.y + margin,
            input_width, input_height,
            self.app.font_ui, input_type='text'
        )
        # --- FIN DE MODIFICACIONES DE LAYOUT ---
        
        self.content_surface = pygame.Surface((self.panel_rect.width, 8000), pygame.SRCALPHA)
        
        scrollbar_width = 15
        self.scrollbar_track_rect = pygame.Rect(
            self.panel_rect.right - scrollbar_width, self.panel_rect.top,
            scrollbar_width, self.panel_rect.height
        )
        self.update_scrollbar_thumb()

    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        # --- LÓGICA DE EVENTOS MODIFICADA PARA LA BÚSQUEDA ---
        # 1. El input de texto ahora se activa al pulsar Enter o el botón.
        if self.search_input.handle_event(event) is not None:
            self.perform_search()
            self.search_input.active = False # Desactivar el input al pulsar Enter
        
        self.search_button.check_hover(mouse_pos)
        if self.search_button.is_clicked(event):
            self.perform_search()
            self.search_input.active = False # También desactivar al usar el botón
        # --- FIN DE MODIFICACIONES DE LÓGICA DE BÚSQUEDA ---

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.scrollbar_thumb_rect and self.scrollbar_thumb_rect.collidepoint(mouse_pos):
                self.is_scrolling_with_thumb = True
                self.scroll_start_y = mouse_pos[1]
                self.scroll_start_scroll_y = self.scroll_y
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.is_scrolling_with_thumb = False
        if event.type == pygame.MOUSEMOTION and self.is_scrolling_with_thumb:
            delta_y = mouse_pos[1] - self.scroll_start_y
            scrollable_px_range = self.scrollbar_track_rect.height - self.scrollbar_thumb_rect.height
            scrollable_content_range = self.content_height - self.panel_rect.height
            if scrollable_px_range > 0:
                ratio = scrollable_content_range / scrollable_px_range
                self.scroll_y = self.scroll_start_scroll_y + delta_y * ratio
                self.clamp_scroll()

        if self.panel_rect.collidepoint(mouse_pos) and event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4: self.scroll_y -= self.SCROLL_SPEED
            elif event.button == 5: self.scroll_y += self.SCROLL_SPEED
            self.clamp_scroll()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            is_on_content = self.panel_rect.collidepoint(mouse_pos) and \
                            not self.scrollbar_track_rect.collidepoint(mouse_pos) and \
                            not self.search_input.rect.collidepoint(mouse_pos) and \
                            not self.search_button.rect.collidepoint(mouse_pos)
            if is_on_content:
                self.handle_panel_click(mouse_pos)
            elif self.selected_deco_item and self.app.editor_rect.collidepoint(mouse_pos):
                self.place_decoration(self.ghost_pos)
        
        if self.selected_deco_item and self.app.editor_rect.collidepoint(mouse_pos):
            self.ghost_pos = screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera_offset)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.selected_deco_item, self.ghost_image = None, None

    # --- NUEVO MÉTODO ---
    def perform_search(self):
        """Actualiza el término de búsqueda activo y resetea el scroll."""
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
                    if elem_id in self.open_main_cat_indices: self.open_main_cat_indices.remove(elem_id)
                    else: self.open_main_cat_indices.add(elem_id)
                elif elem_type == 'sub_cat':
                    if elem_id in self.open_sub_cat_indices: self.open_sub_cat_indices.remove(elem_id)
                    else: self.open_sub_cat_indices.add(elem_id)
                elif elem_type == 'item':
                    self.selected_deco_item = elem_id
                    self.ghost_image = self.app.data_manager.get_image(elem_id['icon_path'])
                return

    def draw_ui_on_panel(self, screen):
        pygame.draw.rect(screen, COLOR_PANEL_BG, self.panel_rect)
        self.draw_content()

        content_y_start = self.search_input.rect.bottom + 10
        draw_area = pygame.Rect(
            self.panel_rect.x, content_y_start, self.panel_rect.width,
            self.panel_rect.height - (content_y_start - self.panel_rect.top)
        )
        source_area = pygame.Rect(0, self.scroll_y, draw_area.width, draw_area.height)
        screen.blit(self.content_surface, draw_area, source_area)

        # Dibuja la barra de búsqueda y el botón
        bg_rect = self.search_button.rect.union(self.search_input.rect).inflate(20, 20)
        pygame.draw.rect(screen, COLOR_PANEL_BG, bg_rect)
        
        self.search_button.draw(screen)
        self.draw_search_icon(screen, self.search_button.rect)

        self.search_input.update()
        self.search_input.draw(screen)
        if not self.search_input.text and not self.search_input.active:
            placeholder = self.app.font_ui.render("Search items...", True, COLOR_INFO_TEXT)
            screen.blit(placeholder, (self.search_input.rect.x + 8, self.search_input.rect.y + 6))

        pygame.draw.rect(screen, COLOR_BORDER, self.panel_rect, 1)
        self.draw_scrollbar(screen)

    # --- NUEVO MÉTODO ---
    def draw_search_icon(self, screen, rect):
        """Dibuja un icono de lupa dentro del rectángulo dado."""
        center = rect.center
        radius = min(rect.width, rect.height) // 4
        
        # Círculo de la lupa
        pygame.draw.circle(screen, COLOR_TEXT, center, radius, 2)
        
        # Mango de la lupa
        angle = math.radians(135) # Abajo a la derecha
        start_pos = (center[0] + radius * math.cos(angle), center[1] - radius * math.sin(angle))
        end_pos = (center[0] + radius * 2 * math.cos(angle), center[1] - radius * 2 * math.sin(angle))
        pygame.draw.line(screen, COLOR_TEXT, start_pos, end_pos, 3)

    def draw_content(self):
        self.content_surface.fill((0, 0, 0, 0))
        self.clickable_elements.clear()
        
        if self.active_search_term:
            y_pos = self.draw_search_results_view()
        else:
            y_pos = self.draw_catalog_view()
        
        self.content_height = y_pos

    def draw_search_results_view(self):
        search_results = []
        for main_cat in self.catalog_data.get("categories", []):
            for sub_cat in main_cat.get("subcategories", []):
                for item in sub_cat.get("items", []):
                    if self.active_search_term in item['name'].lower():
                        search_results.append(item)

        margin = 10
        has_scrollbar = self.content_height > self.panel_rect.height
        content_width = self.panel_rect.width - margin * 2 - (self.scrollbar_track_rect.width if has_scrollbar else 0)

        if not search_results:
            msg_surf = self.font_ui.render(f"No results for '{self.active_search_term}'", True, COLOR_INFO_TEXT)
            r = msg_surf.get_rect(centerx=self.panel_rect.width / 2, y=20)
            self.content_surface.blit(msg_surf, r)
            return 60

        items_height = self.draw_item_grid(search_results, margin, 10, content_width)
        return items_height

    def draw_catalog_view(self):
        y_pos, margin = 0, 10
        has_scrollbar = self.content_height > self.panel_rect.height
        content_width = self.panel_rect.width - margin * 2 - (self.scrollbar_track_rect.width if has_scrollbar else 0)

        for i, main_cat in enumerate(self.catalog_data.get("categories", [])):
            is_open = i in self.open_main_cat_indices
            rect = pygame.Rect(margin, y_pos, content_width, 28)
            color = COLOR_BUTTON_ACTIVE if is_open else COLOR_BUTTON
            pygame.draw.rect(self.content_surface, color, rect, border_radius=5)
            self.clickable_elements.append({'rect': rect, 'type': 'main_cat', 'id': i})

            arrow = "v " if is_open else "> "
            title = self.font_ui.render(arrow + main_cat["name"], True, COLOR_TEXT)
            self.content_surface.blit(title, (rect.x + 10, rect.centery - title.get_height() // 2))
            y_pos += rect.height + 5

            if is_open:
                for j, sub_cat in enumerate(main_cat["subcategories"]):
                    sub_is_open = (i, j) in self.open_sub_cat_indices
                    sub_rect = pygame.Rect(margin + 15, y_pos, content_width - 15, 22)
                    sub_color = COLOR_BUTTON_HOVER if sub_is_open else (45, 55, 65)
                    pygame.draw.rect(self.content_surface, sub_color, sub_rect, border_radius=3)
                    self.clickable_elements.append({'rect': sub_rect, 'type': 'sub_cat', 'id': (i, j)})
                    
                    sub_arrow = "v " if sub_is_open else "> "
                    sub_title = self.font_ui.render(sub_arrow + sub_cat["name"], True, COLOR_TEXT)
                    self.content_surface.blit(sub_title, sub_title.get_rect(center=sub_rect.center))
                    y_pos += sub_rect.height + 4

                    if sub_is_open:
                        items_to_draw = sub_cat["items"]
                        if items_to_draw:
                            y_pos += self.draw_item_grid(items_to_draw, margin + 15, y_pos + 10, content_width - 15)
        return y_pos

    def draw_item_grid(self, items, start_x, start_y, width):
        icon_size, padding = 60, 10
        cols = max(1, (width + padding) // (icon_size + padding))
        
        for k, item in enumerate(items):
            item_rect_x = start_x + (k % cols) * (icon_size + padding)
            item_rect_y = start_y + (k // cols) * (icon_size + 30 + padding)
            item_rect = pygame.Rect(item_rect_x, item_rect_y, icon_size, icon_size)
            self.clickable_elements.append({'rect': pygame.Rect(item_rect.x, item_rect.y, icon_size, icon_size + 30), 'type': 'item', 'id': item})
            
            icon_img = self.app.data_manager.get_image(item['icon_path'])
            if icon_img:
                pygame.draw.rect(self.content_surface, COLOR_EDITOR_BG, item_rect, border_radius=5)
                img_s = pygame.transform.scale(icon_img, (icon_size - 8, icon_size - 8))
                self.content_surface.blit(img_s, img_s.get_rect(center=item_rect.center))
            
            is_selected = self.selected_deco_item and self.selected_deco_item['id'] == item['id']
            border_color = COLOR_HOVER_BORDER if is_selected else COLOR_BORDER
            pygame.draw.rect(self.content_surface, border_color, item_rect, 2 if is_selected else 1, border_radius=5)
            
            item_name_y = item_rect.bottom + 4
            words = item['name'].split(' '); line = ""
            for word in words:
                if self.font_desc.size(line + word + " ")[0] <= icon_size: line += word + " "
                else:
                    surf = self.font_desc.render(line.strip(), True, COLOR_TEXT)
                    self.content_surface.blit(surf, surf.get_rect(centerx=item_rect.centerx, top=item_name_y))
                    item_name_y += self.font_desc.get_linesize(); line = word + " "
            if line:
                surf = self.font_desc.render(line.strip(), True, COLOR_TEXT)
                self.content_surface.blit(surf, surf.get_rect(centerx=item_rect.centerx, top=item_name_y))
        
        num_rows = -(-len(items) // cols) if items else 0
        return num_rows * (icon_size + 30 + padding) + 10

    def update_scrollbar_thumb(self):
        content_visible_h = self.panel_rect.height - (self.search_input.rect.height if self.search_input else 0) - 20
        if self.content_height > content_visible_h:
            thumb_h = max(20, content_visible_h * (content_visible_h / self.content_height))
            scroll_ratio = self.scroll_y / max(1, self.content_height - content_visible_h)
            thumb_y = self.scrollbar_track_rect.y + scroll_ratio * (self.scrollbar_track_rect.height - thumb_h)
            self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_track_rect.x, thumb_y, self.scrollbar_track_rect.width, thumb_h)
        else: self.scrollbar_thumb_rect = None

    def draw_scrollbar(self, screen):
        self.update_scrollbar_thumb()
        if self.scrollbar_thumb_rect:
            pygame.draw.rect(screen, COLOR_SCROLLBAR_BG, self.scrollbar_track_rect)
            is_hovered = self.scrollbar_thumb_rect.collidepoint(pygame.mouse.get_pos())
            color = COLOR_SCROLLBAR_THUMB_HOVER if is_hovered or self.is_scrolling_with_thumb else COLOR_SCROLLBAR_THUMB
            pygame.draw.rect(screen, color, self.scrollbar_thumb_rect, border_radius=4)

    def place_decoration(self, grid_pos):
        if not self.selected_deco_item: return
        self.app.placed_decorations.append({
            "base_id": self.selected_deco_item['base_id'],
            "color_id": self.selected_deco_item['color_id'],
            "grid_pos": list(grid_pos), "rotation": 0
        })

    def draw_on_editor(self, surface):
        for deco in self.app.placed_decorations:
             pos, base_id = deco.get("grid_pos"), deco.get("base_id")
             if pos and base_id:
                 deco_data = self.app.data_manager.load_decoration_data(base_id)
                 if not deco_data: continue
                 asset_key = f"{base_id}_64_a_2_0"
                 if asset_key not in deco_data.get("assets", {}): asset_key = f"{base_id}_icon_a"
                 if asset_key in deco_data.get("assets", {}):
                     asset_info = deco_data["assets"][asset_key]
                     asset_path = f"furnis/{base_id}/{asset_info.get('name', asset_key)}.png"
                     image = self.app.data_manager.get_image(asset_path)
                     if image:
                        offset_x, offset_y = int(asset_info.get('x', 0)), int(asset_info.get('y', 0))
                        sp = grid_to_screen(pos[0], pos[1], self.app.camera_offset)
                        draw_pos = (sp[0] + TILE_WIDTH_HALF + offset_x, sp[1] + TILE_HEIGHT_HALF + offset_y - image.get_height())
                        surface.blit(image, draw_pos)
        if self.ghost_image and self.app.editor_rect.collidepoint(pygame.mouse.get_pos()):
            sp = grid_to_screen(self.ghost_pos[0], self.ghost_pos[1], self.app.camera_offset)
            draw_pos = (sp[0] + (TILE_WIDTH - self.ghost_image.get_width()) // 2, sp[1] - self.ghost_image.get_height() + TILE_HEIGHT)
            temp = self.ghost_image.copy(); temp.set_alpha(150); surface.blit(temp, draw_pos)

    def get_info_lines(self):
        return ["[Click Item] Select", "[Click Canvas] Place", "[Esc] Deselect", "[Mouse Wheel] Scroll List"]