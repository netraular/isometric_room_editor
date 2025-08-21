# src/decoration_editor.py

import pygame
from common.constants import *
from common.ui import Button
from common.utils import grid_to_screen, screen_to_grid

class DecorationEditor:
    # --- CONSTANTES DE UI PARA EL EDITOR ---
    NAV_PANE_RATIO = 0.45  # El panel de navegación ocupa el 45% del panel derecho
    SCROLL_SPEED = 25
    
    def __init__(self, app_ref):
        self.app = app_ref
        self.font_ui = self.app.font_ui
        self.font_title = self.app.font_title
        self.font_desc = pygame.font.SysFont("Arial", 12)

        # --- DATOS ---
        self.catalog_data = self.app.data_manager.load_catalog()
        self.catalog_items = [] # Items de la subcategoría activa

        # --- ESTADO DE LA UI ---
        self.active_main_cat_idx = -1
        self.active_sub_cat_idx = -1
        self.selected_deco_item = None
        
        # --- ESTADO DE SCROLL ---
        self.nav_scroll_y = 0
        self.nav_content_height = 0
        self.item_scroll_y = 0
        self.item_content_height = 0

        # --- ESTADO DEL EDITOR ---
        self.ghost_image = None
        self.ghost_pos = (0, 0)
        
        # --- RECTS Y SURFACES (se inicializan en update_layout) ---
        self.nav_pane_rect = pygame.Rect(0, 0, 0, 0)
        self.item_pane_rect = pygame.Rect(0, 0, 0, 0)
        self.nav_surface = None
        self.item_surface = None

    def update_layout(self):
        """ Se llama desde App cuando la ventana cambia de tamaño. """
        panel = self.app.right_panel_rect
        nav_width = int(panel.width * self.NAV_PANE_RATIO)
        item_width = panel.width - nav_width

        self.item_pane_rect = pygame.Rect(panel.left, panel.top, item_width, panel.height)
        self.nav_pane_rect = pygame.Rect(self.item_pane_rect.right, panel.top, nav_width, panel.height)
        
        # Las superficies virtuales necesitan ser muy altas para contener todo el scroll
        self.nav_surface = pygame.Surface((self.nav_pane_rect.width, 2000), pygame.SRCALPHA)
        self.item_surface = pygame.Surface((self.item_pane_rect.width, 4000), pygame.SRCALPHA)


    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        # --- MANEJO DE SCROLL CON LA RUEDA DEL RATÓN ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.nav_pane_rect.collidepoint(mouse_pos):
                if event.button == 4: # Scroll Arriba
                    self.nav_scroll_y = max(0, self.nav_scroll_y - self.SCROLL_SPEED)
                elif event.button == 5: # Scroll Abajo
                    max_scroll = self.nav_content_height - self.nav_pane_rect.height
                    if max_scroll > 0:
                        self.nav_scroll_y = min(max_scroll, self.nav_scroll_y + self.SCROLL_SPEED)
            elif self.item_pane_rect.collidepoint(mouse_pos):
                if event.button == 4:
                    self.item_scroll_y = max(0, self.item_scroll_y - self.SCROLL_SPEED)
                elif event.button == 5:
                    max_scroll = self.item_content_height - self.item_pane_rect.height
                    if max_scroll > 0:
                        self.item_scroll_y = min(max_scroll, self.item_scroll_y + self.SCROLL_SPEED)

        # --- MANEJO DE CLICS ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.nav_pane_rect.collidepoint(mouse_pos):
                self.handle_nav_click(mouse_pos)
            elif self.item_pane_rect.collidepoint(mouse_pos):
                self.handle_item_click(mouse_pos)
            elif self.selected_deco_item and self.app.editor_rect.collidepoint(mouse_pos):
                # Solo colocar si el clic fue en el editor
                self.place_decoration(self.ghost_pos)

        # --- LÓGICA DE GHOST Y DESELECCIÓN ---
        if self.selected_deco_item and self.app.editor_rect.collidepoint(mouse_pos):
            self.ghost_pos = screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera_offset)
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.selected_deco_item = None
            self.ghost_image = None
            
    def handle_nav_click(self, mouse_pos):
        # Coordenadas relativas al panel de navegación, incluyendo el scroll
        click_y = mouse_pos[1] - self.nav_pane_rect.top + self.nav_scroll_y
        y_pos = 10
        
        for i, main_cat in enumerate(self.catalog_data.get("categories", [])):
            rect = pygame.Rect(5, y_pos, self.nav_pane_rect.width - 10, 28)
            if rect.collidepoint(mouse_pos[0] - self.nav_pane_rect.left, click_y):
                self.active_main_cat_idx = i if self.active_main_cat_idx != i else -1
                self.active_sub_cat_idx = -1
                self.catalog_items = []
                self.item_scroll_y = 0
                return
            y_pos += rect.height + 5

            if self.active_main_cat_idx == i:
                for j, sub_cat in enumerate(main_cat["subcategories"]):
                    sub_rect = pygame.Rect(15, y_pos, self.nav_pane_rect.width - 25, 22)
                    if sub_rect.collidepoint(mouse_pos[0] - self.nav_pane_rect.left, click_y):
                        self.active_sub_cat_idx = j
                        self.catalog_items = sub_cat["items"]
                        self.selected_deco_item = None
                        self.ghost_image = None
                        self.item_scroll_y = 0
                        return
                    y_pos += sub_rect.height + 4
                y_pos += 10

    def handle_item_click(self, mouse_pos):
        click_y = mouse_pos[1] - self.item_pane_rect.top + self.item_scroll_y
        
        # Reconstruimos la geometría del grid para ver dónde se hizo clic
        margin = 15; icon_size = 60; padding = 15
        cols = max(1, (self.item_pane_rect.width - margin*2 + padding) // (icon_size + padding))
        
        y_pos = 10; x_pos = margin

        for i, item in enumerate(self.catalog_items):
            item_rect = pygame.Rect(x_pos, y_pos, icon_size, icon_size + 20) # +20 para el texto
            
            if item_rect.collidepoint(mouse_pos[0] - self.item_pane_rect.left, click_y):
                self.selected_deco_item = item
                self.ghost_image = self.app.data_manager.get_image(item['icon_path'])
                return
            
            x_pos += icon_size + padding
            if (i + 1) % cols == 0:
                x_pos = margin
                y_pos += item_rect.height + padding

    def draw_ui_on_panel(self, screen):
        # Este método es llamado solo cuando el modo de decoración está activo.
        if not self.nav_surface or not self.item_surface: # Salvaguarda por si el layout no se ha creado
            return

        # Dibujar los dos paneles y sus bordes
        pygame.draw.rect(screen, COLOR_PANEL_BG, self.item_pane_rect)
        pygame.draw.rect(screen, (30, 40, 50), self.nav_pane_rect) # Navegación un poco más oscura
        pygame.draw.rect(screen, COLOR_BORDER, self.item_pane_rect, 1)
        pygame.draw.rect(screen, COLOR_BORDER, self.nav_pane_rect, 1)

        # Renderizar contenido en las superficies virtuales
        self.draw_nav_content()
        self.draw_item_content()

        # Blit de las porciones visibles de las superficies en la pantalla
        screen.blit(self.nav_surface, self.nav_pane_rect, (0, self.nav_scroll_y, self.nav_pane_rect.width, self.nav_pane_rect.height))
        screen.blit(self.item_surface, self.item_pane_rect, (0, self.item_scroll_y, self.item_pane_rect.width, self.item_pane_rect.height))

    def draw_nav_content(self):
        self.nav_surface.fill((0,0,0,0)) # Transparente
        y_pos = 10
        width = self.nav_pane_rect.width

        for i, main_cat in enumerate(self.catalog_data.get("categories", [])):
            is_active = (self.active_main_cat_idx == i)
            rect = pygame.Rect(5, y_pos, width - 10, 28)
            color = COLOR_BUTTON_ACTIVE if is_active else COLOR_BUTTON
            pygame.draw.rect(self.nav_surface, color, rect, border_radius=5)
            
            arrow = "v" if is_active else ">"
            arrow_surf = self.font_ui.render(arrow, True, COLOR_TEXT)
            self.nav_surface.blit(arrow_surf, (rect.x + 10, rect.centery - arrow_surf.get_height() // 2))

            title_surf = self.font_ui.render(main_cat["name"], True, COLOR_TEXT)
            self.nav_surface.blit(title_surf, (rect.x + 25, rect.centery - title_surf.get_height() // 2))
            y_pos += rect.height + 5

            if is_active:
                for j, sub_cat in enumerate(main_cat["subcategories"]):
                    is_sub_active = (self.active_sub_cat_idx == j)
                    sub_rect = pygame.Rect(15, y_pos, width - 25, 22)
                    sub_color = COLOR_BUTTON_HOVER if is_sub_active else (45, 55, 65)
                    pygame.draw.rect(self.nav_surface, sub_color, sub_rect, border_radius=3)
                    pygame.draw.rect(self.nav_surface, COLOR_BORDER, sub_rect, 1, border_radius=3)
                    sub_title_surf = self.font_ui.render(sub_cat["name"], True, COLOR_TEXT)
                    self.nav_surface.blit(sub_title_surf, sub_title_surf.get_rect(center=sub_rect.center))
                    y_pos += sub_rect.height + 4
                y_pos += 10
        self.nav_content_height = y_pos

    def draw_item_content(self):
        self.item_surface.fill((0,0,0,0)) # Transparente
        
        if not self.catalog_items:
            y_pos_text = 15
            if self.active_main_cat_idx != -1:
                main_cat = self.catalog_data["categories"][self.active_main_cat_idx]
                
                title_surf = self.font_title.render(main_cat["name"], True, COLOR_TITLE_TEXT)
                self.item_surface.blit(title_surf, (15, y_pos_text))
                y_pos_text += title_surf.get_height() + 10
                
                desc_text = main_cat.get("description", "No description available.")
                words = desc_text.split(' ')
                line = ""
                for word in words:
                    test_line = line + word + " "
                    if self.font_desc.size(test_line)[0] < self.item_pane_rect.width - 30:
                        line = test_line
                    else:
                        line_surf = self.font_desc.render(line, True, COLOR_INFO_TEXT)
                        self.item_surface.blit(line_surf, (15, y_pos_text))
                        y_pos_text += self.font_desc.get_linesize()
                        line = word + " "
                line_surf = self.font_desc.render(line, True, COLOR_INFO_TEXT)
                self.item_surface.blit(line_surf, (15, y_pos_text))
            else:
                msg_surf = self.font_title.render("Select a category", True, COLOR_INFO_TEXT)
                r = msg_surf.get_rect(centerx=self.item_pane_rect.width/2, y=20)
                self.item_surface.blit(msg_surf, r)
            self.item_content_height = 0
            return

        margin = 15; icon_size = 60; padding = 15
        cols = max(1, (self.item_pane_rect.width - margin*2 + padding) // (icon_size + padding))
        y_pos = 10; x_pos = margin

        for i, item in enumerate(self.catalog_items):
            item_rect = pygame.Rect(x_pos, y_pos, icon_size, icon_size)
            
            icon_img = self.app.data_manager.get_image(item['icon_path'])
            if icon_img:
                pygame.draw.rect(self.item_surface, COLOR_EDITOR_BG, item_rect, border_radius=5)
                img_s = pygame.transform.scale(icon_img, (icon_size - 8, icon_size - 8))
                self.item_surface.blit(img_s, img_s.get_rect(center=item_rect.center))

            if self.selected_deco_item and self.selected_deco_item['id'] == item['id']:
                pygame.draw.rect(self.item_surface, COLOR_HOVER_BORDER, item_rect, 2, border_radius=5)
            else:
                pygame.draw.rect(self.item_surface, COLOR_BORDER, item_rect, 1, border_radius=5)
            
            # --- INICIO DE LA CORRECCIÓN ---
            # Implementación manual de word wrap para el nombre del item.
            item_name_y = item_rect.bottom + 4
            words = item['name'].split(' ')
            line = ""
            for word in words:
                test_line = line + word + " "
                # Comprueba si la línea es más ancha que el icono
                if self.font_desc.size(test_line)[0] <= icon_size:
                    line = test_line
                else:
                    # La línea está llena, la renderiza y empieza una nueva
                    name_surf = self.font_desc.render(line.strip(), True, COLOR_TEXT)
                    name_rect = name_surf.get_rect(centerx=item_rect.centerx, top=item_name_y)
                    self.item_surface.blit(name_surf, name_rect)
                    item_name_y += self.font_desc.get_linesize()
                    line = word + " "
            
            # Renderiza la última línea que queda
            if line:
                name_surf = self.font_desc.render(line.strip(), True, COLOR_TEXT)
                name_rect = name_surf.get_rect(centerx=item_rect.centerx, top=item_name_y)
                self.item_surface.blit(name_surf, name_rect)
            # --- FIN DE LA CORRECCIÓN ---

            x_pos += icon_size + padding
            if (i + 1) % cols == 0:
                x_pos = margin
                y_pos += icon_size + 20 + padding # +20 para texto, +padding
        
        self.item_content_height = y_pos + icon_size + 20

    def place_decoration(self, grid_pos):
        if not self.selected_deco_item: return
        self.app.placed_decorations.append({
            "base_id": self.selected_deco_item['base_id'],
            "color_id": self.selected_deco_item['color_id'],
            "grid_pos": list(grid_pos), "rotation": 0
        })

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
                     # --- LÍNEA CORREGIDA: Se usa 'furnis' en lugar de 'decorations' ---
                     asset_path = f"furnis/{base_id}/{asset_info.get('name', asset_key)}.png"
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
        return ["[Click] Place Item", "[Esc] Deselect", "[Mouse Wheel] Scroll"]