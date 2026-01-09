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


