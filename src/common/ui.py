# src/common/ui.py

import pygame
from common.constants import *

class Button:
    def __init__(self, x, y, w, h, text, font): self.rect = pygame.Rect(x, y, w, h); self.text = text; self.font = font; self.is_hovered = False
    def draw(self, screen, is_active=False):
        color = COLOR_BUTTON_ACTIVE if is_active else (COLOR_BUTTON_HOVER if self.is_hovered else COLOR_BUTTON)
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        if self.text:
            ts = self.font.render(self.text, True, COLOR_TEXT)
            tr = ts.get_rect(center=self.rect.center)
            screen.blit(ts, tr)
    def check_hover(self, m_pos): self.is_hovered = self.rect.collidepoint(m_pos)
    def is_clicked(self, event): return self.is_hovered and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

class TextInputBox:
    # --- LÍNEA MODIFICADA: Se añade 'input_type' al constructor ---
    def __init__(self, x, y, w, h, font, text='', input_type='text'): 
        self.rect = pygame.Rect(x, y, w, h); self.color = COLOR_INPUT_INACTIVE; self.text = text; self.font = font; self.txt_surface = self.font.render(text, True, self.color); self.active = False; self.cursor_visible = True; self.cursor_timer = 0
        self.input_type = input_type # Guardamos el tipo de input

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN: 
            self.active = self.rect.collidepoint(event.pos)
            self.color = COLOR_TEXT if self.active else COLOR_INPUT_INACTIVE
        if event.type == pygame.KEYDOWN and self.active:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): 
                return self.text
            elif event.key == pygame.K_BACKSPACE: 
                self.text = self.text[:-1]
            # --- BLOQUE MODIFICADO: Lógica condicional para el tipo de entrada ---
            else:
                if self.input_type == 'numeric':
                    # Lógica original solo para números
                    if event.unicode.isdigit() or (event.unicode == '.' and '.' not in self.text) or (event.unicode == '-' and not self.text): 
                        self.text += event.unicode
                else: # 'text' (o cualquier otro valor)
                    # Lógica general que acepta casi cualquier carácter imprimible
                    if event.unicode:
                         self.text += event.unicode
            # --- FIN DEL BLOQUE MODIFICADO ---
            self.txt_surface = self.font.render(self.text, True, COLOR_TEXT)
        return None

    def update(self):
        if self.active: self.cursor_timer = (self.cursor_timer + 1) % 60; self.cursor_visible = self.cursor_timer < 30
    def draw(self, screen):
        pygame.draw.rect(screen, COLOR_EDITOR_BG, self.rect); pygame.draw.rect(screen, COLOR_INPUT_ACTIVE if self.active else self.color, self.rect, 2); screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        if self.active and self.cursor_visible: c_pos = self.rect.x + 5 + self.txt_surface.get_width(); pygame.draw.line(screen, COLOR_TEXT, (c_pos, self.rect.y + 5), (c_pos, self.rect.y + self.rect.h - 5))
    def set_text(self, text): self.text = str(text); self.txt_surface = self.font.render(self.text, True, COLOR_TEXT)