import pygame
from common.constants import *
from common.ui import Button

class ObjectEditor:
    def __init__(self, app_ref):
        self.app = app_ref
        self.font_ui = self.app.font_ui
        self.font_info = self.app.font_info

    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        # Lógica futura para seleccionar, colocar, mover y rotar objetos.
        pass

    def draw_on_editor(self, surface):
        # Dibuja un fantasma del objeto a colocar, etc.
        # Por ahora, solo dibuja los objetos existentes
        for obj in self.app.placed_objects:
             pos = obj.get("grid_pos")
             if pos:
                 # Esta es una visualización de placeholder
                 from common.utils import grid_to_screen
                 sp = grid_to_screen(pos[0], pos[1], self.app.camera_offset)
                 rect = pygame.Rect(sp[0], sp[1] - TILE_HEIGHT, TILE_WIDTH, TILE_HEIGHT * 2)
                 pygame.draw.rect(surface, (100, 200, 100, 150), rect)
                 pygame.draw.rect(surface, (150, 255, 150), rect, 2)


    def draw_ui_on_panel(self, screen):
        # Dibuja el catálogo de muebles, etc.
        y_pos = self.app.preview_rect.bottom + 80
        placeholder_text = self.font_ui.render("Object Catalog (TBD)", True, COLOR_TEXT)
        screen.blit(placeholder_text, (self.app.preview_rect.left, y_pos))

        # Info de controles
        info_lines_mode = ["[Click] Place Object", "[R] Rotate Object", "[Del] Delete Object"]
        self.app.draw_info_box(info_lines_mode)