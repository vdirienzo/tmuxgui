"""
file_tree - Package para el widget de árbol de archivos

Autor: Homero Thompson del Lago del Terror

Este package contiene los componentes modulares del FileTree:
- local/: Componentes para archivos locales
- remote/: Componentes para archivos remotos via SSH
- ui/: Componentes de interfaz compartidos
"""

from .core import FileTree
from .local import FileTreeRow, SearchResultRow
from .remote import RemoteFileTreeRow, RemoteSearchResultRow

__all__ = [
    "FileTree",
    "FileTreeRow",
    "SearchResultRow",
    "RemoteFileTreeRow",
    "RemoteSearchResultRow",
]
