import json
import os
from tkinter import filedialog, Tk

class DataManager:
    def __init__(self, project_root):
        self.project_root = project_root
        self.root = Tk()
        self.root.withdraw()
        self.current_layout_path = None
        self.current_structure_path = None

    def load_structure_only(self):
        initial_dir = os.path.join(self.project_root, "rooms", "structures")
        os.makedirs(initial_dir, exist_ok=True)
        fp = filedialog.askopenfilename(parent=self.root, initialdir=initial_dir, title="Load Room Structure", filetypes=(("JSON files", "*.json"),))
        self.root.update()
        if not fp:
            return None
        try:
            with open(fp, 'r') as f:
                structure_data = json.load(f)
            self.current_structure_path = fp
            return structure_data
        except Exception as e:
            print(f"Error loading structure file: {e}")
            return None

    def load_layout_and_structure(self, initial_dir=None): # <--- PARÁMETRO AÑADIDO
        # Si no se especifica un directorio de inicio, se usa 'layouts' por defecto.
        if initial_dir is None:
            initial_dir = os.path.join(self.project_root, "rooms", "layouts")
        
        os.makedirs(initial_dir, exist_ok=True) # Se asegura de que la carpeta exista
        
        fp = filedialog.askopenfilename(parent=self.root, initialdir=initial_dir, title="Load Layout or Structure", filetypes=(("JSON files", "*.json"),))
        self.root.update()
        if not fp:
            return None, None

        try:
            with open(fp, 'r') as f:
                file_data = json.load(f)

            # --- LÓGICA INTELIGENTE PARA DETECTAR EL TIPO DE ARCHIVO ---
            # Caso 1: El archivo es un LAYOUT (contiene 'structure_id').
            if "structure_id" in file_data:
                layout_data = file_data
                structure_id = layout_data.get("structure_id")
                if not structure_id:
                     raise ValueError("Layout file has an empty 'structure_id'.")

                structure_fp = os.path.join(self.project_root, "rooms", "structures", f"{structure_id}.json")
                if not os.path.exists(structure_fp):
                    alt_structure_fp = os.path.join(os.path.dirname(fp), f"{structure_id}.json")
                    if os.path.exists(alt_structure_fp):
                        structure_fp = alt_structure_fp
                    else:
                        raise FileNotFoundError(f"Structure file '{structure_id}.json' not found for this layout.")
                
                with open(structure_fp, 'r') as f:
                    structure_data = json.load(f)
                
                self.current_layout_path = fp
                self.current_structure_path = structure_fp
                return structure_data, layout_data

            # Caso 2: El archivo parece ser una ESTRUCTURA (contiene 'tiles' y 'dimensions').
            elif "tiles" in file_data and "dimensions" in file_data:
                print("Loaded a structure file directly. Creating a new layout in memory.")
                structure_data = file_data
                
                new_layout = {
                    "layout_name": f"{structure_data.get('name', 'New')} Layout",
                    "structure_id": structure_data.get('id', 'unknown'),
                    "objects": []
                }
                
                self.current_structure_path = fp
                self.current_layout_path = None
                return structure_data, new_layout

            # Caso 3: El archivo no es un formato reconocido.
            else:
                print(f"Error: The selected file '{os.path.basename(fp)}' is not a valid layout or structure file.")
                return None, None

        except Exception as e:
            print(f"Error loading room: {e}")
            return None, None
    
    def save_layout(self, layout_data, save_as=False):
        fp = self.current_layout_path
        if not fp or save_as:
            initial_dir = os.path.join(self.project_root, "rooms", "layouts")
            os.makedirs(initial_dir, exist_ok=True)
            fp = filedialog.asksaveasfilename(parent=self.root, initialdir=initial_dir, title="Save Room Layout As", defaultextension=".json", filetypes=(("JSON files", "*.json"),))
            self.root.update()
            if not fp: return False, None
        
        try:
            with open(fp, 'w') as f:
                json.dump(layout_data, f, indent=2)
            self.current_layout_path = fp
            return True, os.path.basename(fp)
        except Exception as e:
            print(f"Error saving layout file: {e}")
            return False, None

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
            with open(fp, 'w') as f:
                json.dump(structure_data, f, indent=2)
            self.current_structure_path = fp
            return True
        except Exception as e:
            print(f"Error saving structure file: {e}")
            return False