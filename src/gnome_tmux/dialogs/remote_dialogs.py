"""
remote_dialogs.py - Diálogos para gestión de conexiones remotas SSH

Autor: Homero Thompson del Lago del Terror
"""

from typing import TYPE_CHECKING, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from ..remote_hosts import RemoteHost


def show_add_host_dialog(
    parent: Adw.Window,
    on_save: Callable[["RemoteHost"], None],
    show_toast: Callable[[str], None],
    on_complete: Callable[[], None] | None = None,
) -> None:
    """
    Muestra diálogo para agregar nueva conexión remota.

    Args:
        parent: Ventana padre
        on_save: Callback con el nuevo RemoteHost
        show_toast: Función para mostrar mensajes
        on_complete: Callback opcional al completar
    """
    from datetime import datetime, timezone

    from ..remote_hosts import RemoteHost

    dialog = Adw.Window(transient_for=parent)
    dialog.set_title("Add Connection")
    dialog.set_default_size(380, 320)
    dialog.set_modal(True)

    toolbar_view = Adw.ToolbarView()
    dialog.set_content(toolbar_view)

    header = Adw.HeaderBar()
    header.set_show_end_title_buttons(False)

    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.connect("clicked", lambda b: [dialog.set_focus(None), dialog.close()])
    header.pack_start(cancel_btn)

    save_btn = Gtk.Button(label="Save")
    save_btn.add_css_class("suggested-action")
    header.pack_end(save_btn)

    toolbar_view.add_top_bar(header)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)

    group = Adw.PreferencesGroup()

    name_entry = Adw.EntryRow(title="Name")
    name_entry.set_text("")
    group.add(name_entry)

    host_entry = Adw.EntryRow(title="Host")
    host_entry.set_text("")
    group.add(host_entry)

    user_entry = Adw.EntryRow(title="User")
    user_entry.set_text("")
    group.add(user_entry)

    port_entry = Adw.EntryRow(title="Port")
    port_entry.set_text("22")
    group.add(port_entry)

    content.append(group)
    toolbar_view.set_content(content)

    def on_save_clicked(btn):
        name = name_entry.get_text().strip()
        host = host_entry.get_text().strip()
        user = user_entry.get_text().strip()
        port = port_entry.get_text().strip() or "22"

        if not name or not host or not user:
            show_toast("Name, host and user are required")
            return

        new_host = RemoteHost(
            name=name,
            host=host,
            user=user,
            port=port,
            last_used=datetime.now(timezone.utc).isoformat(),
        )

        dialog.set_focus(None)
        dialog.close()
        parent.set_focus(None)
        parent.close()

        on_save(new_host)
        if on_complete:
            on_complete()

    save_btn.connect("clicked", on_save_clicked)
    dialog.present()
    name_entry.grab_focus()


def show_edit_host_dialog(
    parent: Adw.Window,
    host: "RemoteHost",
    on_save: Callable[["RemoteHost", "RemoteHost"], None],
    show_toast: Callable[[str], None],
    on_complete: Callable[[], None] | None = None,
) -> None:
    """
    Muestra diálogo para editar una conexión remota.

    Args:
        parent: Ventana padre
        host: Host a editar
        on_save: Callback (old_host, new_host)
        show_toast: Función para mostrar mensajes
        on_complete: Callback opcional al completar
    """
    from datetime import datetime, timezone

    from ..remote_hosts import RemoteHost

    dialog = Adw.Window(transient_for=parent)
    dialog.set_title("Edit Connection")
    dialog.set_default_size(380, 320)
    dialog.set_modal(True)

    toolbar_view = Adw.ToolbarView()
    dialog.set_content(toolbar_view)

    header = Adw.HeaderBar()
    header.set_show_end_title_buttons(False)

    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.connect("clicked", lambda b: [dialog.set_focus(None), dialog.close()])
    header.pack_start(cancel_btn)

    save_btn = Gtk.Button(label="Save")
    save_btn.add_css_class("suggested-action")
    header.pack_end(save_btn)

    toolbar_view.add_top_bar(header)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)

    group = Adw.PreferencesGroup()

    name_entry = Adw.EntryRow(title="Name")
    name_entry.set_text(host.name)
    group.add(name_entry)

    host_entry = Adw.EntryRow(title="Host")
    host_entry.set_text(host.host)
    group.add(host_entry)

    user_entry = Adw.EntryRow(title="User")
    user_entry.set_text(host.user)
    group.add(user_entry)

    port_entry = Adw.EntryRow(title="Port")
    port_entry.set_text(host.port)
    group.add(port_entry)

    content.append(group)
    toolbar_view.set_content(content)

    def on_save_clicked(btn):
        name = name_entry.get_text().strip()
        new_host_addr = host_entry.get_text().strip()
        user = user_entry.get_text().strip()
        port = port_entry.get_text().strip() or "22"

        if not name or not new_host_addr or not user:
            show_toast("Name, host and user are required")
            return

        updated_host = RemoteHost(
            name=name,
            host=new_host_addr,
            user=user,
            port=port,
            last_used=datetime.now(timezone.utc).isoformat(),
        )

        dialog.set_focus(None)
        dialog.close()
        parent.set_focus(None)
        parent.close()

        on_save(host, updated_host)
        if on_complete:
            on_complete()

    save_btn.connect("clicked", on_save_clicked)
    dialog.present()


