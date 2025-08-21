# src/decoration_editor.py

import pygame
import math
import os # Necesario para construir rutas de archivo
from common.constants import *
from common.ui import Button, TextInputBox
from common.utils import grid_to_screen, screen_to_grid

class DecorationEditor:
    SCROLL_SPEED = 30
    # Mapea la rotación del editor (0-3) a la dirección del sprite (0,2,4,6).
    ROTATION_MAP = [2, 4, 6, 0]

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
        self.active_search_term = "" 
        self.search_input = None
        self.search_button = None

        # --- ESTADO DEL EDITOR (GHOST) ---
        self.ghost_pos = (0, 0)
        self.ghost_rotation = 0

        # --- RECTS Y SURFACES ---
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.content_surface = None
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None

    def update_layout(self):
        self.panel_rect = self.app.right_panel_rect
        margin, input_height = 10, 28
        
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
        
        self.content_surface = pygame.Surface((self.panel_rect.width, 8000), pygame.SRCALPHA)
        
        scrollbar_width = 15
        self.scrollbar_track_rect = pygame.Rect(
            self.panel_rect.right - scrollbar_width, self.panel_rect.top,
            scrollbar_width, self.panel_rect.height
        )
        self.update_scrollbar_thumb()

    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        if self.search_input.handle_event(event) is not None:
            self.perform_search()
            self.search_input.active = False
        
        self.search_button.check_hover(mouse_pos)
        if self.search_button.is_clicked(event):
            self.perform_search()
            self.search_input.active = False

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
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                print("[LOG] Objeto deseleccionado con ESC.")
                self.selected_deco_item = None
            elif event.key == pygame.K_r and self.selected_deco_item:
                self.ghost_rotation = (self.ghost_rotation + 1) % 4
                print(f"[LOG] Fantasma rotado. Nuevo índice de rotación: {self.ghost_rotation} (Dirección de sprite: {self.ROTATION_MAP[self.ghost_rotation]})")

    def perform_search(self):
        self.active_search_term = self.search_input.text.lower().strip()
        print(f"[LOG] Realizando búsqueda de: '{self.active_search_term}'")
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
                    self.ghost_rotation = 0
                    print(f"[LOG] Objeto seleccionado: {self.selected_deco_item['name']} (base_id: {self.selected_deco_item['base_id']})")
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

        bg_rect = self.search_button.rect.union(self.search_input.rect).inflate(20, 20)
        pygame.draw.rect(screen, COLOR_PANEL_BG, bg_rect)
        
        self.search_button.draw(screen)
        self.draw_search_icon(screen, self.search_button.rect)

        self.search_input.update()
        self.search_input.draw(screen)
        if not self.search_input.text and not self.search_input.active:
            placeholder = self.app.font_ui.render("Buscar objetos...", True, COLOR_INFO_TEXT)
            screen.blit(placeholder, (self.search_input.rect.x + 8, self.search_input.rect.y + 6))

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
        
        if self.active_search_term:
            y_pos = self.draw_search_results_view()
        else:
            y_pos = self.draw_catalog_view()
        
        self.content_height = y_pos

    def draw_search_results_view(self):
        search_results = []
        processed_ids = set()
        for main_cat in self.catalog_data.get("categories", []):
            for sub_cat in main_cat.get("subcategories", []):
                for item in sub_cat.get("items", []):
                    if self.active_search_term in item['name'].lower() and item['id'] not in processed_ids:
                        search_results.append(item)
                        processed_ids.add(item['id'])

        margin = 10
        has_scrollbar = self.content_height > self.panel_rect.height
        content_width = self.panel_rect.width - margin * 2 - (self.scrollbar_track_rect.width if has_scrollbar else 0)

        if not search_results:
            msg_surf = self.font_ui.render(f"No hay resultados para '{self.active_search_term}'", True, COLOR_INFO_TEXT)
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
        print(f"[LOG] Colocando decoración '{self.selected_deco_item['base_id']}' en {grid_pos} con rotación {self.ghost_rotation}")
        self.app.placed_decorations.append({
            "base_id": self.selected_deco_item['base_id'],
            "color_id": self.selected_deco_item['color_id'],
            "grid_pos": list(grid_pos), 
            "rotation": self.ghost_rotation
        })

    def _get_rendered_image(self, base_id, color_id, rotation):
        """Busca y carga la imagen pre-renderizada SIN SOMBRA de un objeto."""
        direction = self.ROTATION_MAP[rotation % 4]
        
        # <-- CAMBIO: Añadido '_no_sd' para usar renders sin sombra -->
        filename_with_color = f"{base_id}_dir_{direction}_{color_id}_no_sd.png"
        relative_path_with_color = os.path.join("furnis", base_id, "rendered", filename_with_color).replace("\\", "/")
        
        image = self.app.data_manager.get_image(relative_path_with_color)
        if image:
            return image

        # <-- CAMBIO: Añadido '_no_sd' para usar renders sin sombra -->
        filename_default = f"{base_id}_dir_{direction}_no_sd.png"
        relative_path_default = os.path.join("furnis", base_id, "rendered", filename_default).replace("\\", "/")

        image = self.app.data_manager.get_image(relative_path_default)
        if image:
            return image
        
        # <-- CAMBIO: Mensaje de error actualizado para reflejar la búsqueda de '_no_sd' -->
        print(f"[ERROR] No se encontró la imagen renderizada SIN SOMBRA para '{base_id}' en dirección {direction} (color: {color_id}). Rutas buscadas:\n  - {relative_path_with_color}\n  - {relative_path_default}")
        return None

    def get_selected_item_image(self):
        """Obtiene la imagen renderizada del ítem actualmente seleccionado para la vista previa, respetando la rotación actual."""
        if not self.selected_deco_item:
            return None
        
        base_id = self.selected_deco_item.get("base_id")
        color_id = self.selected_deco_item.get("color_id")
        
        # <-- CAMBIO: Usa la rotación del fantasma en lugar de un valor fijo -->
        return self._get_rendered_image(base_id, color_id, self.ghost_rotation)

    def _draw_decoration(self, surface, base_id, color_id, grid_pos, rotation, is_ghost=False):
        """Dibuja una decoración usando su imagen pre-renderizada."""
        image = self._get_rendered_image(base_id, color_id, rotation)
        if not image:
            return

        screen_pos = grid_to_screen(grid_pos[0], grid_pos[1], self.app.camera_offset)
        tile_center_x = screen_pos[0] + TILE_WIDTH_HALF
        tile_center_y = screen_pos[1] + TILE_HEIGHT_HALF
        
        draw_x = tile_center_x - image.get_width() // 2
        draw_y = tile_center_y - image.get_height()

        if is_ghost:
            ghost_image = image.copy()
            ghost_image.set_alpha(150)
            surface.blit(ghost_image, (draw_x, draw_y))
        else:
            surface.blit(image, (draw_x, draw_y))

    def draw_on_editor(self, surface):
        sorted_decos = sorted(self.app.placed_decorations, key=lambda d: (d['grid_pos'][1] + d['grid_pos'][0], d['grid_pos'][1] - d['grid_pos'][0]))
        
        for deco in sorted_decos:
            pos = deco.get("grid_pos")
            base_id = deco.get("base_id")
            color_id = deco.get("color_id", "0")
            rotation = deco.get("rotation", 0)
            if pos and base_id:
                self._draw_decoration(surface, base_id, color_id, pos, rotation)

        if self.selected_deco_item and self.app.editor_rect.collidepoint(pygame.mouse.get_pos()):
            base_id = self.selected_deco_item.get("base_id")
            color_id = self.selected_deco_item.get("color_id", "0")
            if base_id:
                self._draw_decoration(surface, base_id, color_id, self.ghost_pos, self.ghost_rotation, is_ghost=True)

    def get_info_lines(self):
        return ["[Click Item] Seleccionar", "[Click Lienzo] Colocar", "[R] Rotar Fantasma", "[Esc] Deseleccionar", "[Rueda Ratón] Scroll"]