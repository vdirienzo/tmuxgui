"""
models.py - Modelos de datos y funciones auxiliares para tmux

Autor: Homero Thompson del Lago del Terror
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


def is_flatpak() -> bool:
    """Detecta si está corriendo en un sandbox de Flatpak."""
    return os.path.exists("/.flatpak-info")


def get_ssh_control_path(host: str, user: str, port: str) -> str:
    """Retorna el path para SSH ControlMaster socket."""
    socket_dir = Path.home() / ".ssh" / "gnome-tmux-sockets"
    socket_dir.mkdir(parents=True, exist_ok=True)
    return str(socket_dir / f"{user}@{host}-{port}")


@dataclass
class Window:
    """Representa una ventana de tmux."""

    index: int
    name: str
    active: bool


@dataclass
class Session:
    """Representa una sesión de tmux."""

    name: str
    window_count: int
    attached: bool
    windows: list[Window] = field(default_factory=list)
