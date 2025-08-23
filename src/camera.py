# src/camera.py

import pygame

class Camera:
    def __init__(self, editor_rect=pygame.Rect(0,0,1,1)):
        self.offset = [0, 0]
        self.editor_rect = editor_rect
        self.is_panning = False
        self.pan_start_pos = (0, 0)
        
        # --- MODIFIED: Switched to snapped zoom levels for pixel-perfect rendering ---
        self.zoom_levels = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
        try:
            # Start at 100% zoom
            self.current_zoom_index = self.zoom_levels.index(1.0)
        except ValueError:
            # Fallback if 1.0 is not in the list for some reason
            self.current_zoom_index = len(self.zoom_levels) // 2
            
        self.zoom = self.zoom_levels[self.current_zoom_index]

    def handle_event(self, event, mouse_pos):
        """Procesa eventos de Pygame para el control de la cámara."""
        if self.editor_rect.collidepoint(mouse_pos):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
                self.is_panning = True
                self.pan_start_pos = event.pos
            
            # --- MODIFIED: Logic for snapped zoom ---
            if event.type == pygame.MOUSEWHEEL:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    local_mouse_pos = (mouse_pos[0] - self.editor_rect.x, mouse_pos[1] - self.editor_rect.y)
                    old_zoom = self.zoom

                    # Move up or down the zoom_levels list
                    if event.y > 0: # Zoom in
                        self.current_zoom_index = min(len(self.zoom_levels) - 1, self.current_zoom_index + 1)
                    elif event.y < 0: # Zoom out
                        self.current_zoom_index = max(0, self.current_zoom_index - 1)
                    
                    self.zoom = self.zoom_levels[self.current_zoom_index]
                    
                    # Adjust offset to zoom towards the mouse cursor, only if zoom changed
                    if self.zoom != old_zoom:
                        zoom_ratio = self.zoom / old_zoom
                        self.offset[0] = local_mouse_pos[0] + (self.offset[0] - local_mouse_pos[0]) * zoom_ratio
                        self.offset[1] = local_mouse_pos[1] + (self.offset[1] - local_mouse_pos[1]) * zoom_ratio
                    
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
        # --- MODIFIED: Account for zoom when centering ---
        self.offset = [
            editor_center[0] - (world_coords[0] * self.zoom),
            editor_center[1] - (world_coords[1] * self.zoom)
        ]