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

class ToggleSwitch:
    def __init__(self, x, y, w, h, font, text, initial_state=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.text = text
        self.state = initial_state
        self.is_hovered = False
        self.knob_radius = (self.rect.height - 8) // 2

    def check_hover(self, m_pos):
        self.is_hovered = self.rect.collidepoint(m_pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
            self.state = not self.state
            return True # Indicates the state has changed
        return False

    def draw(self, screen):
        # Draw the text label
        text_surf = self.font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(centery=self.rect.centery, left=self.rect.left)
        screen.blit(text_surf, text_rect)

        # Calculate position for the switch part
        switch_w = self.knob_radius * 3.5
        switch_h = self.rect.height - 4
        switch_x = self.rect.right - switch_w
        switch_y = self.rect.centery - switch_h / 2
        switch_rect = pygame.Rect(switch_x, switch_y, switch_w, switch_h)
        
        # Reworked logic to handle hover state for both on and off states
        track_color = COLOR_BUTTON
        if self.state: # Is the toggle ON?
            track_color = COLOR_TOGGLE_ON_HOVER if self.is_hovered else COLOR_TOGGLE_ON
        else: # The toggle is OFF
            track_color = COLOR_BUTTON_HOVER if self.is_hovered else COLOR_BUTTON
        
        pygame.draw.rect(screen, track_color, switch_rect, border_radius=int(switch_h / 2))

        # Draw the knob
        knob_x_off = switch_rect.left + self.knob_radius + 4
        knob_x_on = switch_rect.right - self.knob_radius - 4
        knob_x = knob_x_on if self.state else knob_x_off
        knob_pos = (int(knob_x), self.rect.centery)
        pygame.draw.circle(screen, COLOR_TEXT, knob_pos, self.knob_radius)
        pygame.draw.circle(screen, COLOR_BORDER, knob_pos, self.knob_radius, 1)

class TextInputBox:
    def __init__(self, x, y, w, h, font, text='', input_type='text'): 
        self.rect = pygame.Rect(x, y, w, h); self.color = COLOR_INPUT_INACTIVE; self.text = text; self.font = font; self.txt_surface = self.font.render(text, True, self.color); self.active = False; self.cursor_visible = True; self.cursor_timer = 0
        self.input_type = input_type

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN: 
            self.active = self.rect.collidepoint(event.pos)
            self.color = COLOR_TEXT if self.active else COLOR_INPUT_INACTIVE
        if event.type == pygame.KEYDOWN and self.active:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): 
                return self.text
            elif event.key == pygame.K_BACKSPACE: 
                self.text = self.text[:-1]
            else:
                if self.input_type == 'numeric':
                    # Original logic for numbers only
                    if event.unicode.isdigit() or (event.unicode == '.' and '.' not in self.text) or (event.unicode == '-' and not self.text): 
                        self.text += event.unicode
                else: # 'text' (or any other value)
                    # General logic that accepts almost any printable character
                    if event.unicode:
                         self.text += event.unicode
            self.txt_surface = self.font.render(self.text, True, COLOR_TEXT)
        return None

    def update(self):
        if self.active: self.cursor_timer = (self.cursor_timer + 1) % 60; self.cursor_visible = self.cursor_timer < 30
    def draw(self, screen):
        pygame.draw.rect(screen, COLOR_EDITOR_BG, self.rect); pygame.draw.rect(screen, COLOR_INPUT_ACTIVE if self.active else self.color, self.rect, 2); screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        if self.active and self.cursor_visible: c_pos = self.rect.x + 5 + self.txt_surface.get_width(); pygame.draw.line(screen, COLOR_TEXT, (c_pos, self.rect.y + 5), (c_pos, self.rect.y + self.rect.h - 5))
    def set_text(self, text): self.text = str(text); self.txt_surface = self.font.render(self.text, True, COLOR_TEXT)