# src/data_manager.py
import json
import os
from tkinter import filedialog, Tk
import pygame

class DataManager:
    # --- MODIFIED: Accept assets_root ---
    def __init__(self, project_root, assets_root):
        self.project_root = project_root
        self.assets_root = assets_root  # Path to the pipeline's assets folder
        self.root = Tk()
        self.root.withdraw()
        self.current_decoration_set_path = None
        self.current_structure_path = None
        self.image_cache = {}
        self.furni_data_cache = {}

    def load_catalog(self):
        # Catalog is still local to the editor project
        catalog_path = os.path.join(self.project_root, "assets", "catalog.json")
        if not os.path.exists(catalog_path):
            print("Error: catalog.json not found. Run build_catalog.py first.")
            return {}
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading catalog: {e}")
            return {}

    def get_furni_data(self, base_id):
        if base_id in self.furni_data_cache:
            return self.furni_data_cache[base_id]

        # --- MODIFIED: Read from the final pipeline output directory ---
        data_path = os.path.join(self.assets_root, "4_final_furni_data", base_id, "data.json")
        
        if not os.path.exists(data_path):
            # print(f"Warning: data.json for '{base_id}' not found at {data_path}")
            self.furni_data_cache[base_id] = None
            return None
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.furni_data_cache[base_id] = data
                return data
        except Exception as e:
            print(f"Error loading data.json for {base_id}: {e}")
            self.furni_data_cache[base_id] = None
            return None

    # --- MODIFIED: New signature to handle self-contained packages ---
    def get_image(self, base_id, relative_path):
        """
        Loads an image from a furni's final package directory.
        base_id: The base ID of the furni (e.g., 'rare_dragonlamp').
        relative_path: The path within that package (e.g., 'icons/rare_dragonlamp_icon_0.png').
        """
        cache_key = f"{base_id}/{relative_path}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        # Build the full, absolute path to the image asset
        full_path = os.path.join(self.assets_root, "4_final_furni_data", base_id, relative_path)
        
        if not os.path.exists(full_path):
            # print(f"Warning: Image not found at {full_path}")
            return None
        try:
            image = pygame.image.load(full_path).convert_alpha()
            self.image_cache[cache_key] = image
            return image
        except Exception as e:
            print(f"Error loading image {full_path}: {e}")
            return None
            
    def load_structure_only(self):
        initial_dir = os.path.join(self.project_root, "rooms", "structures")
        os.makedirs(initial_dir, exist_ok=True)
        fp = filedialog.askopenfilename(parent=self.root, initialdir=initial_dir, title="Load Room Structure", filetypes=(("JSON files", "*.json"),))
        self.root.update()
        if not fp: return None
        try:
            with open(fp, 'r') as f: structure_data = json.load(f)
            self.current_structure_path = fp
            return structure_data
        except Exception as e: print(f"Error loading structure file: {e}"); return None

    def load_decoration_set_and_structure(self, initial_dir=None):
        if initial_dir is None: initial_dir = os.path.join(self.project_root, "rooms", "decoration_sets")
        os.makedirs(initial_dir, exist_ok=True)
        fp = filedialog.askopenfilename(parent=self.root, initialdir=initial_dir, title="Load Decoration Set or Structure", filetypes=(("JSON files", "*.json"),))
        self.root.update()
        if not fp: return None, None
        try:
            with open(fp, 'r') as f: file_data = json.load(f)
            if "structure_id" in file_data:
                decoration_set_data = file_data
                structure_id = decoration_set_data.get("structure_id")
                if not structure_id: raise ValueError("Decoration Set file has an empty 'structure_id'.")
                structure_fp = os.path.join(self.project_root, "rooms", "structures", f"{structure_id}.json")
                if not os.path.exists(structure_fp): raise FileNotFoundError(f"Structure file '{structure_id}.json' not found for this decoration set.")
                with open(structure_fp, 'r') as f: structure_data = json.load(f)
                self.current_decoration_set_path = fp; self.current_structure_path = structure_fp
                return structure_data, decoration_set_data
            elif "tiles" in file_data and "dimensions" in file_data:
                structure_data = file_data
                new_decoration_set = {"decoration_set_name": f"{structure_data.get('name', 'New')} Decoration Set", "structure_id": structure_data.get('id', 'unknown'), "decorations": []}
                self.current_structure_path = fp; self.current_decoration_set_path = None
                return structure_data, new_decoration_set
            else: return None, None
        except Exception as e: print(f"Error loading room: {e}"); return None, None
    
    def save_decoration_set(self, decoration_set_data, save_as=False):
        fp = self.current_decoration_set_path
        if not fp or save_as:
            initial_dir = os.path.join(self.project_root, "rooms", "decoration_sets")
            os.makedirs(initial_dir, exist_ok=True)
            fp = filedialog.asksaveasfilename(parent=self.root, initialdir=initial_dir, title="Save Decoration Set As", defaultextension=".json", filetypes=(("JSON files", "*.json"),))
            self.root.update()
            if not fp: return False, None
        try:
            with open(fp, 'w') as f: json.dump(decoration_set_data, f, indent=2)
            self.current_decoration_set_path = fp
            return True, os.path.basename(fp)
        except Exception as e: print(f"Error saving decoration set file: {e}"); return False, None

    def save_structure(self, structure_data, save_as=False):
        fp = self.current_structure_path
        if not fp or save_as:
            initial_dir = os.path.join(self.project_root, "rooms", "structures")
            os.makedirs(initial_dir, exist_ok=True)
            fp = filedialog.asksaveasfilename(parent=self.root, initialdir=initial_dir, title="Save Room Structure As", defaultextension=".json", filetypes=(("JSON files", "*.json"),))
            self.root.update()
            if not fp: return False
        try:
            structure_data['id'] = os.path.splitext(os.path.basename(fp))[0]
            with open(fp, 'w') as f: json.dump(structure_data, f, indent=2)
            self.current_structure_path = fp
            return True
        except Exception as e: print(f"Error saving structure file: {e}"); return False