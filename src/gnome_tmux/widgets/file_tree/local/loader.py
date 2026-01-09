"""
loader.py - Carga recursiva de directorios locales

Autor: Homero Thompson del Lago del Terror
"""

from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk


def load_directory_recursive(
    root_path: Path,
    list_box: Gtk.ListBox,
    expanded_dirs: set[str],
    depth: int,
    create_row: Callable,
    create_error_row: Callable,
):
    """
    Carga un directorio recursivamente en el ListBox.

    Args:
        root_path: Directorio a cargar
        list_box: Widget donde agregar las filas
        expanded_dirs: Set de directorios expandidos
        depth: Profundidad actual
        create_row: Función para crear FileTreeRow
        create_error_row: Función para crear fila de error
    """
    try:
        entries = sorted(root_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

        for entry in entries:
            # Saltar archivos/carpetas ocultos
            if entry.name.startswith("."):
                continue

            # Crear fila
            is_expanded = str(entry) in expanded_dirs
            row = create_row(entry, depth, is_expanded)
            list_box.append(row)

            # Si es directorio expandido, cargar recursivamente
            if entry.is_dir() and is_expanded:
                load_directory_recursive(
                    entry,
                    list_box,
                    expanded_dirs,
                    depth + 1,
                    create_row,
                    create_error_row,
                )

    except PermissionError:
        if depth == 0:
            row = create_error_row("Permission denied", depth)
            list_box.append(row)
