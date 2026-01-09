"""
clients - Clientes tmux local y remoto

Autor: Homero Thompson del Lago del Terror
"""

from .local import TmuxClient
from .models import Session, Window, get_ssh_control_path, is_flatpak
from .parsers import (
    SESSION_FORMAT,
    WINDOW_FORMAT,
    parse_sessions_output,
    parse_windows_output,
)
from .remote import RemoteTmuxClient

__all__ = [
    "TmuxClient",
    "RemoteTmuxClient",
    "Session",
    "Window",
    "is_flatpak",
    "get_ssh_control_path",
    "SESSION_FORMAT",
    "WINDOW_FORMAT",
    "parse_sessions_output",
    "parse_windows_output",
]
