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
        
        # Catalog/Search state
        self.open_main_cat_indices = set()
        self.selected_deco_item = None
        self.clickable_elements = []
        self.catalog_scroll_y = 0
        self.catalog_content_height = 0
        self.scrolling_with_catalog_thumb = False
        self.active_search_term = ""
        self.search_input = None
        self.search_button = None

        # Ghost state for placing items
        self.ghost_pos = (0, 0)
        self.hover_grid_pos = None 
        self.ghost_rotation = 0

        # Room objects list state
        self.clickable_room_objects = []
        self.room_objects_scroll_y = 0
        self.room_objects_content_height = 0
        self.scrolling_with_objects_thumb = False
        self.selected_room_object_uid = None
        self.walkable_group_open = True
        self.non_walkable_group_open = True
        self.scroll_to_y_target = None
        self.needs_to_scroll_to_selection = False

        # UI Rects and Surfaces
        self.panel_rect, self.catalog_panel_rect, self.room_objects_panel_rect = pygame.Rect(0,0,0,0), pygame.Rect(0,0,0,0), pygame.Rect(0,0,0,0)
        self.catalog_content_surface, self.catalog_scrollbar_track_rect, self.catalog_scrollbar_thumb_rect = None, None, None
        self.room_objects_content_surface, self.room_objects_scrollbar_track_rect, self.room_objects_scrollbar_thumb_rect = None, None, None

        # Common scroll state
        self.scroll_start_y, self.scroll_start_scroll_y = 0, 0

    def update_layout(self):
        self.panel_rect = self.app.right_panel_rect
        self.catalog_panel_rect = pygame.Rect(self.panel_rect.x, self.panel_rect.y, self.panel_rect.width, int(self.panel_rect.height * 2 / 3))
        self.room_objects_panel_rect = pygame.Rect(self.panel_rect.x, self.catalog_panel_rect.bottom, self.panel_rect.width, self.panel_rect.height - self.catalog_panel_rect.height)

        margin, input_height, button_padding, scrollbar_width = 10, 28, 5, 15
        button_size = input_height
        self.search_button = Button(self.catalog_panel_rect.x + margin, self.catalog_panel_rect.y + margin, button_size, button_size, "", self.app.font_ui)
        input_x = self.search_button.rect.right + button_padding
        input_width = self.catalog_panel_rect.width - (margin * 2) - button_size - button_padding
        self.search_input = TextInputBox(input_x, self.catalog_panel_rect.y + margin, input_width, input_height, self.app.font_ui, input_type='text')
        self.catalog_content_surface = pygame.Surface((self.catalog_panel_rect.width, 8000), pygame.SRCALPHA)
        self.catalog_scrollbar_track_rect = pygame.Rect(self.catalog_panel_rect.right - scrollbar_width, self.catalog_panel_rect.top, scrollbar_width, self.catalog_panel_rect.height)
        self.update_catalog_scrollbar_thumb()

        self.room_objects_content_surface = pygame.Surface((self.room_objects_panel_rect.width, 4000), pygame.SRCALPHA)
        self.room_objects_scrollbar_track_rect = pygame.Rect(self.room_objects_panel_rect.right - scrollbar_width, self.room_objects_panel_rect.top, scrollbar_width, self.room_objects_panel_rect.height)
        self.update_room_objects_scrollbar_thumb()

    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        if self.search_input.handle_event(event) is not None: self.perform_search(); self.search_input.active = False
        self.search_button.check_hover(mouse_pos)
        if self.search_button.is_clicked(event): self.perform_search(); self.search_input.active = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.catalog_scrollbar_thumb_rect and self.catalog_scrollbar_thumb_rect.collidepoint(mouse_pos): self.scrolling_with_catalog_thumb = True; self.scroll_start_y = mouse_pos[1]; self.scroll_start_scroll_y = self.catalog_scroll_y
                elif self.room_objects_scrollbar_thumb_rect and self.room_objects_scrollbar_thumb_rect.collidepoint(mouse_pos): self.scrolling_with_objects_thumb = True; self.scroll_start_y = mouse_pos[1]; self.scroll_start_scroll_y = self.room_objects_scroll_y
            
            if self.catalog_panel_rect.collidepoint(mouse_pos):
                if event.button == 4: self.catalog_scroll_y -= self.SCROLL_SPEED
                elif event.button == 5: self.catalog_scroll_y += self.SCROLL_SPEED
                self.clamp_catalog_scroll()
            elif self.room_objects_panel_rect.collidepoint(mouse_pos):
                if event.button == 4: self.room_objects_scroll_y -= self.SCROLL_SPEED
                elif event.button == 5: self.room_objects_scroll_y += self.SCROLL_SPEED
                self.clamp_room_objects_scroll()

            if event.button == 1:
                if self.catalog_panel_rect.collidepoint(mouse_pos) and not self.catalog_scrollbar_track_rect.collidepoint(mouse_pos) and not self.search_input.rect.collidepoint(mouse_pos) and not self.search_button.rect.collidepoint(mouse_pos): self.handle_catalog_click(mouse_pos)
                elif self.room_objects_panel_rect.collidepoint(mouse_pos) and not self.room_objects_scrollbar_track_rect.collidepoint(mouse_pos): self.handle_room_objects_click(mouse_pos)
                elif self.app.editor_rect.collidepoint(mouse_pos):
                    # If holding an item from the catalog, the primary action is to place it.
                    if self.selected_deco_item:
                        self.place_decoration(self.ghost_pos)
                    # Otherwise, if not holding an item, the action is to select an existing one.
                    else:
                        self.handle_editor_area_click(local_mouse_pos)
            
            if event.button == 3 and self.app.editor_rect.collidepoint(mouse_pos): self.delete_decoration_at(screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera.offset, self.app.camera.zoom))

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.scrolling_with_catalog_thumb = False; self.scrolling_with_objects_thumb = False
        
        if event.type == pygame.MOUSEMOTION:
            if self.scrolling_with_catalog_thumb:
                delta_y = mouse_pos[1] - self.scroll_start_y; track, thumb = self.catalog_scrollbar_track_rect, self.catalog_scrollbar_thumb_rect
                scrollable_px = track.height - thumb.height; scrollable_content = self.catalog_content_height - (self.catalog_panel_rect.height - self.search_input.rect.bottom)
                if scrollable_px > 0: self.catalog_scroll_y = self.scroll_start_scroll_y + delta_y * (scrollable_content / scrollable_px); self.clamp_catalog_scroll()
            elif self.scrolling_with_objects_thumb:
                delta_y = mouse_pos[1] - self.scroll_start_y; track, thumb = self.room_objects_scrollbar_track_rect, self.room_objects_scrollbar_thumb_rect
                scrollable_px = track.height - thumb.height; scrollable_content = self.room_objects_content_height - (self.room_objects_panel_rect.height - 30)
                if scrollable_px > 0: self.room_objects_scroll_y = self.scroll_start_scroll_y + delta_y * (scrollable_content / scrollable_px); self.clamp_room_objects_scroll()
            
            if self.app.editor_rect.collidepoint(mouse_pos) and not self.app.camera.is_panning:
                self.hover_grid_pos = screen_to_grid(local_mouse_pos[0], local_mouse_pos[1], self.app.camera.offset, self.app.camera.zoom)
                if self.selected_deco_item: self.ghost_pos = self.hover_grid_pos
            else: self.hover_grid_pos = None
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.selected_deco_item = None; self.selected_room_object_uid = None
            elif event.key == pygame.K_r and self.selected_deco_item: self.rotate_ghost_to_next_valid()

    def _ensure_selected_object_group_is_open(self):
        if not self.selected_room_object_uid or not self.app.current_room: return
        selected_deco = next((d for d in self.app.current_room.decorations if id(d) == self.selected_room_object_uid), None)
        if not selected_deco: return

        is_walkable = self.app.current_room.walkable_map.get(tuple(selected_deco.get("grid_pos", ())), 0) == 1
        if is_walkable and not self.walkable_group_open:
            self.walkable_group_open = True
        elif not is_walkable and not self.non_walkable_group_open:
            self.non_walkable_group_open = True

    def handle_editor_area_click(self, local_mouse_pos):
        if not self.app.current_room: return False
        
        sorted_decos = self.app.current_room.get_decorations_sorted_for_render(); sorted_decos.reverse()
        
        for deco in sorted_decos:
            render_details = self.app.renderer.get_decoration_render_details(deco, self.app.camera.offset, self.app.camera.zoom)
            if render_details and render_details[0]:
                image, pos = render_details
                if pygame.Rect(pos, image.get_size()).collidepoint(local_mouse_pos):
                    try:
                        mask = pygame.mask.from_surface(image)
                        if mask.get_at((local_mouse_pos[0] - pos[0], local_mouse_pos[1] - pos[1])):
                            clicked_uid = id(deco)
                            if self.selected_room_object_uid == clicked_uid:
                                self.selected_room_object_uid = None # Deselect if clicked again
                            else:
                                self.selected_room_object_uid = clicked_uid # Select new object
                                self._ensure_selected_object_group_is_open()
                                self.needs_to_scroll_to_selection = True
                            return True
                    except IndexError: continue
        return False

    def rotate_ghost_to_next_valid(self):
        base_id, variant_id = self.selected_deco_item.get("base_id"), self.selected_deco_item.get("variant_id", "0")
        for i in range(1, 5):
            next_rotation_idx = (self.ghost_rotation + i) % 4
            if self.app.renderer.get_rendered_image_and_offset(base_id, variant_id, next_rotation_idx)[0]: self.ghost_rotation = next_rotation_idx; return
    
    def delete_decoration_at(self, grid_pos):
        if self.app.current_room: self.app.current_room.remove_decoration_at(grid_pos)

    def place_decoration(self, grid_pos):
        if self.selected_deco_item and self.app.current_room: self.app.current_room.add_decoration(self.selected_deco_item['base_id'], self.selected_deco_item['variant_id'], grid_pos, self.ghost_rotation)
        
    def perform_search(self): self.active_search_term = self.search_input.text.lower().strip(); self.catalog_scroll_y = 0

    def clamp_catalog_scroll(self):
        content_visible_h = self.catalog_panel_rect.height - (self.search_input.rect.height if self.search_input else 0) - 20
        self.catalog_scroll_y = max(0, min(self.catalog_scroll_y, max(0, self.catalog_content_height - content_visible_h)))

    def clamp_room_objects_scroll(self):
        content_visible_h = self.room_objects_panel_rect.height - 30 
        self.room_objects_scroll_y = max(0, min(self.room_objects_scroll_y, max(0, self.room_objects_content_height - content_visible_h)))

    def handle_catalog_click(self, mouse_pos):
        local_x, local_y = mouse_pos[0] - self.catalog_panel_rect.x, mouse_pos[1] - (self.search_input.rect.bottom + 10) + self.catalog_scroll_y
        for element in self.clickable_elements:
            if element['rect'].collidepoint(local_x, local_y):
                elem_type, elem_id = element['type'], element['id']
                if elem_type == 'main_cat':
                    if elem_id in self.open_main_cat_indices: self.open_main_cat_indices.remove(elem_id)
                    else: self.open_main_cat_indices.add(elem_id)
                elif elem_type == 'item': self.selected_deco_item = elem_id; self.ghost_rotation = 0
                return

    def handle_room_objects_click(self, mouse_pos):
        local_x, local_y = mouse_pos[0] - self.room_objects_panel_rect.x, mouse_pos[1] - (self.room_objects_panel_rect.y + 30) + self.room_objects_scroll_y
        for element in self.clickable_room_objects:
            if element['rect'].collidepoint(local_x, local_y):
                if element['type'] == 'item':
                    clicked_uid = element['uid']
                    if self.selected_room_object_uid == clicked_uid:
                        self.selected_room_object_uid = None # Deselect
                    else:
                        self.selected_room_object_uid = clicked_uid # Select
                        self.needs_to_scroll_to_selection = True
                elif element['type'] == 'header':
                    if element['group'] == 'walkable': self.walkable_group_open = not self.walkable_group_open
                    else: self.non_walkable_group_open = not self.non_walkable_group_open
                return

    def get_selected_item_image(self):
        if not self.selected_deco_item: return None, None
        return self.app.renderer.get_rendered_image_and_offset(self.selected_deco_item.get("base_id"), self.selected_deco_item.get("variant_id"), self.ghost_rotation)

    def draw_on_editor(self, surface):
        if self.hover_grid_pos:
            p = self.app.renderer._get_tile_points(grid_to_screen(*self.hover_grid_pos, self.app.camera.offset, self.app.camera.zoom), self.app.camera.zoom)
            pygame.draw.polygon(surface, COLOR_HOVER_BORDER, [p['top'], p['right'], p['bottom'], p['left']], 3)

        if self.selected_room_object_uid and self.app.current_room:
            selected_deco = next((d for d in self.app.current_room.decorations if id(d) == self.selected_room_object_uid), None)
            if selected_deco:
                if pos := selected_deco.get("grid_pos"):
                    p = self.app.renderer._get_tile_points(grid_to_screen(*pos, self.app.camera.offset, self.app.camera.zoom), self.app.camera.zoom)
                    pygame.draw.polygon(surface, COLOR_ANCHOR, [p['top'], p['right'], p['bottom'], p['left']], 2)
                
                render_details = self.app.renderer.get_decoration_render_details(selected_deco, self.app.camera.offset, self.app.camera.zoom)
                if render_details and render_details[0]:
                    self.draw_sprite_outline(surface, render_details[0], render_details[1], COLOR_ANCHOR, 2)

        if self.selected_deco_item and self.app.current_room and self.hover_grid_pos:
            ghost_data = {"base_id": self.selected_deco_item.get("base_id"), "variant_id": self.selected_deco_item.get("variant_id", "0"), "grid_pos": self.ghost_pos, "rotation": self.ghost_rotation}
            is_occupied = tuple(self.ghost_pos) in self.app.current_room.occupied_tiles
            self.app.renderer._draw_decoration(surface, ghost_data, self.app.camera.offset, self.app.camera.zoom, is_ghost=True, is_occupied=is_occupied)

    def draw_sprite_outline(self, surface, image, pos, color, thickness):
        mask = pygame.mask.from_surface(image)
        outline_points = mask.outline()
        if len(outline_points) > 1:
            offset_points = [(p[0] + pos[0], p[1] + pos[1]) for p in outline_points]
            pygame.draw.lines(surface, color, True, offset_points, thickness)

    def get_info_lines(self):
        lines = ["[R Click] Delete", "[R] Rotate Ghost", "[Esc] Deselect All"]
        if self.selected_deco_item:
            lines.insert(0, "[L Click] Place Item")
        else:
            lines.insert(0, "[L Click] Select Item")
        return lines

    def draw_ui_on_panel(self, screen):
        pygame.draw.rect(screen, COLOR_PANEL_BG, self.panel_rect)
        self.draw_catalog_section(screen); self.draw_room_objects_section(screen)
        pygame.draw.rect(screen, COLOR_BORDER, self.panel_rect, 1)

    def draw_catalog_section(self, screen):
        self.draw_catalog_content()
        content_y_start = self.search_input.rect.bottom + 10
        draw_area = pygame.Rect(self.catalog_panel_rect.x, content_y_start, self.catalog_panel_rect.width, self.catalog_panel_rect.height - (content_y_start - self.catalog_panel_rect.top))
        screen.blit(self.catalog_content_surface, draw_area, pygame.Rect(0, self.catalog_scroll_y, draw_area.width, draw_area.height))
        bg_rect = self.search_button.rect.union(self.search_input.rect).inflate(20, 20)
        pygame.draw.rect(screen, COLOR_PANEL_BG, bg_rect)
        self.search_button.draw(screen); self.draw_search_icon(screen, self.search_button.rect)
        self.search_input.update(); self.search_input.draw(screen)
        if not self.search_input.text and not self.search_input.active: screen.blit(self.app.font_ui.render("Search items...", True, COLOR_INFO_TEXT), (self.search_input.rect.x + 8, self.search_input.rect.y + 6))
        self.draw_catalog_scrollbar(screen)

    def draw_room_objects_section(self, screen):
        pygame.draw.line(screen, COLOR_BORDER, self.room_objects_panel_rect.topleft, self.room_objects_panel_rect.topright, 1)
        title_surf = self.app.font_title.render("Room Objects", True, COLOR_TITLE_TEXT); screen.blit(title_surf, (self.room_objects_panel_rect.x + 10, self.room_objects_panel_rect.y + 5))
        
        self.draw_room_objects_list_content()
        
        if self.needs_to_scroll_to_selection and self.scroll_to_y_target is not None:
            view_h = self.room_objects_panel_rect.height - 30
            self.room_objects_scroll_y = self.scroll_to_y_target - (view_h / 2)
            self.clamp_room_objects_scroll()
            self.needs_to_scroll_to_selection = False

        content_y_start = self.room_objects_panel_rect.y + 30
        draw_area = pygame.Rect(self.room_objects_panel_rect.x, content_y_start, self.room_objects_panel_rect.width, self.room_objects_panel_rect.height - 30)
        screen.blit(self.room_objects_content_surface, draw_area, pygame.Rect(0, self.room_objects_scroll_y, draw_area.width, draw_area.height))
        self.draw_room_objects_scrollbar(screen)

    def draw_search_icon(self, screen, rect):
        center, r = rect.center, min(rect.width, rect.height)//4; pygame.draw.circle(screen, COLOR_TEXT, center, r, 2)
        a = math.radians(135); p1 = (center[0]+r*math.cos(a), center[1]-r*math.sin(a)); p2 = (center[0]+r*2*math.cos(a), center[1]-r*2*math.sin(a)); pygame.draw.line(screen, COLOR_TEXT, p1, p2, 3)

    def draw_catalog_content(self):
        self.catalog_content_surface.fill((0,0,0,0)); self.clickable_elements.clear()
        self.catalog_content_height = self.draw_search_results_view() if self.active_search_term else self.draw_catalog_view()

    def draw_room_objects_list_content(self):
        self.room_objects_content_surface.fill((0,0,0,0)); self.clickable_room_objects.clear()
        self.scroll_to_y_target = None
        if not self.app.current_room: self.room_objects_content_height = 0; return

        sorted_decos = self.app.current_room.get_decorations_sorted_for_render(); sorted_decos.reverse()
        walkable_decos, non_walkable_decos = [], []
        for deco in sorted_decos:
            if self.app.current_room.walkable_map.get(tuple(deco.get("grid_pos", ())), 0) == 1: walkable_decos.append(deco)
            else: non_walkable_decos.append(deco)

        margin, y_pos, line_h, header_h = 10, 5, 22, 25
        has_sb = self.room_objects_content_height > self.room_objects_panel_rect.height
        content_w = self.room_objects_panel_rect.width - margin*2 - (self.room_objects_scrollbar_track_rect.width if has_sb else 0)

        def draw_group(title, decos, is_open):
            nonlocal y_pos
            header_rect = pygame.Rect(margin, y_pos, content_w, header_h)
            pygame.draw.rect(self.room_objects_content_surface, COLOR_BUTTON, header_rect, border_radius=3)
            self.clickable_room_objects.append({'rect': header_rect, 'type': 'header', 'group': title.split(' ')[0].lower()})
            arrow = "v" if is_open else ">"; text_surf = self.font_ui.render(f"{arrow} {title} ({len(decos)})", True, COLOR_TEXT)
            self.room_objects_content_surface.blit(text_surf, (header_rect.x+5, header_rect.centery - text_surf.get_height()//2)); y_pos += header_h + 2
            if is_open:
                for deco in decos:
                    item_name = "Unknown"; data = self.app.data_manager.get_furni_data(deco.get("base_id"))
                    if data: item_name = data.get("name", deco.get("base_id"))
                    rect = pygame.Rect(margin + 10, y_pos, content_w - 10, line_h)
                    if self.selected_room_object_uid == id(deco):
                        pygame.draw.rect(self.room_objects_content_surface, COLOR_BUTTON_ACTIVE, rect, border_radius=3)
                        self.scroll_to_y_target = rect.centery
                    self.clickable_room_objects.append({'rect': rect, 'type': 'item', 'uid': id(deco)})
                    text_surf = self.font_desc.render(item_name, True, COLOR_TEXT); self.room_objects_content_surface.blit(text_surf, (rect.x+5, rect.centery-text_surf.get_height()//2)); y_pos += line_h

        draw_group("Walkable Area", walkable_decos, self.walkable_group_open)
        y_pos += 5
        draw_group("Non-Walkable Area", non_walkable_decos, self.non_walkable_group_open)
        self.room_objects_content_height = y_pos

    def draw_search_results_view(self):
        results = []; processed = set()
        for cat in self.catalog_data.get("categories", []):
            for item in cat.get("items", []):
                if self.active_search_term in item['name'].lower() and item['id'] not in processed: results.append(item); processed.add(item['id'])
        margin = 10; has_sb = self.catalog_content_height > self.catalog_panel_rect.height
        content_w = self.catalog_panel_rect.width - margin*2 - (self.catalog_scrollbar_track_rect.width if has_sb else 0)
        if not results:
            msg = self.font_ui.render(f"No results for '{self.active_search_term}'", True, COLOR_INFO_TEXT)
            self.catalog_content_surface.blit(msg, msg.get_rect(centerx=self.catalog_panel_rect.width/2, y=20)); return 60
        return self.draw_item_grid(results, margin, 10, content_w)

    def draw_catalog_view(self):
        y, m = 0, 10; has_sb = self.catalog_content_height > self.catalog_panel_rect.height
        content_w = self.catalog_panel_rect.width - m*2 - (self.catalog_scrollbar_track_rect.width if has_sb else 0)
        for i, cat in enumerate(self.catalog_data.get("categories", [])):
            is_open = i in self.open_main_cat_indices; rect = pygame.Rect(m, y, content_w, 28)
            pygame.draw.rect(self.catalog_content_surface, COLOR_BUTTON_ACTIVE if is_open else COLOR_BUTTON, rect, border_radius=5)
            self.clickable_elements.append({'rect': rect, 'type': 'main_cat', 'id': i})
            title = self.font_ui.render(f"{'v ' if is_open else '> '}{cat['name']}", True, COLOR_TEXT)
            self.catalog_content_surface.blit(title, (rect.x+10, rect.centery-title.get_height()//2)); y += rect.height + 5
            if is_open and cat["items"]: y += self.draw_item_grid(cat["items"], m+15, y, content_w-15)
        return y

    def draw_item_grid(self, items, start_x, start_y, width):
        icon_size, padding, text_h = 60, 10, 30
        cols = max(1, (width + padding) // (icon_size + padding))
        for k, item in enumerate(items):
            item_rect = pygame.Rect(start_x + (k % cols) * (icon_size + padding), start_y + (k // cols) * (icon_size + text_h + padding), icon_size, icon_size)
            self.clickable_elements.append({'rect': pygame.Rect(item_rect.x, item_rect.y, icon_size, icon_size + text_h), 'type': 'item', 'id': item})
            if img := self.app.data_manager.get_image(item['base_id'], item['icon_path']):
                pygame.draw.rect(self.catalog_content_surface, COLOR_EDITOR_BG, item_rect, border_radius=5)
                max_s = icon_size - 8; w,h = img.get_size(); final_img = img
                if w > max_s or h > max_s: final_img = pygame.transform.smoothscale(img, (int(w*min(max_s/w,max_s/h)), int(h*min(max_s/w,max_s/h))))
                self.catalog_content_surface.blit(final_img, final_img.get_rect(center=item_rect.center))
            is_sel = self.selected_deco_item and self.selected_deco_item['id'] == item['id']
            pygame.draw.rect(self.catalog_content_surface, COLOR_HOVER_BORDER if is_sel else COLOR_BORDER, item_rect, 2 if is_sel else 1, border_radius=5)
            name_y = item_rect.bottom+4; words = item['name'].split(' '); line = ""
            for word in words:
                if self.font_desc.size(line+word+" ")[0] <= icon_size: line += word + " "
                else: surf = self.font_desc.render(line.strip(), True, COLOR_TEXT); self.catalog_content_surface.blit(surf, surf.get_rect(centerx=item_rect.centerx, top=name_y)); name_y += self.font_desc.get_linesize(); line = word + " "
            if line: surf = self.font_desc.render(line.strip(), True, COLOR_TEXT); self.catalog_content_surface.blit(surf, surf.get_rect(centerx=item_rect.centerx, top=name_y))
        return (-(-len(items)//cols) if items else 0) * (icon_size + text_h + padding) + 10

    def update_catalog_scrollbar_thumb(self):
        if not self.search_input: return
        vis_h = self.catalog_panel_rect.height - self.search_input.rect.height - 20
        if self.catalog_content_height > vis_h:
            thumb_h = max(20, vis_h * (vis_h / self.catalog_content_height)); ratio = self.catalog_scroll_y / max(1, self.catalog_content_height-vis_h)
            thumb_y = self.catalog_scrollbar_track_rect.y + ratio * (self.catalog_scrollbar_track_rect.height-thumb_h)
            self.catalog_scrollbar_thumb_rect = pygame.Rect(self.catalog_scrollbar_track_rect.x, thumb_y, self.catalog_scrollbar_track_rect.width, thumb_h)
        else: self.catalog_scrollbar_thumb_rect = None

    def draw_catalog_scrollbar(self, screen):
        self.update_catalog_scrollbar_thumb()
        if self.catalog_scrollbar_thumb_rect:
            pygame.draw.rect(screen, COLOR_SCROLLBAR_BG, self.catalog_scrollbar_track_rect)
            color = COLOR_SCROLLBAR_THUMB_HOVER if self.catalog_scrollbar_thumb_rect.collidepoint(pygame.mouse.get_pos()) or self.scrolling_with_catalog_thumb else COLOR_SCROLLBAR_THUMB
            pygame.draw.rect(screen, color, self.catalog_scrollbar_thumb_rect, border_radius=4)
            
    def update_room_objects_scrollbar_thumb(self):
        vis_h = self.room_objects_panel_rect.height - 30
        if self.room_objects_content_height > vis_h:
            thumb_h = max(20, vis_h * (vis_h/self.room_objects_content_height)); ratio = self.room_objects_scroll_y / max(1, self.room_objects_content_height-vis_h)
            thumb_y = self.room_objects_scrollbar_track_rect.y + ratio * (self.room_objects_scrollbar_track_rect.height-thumb_h)
            self.room_objects_scrollbar_thumb_rect = pygame.Rect(self.room_objects_scrollbar_track_rect.x, thumb_y, self.room_objects_scrollbar_track_rect.width, thumb_h)
        else: self.room_objects_scrollbar_thumb_rect = None
            
    def draw_room_objects_scrollbar(self, screen):
        self.update_room_objects_scrollbar_thumb()
        if self.room_objects_scrollbar_thumb_rect:
            pygame.draw.rect(screen, COLOR_SCROLLBAR_BG, self.room_objects_scrollbar_track_rect)
            color = COLOR_SCROLLBAR_THUMB_HOVER if self.room_objects_scrollbar_thumb_rect.collidepoint(pygame.mouse.get_pos()) or self.scrolling_with_objects_thumb else COLOR_SCROLLBAR_THUMB
            pygame.draw.rect(screen, color, self.room_objects_scrollbar_thumb_rect, border_radius=4)