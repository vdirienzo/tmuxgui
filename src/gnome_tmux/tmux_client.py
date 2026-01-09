"""
tmux_client.py - Alias de compatibilidad (DEPRECATED)

Este archivo existe para mantener compatibilidad con imports existentes.
Usar directamente: from .clients import TmuxClient, RemoteTmuxClient

Autor: Homero Thompson del Lago del Terror
"""

# Re-exportar desde el nuevo módulo para compatibilidad
from .clients import (
    RemoteTmuxClient,
    Session,
    TmuxClient,
    Window,
    get_ssh_control_path,
    is_flatpak,
)

__all__ = [
    "TmuxClient",
    "RemoteTmuxClient",
    "Session",
    "Window",
    "is_flatpak",
    "get_ssh_control_path",
]
