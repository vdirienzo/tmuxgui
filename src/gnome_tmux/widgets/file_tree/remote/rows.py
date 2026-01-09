"""
rows.py - Filas para el árbol de archivos remoto

Autor: Homero Thompson del Lago del Terror
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gio, GObject, Gtk


class RemoteFileTreeRow(Gtk.ListBoxRow):
    """Fila que representa un archivo o directorio remoto."""

    __gtype_name__ = "RemoteFileTreeRow"

    __gsignals__ = {
        "toggle-expand": (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
        "copy-path-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "download-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "rename-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "delete-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "create-folder-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "copy-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "paste-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(
        self,
        path: str,
        name: str,
        is_dir: bool,
        depth: int,
        expanded: bool = False,
        is_hidden: bool = False,
    ):
        super().__init__()

        self.path = path
        self.name = name
        self.depth = depth
        self.is_directory = is_dir
        self.expanded = expanded
        self.is_hidden = is_hidden

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

            label = Gtk.Label(label=name)
            label.set_ellipsize(3)
            label.set_hexpand(True)
            label.set_xalign(0)
            if is_hidden:
                label.add_css_class("dim-label")
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

            label = Gtk.Label(label=name)
            label.set_ellipsize(3)
            label.set_hexpand(True)
            label.set_xalign(0)
            if is_hidden:
                label.add_css_class("dim-label")
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

        if not self.is_directory:
            double_click = Gtk.GestureClick()
            double_click.set_button(1)
            double_click.connect("released", self._on_double_click)
            self.add_controller(double_click)

    def _on_double_click(self, gesture, n_press, x, y):
        """Descarga el archivo con doble click."""
        if n_press == 2 and not self.is_directory:
            self.emit("download-requested", self.path)

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
        return Gdk.ContentProvider.new_for_value(self.path)

    def _on_drag_begin(self, source, drag):
        """Configura el icono del drag."""
        icon = Gtk.Image.new_from_icon_name(
            "folder-symbolic" if self.is_directory else "text-x-generic-symbolic"
        )
        source.set_icon(icon.get_paintable(), 0, 0)

    def _on_right_click(self, gesture, n_press, x, y):
        """Muestra el menú contextual."""
        menu = Gio.Menu()

        if not self.is_directory:
            download_section = Gio.Menu()
            download_section.append("Download", "file.download")
            menu.append_section(None, download_section)

        copy_paste_section = Gio.Menu()
        copy_paste_section.append("Copy", "file.copy")
        copy_paste_section.append("Paste", "file.paste")
        menu.append_section(None, copy_paste_section)

        path_section = Gio.Menu()
        path_section.append("Copy Path", "file.copy_path")
        menu.append_section(None, path_section)

        if self.is_directory:
            create_section = Gio.Menu()
            create_section.append("New Folder", "file.create_folder")
            menu.append_section(None, create_section)

        edit_section = Gio.Menu()
        edit_section.append("Rename", "file.rename")
        edit_section.append("Delete", "file.delete")
        menu.append_section(None, edit_section)

        action_group = Gio.SimpleActionGroup()

        copy_action = Gio.SimpleAction.new("copy", None)
        copy_action.connect("activate", lambda a, p: self.emit("copy-requested", self.path))
        action_group.add_action(copy_action)

        paste_action = Gio.SimpleAction.new("paste", None)
        paste_action.connect("activate", lambda a, p: self.emit("paste-requested", self.path))
        action_group.add_action(paste_action)

        copy_path_action = Gio.SimpleAction.new("copy_path", None)
        copy_path_action.connect(
            "activate", lambda a, p: self.emit("copy-path-requested", self.path)
        )
        action_group.add_action(copy_path_action)

        download_action = Gio.SimpleAction.new("download", None)
        download_action.connect("activate", lambda a, p: self.emit("download-requested", self.path))
        action_group.add_action(download_action)

        rename_action = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", lambda a, p: self.emit("rename-requested", self.path))
        action_group.add_action(rename_action)

        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", lambda a, p: self.emit("delete-requested", self.path))
        action_group.add_action(delete_action)

        create_folder_action = Gio.SimpleAction.new("create_folder", None)
        create_folder_action.connect(
            "activate", lambda a, p: self.emit("create-folder-requested", self.path)
        )
        action_group.add_action(create_folder_action)

        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(self)
        popover.insert_action_group("file", action_group)
        popover.set_has_arrow(False)

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.popup()


class RemoteSearchResultRow(Gtk.ListBoxRow):
    """Fila que representa un resultado de búsqueda remota."""

    __gtype_name__ = "RemoteSearchResultRow"

    __gsignals__ = {
        "navigate-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "copy-path-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, path: str, name: str, is_dir: bool, root_path: str):
        super().__init__()

        self.path = path
        self.name = name
        self.root_path = root_path
        self.is_directory = is_dir

        self.set_selectable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(2)
        box.set_margin_bottom(2)

        icon_name = "folder-symbolic" if self.is_directory else "text-x-generic-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(14)
        box.append(icon)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text_box.set_hexpand(True)

        name_label = Gtk.Label(label=name)
        name_label.set_ellipsize(3)
        name_label.set_xalign(0)
        text_box.append(name_label)

        if path.startswith(root_path):
            relative = path[len(root_path) :].lstrip("/")
        else:
            relative = path
        path_label = Gtk.Label(label=relative)
        path_label.set_ellipsize(3)
        path_label.set_xalign(0)
        path_label.add_css_class("dim-label")
        path_label.add_css_class("caption")
        text_box.append(path_label)

        box.append(text_box)

        nav_btn = Gtk.Button()
        nav_btn.set_icon_name("find-location-symbolic")
        nav_btn.set_tooltip_text("Go to location")
        nav_btn.add_css_class("flat")
        nav_btn.set_valign(Gtk.Align.CENTER)
        nav_btn.connect("clicked", self._on_navigate_clicked)
        box.append(nav_btn)

        self.set_child(box)

        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.COPY)
        drag_source.connect("prepare", self._on_drag_prepare)
        self.add_controller(drag_source)

    def _on_navigate_clicked(self, button: Gtk.Button):
        """Navega a la ubicación del archivo."""
        self.emit("navigate-requested", self.path)

    def _on_drag_prepare(self, source, x, y):
        """Prepara los datos para el drag."""
        return Gdk.ContentProvider.new_for_value(self.path)
