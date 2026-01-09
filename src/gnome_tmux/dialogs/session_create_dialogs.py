"""
session_create_dialogs.py - Diálogos para crear sesiones

Autor: Homero Thompson del Lago del Terror
"""

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


def show_create_local_dialog(
    parent: Adw.Window,
    on_create: Callable[[str], None],
    show_toast: Callable[[str], None],
) -> None:
    """
    Muestra diálogo para crear sesión local.

    Args:
        parent: Ventana padre del diálogo
        on_create: Callback con el nombre de la sesión a crear
        show_toast: Función para mostrar mensajes toast
    """
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading="New Local Session",
        body="Enter a name for the new tmux session:",
    )

    entry = Gtk.Entry()
    entry.set_placeholder_text("session-name")
    entry.connect("activate", lambda e: [dialog.set_focus(None), dialog.response("create")])
    dialog.set_extra_child(entry)

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("create", "Create")
    dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("create")

    def on_response(dlg, response):
        dlg.set_focus(None)
        if response == "create":
            name = entry.get_text().strip()
            if name:
                on_create(name)
            else:
                show_toast("Session name cannot be empty")

    dialog.connect("response", on_response)
    dialog.present()
    entry.grab_focus()


def show_new_session_menu(
    parent: Adw.Window,
    callbacks: dict,
) -> Adw.Window:
    """
    Muestra el menú principal de nueva sesión (local/remota).

    Args:
        parent: Ventana padre
        callbacks: Dict con callbacks necesarios:
            - on_create_local: Callback para crear local
            - on_add_host: Callback para agregar host
            - on_edit_host: Callback para editar host
            - on_delete_host: Callback para eliminar host
            - on_connect_host: Callback para conectar a host
            - get_hosts: Función para obtener lista de hosts
            - show_toast: Función para mostrar toasts

    Returns:
        El diálogo creado
    """
    from ..remote_hosts import remote_hosts_manager

    dialog = Adw.Window(transient_for=parent)
    dialog.set_title("Sessions")
    dialog.set_default_size(420, 500)
    dialog.set_modal(True)

    toolbar_view = Adw.ToolbarView()
    dialog.set_content(toolbar_view)

    header = Adw.HeaderBar()
    header.set_show_end_title_buttons(True)
    toolbar_view.add_top_bar(header)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)

    # Grupo: Sesión Local
    local_group = Adw.PreferencesGroup(title="Local Session")

    local_row = Adw.ActionRow(
        title="Create local session", subtitle="Start a new tmux session on this machine"
    )
    local_row.set_activatable(True)
    local_icon = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
    local_row.add_prefix(local_icon)
    arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
    local_row.add_suffix(arrow)
    local_row.connect("activated", lambda r: callbacks["on_create_local"](dialog))
    local_group.add(local_row)

    content.append(local_group)

    # Grupo: Conexiones Remotas
    saved_hosts = remote_hosts_manager.get_hosts()
    remote_group = Adw.PreferencesGroup(title="Remote Connections")

    if saved_hosts:
        for host in saved_hosts:
            port_suffix = f":{host.port}" if host.port != "22" else ""
            host_row = Adw.ActionRow(
                title=host.name, subtitle=f"{host.user}@{host.host}{port_suffix}"
            )
            host_row.set_activatable(True)

            server_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
            host_row.add_prefix(server_icon)

            edit_btn = Gtk.Button()
            edit_btn.set_icon_name("document-edit-symbolic")
            edit_btn.set_valign(Gtk.Align.CENTER)
            edit_btn.add_css_class("flat")
            edit_btn.set_tooltip_text("Edit connection")
            edit_btn.connect("clicked", lambda b, h=host: callbacks["on_edit_host"](dialog, h))
            host_row.add_suffix(edit_btn)

            delete_btn = Gtk.Button()
            delete_btn.set_icon_name("user-trash-symbolic")
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")
            delete_btn.add_css_class("error")
            delete_btn.set_tooltip_text("Delete connection")
            delete_btn.connect("clicked", lambda b, h=host: callbacks["on_delete_host"](dialog, h))
            host_row.add_suffix(delete_btn)

            connect_arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
            host_row.add_suffix(connect_arrow)

            host_row.connect("activated", lambda r, h=host: callbacks["on_connect_host"](dialog, h))
            remote_group.add(host_row)
    else:
        empty_row = Adw.ActionRow(
            title="No saved connections", subtitle="Add a remote connection to get started"
        )
        empty_row.set_sensitive(False)
        empty_icon = Gtk.Image.new_from_icon_name("network-offline-symbolic")
        empty_icon.add_css_class("dim-label")
        empty_row.add_prefix(empty_icon)
        remote_group.add(empty_row)

    add_row = Adw.ActionRow(title="Add new connection", subtitle="Configure a new remote server")
    add_row.set_activatable(True)
    add_row.add_css_class("accent")
    add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
    add_row.add_prefix(add_icon)
    add_arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
    add_row.add_suffix(add_arrow)
    add_row.connect("activated", lambda r: callbacks["on_add_host"](dialog))
    remote_group.add(add_row)

    content.append(remote_group)

    scrolled.set_child(content)
    toolbar_view.set_content(scrolled)

    dialog.present()
    return dialog
