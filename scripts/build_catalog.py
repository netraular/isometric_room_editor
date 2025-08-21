# scripts/build_catalog.py
import os
import json
import re

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# <-- CAMBIO: Ya no necesitamos furnidata.json -->
# FURNIDATA_PATH = os.path.join(PROJECT_ROOT, "assets", "furnidata.json")

CATALOG_STRUCT_PATH = os.path.join(PROJECT_ROOT, "assets", "catalog_structure.json")
CATALOG_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "assets", "catalog.json")
FURNIS_SUBDIR_IN_ASSETS = "furnis"
FURNIS_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "assets", FURNIS_SUBDIR_IN_ASSETS)
# -----------------------------------

def build_structured_catalog():
    """
    Construye el archivo catalog.json final.
    NO DEPENDE de furnidata.json. Usa el item_id como nombre.
    """
    if not os.path.exists(CATALOG_STRUCT_PATH):
        print(f"Error: No se encontró catalog_structure.json en {CATALOG_STRUCT_PATH}")
        return
    
    # <-- CAMBIO: Se eliminan las comprobaciones y la carga de furnidata.json -->
    
    if not os.path.exists(FURNIS_OUTPUT_DIR):
        print(f"Error: El directorio de furnis '{FURNIS_OUTPUT_DIR}' no existe.")
        print("Asegúrate de que el programa extractor de C# esté configurado para guardar en esa ruta.")
        return

    with open(CATALOG_STRUCT_PATH, 'r', encoding='utf-8') as f:
        catalog_structure = json.load(f)

    print(f"Construyendo catálogo desde '{CATALOG_STRUCT_PATH}'...")
    print(f"Verificando assets en '{FURNIS_OUTPUT_DIR}'...")
    
    final_catalog = {"categories": []}
    items_processed = 0
    items_skipped = 0

    for main_cat_data in catalog_structure.get("catalogStructure", []):
        final_main_cat = { "name": main_cat_data.get("name"), "description": main_cat_data.get("description"), "subcategories": [] }
        for sub_cat_data in main_cat_data.get("subcategories", []):
            final_sub_cat = { "name": sub_cat_data.get("name"), "items": [] }
            
            for item_id in sub_cat_data.get("items", []):
                
                # Lógica para parsear el ID (se mantiene igual)
                match = re.match(r'^(.*?)_(\d+)$', item_id)
                if match:
                    base_id, color_id = match.groups()
                else:
                    base_id = item_id
                    color_id = "0"

                # <-- INICIO DEL CAMBIO PRINCIPAL -->
                # 1. Usar el ID del ítem como su nombre. No se necesita furnidata.json.
                item_name = item_id
                # <-- FIN DEL CAMBIO PRINCIPAL -->

                # 2. Verificar que el furni fue extraído y existe la carpeta
                furni_dir_absolute = os.path.join(FURNIS_OUTPUT_DIR, base_id)
                if not os.path.isdir(furni_dir_absolute):
                    print(f"  ! Aviso: No se encontró la carpeta para '{base_id}' en '{FURNIS_OUTPUT_DIR}'. Omitiendo ítem '{item_id}'.")
                    items_skipped += 1
                    continue

                # 3. Buscar el archivo del icono
                icon_filename_with_color = f"{base_id}_icon_{color_id}.png"
                icon_filename_no_color = f"{base_id}_icon.png"
                
                final_icon_path_relative = ""
                if os.path.exists(os.path.join(furni_dir_absolute, icon_filename_with_color)):
                    final_icon_path_relative = os.path.join(FURNIS_SUBDIR_IN_ASSETS, base_id, icon_filename_with_color)
                elif os.path.exists(os.path.join(furni_dir_absolute, icon_filename_no_color)):
                    final_icon_path_relative = os.path.join(FURNIS_SUBDIR_IN_ASSETS, base_id, icon_filename_no_color)
                
                if not final_icon_path_relative:
                    print(f"  ! Aviso: Icono no encontrado para '{item_id}' dentro de '{furni_dir_absolute}'. Omitiendo.")
                    items_skipped += 1
                    continue
                
                # 4. Construir el objeto final del ítem
                final_sub_cat["items"].append({
                    "id": item_id,
                    "name": item_name, # Ahora es igual a item_id
                    "base_id": base_id,
                    "color_id": color_id,
                    "icon_path": final_icon_path_relative.replace(os.sep, '/')
                })
                items_processed += 1
            
            final_main_cat["subcategories"].append(final_sub_cat)
        
        final_catalog["categories"].append(final_main_cat)

    with open(CATALOG_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_catalog, f, indent=2)

    print(f"\n¡Catálogo estructurado construido! Guardado en {CATALOG_OUTPUT_FILE}")
    print(f"  - Items procesados correctamente: {items_processed}")
    print(f"  - Items omitidos (ver avisos):   {items_skipped}")


if __name__ == "__main__":
    build_structured_catalog()