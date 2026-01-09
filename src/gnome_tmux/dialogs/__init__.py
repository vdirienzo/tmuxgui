"""
dialogs - Diálogos de la aplicación

Autor: Homero Thompson del Lago del Terror
"""

from .help_dialog import show_help_dialog, show_theme_dialog
from .remote_connect_dialogs import confirm_delete_host, show_connect_to_host_dialog
from .remote_host_dialogs import show_add_host_dialog, show_edit_host_dialog
from .session_create_dialogs import show_create_local_dialog, show_new_session_menu
from .session_edit_dialogs import (
    show_delete_session_dialog,
    show_new_window_dialog,
    show_rename_session_dialog,
    show_rename_window_dialog,
)

__all__ = [
    # Session dialogs
    "show_new_session_menu",
    "show_create_local_dialog",
    "show_rename_session_dialog",
    "show_rename_window_dialog",
    "show_new_window_dialog",
    "show_delete_session_dialog",
    # Remote dialogs
    "show_add_host_dialog",
    "show_edit_host_dialog",
    "show_connect_to_host_dialog",
    "confirm_delete_host",
    # Help dialogs
    "show_help_dialog",
    "show_theme_dialog",
]
