from common.constants import TILE_WIDTH_HALF, TILE_HEIGHT_HALF

def grid_to_screen(grid_x, grid_y, offset, zoom=1.0):
    scaled_twh = TILE_WIDTH_HALF * zoom
    scaled_thh = TILE_HEIGHT_HALF * zoom
    sx = (grid_x - grid_y) * scaled_twh + offset[0]
    sy = (grid_x + grid_y) * scaled_thh + offset[1]
    return int(sx), int(sy)

def screen_to_grid(screen_x, screen_y, offset, zoom=1.0):
    if zoom == 0: return 0, 0
    scaled_twh = TILE_WIDTH_HALF * zoom
    scaled_thh = TILE_HEIGHT_HALF * zoom
    
    # Adjust for the tile's top-left corner being the drawing reference
    wx = screen_x - offset[0] - scaled_twh
    wy = screen_y - offset[1] - scaled_thh
    
    # Inverse transformation
    gx = round((wx / scaled_twh + wy / scaled_thh) / 2)
    gy = round((wy / scaled_thh - wx / scaled_twh) / 2)
    return int(gx), int(gy)