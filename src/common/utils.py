from common.constants import TILE_WIDTH_HALF, TILE_HEIGHT_HALF

def grid_to_screen(grid_x, grid_y, offset):
    sx = (grid_x - grid_y) * TILE_WIDTH_HALF + offset[0]
    sy = (grid_x + grid_y) * TILE_HEIGHT_HALF + offset[1]
    return int(sx), int(sy)

def screen_to_grid(screen_x, screen_y, offset):
    # Ajusta para el origen del tile, que no es (0,0)
    wx = screen_x - offset[0] - TILE_WIDTH_HALF
    wy = screen_y - offset[1] - TILE_HEIGHT_HALF
    gx = round((wx / TILE_WIDTH_HALF + wy / TILE_HEIGHT_HALF) / 2)
    gy = round((wy / TILE_HEIGHT_HALF - wx / TILE_WIDTH_HALF) / 2)
    return int(gx), int(gy)