# scripts/generate_catalog_structure.py
import os
import csv
import json
from collections import defaultdict

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_INPUT_PATH = os.path.join(PROJECT_ROOT, "assets", "habbo_items.csv")
JSON_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "assets", "catalog_structure.json")

# --- MAPA DE CATEGORÍAS ---
# Mapea las palabras clave del CSV (en minúsculas) a la tupla (Categoría Principal, Subcategoría)
# Esta es la parte más importante: define dónde va cada tipo de ítem.
CATEGORY_MAPPING = {
    # General & Core Furniture
    "seating": ("General & Core Furniture", "Seating"),
    "surfaces": ("General & Core Furniture", "Surfaces"),
    "beds": ("General & Core Furniture", "Beds & Rest"),
    "storage": ("General & Core Furniture", "Storage & Display"),
    "lighting": ("General & Core Furniture", "Lighting"),
    "core lines": ("General & Core Furniture", "Core Lines"),

    # Themed & Seasonal Collections
    "seasonal": ("Themed & Seasonal Collections", "Seasonal Events"),
    "cultural": ("Themed & Seasonal Collections", "Cultural & Geographic"),
    "fantasy & sci-fi": ("Themed & Seasonal Collections", "Fantasy & Sci-Fi"),
    "hobby & location": ("Themed & Seasonal Collections", "Hobby & Location-Based"),
    "exclusive (hc/vip)": ("Themed & Seasonal Collections", "Exclusive Memberships"),

    # Room Architecture & Construction
    "walls & floors": ("Room Architecture & Construction", "Walls, Floors & Carpets"),
    "windows & doors": ("Room Architecture & Construction", "Windows & Doors"),
    "structural pieces": ("Room Architecture & Construction", "Dividers & Structural"),
    "bc blocks": ("Room Architecture & Construction", "Builders Club (BC) Blocks"),

    # Interactive & Game Systems
    "wired": ("Interactive & Game Systems", "Wired Logic"),
    "game items": ("Interactive & Game Systems", "Game Mechanics"),
    "teleporters": ("Interactive & Game Systems", "Teleporters"),
    "crafting": ("Interactive & Game Systems", "Crafting & Enchanting"),

    # Rares, LTDs & Valuables
    "classic rares": ("Rares, LTDs & Valuables", "Classic Rares & Thrones"),
    "ltds": ("Rares, LTDs & Valuables", "Limited Edition Rares (LTDs)"),
    "currency": ("Rares, LTDs & Valuables", "Currency Furni"),
    "trophies": ("Rares, LTDs & Valuables", "Trophies & Prizes"),
    "collectibles": ("Rares, LTDs & Valuables", "Collectibles"),

    # Clothing & Accessories
    "wearables": ("Clothing & Accessories", "Wearable Items"),

    # Pets & Animals
    "pet gear": ("Pets & Animals", "Pet Accessories"),
    "animal decor": ("Pets & Animals", "Animal Figures"),

    # Promotional & Sponsored (ADS)
    "branded": ("Promotional & Sponsored (ADS)", "Branded Items"),

    # General Decor & Miscellaneous
    "plants": ("General Decor & Miscellaneous", "Plants & Nature"),
    "wall decor": ("General Decor & Miscellaneous", "Wall Decor"),
    "food & drink": ("General Decor & Miscellaneous", "Decorative Food & Drink"),
    "effects & tools": ("General Decor & Miscellaneous", "Special Effects & Tools"),
}

