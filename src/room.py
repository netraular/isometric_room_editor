# src/room.py

from common.constants import *

class Room:
    def __init__(self, structure_data, decoration_set_data):
        self.structure_data = structure_data
        self.decoration_set_data = decoration_set_data
        
        self.tiles = {}
        self.walls = set()
        self.walkable_map = {}
        self.layer_map = {}
        self.decorations = []
        self.occupied_layer_tiles = {} # Key: (gx, gy), Value: set of layer_id
        
        self.populate_internal_data()

    def _calculate_automatic_layers(self):
        """
        Automatically assigns special layers based on room structure.
        - The WALL layer is assigned to tiles behind NE and NW walls.
        This overrides any manually painted layer on those specific tiles.
        """
        for pos, edge in self.walls:
            behind_pos = None
            if edge == EDGE_NE:
                behind_pos = (pos[0], pos[1] - 1)
            elif edge == EDGE_NW:
                behind_pos = (pos[0] - 1, pos[1])
            
            if behind_pos:
                self.layer_map[behind_pos] = LAYER_WALL
                # Note: We don't need to add this to self.tiles if it doesn't exist.
                # The renderer will handle drawing the layer overlay on non-tile positions.

    def populate_internal_data(self):
        """Populates internal dictionaries and sets from JSON data."""
        self.tiles.clear(); self.walls.clear(); self.decorations.clear()
        self.walkable_map.clear(); self.layer_map.clear(); self.occupied_layer_tiles.clear()
        
        dims = self.structure_data.get('dimensions', {})
        ox, oy = dims.get('origin_x', 0), dims.get('origin_y', 0)
        
        for y, row in enumerate(self.structure_data.get('tiles', [])):
            for x, char_val in enumerate(row):
                if char_val != '0':
                    self.tiles[(x + ox, y + oy)] = int(char_val)
        
        for y, row in enumerate(self.structure_data.get('walkable', [])):
            for x, char_val in enumerate(row):
                if char_val in ('0', '1'):
                    grid_pos = (x + ox, y + oy)
                    if grid_pos in self.tiles:
                        self.walkable_map[grid_pos] = int(char_val)

        for y, row in enumerate(self.structure_data.get('layers', [])):
            for x, char_val in enumerate(row):
                grid_pos = (x + ox, y + oy)
                layer_id = LAYER_CHARS_TO_ID.get(char_val)
                if layer_id is not None and grid_pos in self.tiles:
                    # We only load manually paintable layers. Wall layer is calculated.
                    if layer_id not in [LAYER_WALL, LAYER_FLOOR]:
                        self.layer_map[grid_pos] = layer_id

        for pos in self.tiles:
            if pos not in self.layer_map: self.layer_map[pos] = DEFAULT_LAYER

        for wall_data in self.structure_data.get('walls', []):
            self.walls.add((tuple(wall_data['grid_pos']), wall_data['edge']))
        
        # After loading all structure, calculate automatic layers
        self._calculate_automatic_layers()
            
        self.decorations = self.decoration_set_data.get("decorations", [])
        for deco in self.decorations:
            pos_tuple = tuple(deco["grid_pos"])
            layer_id = deco.get("layer", DEFAULT_LAYER)
            if pos_tuple not in self.occupied_layer_tiles:
                self.occupied_layer_tiles[pos_tuple] = set()
            self.occupied_layer_tiles[pos_tuple].add(layer_id)

    def add_decoration(self, base_id, variant_id, grid_pos, rotation, layer):
        """Adds a decoration if the specific layer on the tile is not occupied."""
        grid_pos_tuple = tuple(grid_pos)

        if self.occupied_layer_tiles.get(grid_pos_tuple) and layer in self.occupied_layer_tiles[grid_pos_tuple]:
            print(f"[WARN] Cannot place item: tile {grid_pos_tuple} is already occupied on layer {layer}.")
            return False
        
        self.decorations.append({
            "base_id": base_id, "variant_id": variant_id,
            "grid_pos": list(grid_pos), "rotation": rotation, "layer": layer
        })
        
        if grid_pos_tuple not in self.occupied_layer_tiles:
            self.occupied_layer_tiles[grid_pos_tuple] = set()
        self.occupied_layer_tiles[grid_pos_tuple].add(layer)
        
        print(f"[LOG] Placing '{base_id}' at {grid_pos_tuple} on layer {layer}")
        return True

    def remove_decoration_at(self, grid_pos, layer):
        """Removes the decoration at the given grid position on a specific layer."""
        grid_pos_tuple = tuple(grid_pos)

        for deco in reversed(self.decorations):
            if tuple(deco.get("grid_pos")) == grid_pos_tuple and deco.get("layer", DEFAULT_LAYER) == layer:
                self.decorations.remove(deco)
                if grid_pos_tuple in self.occupied_layer_tiles:
                    self.occupied_layer_tiles[grid_pos_tuple].remove(layer)
                    if not self.occupied_layer_tiles[grid_pos_tuple]:
                        del self.occupied_layer_tiles[grid_pos_tuple]
                print(f"[LOG] Item '{deco.get('base_id')}' removed from position {grid_pos_tuple} on layer {layer}")
                return True
        return False

    def get_decorations_sorted_for_render(self):
        """
        Sorts decorations for correct rendering order.
        Primary sort key: Layer ID (lower layers are drawn first).
        Secondary sort key: Tile depth (decorations further back are drawn first).
        """
        return sorted(self.decorations, key=lambda d: (
            d.get('layer', DEFAULT_LAYER),
            (d['grid_pos'][1] + d['grid_pos'][0], d['grid_pos'][1] - d['grid_pos'][0])
        ))

    def calculate_center_world_coords(self):
        if not self.tiles: return (TILE_WIDTH_HALF, TILE_HEIGHT_HALF)
        all_x = [p[0] for p in self.tiles.keys()]; all_y = [p[1] for p in self.tiles.keys()]
        center_gx = (min(all_x) + max(all_x)) / 2; center_gy = (min(all_y) + max(all_y)) / 2
        center_wx = (center_gx - center_gy) * TILE_WIDTH_HALF; center_wy = (center_gx + center_gy) * TILE_HEIGHT_HALF
        return center_wx + TILE_WIDTH_HALF, center_wy + TILE_HEIGHT_HALF

    def update_structure_data_from_internal(self):
        all_coords = set(self.tiles.keys())
        for pos, layer_id in self.layer_map.items():
            if layer_id == LAYER_WALL: all_coords.add(pos)
        
        if not all_coords: min_x, min_y, max_x, max_y = 0, 0, -1, -1
        else:
            all_x = [p[0] for p in all_coords]; all_y = [p[1] for p in all_coords]
            min_x, max_x = min(all_x), max(all_x); min_y, max_y = min(all_y), max(all_y)
            
        new_w = max_x - min_x + 1; new_d = max_y - min_y + 1
        new_grid = [['0'] * new_w for _ in range(new_d)]
        new_walkable_grid = [['x'] * new_w for _ in range(new_d)]
        new_layer_grid = [['x'] * new_w for _ in range(new_d)]
        
        for (gx, gy), tile_type in self.tiles.items():
            row, col = gy - min_y, gx - min_x
            new_grid[row][col] = str(tile_type)
            new_walkable_grid[row][col] = str(self.walkable_map.get((gx, gy), 0))

        for (gx, gy), layer_id in self.layer_map.items():
            if min_x <= gx <= max_x and min_y <= gy <= max_y:
                # Do not save automatically calculated Wall layers. Only save painted layers.
                if layer_id != LAYER_WALL:
                    new_layer_grid[gy - min_y][gx - min_x] = LAYER_DATA[layer_id]['char']
        
        self.structure_data['dimensions'] = {'width': new_w, 'depth': new_d, 'origin_x': min_x, 'origin_y': min_y}
        self.structure_data['tiles'] = ["".join(row) for row in new_grid]
        self.structure_data['walkable'] = ["".join(row) for row in new_walkable_grid]
        self.structure_data['layers'] = ["".join(row) for row in new_layer_grid]
        self.structure_data['walls'] = [{"grid_pos": list(pos), "edge": edge} for pos, edge in sorted(list(self.walls))]
    
    def update_decoration_set_data_from_internal(self):
        self.decoration_set_data["decorations"] = self.decorations