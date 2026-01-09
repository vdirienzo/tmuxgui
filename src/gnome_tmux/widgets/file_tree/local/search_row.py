"""
search_row.py - Fila para resultados de búsqueda local

Autor: Homero Thompson del Lago del Terror
"""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gio, GObject, Gtk


class SearchResultRow(Gtk.ListBoxRow):
    """Fila que representa un resultado de búsqueda."""

    __gtype_name__ = "SearchResultRow"

    __gsignals__ = {
        "copy-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "paste-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "rename-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "delete-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "copy-path-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "copy-relative-path-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "navigate-requested": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, path: Path, root_path: Path):
        super().__init__()

        self.path = path
        self.root_path = root_path
        self.is_directory = path.is_dir()
        self._popover = None

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

        name_label = Gtk.Label(label=path.name)
        name_label.set_ellipsize(3)
        name_label.set_xalign(0)
        text_box.append(name_label)

        try:
            relative = str(path.relative_to(root_path))
        except ValueError:
            relative = str(path)
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

        right_click = Gtk.GestureClick()
        right_click.set_button(3)
        right_click.connect("pressed", self._on_right_click)
        self.add_controller(right_click)

        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.COPY)
        drag_source.connect("prepare", self._on_drag_prepare)
        self.add_controller(drag_source)

    def _on_navigate_clicked(self, button: Gtk.Button):
        """Navega a la ubicación del archivo."""
        self.emit("navigate-requested", self.path)

    def _on_drag_prepare(self, source, x, y):
        """Prepara los datos para el drag."""
        return Gdk.ContentProvider.new_for_value(str(self.path))

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

        nav_section = Gio.Menu()
        nav_section.append("Go to Location", "file.navigate")
        menu.append_section(None, nav_section)

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

        copy_relative_path_action = Gio.SimpleAction.new("copy_relative_path", None)
        copy_relative_path_action.connect(
            "activate",
            lambda a, p: self.emit("copy-relative-path-requested", self.path),
        )
        action_group.add_action(copy_relative_path_action)

        navigate_action = Gio.SimpleAction.new("navigate", None)
        navigate_action.connect("activate", lambda a, p: self.emit("navigate-requested", self.path))
        action_group.add_action(navigate_action)

        rename_action = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", lambda a, p: self.emit("rename-requested", self.path))
        action_group.add_action(rename_action)

        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", lambda a, p: self.emit("delete-requested", self.path))
        action_group.add_action(delete_action)

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