# --- ESTRUCTURA BASE DEL CATÁLOGO ---
# Esta es la plantilla que se llenará con los items.
CATALOG_SKELETON = {
    "catalogStructure": [
        {
            "name": "General & Core Furniture",
            "description": "Standard, versatile furniture for any room design, covering basic necessities and classic, non-themed lines.",
            "subcategories": [
                {"name": "Seating", "items": []}, {"name": "Surfaces", "items": []},
                {"name": "Beds & Rest", "items": []}, {"name": "Storage & Display", "items": []},
                {"name": "Lighting", "items": []}, {"name": "Core Lines", "items": []}
            ]
        },
        # ... (el resto de las categorías principales y subcategorías vacías)
        { "name": "Themed & Seasonal Collections", "description": "Collections for specific events, holidays, or campaigns with a strong, consistent aesthetic.", "subcategories": [ { "name": "Seasonal Events", "items": [] }, { "name": "Cultural & Geographic", "items": [] }, { "name": "Fantasy & Sci-Fi", "items": [] }, { "name": "Hobby & Location-Based", "items": [] }, { "name": "Exclusive Memberships", "items": [] } ] },
        { "name": "Room Architecture & Construction", "description": "Structural elements and modular pieces to build the fundamental layout of a room.", "subcategories": [ { "name": "Walls, Floors & Carpets", "items": [] }, { "name": "Windows & Doors", "items": [] }, { "name": "Dividers & Structural", "items": [] }, { "name": "Builders Club (BC) Blocks", "items": [] } ] },
        { "name": "Interactive & Game Systems", "description": "Functional items to create games, automation, and interactive experiences.", "subcategories": [ { "name": "Wired Logic", "items": [] }, { "name": "Game Mechanics", "items": [] }, { "name": "Teleporters", "items": [] }, { "name": "Crafting & Enchanting", "items": [] } ] },
        { "name": "Rares, LTDs & Valuables", "description": "High-value, often limited items sought-after by collectors.", "subcategories": [ { "name": "Classic Rares & Thrones", "items": [] }, { "name": "Limited Edition Rares (LTDs)", "items": [] }, { "name": "Currency Furni", "items": [] }, { "name": "Trophies & Prizes", "items": [] }, { "name": "Collectibles", "items": [] } ] },
        { "name": "Clothing & Accessories", "description": "Wearable items that customize an avatar. These are stored in the wardrobe, not placed in a room.", "subcategories": [ { "name": "Wearable Items", "items": [] } ] },
        { "name": "Pets & Animals", "description": "Items related to pets and decorative, non-playable animals.", "subcategories": [ { "name": "Pet Accessories", "items": [] }, { "name": "Animal Figures", "items": [] } ] },
        { "name": "Promotional & Sponsored (ADS)", "description": "Furniture released as part of advertising campaigns and collaborations with external brands.", "subcategories": [ { "name": "Branded Items", "items": [] } ] },
        { "name": "General Decor & Miscellaneous", "description": "A catch-all for smaller, decorative items and unique tools that don't fit into a specific group.", "subcategories": [ { "name": "Plants & Nature", "items": [] }, { "name": "Wall Decor", "items": [] }, { "name": "Decorative Food & Drink", "items": [] }, { "name": "Special Effects & Tools", "items": [] } ] }
    ]
}


def generate_catalog_structure():
    """Lee el CSV, mapea los items a las categorías y genera el archivo catalog_structure.json."""
    
    if not os.path.exists(CSV_INPUT_PATH):
        print(f"Error: No se encontró el archivo de entrada '{CSV_INPUT_PATH}'.")
        return

    print(f"Leyendo items desde '{CSV_INPUT_PATH}'...")

    # Usamos un diccionario para acceder fácilmente a las listas de items
    # La clave será (Categoría Principal, Subcategoría)
    category_items = defaultdict(list)
    unmapped_keywords = set()

    with open(CSV_INPUT_PATH, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        next(reader)  # Saltar la cabecera (name,category)
        
        for row in reader:
            if not row: continue # Saltar filas vacías
            item_name = row[0].strip()
            category_keywords_str = row[1].strip().lower()
            
            # Un item puede tener múltiples categorías separadas por coma
            keywords = [k.strip() for k in category_keywords_str.split(',')]
            
            for keyword in keywords:
                if keyword in CATEGORY_MAPPING:
                    target_category = CATEGORY_MAPPING[keyword]
                    category_items[target_category].append(item_name)
                else:
                    unmapped_keywords.add(keyword)

    # Ahora, llenamos el esqueleto del catálogo con los items que hemos recolectado
    for main_cat in CATALOG_SKELETON["catalogStructure"]:
        for sub_cat in main_cat["subcategories"]:
            key = (main_cat["name"], sub_cat["name"])
            if key in category_items:
                # Ordenar y eliminar duplicados
                unique_sorted_items = sorted(list(set(category_items[key])))
                sub_cat["items"] = unique_sorted_items

    # Guardar el resultado en el archivo JSON
    try:
        with open(JSON_OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(CATALOG_SKELETON, f, indent=2)
        print(f"\n¡Éxito! Se ha generado '{JSON_OUTPUT_PATH}' correctamente.")
        total_items = sum(len(v) for v in category_items.values())
        print(f"Se han procesado y asignado un total de {total_items} entradas de items.")
    except Exception as e:
        print(f"\nError al guardar el archivo JSON: {e}")

    # Informar sobre las palabras clave que no se pudieron mapear (muy útil para depurar)
    if unmapped_keywords:
        print("\n--- AVISO ---")
        print("Las siguientes palabras clave del CSV no se encontraron en CATEGORY_MAPPING y fueron ignoradas:")
        for keyword in sorted(list(unmapped_keywords)):
            print(f" - '{keyword}'")
        print("Puedes añadirlas al diccionario CATEGORY_MAPPING en el script para que se incluyan.")


if __name__ == "__main__":
    generate_catalog_structure()