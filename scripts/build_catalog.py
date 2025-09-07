# scripts/build_catalog.py
import os
import json

# --- PATH CONFIGURATION ---
# The root of the 'isometric_room_editor' project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to the sibling pipeline project
PIPELINE_PROJECT_ROOT = os.path.join(PROJECT_ROOT, "..", "habbo-furni-asset-pipeline")
FINAL_DATA_DIR = os.path.join(PIPELINE_PROJECT_ROOT, "assets", "4_final_furni_data")

# Input and Output files for this script
CATEGORIES_INPUT_FILE = os.path.join(PROJECT_ROOT, "assets", "categories.txt")
CATALOG_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "assets", "catalog.json")

def build_catalog_from_assets():
    """
    Builds the final catalog.json directly from the asset pipeline's final data.
    It reads a list of categories and then scans all furni data.json files,
    assigning each item to its respective category.
    """
    # 1. Validate that all necessary files and directories exist
    if not os.path.exists(FINAL_DATA_DIR):
        print(f"Error: The final data directory '{FINAL_DATA_DIR}' does not exist.")
        print("Please ensure the pipeline project is a sibling and has been run.")
        return
    if not os.path.exists(CATEGORIES_INPUT_FILE):
        print(f"Error: Categories definition file not found at '{CATEGORIES_INPUT_FILE}'")
        return

    # 2. Read the category definitions and prepare the catalog structure
    print(f"Reading category definitions from '{CATEGORIES_INPUT_FILE}'...")
    # Use 'utf-8-sig' to automatically handle the BOM character if it exists
    with open(CATEGORIES_INPUT_FILE, 'r', encoding='utf-8-sig') as f:
        category_keys = [line.strip() for line in f if line.strip()]

    # Create a skeleton for the final catalog
    final_catalog = {"categories": []}
    # Create a quick-access map to avoid searching the list repeatedly
    category_map = {}

    for key in category_keys:
        # Format the name nicely (e.g., "wall_decoration" -> "Wall Decoration")
        pretty_name = key.replace('_', ' ').title()
        category_obj = {
            "name": pretty_name,
            "description": f"A collection of {pretty_name} items.", # Generic description
            "items": []
        }
        final_catalog["categories"].append(category_obj)
        category_map[key] = category_obj

    # Add a special category for items whose category isn't in our list
    uncategorized_obj = {
        "name": "Uncategorized",
        "description": "Items that could not be automatically categorized.",
        "items": []
    }
    final_catalog["categories"].append(uncategorized_obj)


    # 3. Scan the final assets directory and populate the catalog
    print(f"Scanning asset data in '{FINAL_DATA_DIR}'...")
    items_processed = 0
    items_skipped = 0
    
    # Each subdirectory is a base_id
    for base_id in os.listdir(FINAL_DATA_DIR):
        furni_dir_path = os.path.join(FINAL_DATA_DIR, base_id)
        if not os.path.isdir(furni_dir_path):
            continue

        data_json_path = os.path.join(furni_dir_path, "data.json")
        if not os.path.exists(data_json_path):
            continue

        try:
            with open(data_json_path, 'r', encoding='utf-8') as f:
                furni_data = json.load(f)

            item_category_key = furni_data.get("category", "other").lower()

            # Iterate through all color/state variants of the item
            for variant_id, variant_data in furni_data.get("variants", {}).items():
                
                # We need an icon to show it in the editor
                if not variant_data.get("icon_path"):
                    items_skipped += 1
                    continue

                # Construct the item object for the catalog
                catalog_item = {
                    "id": variant_data.get("id", f"{base_id}_{variant_id}"),
                    "name": variant_data.get("name", base_id),
                    "base_id": base_id,
                    "variant_id": variant_id,
                    "icon_path": variant_data.get("icon_path")
                }
                
                # Add the item to the correct category
                if item_category_key in category_map:
                    category_map[item_category_key]["items"].append(catalog_item)
                else:
                    # If the category from data.json isn't in our list, put it in "Uncategorized"
                    uncategorized_obj["items"].append(catalog_item)
                
                items_processed += 1

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not process {data_json_path}. Error: {e}")
            items_skipped += 1
            continue
    
    # 4. Clean up and save the final catalog
    
    # Remove categories that have no items, except for the "Uncategorized" one if it's also empty
    final_catalog["categories"] = [cat for cat in final_catalog["categories"] if cat["items"]]
    
    # Sort items within each category alphabetically by name
    for category in final_catalog["categories"]:
        category["items"].sort(key=lambda x: x['name'])

    with open(CATALOG_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_catalog, f, indent=2)

    print(f"\nCatalog built successfully! Saved to {CATALOG_OUTPUT_FILE}")
    print(f"  - Items added to catalog: {items_processed}")
    print(f"  - Items skipped (missing data or icon): {items_skipped}")


if __name__ == "__main__":
    build_catalog_from_assets()