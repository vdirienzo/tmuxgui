"""
loader.py - Carga recursiva de directorios remotos

Autor: Homero Thompson del Lago del Terror
"""

from typing import TYPE_CHECKING, Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

if TYPE_CHECKING:
    from ....clients import RemoteTmuxClient


def load_remote_directory_recursive(
    client: "RemoteTmuxClient",
    remote_path: str,
    list_box: Gtk.ListBox,
    expanded_dirs: set[str],
    depth: int,
    create_row: Callable,
    create_error_row: Callable,
):
    """
    Carga un directorio remoto recursivamente.

    Args:
        client: Cliente SSH remoto
        remote_path: Path remoto a cargar
        list_box: Widget donde agregar filas
        expanded_dirs: Set de directorios expandidos
        depth: Profundidad actual
        create_row: Función para crear RemoteFileTreeRow
        create_error_row: Función para crear fila de error
    """
    entries = client.list_dir(remote_path)
    if entries is None:
        if depth == 0:
            row = create_error_row("Error loading directory", depth)
            list_box.append(row)
        return

    for entry in entries:
        name = entry["name"]
        is_dir = entry["is_dir"]
        is_hidden = entry["is_hidden"]
        full_path = f"{remote_path.rstrip('/')}/{name}"

        is_expanded = full_path in expanded_dirs
        row = create_row(full_path, name, is_dir, depth, is_expanded, is_hidden)
        list_box.append(row)

        # Si es directorio expandido, cargar recursivamente
        if is_dir and is_expanded:
            load_remote_directory_recursive(
                client,
                full_path,
                list_box,
                expanded_dirs,
                depth + 1,
                create_row,
                create_error_row,
            )
