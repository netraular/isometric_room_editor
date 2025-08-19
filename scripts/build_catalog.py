import os
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FURNIDATA_PATH = os.path.join(PROJECT_ROOT, "assets", "furnidata.json")
CATALOG_STRUCT_PATH = os.path.join(PROJECT_ROOT, "assets", "catalog_structure.json")
CATALOG_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "assets", "catalog.json")
ICONS_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")

def build_structured_catalog():
    if not os.path.exists(CATALOG_STRUCT_PATH):
        print(f"Error: No se encontró catalog_structure.json en {CATALOG_STRUCT_PATH}")
        return
    if not os.path.exists(FURNIDATA_PATH):
        print(f"Error: No se encontró furnidata.json en {FURNIDATA_PATH}")
        return

    with open(CATALOG_STRUCT_PATH, 'r', encoding='utf-8') as f:
        catalog_structure = json.load(f)
    with open(FURNIDATA_PATH, 'r', encoding='utf-8') as f:
        furnidata = json.load(f)

    print("Construyendo catálogo estructurado desde catalog_structure.json...")
    
    final_catalog = {"categories": []}
    items_processed = 0

    for main_cat_data in catalog_structure.get("catalogStructure", []):
        final_main_cat = {
            "name": main_cat_data.get("name"),
            "description": main_cat_data.get("description"),
            "subcategories": []
        }
        
        for sub_cat_data in main_cat_data.get("subcategories", []):
            final_sub_cat = {
                "name": sub_cat_data.get("name"),
                "items": []
            }
            
            for item_id in sub_cat_data.get("items", []):
                match = re.match(r'^(.*?)_(\d+)$', item_id)
                if not match:
                    print(f"  ! Aviso: Formato de ID incorrecto '{item_id}'. Omitiendo.")
                    continue
                
                base_id, color_id = match.groups()

                item_metadata = furnidata.get(base_id)
                if not item_metadata:
                    print(f"  ! Aviso: No hay metadatos para '{base_id}' en furnidata.json. Omitiendo '{item_id}'.")
                    continue
                
                item_name = item_metadata.get("name", base_id)
                
                icon_filename_with_color = f"{base_id}_{color_id}_icon.png"
                icon_filename_without_color = f"{base_id}_icon.png"
                icon_path = ""

                if os.path.exists(os.path.join(ICONS_DIR, icon_filename_with_color)):
                    icon_path = f"icons/{icon_filename_with_color}"
                elif color_id == "0" and os.path.exists(os.path.join(ICONS_DIR, icon_filename_without_color)):
                    icon_path = f"icons/{icon_filename_without_color}"
                
                if not icon_path:
                    print(f"  ! Aviso: Icono no encontrado para '{item_id}'. Omitiendo.")
                    continue

                final_sub_cat["items"].append({
                    "id": item_id,
                    "name": item_name,
                    "base_id": base_id,
                    "color_id": color_id,
                    "icon_path": icon_path
                })
                items_processed += 1
            
            final_main_cat["subcategories"].append(final_sub_cat)
        
        final_catalog["categories"].append(final_main_cat)

    with open(CATALOG_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_catalog, f, indent=2)

    print(f"\n¡Catálogo estructurado construido! Guardado en {CATALOG_OUTPUT_FILE}")
    print(f"Total de items procesados: {items_processed}")


if __name__ == "__main__":
    build_structured_catalog()