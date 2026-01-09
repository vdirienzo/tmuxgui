"""
remote - Componentes para manejo de archivos remotos

Autor: Homero Thompson del Lago del Terror
"""

from .operations import RemoteFileOperations
from .rows import RemoteFileTreeRow, RemoteSearchResultRow

__all__ = ["RemoteFileTreeRow", "RemoteSearchResultRow", "RemoteFileOperations"]
