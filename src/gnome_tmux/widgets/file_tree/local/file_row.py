"""
file_row.py - Fila para archivos/directorios locales

Autor: Homero Thompson del Lago del Terror
"""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gio, GObject, Gtk


class FileTreeRow(Gtk.ListBoxRow):
    """Fila que representa un archivo o directorio en el árbol."""

    __gtype_name__ = "FileTreeRow"

    __gsignals__ = {
        "toggle-expand": (GObject.SignalFlags.RUN_FIRST, None, (object, bool)),
        "copy-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "paste-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "rename-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "delete-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "copy-path-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "copy-relative-path-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "add-to-favorites-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "create-folder-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, path: Path, depth: int, expanded: bool = False):
        super().__init__()

        self.path = path
        self.depth = depth
        self.is_directory = path.is_dir()
        self.expanded = expanded
        self._popover = None

        self.set_selectable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(4 + depth * 16)
        box.set_margin_end(4)
        box.set_margin_top(1)
        box.set_margin_bottom(1)

        if self.is_directory:
            self._arrow = Gtk.Image()
            self._update_arrow()
            box.append(self._arrow)

            folder_icon = Gtk.Image.new_from_icon_name(
                "folder-open-symbolic" if expanded else "folder-symbolic"
            )
            folder_icon.set_pixel_size(14)
            box.append(folder_icon)

            label = Gtk.Label(label=path.name)
            label.set_ellipsize(3)
            label.set_hexpand(True)
            label.set_xalign(0)
            box.append(label)

            click = Gtk.GestureClick()
            click.connect("released", self._on_clicked)
            self.add_controller(click)
        else:
            spacer = Gtk.Box()
            spacer.set_size_request(14, -1)
            box.append(spacer)

            file_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
            file_icon.set_pixel_size(14)
            box.append(file_icon)

            label = Gtk.Label(label=path.name)
            label.set_ellipsize(3)
            label.set_hexpand(True)
            label.set_xalign(0)
            box.append(label)

        self.set_child(box)

        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.COPY)
        drag_source.connect("prepare", self._on_drag_prepare)
        drag_source.connect("drag-begin", self._on_drag_begin)
        self.add_controller(drag_source)

        right_click = Gtk.GestureClick()
        right_click.set_button(3)
        right_click.connect("pressed", self._on_right_click)
        self.add_controller(right_click)

    def _update_arrow(self):
        """Actualiza el icono de la flecha."""
        if self.expanded:
            self._arrow.set_from_icon_name("pan-down-symbolic")
        else:
            self._arrow.set_from_icon_name("pan-end-symbolic")
        self._arrow.set_pixel_size(12)

    def _on_clicked(self, gesture, n_press, x, y):
        """Maneja el click para expandir/colapsar."""
        if self.is_directory:
            self.expanded = not self.expanded
            self.emit("toggle-expand", self.path, self.expanded)

    def _on_drag_prepare(self, source, x, y):
        """Prepara los datos para el drag."""
        return Gdk.ContentProvider.new_for_value(str(self.path))

    def _on_drag_begin(self, source, drag):
        """Configura el icono del drag."""
        icon = Gtk.Image.new_from_icon_name(
            "folder-symbolic" if self.is_directory else "text-x-generic-symbolic"
        )
        source.set_icon(icon.get_paintable(), 0, 0)

    def _on_right_click(self, gesture, n_press, x, y):
        """Muestra el menú contextual."""
        menu = Gio.Menu()

        copy_paste_section = Gio.Menu()
        copy_paste_section.append("Copy", "file.copy")
        copy_paste_section.append("Paste", "file.paste")
        menu.append_section(None, copy_paste_section)

        path_section = Gio.Menu()
        path_section.append("Copy Path", "file.copy_path")
        path_section.append("Copy Relative Path", "file.copy_relative_path")
        menu.append_section(None, path_section)

        if self.is_directory:
            dir_section = Gio.Menu()
            dir_section.append("New Folder", "file.create_folder")
            dir_section.append("Add to Favorites", "file.add_favorite")
            menu.append_section(None, dir_section)

        edit_section = Gio.Menu()
        edit_section.append("Rename", "file.rename")
        edit_section.append("Delete", "file.delete")
        menu.append_section(None, edit_section)

        action_group = Gio.SimpleActionGroup()

        copy_action = Gio.SimpleAction.new("copy", None)
        copy_action.connect("activate", self._on_copy_action)
        action_group.add_action(copy_action)

        paste_action = Gio.SimpleAction.new("paste", None)
        paste_action.connect("activate", self._on_paste_action)
        action_group.add_action(paste_action)

        copy_path_action = Gio.SimpleAction.new("copy_path", None)
        copy_path_action.connect("activate", self._on_copy_path_action)
        action_group.add_action(copy_path_action)

        copy_relative_path_action = Gio.SimpleAction.new("copy_relative_path", None)
        copy_relative_path_action.connect("activate", self._on_copy_relative_path_action)
        action_group.add_action(copy_relative_path_action)

        rename_action = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", self._on_rename_action)
        action_group.add_action(rename_action)

        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", self._on_delete_action)
        action_group.add_action(delete_action)

        add_favorite_action = Gio.SimpleAction.new("add_favorite", None)
        add_favorite_action.connect("activate", self._on_add_favorite_action)
        action_group.add_action(add_favorite_action)

        create_folder_action = Gio.SimpleAction.new("create_folder", None)
        create_folder_action.connect("activate", self._on_create_folder_action)
        action_group.add_action(create_folder_action)

        self._popover = Gtk.PopoverMenu.new_from_model(menu)
        self._popover.set_parent(self)
        self._popover.insert_action_group("file", action_group)
        self._popover.set_has_arrow(False)

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        self._popover.set_pointing_to(rect)

        self._popover.popup()

    def _on_copy_action(self, action, param):
        """Acción de copiar."""
        self.emit("copy-requested", self.path)

    def _on_paste_action(self, action, param):
        """Acción de pegar."""
        self.emit("paste-requested", self.path)

    def _on_rename_action(self, action, param):
        """Acción de renombrar."""
        self.emit("rename-requested", self.path)

    def _on_delete_action(self, action, param):
        """Acción de eliminar."""
        self.emit("delete-requested", self.path)

    def _on_copy_path_action(self, action, param):
        """Acción de copiar path absoluto."""
        self.emit("copy-path-requested", self.path)

    def _on_copy_relative_path_action(self, action, param):
        """Acción de copiar path relativo."""
        self.emit("copy-relative-path-requested", self.path)

    def _on_add_favorite_action(self, action, param):
        """Acción de agregar a favoritos."""
        self.emit("add-to-favorites-requested", self.path)

    def _on_create_folder_action(self, action, param):
        """Acción de crear carpeta."""
        self.emit("create-folder-requested", self.path)
