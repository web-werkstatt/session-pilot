"""
Zentralisierte Projektpfad-Auflösung - eliminiert Duplikate in app.py und document_routes.py
"""
import os
from config import PROJECTS_DIR

# Standard Sub-Projekt-Ordner
SUB_PROJECT_DIRS = [
    '', 'apps/', 'packages/', 'services/', 'modules/',
    'libs/', 'plugins/', 'themes/', 'sites/',
]


def resolve_project_path(name):
    """Löst Projektpfad auf inkl. Sub-Projekte und Bindestrich/Underscore Fallback"""
    if '/' in name:
        parts = name.split('/', 1)
        parent = parts[0]
        sub = parts[1]
        for sub_dir in SUB_PROJECT_DIRS:
            p = os.path.join(PROJECTS_DIR, parent, sub_dir + sub)
            if os.path.isdir(p):
                return p
        return None

    p = os.path.join(PROJECTS_DIR, name)
    if os.path.isdir(p):
        return p
    # Fallback: Bindestrich <-> Underscore
    alt = name.replace('-', '_') if '-' in name else name.replace('_', '-')
    p = os.path.join(PROJECTS_DIR, alt)
    return p if os.path.isdir(p) else None
