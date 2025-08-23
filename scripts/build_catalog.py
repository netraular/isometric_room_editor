# scripts/build_catalog.py
import os
import json
import re

# --- PATH CONFIGURATION ---
# The root of the 'isometric_room_editor' project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- MODIFIED: Path to the sibling pipeline project ---
PIPELINE_PROJECT_ROOT = os.path.join(PROJECT_ROOT, "..", "habbo-furni-asset-pipeline")
FINAL_DATA_DIR = os.path.join(PIPELINE_PROJECT_ROOT, "assets", "4_final_furni_data")

# These paths are relative to the 'isometric_room_editor' project
CATALOG_STRUCT_PATH = os.path.join(PROJECT_ROOT, "assets", "catalog_structure.json")
CATALOG_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "assets", "catalog.json")

def build_structured_catalog():
    """
    Builds the final catalog.json file.
    It uses the 'data.json' files from the pipeline's '4_final_furni_data'
    directory to get names and filter items.
    """
    if not os.path.exists(CATALOG_STRUCT_PATH):
        print(f"Error: catalog_structure.json not found at {CATALOG_STRUCT_PATH}")
        return
    
    if not os.path.exists(FINAL_DATA_DIR):
        print(f"Error: The final data directory '{FINAL_DATA_DIR}' does not exist.")
        print("Please ensure the pipeline project is a sibling to this project and has been run completely.")
        return

    with open(CATALOG_STRUCT_PATH, 'r', encoding='utf-8') as f:
        catalog_structure = json.load(f)

    print(f"Building catalog from '{CATALOG_STRUCT_PATH}'...")
    print(f"Verifying final data in '{FINAL_DATA_DIR}'...")
    
    final_catalog = {"categories": []}
    items_processed = 0
    items_skipped = 0

    for main_cat_data in catalog_structure.get("catalogStructure", []):
        final_main_cat = { "name": main_cat_data.get("name"), "description": main_cat_data.get("description"), "subcategories": [] }
        for sub_cat_data in main_cat_data.get("subcategories", []):
            final_sub_cat = { "name": sub_cat_data.get("name"), "items": [] }
            
            for item_id in sub_cat_data.get("items", []):
                match = re.match(r'^(.*?)_(\d+)$', item_id)
                base_id, color_id = match.groups() if match else (item_id, "0")

                final_data_path = os.path.join(FINAL_DATA_DIR, base_id, "data.json")
                if not os.path.exists(final_data_path):
                    items_skipped += 1
                    continue
                
                try:
                    with open(final_data_path, 'r', encoding='utf-8') as f:
                        final_data = json.load(f)
                    
                    variant_data = final_data.get("variants", {}).get(color_id)
                    if not variant_data:
                        items_skipped += 1
                        continue

                    # The catalog item name is the specific variant name
                    item_name = variant_data.get("name", item_id)
                    
                    # The icon path is relative to the furni package, which is what we need
                    final_icon_path_relative = variant_data.get("icon_path", "")

                    if not final_icon_path_relative:
                        items_skipped += 1
                        continue
                        
                except (json.JSONDecodeError, KeyError):
                    items_skipped += 1
                    continue
                
                final_sub_cat["items"].append({
                    "id": item_id, 
                    "name": item_name, 
                    "base_id": base_id,
                    "color_id": color_id, 
                    "icon_path": final_icon_path_relative
                })
                items_processed += 1
            
            if final_sub_cat["items"]:
                final_main_cat["subcategories"].append(final_sub_cat)
        
        if final_main_cat["subcategories"]:
            final_catalog["categories"].append(final_main_cat)

    with open(CATALOG_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_catalog, f, indent=2)

    print(f"\nStructured catalog built successfully! Saved to {CATALOG_OUTPUT_FILE}")
    print(f"  - Items added to catalog: {items_processed}")
    print(f"  - Items skipped (not found in final data): {items_skipped}")

if __name__ == "__main__":
    build_structured_catalog()