import pygame
from common.constants import *
from common.ui import Button
from common.utils import grid_to_screen, screen_to_grid

class DecorationEditor:
    def __init__(self, app_ref):
        self.app = app_ref
        self.font_ui = self.app.font_ui
        self.font_info = self.app.font_info
        self.font_title = self.app.font_title

        self.catalog_data = self.app.data_manager.load_catalog()
        
        # Estado de la UI
        self.active_main_cat_idx = -1  # Índice de la categoría principal abierta
        self.active_sub_cat_idx = -1   # Índice de la subcategoría seleccionada
        self.selected_deco_item = None
        self.scroll_y = 0 # Para el scroll de los items

        # Estado del editor
        self.ghost_image = None
        self.ghost_pos = (0, 0)
        
        # Rects para la detección de clics
        self.main_cat_rects = []
        self.sub_cat_rects = []
        self.icon_rects = []

    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Comprobar clics en categorías principales
            for i, rect in enumerate(self.main_cat_rects):
                if rect.collidepoint(mouse_pos):
                    if self.active_main_cat_idx == i:
                        self.active_main_cat_idx = -1 # Colapsar
                    else:
                        self.active_main_cat_idx = i  # Expandir
                    # Resetear selecciones inferiores
                    self.active_sub_cat_idx = -1
                    self.selected_deco_item = None
                    self.ghost_image = None
                    self.scroll_y = 0
                    return # Evento manejado

            # Comprobar clics en subcategorías
            for i, rect in enumerate(self.sub_cat_rects):
                if rect.collidepoint(mouse_pos):
                    self.active_sub_cat_idx = i
                    self.selected_deco_item = None
                    self.ghost_image = None
                    self.scroll_y = 0
                    return # Evento manejado

            # Comprobar clics en iconos de items
            for i, rect in enumerate(self.icon_rects):
                 if rect.collidepoint(mouse_pos):
                    active_main = self.catalog_data["categories"][self.active_main_cat_idx]
                    active_sub = active_main["subcategories"][self.active_sub_cat_idx]
                    item = active_sub["items"][i]
                    self.selected_deco_item = item
                    self.ghost_image = self.app.data_manager.get_image(item['icon_path'])
                    return # Evento manejado

        # Lógica de colocación en el editor
        if self.selected_deco_item and self.app.editor_rect.collidepoint(mouse_pos):
            self.ghost_pos = screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera_offset)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.place_decoration(self.ghost_pos)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.selected_deco_item = None
            self.ghost_image = None

    def place_decoration(self, grid_pos):
        if not self.selected_deco_item: return
        self.app.placed_decorations.append({
            "base_id": self.selected_deco_item['base_id'],
            "color_id": self.selected_deco_item['color_id'],
            "grid_pos": list(grid_pos), "rotation": 0
        })

    def draw_ui_on_panel(self, screen):
        self.main_cat_rects.clear(); self.sub_cat_rects.clear(); self.icon_rects.clear()
        margin = 15
        y_pos = self.app.right_panel_rect.y + 10
        panel_width = self.app.right_panel_rect.width

        # 1. Dibujar Categorías Principales (Acordeón)
        for i, main_cat in enumerate(self.catalog_data.get("categories", [])):
            is_active = (self.active_main_cat_idx == i)
            rect = pygame.Rect(self.app.right_panel_rect.x + 5, y_pos, panel_width - 10, 28)
            self.main_cat_rects.append(rect)

            color = COLOR_BUTTON_ACTIVE if is_active else COLOR_BUTTON
            pygame.draw.rect(screen, color, rect, border_radius=5)
            
            # Flecha indicadora
            arrow = ">" if not is_active else "v"
            arrow_surf = self.font_ui.render(arrow, True, COLOR_TEXT)
            screen.blit(arrow_surf, (rect.x + 10, rect.centery - arrow_surf.get_height() // 2))

            title_surf = self.font_ui.render(main_cat["name"], True, COLOR_TEXT)
            screen.blit(title_surf, (rect.x + 25, rect.centery - title_surf.get_height() // 2))
            y_pos += rect.height + 5

            # 2. Si está activa, dibujar Subcategorías
            if is_active:
                sub_y_pos = y_pos
                for j, sub_cat in enumerate(main_cat["subcategories"]):
                    is_sub_active = (self.active_sub_cat_idx == j)
                    sub_rect = pygame.Rect(self.app.right_panel_rect.x + 15, sub_y_pos, panel_width - 30, 22)
                    self.sub_cat_rects.append(sub_rect)

                    sub_color = COLOR_BUTTON_HOVER if is_sub_active else COLOR_EDITOR_BG
                    pygame.draw.rect(screen, sub_color, sub_rect, border_radius=3)
                    pygame.draw.rect(screen, COLOR_BORDER, sub_rect, 1, border_radius=3)

                    sub_title_surf = self.font_ui.render(sub_cat["name"], True, COLOR_TEXT)
                    screen.blit(sub_title_surf, sub_title_surf.get_rect(center=sub_rect.center))
                    sub_y_pos += sub_rect.height + 4
                
                y_pos = sub_y_pos + 10

                # 3. Si una subcategoría está activa, dibujar los items
                if self.active_sub_cat_idx != -1:
                    items_to_draw = main_cat["subcategories"][self.active_sub_cat_idx]["items"]
                    self.draw_item_grid(screen, items_to_draw, y_pos)

    def draw_item_grid(self, screen, items, start_y):
        margin = 15; icon_size = 50
        panel = self.app.right_panel_rect
        padding = (panel.width - (4 * icon_size) - (2 * margin)) / 3
        x_pos = panel.x + margin
        y_pos = start_y

        mouse_pos = pygame.mouse.get_pos()

        for item in items:
            rect = pygame.Rect(x_pos, y_pos, icon_size, icon_size)
            self.icon_rects.append(rect)
            
            icon_img = self.app.data_manager.get_image(item['icon_path'])
            if icon_img:
                pygame.draw.rect(screen, COLOR_EDITOR_BG, rect, border_radius=5)
                img_s = pygame.transform.scale(icon_img, (icon_size - 8, icon_size - 8))
                screen.blit(img_s, img_s.get_rect(center=rect.center))

            if self.selected_deco_item and self.selected_deco_item['id'] == item['id']:
                pygame.draw.rect(screen, COLOR_HOVER_BORDER, rect, 2, border_radius=5)
            elif rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER, rect, 1, border_radius=5)
            else:
                pygame.draw.rect(screen, COLOR_BORDER, rect, 1, border_radius=5)

            x_pos += icon_size + padding
            if x_pos + icon_size > panel.right:
                x_pos = panel.x + margin
                y_pos += icon_size + 10

    # La lógica para draw_on_editor y get_info_lines no necesita cambios y funciona como antes.
    def draw_on_editor(self, surface):
        for deco in self.app.placed_decorations:
             pos = deco.get("grid_pos"); base_id = deco.get("base_id")
             if pos and base_id:
                 deco_data = self.app.data_manager.load_decoration_data(base_id)
                 if not deco_data: continue
                 asset_key = f"{base_id}_64_a_2_0"
                 if asset_key not in deco_data.get("assets", {}): asset_key = f"{base_id}_icon_a"
                 if asset_key in deco_data.get("assets", {}):
                     asset_info = deco_data["assets"][asset_key]
                     asset_path = f"decorations/{base_id}/{asset_info.get('name', asset_key)}.png"
                     image = self.app.data_manager.get_image(asset_path)
                     if image:
                        offset_x = int(asset_info.get('x', 0)); offset_y = int(asset_info.get('y', 0))
                        sp = grid_to_screen(pos[0], pos[1], self.app.camera_offset)
                        draw_pos = (sp[0] + TILE_WIDTH_HALF + offset_x, sp[1] + TILE_HEIGHT_HALF + offset_y - image.get_height())
                        surface.blit(image, draw_pos)
        if self.ghost_image and self.app.editor_rect.collidepoint(pygame.mouse.get_pos()):
            sp = grid_to_screen(self.ghost_pos[0], self.ghost_pos[1], self.app.camera_offset)
            draw_pos = (sp[0] + (TILE_WIDTH - self.ghost_image.get_width()) // 2, sp[1] - self.ghost_image.get_height() + TILE_HEIGHT)
            temp = self.ghost_image.copy(); temp.set_alpha(150); surface.blit(temp, draw_pos)

    def get_info_lines(self):
        return ["[Click] Place Item", "[Esc] Deselect", "[Del] Delete Item"]