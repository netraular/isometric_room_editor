# src/data_manager.py
import json
import os
from tkinter import filedialog, Tk, messagebox
import pygame
import shutil

class DataManager:
    def __init__(self, project_root, assets_root):
        self.project_root = project_root
        self.assets_root = assets_root
        self.root = None
        self.current_decoration_set_path = None
        self.current_structure_path = None
        self.image_cache = {}
        self.furni_data_cache = {}

    def _init_tk_root(self):
        if self.root is None:
            self.root = Tk()
            self.root.withdraw()

    def _export_used_assets(self, decoration_set_data, export_dir):
        """Copies the asset folders of the furniture to a destination directory."""
        if not decoration_set_data.get("decorations"): return 0
        
        used_base_ids = {deco['base_id'] for deco in decoration_set_data["decorations"]}
        if not used_base_ids: return 0

        print(f"Exporting assets for {len(used_base_ids)} items to: {export_dir}")
        exported_count = 0
        for base_id in used_base_ids:
            source_path = os.path.join(self.assets_root, "4_final_furni_data", base_id)
            dest_path = os.path.join(export_dir, base_id)
            if os.path.isdir(source_path):
                try:
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    exported_count += 1
                except Exception as e:
                    print(f"Error exporting assets for '{base_id}': {e}")
            else:
                print(f"Warning: Source asset directory not found for '{base_id}' at {source_path}")
        return exported_count

    def save_project_to_folder(self, structure_data, decoration_set_data):
        """
        Asks the user for a folder and saves the structure, decorations, and
        assets of the used furniture in it.
        """
        self._init_tk_root()
        initial_dir = os.path.join(self.project_root, "rooms")
        target_folder = filedialog.askdirectory(
            parent=self.root,
            initialdir=initial_dir,
            title="Select a folder to save the entire room project"
        )
        self.root.update()

        if not target_folder:
            return False, None # User cancelled

        try:
            # 1. Prepare filenames and paths
            base_name = os.path.basename(target_folder)
            structure_filename = f"{base_name}_structure.json"
            decorations_filename = f"{base_name}_decorations.json"
            furnis_folder_path = os.path.join(target_folder, "furnis")

            structure_filepath = os.path.join(target_folder, structure_filename)
            decorations_filepath = os.path.join(target_folder, decorations_filename)

            # 2. Update internal IDs to match
            structure_data['id'] = base_name
            decoration_set_data['structure_id'] = base_name
            decoration_set_data['decoration_set_name'] = f"{base_name.replace('_', ' ').title()} Decorations"

            # 3. Save the structure file
            with open(structure_filepath, 'w') as f:
                json.dump(structure_data, f, indent=2)

            # 4. Save the decorations file
            with open(decorations_filepath, 'w') as f:
                json.dump(decoration_set_data, f, indent=2)

            # 5. Export the assets
            os.makedirs(furnis_folder_path, exist_ok=True)
            num_exported = self._export_used_assets(decoration_set_data, furnis_folder_path)

            # 6. Update the current paths of the application
            self.current_structure_path = structure_filepath
            self.current_decoration_set_path = decorations_filepath

            # 7. Show success message
            messagebox.showinfo(
                "Save Complete",
                f"Project '{base_name}' saved successfully!\n\n"
                f"- Structure: {structure_filename}\n"
                f"- Decorations: {decorations_filename}\n"
                f"- Exported {num_exported} furniture assets to 'furnis' folder."
            )
            return True, base_name

        except Exception as e:
            messagebox.showerror("Save Error", f"An error occurred while saving the project: {e}")
            return False, None

    def load_catalog(self):
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
        data_path = os.path.join(self.assets_root, "4_final_furni_data", base_id, "data.json")
        if not os.path.exists(data_path):
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

    def get_image(self, base_id, relative_path):
        cache_key = f"{base_id}/{relative_path}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        full_path = os.path.join(self.assets_root, "4_final_furni_data", base_id, relative_path)
        if not os.path.exists(full_path):
            return None
        try:
            image = pygame.image.load(full_path).convert_alpha()
            self.image_cache[cache_key] = image
            return image
        except Exception as e:
            print(f"Error loading image {full_path}: {e}")
            return None

    def load_structure_only(self):
        self._init_tk_root()
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
        self._init_tk_root()
        if initial_dir is None:
            initial_dir = os.path.join(self.project_root, "rooms")
        os.makedirs(initial_dir, exist_ok=True)
        
        fp = filedialog.askopenfilename(
            parent=self.root,
            initialdir=initial_dir,
            title="Load Room Project File",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        self.root.update()
        if not fp: return None, None
        
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                file_data = json.load(f)

            # Case 1: User selected a decoration set file
            if "structure_id" in file_data:
                print("Loading project from decoration set file...")
                decoration_set_data = file_data
                structure_id = decoration_set_data.get("structure_id")
                if not structure_id:
                    raise ValueError("Decoration set file has an empty 'structure_id'.")
                
                # Look for the structure file in the same folder (primary method)
                structure_fp_relative = os.path.join(os.path.dirname(fp), f"{structure_id}_structure.json")
                # Fallback for old, non-project structure files
                structure_fp_standard = os.path.join(self.project_root, "rooms", "structures", f"{structure_id}.json")

                structure_fp = None
                if os.path.exists(structure_fp_relative):
                    structure_fp = structure_fp_relative
                    print(f"Found associated structure file: {structure_fp}")
                elif os.path.exists(structure_fp_standard):
                    structure_fp = structure_fp_standard
                    print(f"Found associated structure file (legacy path): {structure_fp}")

                if structure_fp:
                    with open(structure_fp, 'r', encoding='utf-8') as f:
                        structure_data = json.load(f)
                    self.current_structure_path = structure_fp
                else:
                    messagebox.showwarning("Structure Not Found", f"Could not find the structure file for ID '{structure_id}'.\nLoading decorations with a default empty structure.")
                    structure_data = {"name": "Missing Structure", "id": structure_id, "dimensions": {"width": 0, "depth": 0, "origin_x": 0, "origin_y": 0}, "renderAnchor": {"x": 0, "y": 0}, "tiles": [], "walls": []}
                    self.current_structure_path = None
                
                self.current_decoration_set_path = fp
                return structure_data, decoration_set_data

            # Case 2: User selected a structure file
            elif "tiles" in file_data and "dimensions" in file_data:
                print("Loading project from structure file...")
                structure_data = file_data
                structure_id = structure_data.get('id', 'unknown')

                # Look for the corresponding decoration set file in the same folder.
                decorations_fp_relative = os.path.join(os.path.dirname(fp), f"{structure_id}_decorations.json")
                
                if os.path.exists(decorations_fp_relative):
                    print(f"Found associated decorations file: {decorations_fp_relative}")
                    with open(decorations_fp_relative, 'r', encoding='utf-8') as f:
                        decoration_set_data = json.load(f)
                    self.current_decoration_set_path = decorations_fp_relative
                else:
                    # Fallback: create a new, empty decoration set if none is found.
                    print("No associated decorations file found. Creating a new empty set.")
                    decoration_set_data = {"decoration_set_name": f"{structure_data.get('name', 'New')} Decoration Set", "structure_id": structure_id, "decorations": []}
                    self.current_decoration_set_path = None
                
                self.current_structure_path = fp
                return structure_data, decoration_set_data
            
            # Case 3: Invalid file
            else:
                messagebox.showerror("Invalid File", "The selected JSON file is not a valid structure or decoration set file.")
                return None, None
                
        except Exception as e:
            messagebox.showerror("Load Error", f"An error occurred while loading the project: {e}")
            print(f"Error loading project file: {e}")
            return None, None