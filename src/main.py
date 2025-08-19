import os
from app import App

if __name__ == "__main__":
    # Determina la ruta raíz del proyecto (la carpeta que contiene 'src')
    # __file__ es la ruta a este script (src/main.py)
    # os.path.dirname(...) nos da la carpeta 'src'
    # un segundo os.path.dirname(...) nos sube a la raíz del proyecto
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    editor_app = App(project_root=PROJECT_ROOT)
    editor_app.run()