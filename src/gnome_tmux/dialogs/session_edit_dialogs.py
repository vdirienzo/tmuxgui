"""
session_dialogs.py - Diálogos para gestión de sesiones locales

Autor: Homero Thompson del Lago del Terror
"""

from typing import TYPE_CHECKING, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    pass


def show_rename_session_dialog(
    parent: Adw.Window,
    session_name: str,
    on_rename: Callable[[str, str], bool],
    show_toast: Callable[[str], None],
) -> None:
    """
    Muestra diálogo para renombrar sesión.

    Args:
        parent: Ventana padre
        session_name: Nombre actual de la sesión
        on_rename: Callback (old_name, new_name) -> success
        show_toast: Función para mostrar mensajes
    """
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading="Rename Session",
        body=f"Enter new name for session '{session_name}':",
    )

    entry = Gtk.Entry()
    entry.set_text(session_name)
    entry.connect("activate", lambda e: [dialog.set_focus(None), dialog.response("rename")])
    dialog.set_extra_child(entry)

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("rename", "Rename")
    dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("rename")

    def on_response(dlg, response):
        dlg.set_focus(None)
        dlg.close()
        if response == "rename":
            new_name = entry.get_text().strip()
            if new_name and new_name != session_name:
                if not on_rename(session_name, new_name):
                    show_toast("Failed to rename session")

    dialog.connect("response", on_response)
    dialog.present()


def show_rename_window_dialog(
    parent: Adw.Window,
    session_name: str,
    window_index: int,
    current_name: str,
    on_rename: Callable[[str, int, str], bool],
    show_toast: Callable[[str], None],
) -> None:
    """
    Muestra diálogo para renombrar ventana.

    Args:
        parent: Ventana padre
        session_name: Nombre de la sesión
        window_index: Índice de la ventana
        current_name: Nombre actual de la ventana
        on_rename: Callback (session, index, new_name) -> success
        show_toast: Función para mostrar mensajes
    """
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading="Rename Window",
        body=f"Enter new name for window '{current_name}':",
    )

    entry = Gtk.Entry()
    entry.set_text(current_name)
    entry.connect("activate", lambda e: [dialog.set_focus(None), dialog.response("rename")])
    dialog.set_extra_child(entry)

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("rename", "Rename")
    dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("rename")

    def on_response(dlg, response):
        dlg.set_focus(None)
        dlg.close()
        if response == "rename":
            new_name = entry.get_text().strip()
            if new_name:
                if not on_rename(session_name, window_index, new_name):
                    show_toast("Failed to rename window")

    dialog.connect("response", on_response)
    dialog.present()


def show_new_window_dialog(
    parent: Adw.Window,
    session_name: str,
    on_create: Callable[[str, str | None], bool],
    show_toast: Callable[[str], None],
) -> None:
    """
    Muestra diálogo para crear nueva ventana.

    Args:
        parent: Ventana padre
        session_name: Nombre de la sesión
        on_create: Callback (session_name, window_name) -> success
        show_toast: Función para mostrar mensajes
    """
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading="New Window",
        body=f"Enter a name for the new window in '{session_name}':",
    )

    entry = Gtk.Entry()
    entry.set_placeholder_text("window-name (optional)")
    entry.connect("activate", lambda e: [dialog.set_focus(None), dialog.response("create")])
    dialog.set_extra_child(entry)

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("create", "Create")
    dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("create")

    def on_response(dlg, response):
        dlg.set_focus(None)
        dlg.close()
        if response == "create":
            name = entry.get_text().strip() or None
            if not on_create(session_name, name):
                show_toast("Failed to create window")

    dialog.connect("response", on_response)
    dialog.present()


def show_delete_session_dialog(
    parent: Adw.Window,
    session_name: str,
    on_delete: Callable[[str], bool],
    show_toast: Callable[[str], None],
) -> None:
    """
    Muestra diálogo de confirmación para eliminar sesión.

    Args:
        parent: Ventana padre
        session_name: Nombre de la sesión a eliminar
        on_delete: Callback (session_name) -> success
        show_toast: Función para mostrar mensajes
    """
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading="Delete Session?",
        body=f"Are you sure you want to delete '{session_name}'?\n"
        "This will terminate all processes in the session.",
    )

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("delete", "Delete")
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

    def on_response(dlg, response):
        dlg.close()
        if response == "delete":
            if not on_delete(session_name):
                show_toast("Failed to delete session")

    dialog.connect("response", on_response)
    dialog.present()


