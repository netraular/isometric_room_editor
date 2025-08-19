import pygame
from common.constants import *
from common.ui import Button

class DecorationEditor:
    def __init__(self, app_ref):
        self.app = app_ref
        self.font_ui = self.app.font_ui
        self.font_info = self.app.font_info

    def handle_events(self, event, mouse_pos, local_mouse_pos, keys):
        # Lógica futura para seleccionar, colocar, mover y rotar decoraciones.
        pass

    def draw_on_editor(self, surface):
        # Dibuja un fantasma de la decoración a colocar, etc.
        # Por ahora, solo dibuja las decoraciones existentes
        for deco in self.app.placed_decorations:
             pos = deco.get("grid_pos")
             if pos:
                 # Esta es una visualización de placeholder
                 from common.utils import grid_to_screen
                 sp = grid_to_screen(pos[0], pos[1], self.app.camera_offset)
                 rect = pygame.Rect(sp[0], sp[1] - TILE_HEIGHT, TILE_WIDTH, TILE_HEIGHT * 2)
                 pygame.draw.rect(surface, (100, 200, 100, 150), rect)
                 pygame.draw.rect(surface, (150, 255, 150), rect, 2)


    def draw_ui_on_panel(self, screen):
        # Dibuja el catálogo de decoraciones en la parte superior del panel derecho
        margin = 15
        y_pos = self.app.right_panel_rect.y + margin
        placeholder_text = self.font_ui.render("Decoration Catalog (TBD)", True, COLOR_TEXT)
        screen.blit(placeholder_text, (self.app.right_panel_rect.left + margin, y_pos))

    def get_info_lines(self):
        # Devuelve las líneas de información para que App las dibuje
        return ["[Click] Place Decoration", "[R] Rotate Decoration", "[Del] Delete Decoration"]