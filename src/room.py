# src/room.py

from common.constants import TILE_WIDTH_HALF, TILE_HEIGHT_HALF

class Room:
    def __init__(self, structure_data, decoration_set_data):
        self.structure_data = structure_data
        self.decoration_set_data = decoration_set_data
        
        self.tiles = {}
        self.walls = set()
        self.decorations = []
        self.occupied_tiles = set()
        
        self.populate_internal_data()

    def populate_internal_data(self):
        """Populates internal dictionaries and sets from JSON data."""
        self.tiles.clear(); self.walls.clear(); self.decorations.clear(); self.occupied_tiles.clear()
        
        dims = self.structure_data.get('dimensions', {})
        ox, oy = dims.get('origin_x', 0), dims.get('origin_y', 0)
        
        for y, row in enumerate(self.structure_data.get('tiles', [])):
            for x, char_val in enumerate(row):
                if char_val != '0':
                    self.tiles[(x + ox, y + oy)] = int(char_val)
        
        for wall_data in self.structure_data.get('walls', []):
            self.walls.add((tuple(wall_data['grid_pos']), wall_data['edge']))
            
        self.decorations = self.decoration_set_data.get("decorations", [])
        for deco in self.decorations:
            self.occupied_tiles.add(tuple(deco.get("grid_pos")))

    def add_decoration(self, base_id, variant_id, grid_pos, rotation):
        """Adds a decoration if the tile is not occupied."""
        grid_pos_tuple = tuple(grid_pos)
        if grid_pos_tuple in self.occupied_tiles:
            print(f"[WARN] Cannot place item: tile {grid_pos_tuple} is already occupied.")
            return False
        
        self.decorations.append({
            "base_id": base_id, "variant_id": variant_id,
            "grid_pos": list(grid_pos), "rotation": rotation
        })
        self.occupied_tiles.add(grid_pos_tuple)
        print(f"[LOG] Placing '{base_id}' at {grid_pos_tuple} with rotation {rotation}")
        return True

    def remove_decoration_at(self, grid_pos):
        """Removes the decoration at the given grid position."""
        for deco in reversed(self.decorations):
            if tuple(deco.get("grid_pos")) == grid_pos:
                self.decorations.remove(deco)
                self.occupied_tiles.remove(grid_pos)
                print(f"[LOG] Item '{deco.get('base_id')}' removed from position {grid_pos}")
                return True
        return False

    def get_decorations_sorted_for_render(self):
        """Returns decorations sorted by depth for correct rendering."""
        return sorted(self.decorations, key=lambda d: (d['grid_pos'][1] + d['grid_pos'][0], d['grid_pos'][1] - d['grid_pos'][0]))

    def calculate_center_world_coords(self):
        """Calculates the geometric center of the room in world coordinates."""
        if not self.tiles: 
            # Return world coords for grid(0,0), adjusted to tile center
            return (TILE_WIDTH_HALF, TILE_HEIGHT_HALF)
            
        all_x = [p[0] for p in self.tiles.keys()]
        all_y = [p[1] for p in self.tiles.keys()]
        center_gx = (min(all_x) + max(all_x)) / 2
        center_gy = (min(all_y) + max(all_y)) / 2
        
        # Convert grid center to world center using the direct formula
        center_wx = (center_gx - center_gy) * TILE_WIDTH_HALF
        center_wy = (center_gx + center_gy) * TILE_HEIGHT_HALF
        
        # Add offset to be in the middle of the center tile's bounding box
        return center_wx + TILE_WIDTH_HALF, center_wy + TILE_HEIGHT_HALF

    def update_structure_data_from_internal(self):
        """Updates the structure_data dictionary from the internal state (tiles, walls)."""
        if not self.tiles:
            min_x, min_y, max_x, max_y = 0, 0, 0, 0
        else:
            all_x = [p[0] for p in self.tiles.keys()]
            all_y = [p[1] for p in self.tiles.keys()]
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            
        new_w = max_x - min_x + 1 if self.tiles else 0
        new_d = max_y - min_y + 1 if self.tiles else 0
        new_grid = [['0'] * new_w for _ in range(new_d)]
        for (gx, gy), tile_type in self.tiles.items():
            new_grid[gy - min_y][gx - min_x] = str(tile_type)
        
        self.structure_data['dimensions'] = {'width': new_w, 'depth': new_d, 'origin_x': min_x, 'origin_y': min_y}
        self.structure_data['tiles'] = ["".join(row) for row in new_grid]
        self.structure_data['walls'] = [{"grid_pos": list(pos), "edge": edge} for pos, edge in sorted(list(self.walls))]
    
    def update_decoration_set_data_from_internal(self):
        """Updates the decoration_set_data dictionary from the internal state."""
        self.decoration_set_data["decorations"] = self.decorations