def confirm_delete_host(
    parent: Adw.Window,
    host: "RemoteHost",
    on_delete: Callable[["RemoteHost"], None],
    on_complete: Callable[[], None] | None = None,
) -> None:
    """
    Confirma eliminación de un host guardado.

    Args:
        parent: Ventana padre
        host: Host a eliminar
        on_delete: Callback con el host a eliminar
        on_complete: Callback opcional al completar
    """
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading="Delete Connection?",
        body=f"Are you sure you want to delete '{host.name}'?\n({host.user}@{host.host})",
    )

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("delete", "Delete")
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

    def on_response(dlg, response):
        dlg.close()
        if response == "delete":
            parent.close()
            on_delete(host)
            if on_complete:
                on_complete()

    dialog.connect("response", on_response)
    dialog.present()


def show_connect_to_host_dialog(
    parent: Adw.Window,
    host: "RemoteHost",
    on_connect_new: Callable[[str, str, str, str], None],
    on_connect_existing: Callable[[str, str, str], None],
    show_toast: Callable[[str], None],
) -> None:
    """
    Muestra diálogo para conectar a un host guardado.

    Args:
        parent: Ventana padre
        host: Host al que conectar
        on_connect_new: Callback (name, host, user, port) para nueva sesión
        on_connect_existing: Callback (host, user, port) para sesión existente
        show_toast: Función para mostrar mensajes
    """
    dialog = Adw.Window(transient_for=parent)
    dialog.set_title(f"Connect to {host.name}")
    dialog.set_default_size(380, 280)
    dialog.set_modal(True)

    toolbar_view = Adw.ToolbarView()
    dialog.set_content(toolbar_view)

    header = Adw.HeaderBar()
    header.set_show_end_title_buttons(False)

    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.connect("clicked", lambda b: [dialog.set_focus(None), dialog.close()])
    header.pack_start(cancel_btn)

    connect_btn = Gtk.Button(label="Connect")
    connect_btn.add_css_class("suggested-action")
    header.pack_end(connect_btn)

    toolbar_view.add_top_bar(header)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)

    group = Adw.PreferencesGroup(title="Session", description=f"Connect to {host.user}@{host.host}")

    name_entry = Adw.EntryRow(title="Session name")
    name_entry.set_text("")
    group.add(name_entry)

    attach_row = Adw.SwitchRow(
        title="Attach to existing",
        subtitle="Connect to an existing session instead of creating new",
    )
    group.add(attach_row)

    def on_attach_toggled(row, _pspec):
        name_entry.set_sensitive(not row.get_active())

    attach_row.connect("notify::active", on_attach_toggled)

    content.append(group)
    toolbar_view.set_content(content)

    def on_connect_clicked(btn):
        dialog.set_focus(None)
        dialog.close()
        parent.set_focus(None)
        parent.close()

        if attach_row.get_active():
            on_connect_existing(host.host, host.user, host.port)
        else:
            name = name_entry.get_text().strip()
            if not name:
                show_toast("Session name is required")
                return
            on_connect_new(name, host.host, host.user, host.port)

    connect_btn.connect("clicked", on_connect_clicked)
    name_entry.connect("apply", lambda e: [dialog.set_focus(None), on_connect_clicked(connect_btn)])

    dialog.present()
    name_entry.grab_focus()
