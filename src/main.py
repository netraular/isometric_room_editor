# src/main.py
import os
from app import App

if __name__ == "__main__":
    # Determine the project root (the folder containing 'src')
    # __file__ is the path to this script (src/main.py)
    # os.path.dirname(...) gives us the 'src' folder
    # a second os.path.dirname(...) moves up to the project root
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # --- NEW: Define the path to the sibling pipeline project's assets ---
    # This robustly finds the sibling directory.
    ASSETS_ROOT = os.path.join(os.path.dirname(PROJECT_ROOT), "habbo-furni-asset-pipeline", "assets")
    
    if not os.path.isdir(ASSETS_ROOT):
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: Could not find the pipeline's assets directory.  !!!")
        print(f"!!! Searched at: {ASSETS_ROOT} !!!")
        print("!!! Please ensure both projects are in the same parent dir. !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        exit()

    # --- MODIFIED: Pass both paths to the App ---
    editor_app = App(project_root=PROJECT_ROOT, assets_root=ASSETS_ROOT)
    editor_app.run()