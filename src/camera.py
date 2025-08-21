# src/camera.py

import pygame

class Camera:
    def __init__(self, editor_rect=pygame.Rect(0,0,1,1)):
        self.offset = [0, 0]
        self.editor_rect = editor_rect
        self.is_panning = False
        self.pan_start_pos = (0, 0)
    
    def handle_event(self, event, mouse_pos):
        """Procesa eventos de Pygame para el control de la cámara."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2 and self.editor_rect.collidepoint(mouse_pos):
            self.is_panning = True
            self.pan_start_pos = event.pos
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.is_panning = False
        if event.type == pygame.MOUSEMOTION and self.is_panning:
            delta = (event.pos[0] - self.pan_start_pos[0], event.pos[1] - self.pan_start_pos[1])
            self.offset[0] += delta[0]
            self.offset[1] += delta[1]
            self.pan_start_pos = event.pos
    
    def center_on_coords(self, world_coords):
        """Centra la cámara en un punto específico del mundo."""
        editor_center = (self.editor_rect.w / 2, self.editor_rect.h / 2)
        self.offset = [editor_center[0] - world_coords[0], editor_center[1] - world_coords[1]]