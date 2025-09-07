# src/app.py

import pygame
import json
import sys
import os
import re 
from common.constants import *
from common.ui import Button, TextInputBox, ToggleSwitch
from common.utils import grid_to_screen # Needed for anchor

# Only import modules that do NOT depend on App
# We keep these at the top because they are independent utilities or base classes.
from camera import Camera
from renderer import RoomRenderer
from room import Room


class App:
    def __init__(self, project_root, assets_root):
        pygame.init()
        self.project_root = project_root
        self.assets_root = assets_root # Store the assets path
        self.win_width, self.win_height = INITIAL_WIN_WIDTH, INITIAL_WIN_HEIGHT
        self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
        pygame.display.set_caption("Isometric Room Editor")
        self.clock = pygame.time.Clock()
        self.font_ui = pygame.font.SysFont("Arial", 14); self.font_title = pygame.font.SysFont("Arial", 18, bold=True); self.font_info = pygame.font.SysFont("Consolas", 12)
        
        # KEY CHANGE TO FIX IMPORT ERROR
        # Import all classes that are instantiated here, inside the __init__ method.
        # This breaks any potential circular dependencies by ensuring the 'app' module
        # is fully loaded before these other modules are touched.
        from data_manager import DataManager
        from structure_editor import StructureEditor
        from decoration_editor import DecorationEditor

        self.data_manager = DataManager(self.project_root, self.assets_root)
        self.camera = Camera()
        self.renderer = RoomRenderer(self.data_manager)
        self.current_room = None
        self.save_confirmation_timer = 0
        
        self.main_mode = EDITOR_MODE_STRUCTURE
        self.structure_editor = StructureEditor(self)
        self.decoration_editor = DecorationEditor(self)
        self.active_editor = self.structure_editor
        
        self.update_layout()
        self.load_initial_room()

    def update_layout(self):
        margin = 15; btn_y = 5; btn_height = 30
        right_panel_width = self.win_width // 3 
        self.top_bar_rect = pygame.Rect(0, 0, self.win_width, TOP_BAR_HEIGHT)
        self.right_panel_rect = pygame.Rect(self.win_width - right_panel_width, TOP_BAR_HEIGHT, right_panel_width, self.win_height - TOP_BAR_HEIGHT)
        self.editor_rect = pygame.Rect(0, TOP_BAR_HEIGHT, self.win_width - right_panel_width, self.win_height - TOP_BAR_HEIGHT)
        self.editor_surface = pygame.Surface(self.editor_rect.size, pygame.SRCALPHA)
        
        self.camera.editor_rect = self.editor_rect
        
        self.main_buttons = { "structure": Button(margin, btn_y, 140, btn_height, "Structure Editor", self.font_ui), "decorations": Button(margin + 150, btn_y, 140, btn_height, "Decorations Editor", self.font_ui) }
        
        btn_file_h = 25; btn_file_y = (TOP_BAR_HEIGHT - btn_file_h) // 2
        btn_save_all = Button(self.win_width - margin - 90, btn_file_y, 90, btn_file_h, "Save All...", self.font_ui)
        btn_load = Button(btn_save_all.rect.left - 10 - 60, btn_file_y, 60, btn_file_h, "Load", self.font_ui)
        btn_new = Button(btn_load.rect.left - 10 - 60, btn_file_y, 60, btn_file_h, "New", self.font_ui)
        btn_screenshot = Button(btn_new.rect.left - 10 - 90, btn_file_y, 90, btn_file_h, "Screenshot", self.font_ui)
        self.file_buttons = {"screenshot": btn_screenshot, "new": btn_new, "load": btn_load, "save_all": btn_save_all}

        self.preview_rect = pygame.Rect(0, 0, PREVIEW_SIZE[0], PREVIEW_SIZE[1]); self.preview_rect.topright = (self.editor_rect.right - margin, self.editor_rect.top + margin); self.preview_surface = pygame.Surface(PREVIEW_SIZE)
        self.item_preview_rect = pygame.Rect(0, 0, 180, 180); self.item_preview_rect.topright = (self.preview_rect.right, self.preview_rect.bottom + 40); self.item_preview_surface = pygame.Surface((180,180), pygame.SRCALPHA)

        input_y = self.right_panel_rect.y + margin + 20
        self.anchor_offset_input_x = TextInputBox(self.right_panel_rect.left + margin, input_y, 100, 25, self.font_ui, input_type='numeric')
        self.anchor_offset_input_y = TextInputBox(self.right_panel_rect.right - 100 - margin, input_y, 100, 25, self.font_ui, input_type='numeric')
        self.input_boxes = [self.anchor_offset_input_x, self.anchor_offset_input_y]
        
        if hasattr(self, 'structure_editor'): self.structure_editor.setup_ui()
        if hasattr(self, 'decoration_editor'): self.decoration_editor.update_layout()

    def load_initial_room(self):
        s_path = os.path.join(self.project_root, "rooms", "structures", "new_room_01.json")
        d_path = os.path.join(self.project_root, "rooms", "decoration_sets", "new_room_01_decoration_set.json")
        if os.path.exists(s_path) and os.path.exists(d_path):
            with open(s_path, 'r') as f: s_data = json.load(f)
            with open(d_path, 'r') as f: d_data = json.load(f)
            self.data_manager.current_structure_path = s_path
            self.data_manager.current_decoration_set_path = d_path
            self.set_new_room_data(s_data, d_data)
        else: self.create_new_room()

    def set_new_room_data(self, structure_data, decoration_set_data):
        self.current_room = Room(structure_data, decoration_set_data)
        self.center_camera_on_room()
        self.update_anchor_offset_inputs()
        set_name = decoration_set_data.get("decoration_set_name", "Untitled Decoration Set")
        pygame.display.set_caption(f"Editor - {set_name}")

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()
        local_mouse_pos = (mouse_pos[0] - self.editor_rect.x, mouse_pos[1] - self.editor_rect.y)
        
        for btn in list(self.main_buttons.values()) + list(self.file_buttons.values()): btn.check_hover(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.VIDEORESIZE: self.win_width, self.win_height = event.size; self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE); self.update_layout()
            
            self.camera.handle_event(event, mouse_pos)
            
            if self.main_mode == EDITOR_MODE_STRUCTURE:
                for box in self.input_boxes:
                    if box.handle_event(event) is not None: self.apply_anchor_offset(); box.active = False
            
            if self.main_buttons['structure'].is_clicked(event): self.main_mode = EDITOR_MODE_STRUCTURE; self.active_editor = self.structure_editor
            if self.main_buttons['decorations'].is_clicked(event): self.main_mode = EDITOR_MODE_DECORATIONS; self.active_editor = self.decoration_editor
            
            if self.file_buttons['screenshot'].is_clicked(event): self.take_screenshot()
            if self.file_buttons['new'].is_clicked(event): self.create_new_room()
            if self.file_buttons['load'].is_clicked(event): self.load_file_for_current_mode()
            if self.file_buttons['save_all'].is_clicked(event): self.save_all()
            
            self.active_editor.handle_events(event, mouse_pos, local_mouse_pos, keys)
        return True

    def draw(self):
        self.screen.fill(COLOR_BG)
        pygame.draw.rect(self.screen, COLOR_TOP_BAR, self.top_bar_rect)
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, self.right_panel_rect)
        
        # Determine which overlays to show in the editor view
        is_walkable_visible = False
        is_layer_visible = False
        if self.main_mode == EDITOR_MODE_STRUCTURE:
            if self.structure_editor.edit_mode == MODE_LAYERS:
                is_layer_visible = True
            elif self.structure_editor.show_walkable_overlay: # Only show walkable if not in layer mode
                is_walkable_visible = True
        
        should_draw_decos = self.main_mode == EDITOR_MODE_DECORATIONS
        
        walkable_view_filter = False
        if self.main_mode == EDITOR_MODE_DECORATIONS:
            walkable_view_filter = self.decoration_editor.walkable_only_view

        self.renderer.draw_room_on_surface(
            self.editor_surface, self.current_room, self.camera.offset, self.camera.zoom, 
            is_editor_view=True, 
            draw_walkable_overlay=is_walkable_visible,
            draw_layer_overlay=is_layer_visible,
            draw_decorations=should_draw_decos,
            walkable_view_filter=walkable_view_filter
        )
        self.active_editor.draw_on_editor(self.editor_surface)
        self.screen.blit(self.editor_surface, self.editor_rect)

        pygame.draw.rect(self.screen, COLOR_BORDER, self.editor_rect, 1)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.right_panel_rect, 1)

        # The preview should always show everything
        self.renderer.draw_room_on_surface(self.preview_surface, self.current_room, self.calculate_preview_offset(PREVIEW_SIZE), 1.0, is_editor_view=False, draw_decorations=True)
        self.screen.blit(self.preview_surface, self.preview_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.preview_rect, 1)
        title_surf = self.font_title.render("Room Preview", True, COLOR_TITLE_TEXT); title_rect = title_surf.get_rect(topright=(self.preview_rect.right, self.preview_rect.bottom + 5)); self.screen.blit(title_surf, title_rect)

        if self.main_mode == EDITOR_MODE_DECORATIONS: self.draw_item_preview()
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

    def draw_item_preview(self):
        self.item_preview_surface.fill(COLOR_TILE)
        preview_anchor_pos = (self.item_preview_rect.w / 2, self.item_preview_rect.h / 2)
        self.renderer._draw_iso_grid_on_surface(self.item_preview_surface, self.item_preview_surface.get_rect(), preview_anchor_pos)
        
        item_image, item_offset = self.decoration_editor.get_selected_item_image()
        
        if item_image and item_offset:
            img_w, img_h = item_image.get_size()
            box_w, box_h = self.item_preview_rect.size
            
            scale = 1.0
            if img_w > box_w or img_h > box_h:
                scale = min(box_w / img_w, box_h / img_h)

            final_image = item_image
            final_offset = item_offset
            if scale < 1.0:
                scaled_size = (int(img_w * scale), int(img_h * scale))
                final_image = pygame.transform.smoothscale(item_image, scaled_size)
                final_offset = (item_offset[0] * scale, item_offset[1] * scale)
            
            draw_x = preview_anchor_pos[0] - final_offset[0]
            draw_y = preview_anchor_pos[1] - final_offset[1]
            self.item_preview_surface.blit(final_image, (draw_x, draw_y))
        
        self.screen.blit(self.item_preview_surface, self.item_preview_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.item_preview_rect, 1)

        title_text = "Item Preview"
        if self.decoration_editor.selected_deco_item:
            title_text = self.decoration_editor.selected_deco_item.get('name', 'Item Preview')
            
        title_surf = self.font_title.render(title_text, True, COLOR_TITLE_TEXT)
        title_rect = title_surf.get_rect(topright=(self.item_preview_rect.right, self.item_preview_rect.bottom + 5))
        self.screen.blit(title_surf, title_rect)

    def run(self):
        running = True
        try:
            while running: running = self.handle_events(); self.draw(); self.clock.tick(60)
        except KeyboardInterrupt: print("\nEditor closed with Ctrl+C.")
        finally: pygame.quit()
    
    def create_new_room(self):
        new_structure = {"name": "New Structure", "id": "new_structure", "dimensions": {"width": 0, "depth": 0, "origin_x": 0, "origin_y": 0}, "renderAnchor": {"x": 0, "y": 0}, "tiles": [], "walkable": [], "layers": [], "walls": []}
        new_decoration_set = {"decoration_set_name": "New Decoration Set", "structure_id": "new_structure", "decorations": []}
        self.data_manager.current_decoration_set_path = None; self.data_manager.current_structure_path = None
        self.set_new_room_data(new_structure, new_decoration_set)

    def load_file_for_current_mode(self):
        start_dir = os.path.join(self.project_root, "rooms")
        s_data, d_data = self.data_manager.load_decoration_set_and_structure(initial_dir=start_dir)
        if s_data and d_data: self.set_new_room_data(s_data, d_data)

    def take_screenshot(self):
        """Saves the content of the preview surface to a PNG file."""
        from tkinter import filedialog, messagebox

        if not self.current_room:
            messagebox.showwarning("Screenshot", "There is no room to take a screenshot of.")
            return

        self.data_manager._init_tk_root()

        default_name = "room_preview.png"
        if self.current_room.decoration_set_data:
            room_name = self.current_room.decoration_set_data.get("decoration_set_name", "Untitled")
            sane_name = re.sub(r'[^\w\s-]', '', room_name).strip().replace(' ', '_')
            if sane_name: default_name = f"{sane_name}_preview.png"
        
        screenshots_dir = os.path.join(self.project_root, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        filepath = filedialog.asksaveasfilename(
            parent=self.data_manager.root,
            title="Save Preview Screenshot",
            initialdir=screenshots_dir,
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
        )
        self.data_manager.root.update()

        if filepath:
            try:
                pygame.image.save(self.preview_surface, filepath)
                print(f"Screenshot saved to {filepath}")
            except Exception as e:
                print(f"Error saving screenshot: {e}")
                messagebox.showerror("Screenshot Error", f"Could not save the image:\n{e}")

    def save_all(self):
        if not self.current_room: return
        
        # First, update the data dictionaries with the current state of the editor
        self.current_room.update_structure_data_from_internal()
        self.current_room.update_decoration_set_data_from_internal()

        # Then, call the new save function from the DataManager
        ok, new_name = self.data_manager.save_project_to_folder(
            self.current_room.structure_data,
            self.current_room.decoration_set_data
        )

        if ok:
            self.save_confirmation_timer = 120
            new_caption = new_name.replace('_', ' ').title() if new_name else "Project"
            pygame.display.set_caption(f"Editor - {new_caption}")

    def center_camera_on_room(self):
        if not self.current_room or not self.editor_rect.w or not self.editor_rect.h: return
        center_world_coords = self.current_room.calculate_center_world_coords()
        self.camera.center_on_coords(center_world_coords)

    def draw_info_box(self, mode_specific_lines):
        margin, padding, line_height = 15, 8, 15
        base_lines = ["Controls:", "[Middle Mouse] Pan View", "[Ctrl+Wheel] Zoom"]
        if self.main_mode == EDITOR_MODE_STRUCTURE: base_lines.append("[Shift+Click] Set Anchor")
        info_lines = base_lines[:1] + mode_specific_lines + base_lines[1:]
        rendered_lines = [self.font_info.render(line, True, COLOR_INFO_TEXT) for line in info_lines]
        box_w = max(line.get_width() for line in rendered_lines) + padding * 2; box_h = len(info_lines) * line_height + padding * 2
        box_rect = pygame.Rect(0, 0, box_w, box_h); box_rect.bottomright = (self.editor_rect.right - margin, self.editor_rect.bottom - margin)
        pygame.draw.rect(self.screen, COLOR_EDITOR_BG, box_rect, border_radius=5); pygame.draw.rect(self.screen, COLOR_BORDER, box_rect, 1, border_radius=5)
        for i, line_surf in enumerate(rendered_lines): self.screen.blit(line_surf, (box_rect.left + padding, box_rect.top + padding + i * line_height))
    
    def draw_save_confirmation(self):
        if self.save_confirmation_timer > 0:
            self.save_confirmation_timer -= 1
            surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            text_surf = self.font_title.render("Project Saved!", True, COLOR_TEXT)
            bg_rect = text_surf.get_rect(center=self.editor_rect.center).inflate(30, 20)
            pygame.draw.rect(surf, COLOR_SAVE_CONFIRM_BG, bg_rect, border_radius=8)
            self.screen.blit(surf, (0, 0)); self.screen.blit(text_surf, text_surf.get_rect(center=self.editor_rect.center))

    def update_anchor_offset_inputs(self):
        if self.current_room and 'renderAnchor' in self.current_room.structure_data:
            center_wx, center_wy = self.current_room.calculate_center_world_coords()
            offset_x = self.current_room.structure_data['renderAnchor']['x'] - center_wx; offset_y = self.current_room.structure_data['renderAnchor']['y'] - center_wy
            self.anchor_offset_input_x.set_text(f"{offset_x:.0f}"); self.anchor_offset_input_y.set_text(f"{offset_y:.0f}")

    def apply_anchor_offset(self):
        try:
            offset_x = float(self.anchor_offset_input_x.text); offset_y = float(self.anchor_offset_input_y.text)
            center_wx, center_wy = self.current_room.calculate_center_world_coords()
            self.current_room.structure_data['renderAnchor']['x'] = center_wx + offset_x; self.current_room.structure_data['renderAnchor']['y'] = center_wy + offset_y
        except (ValueError, KeyError): self.update_anchor_offset_inputs()

    def calculate_preview_offset(self, surface_size):
        if self.current_room and "renderAnchor" in self.current_room.structure_data:
            ax, ay = self.current_room.structure_data["renderAnchor"]["x"], self.current_room.structure_data["renderAnchor"]["y"]
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
        elif button_name == "mode_walkable":
            icon_rect = pygame.Rect(0, 0, 24, 24)
            icon_rect.center = (center_x, top_y + 4)
            pygame.draw.rect(screen, COLOR_WALKABLE_OVERLAY, icon_rect, border_radius=3)
            pygame.draw.rect(screen, (200, 255, 200), icon_rect, 1, border_radius=3)
        elif button_name == "mode_layers":
            r1 = pygame.Rect(0,0,28,12); r1.center = (center_x, top_y)
            r2 = r1.copy(); r2.move_ip(4, 4)
            r3 = r2.copy(); r3.move_ip(4, 4)
            pygame.draw.rect(screen, LAYER_DATA[LAYER_BACKGROUND]["color"], r3, border_radius=2)
            pygame.draw.rect(screen, LAYER_DATA[LAYER_MAIN]["color"], r2, border_radius=2)
            pygame.draw.rect(screen, LAYER_DATA[LAYER_FOREGROUND]["color"], r1, border_radius=2)
            pygame.draw.rect(screen, COLOR_BORDER, r1, 1, border_radius=2)
            pygame.draw.rect(screen, COLOR_BORDER, r2, 1, border_radius=2)
            pygame.draw.rect(screen, COLOR_BORDER, r3, 1, border_radius=2)