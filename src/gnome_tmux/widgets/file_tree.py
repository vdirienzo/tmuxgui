"""
file_tree.py - Widget de árbol de archivos estilo VS Code

Autor: Homero Thompson del Lago del Terror
"""

import json
import os
import re
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GObject, Gtk


class FileTree(Gtk.Box):
    """Widget de árbol de archivos con navegación estilo VS Code."""

    __gtype_name__ = "FileTree"

    # Archivo de configuración para favoritos
    _FAVORITES_FILE = Path.home() / ".config" / "gnome-tmux" / "favorites.json"

    def __init__(self, root_path: str | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._root_path = Path(root_path or os.environ.get("HOME", "/"))
        self._expanded_dirs: set[str] = set()  # Directorios expandidos
        self._clipboard_path: str | None = None  # Path copiado al clipboard
        self._favorites: list[str] = self._load_favorites()

        self._setup_ui()
        self._load_tree()

    def _setup_ui(self):
        """Configura la interfaz del árbol de archivos."""
        # Header con path actual y botones
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header_box.set_margin_start(4)
        header_box.set_margin_end(4)
        header_box.set_margin_top(4)
        header_box.set_margin_bottom(4)

        # Drag handle (expuesto para que window.py pueda agregar DragSource)
        self.drag_handle_box = Gtk.Box()
        drag_handle = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        drag_handle.set_opacity(0.5)
        drag_handle.set_tooltip_text("Drag to reorder")
        self.drag_handle_box.append(drag_handle)
        header_box.append(self.drag_handle_box)

        # Botón ir al home
        home_btn = Gtk.Button()
        home_btn.set_icon_name("go-home-symbolic")
        home_btn.set_tooltip_text("Go to home")
        home_btn.add_css_class("flat")
        home_btn.connect("clicked", self._on_home_clicked)
        header_box.append(home_btn)

        # Botón ir arriba
        up_btn = Gtk.Button()
        up_btn.set_icon_name("go-up-symbolic")
        up_btn.set_tooltip_text("Go up")
        up_btn.add_css_class("flat")
        up_btn.connect("clicked", self._on_up_clicked)
        header_box.append(up_btn)

        # Botón colapsar todo
        collapse_btn = Gtk.Button()
        collapse_btn.set_icon_name("view-restore-symbolic")
        collapse_btn.set_tooltip_text("Collapse all")
        collapse_btn.add_css_class("flat")
        collapse_btn.connect("clicked", self._on_collapse_all)
        header_box.append(collapse_btn)

        # Label con path actual
        self._path_label = Gtk.Label()
        self._path_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        self._path_label.set_hexpand(True)
        self._path_label.set_xalign(0)
        self._path_label.add_css_class("dim-label")
        header_box.append(self._path_label)

        # Botón de favoritos
        self._favorites_button = Gtk.MenuButton()
        self._favorites_button.set_icon_name("starred-symbolic")
        self._favorites_button.set_tooltip_text("Favorites")
        self._favorites_button.add_css_class("flat")
        self._update_favorites_menu()
        header_box.append(self._favorites_button)

        self.append(header_box)

        # Separator
        self.append(Gtk.Separator())

        # Search entry
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        search_box.set_margin_start(4)
        search_box.set_margin_end(4)
        search_box.set_margin_top(4)
        search_box.set_margin_bottom(4)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search files...")
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("stop-search", self._on_search_stopped)
        search_box.append(self._search_entry)

        # Botón de opciones de búsqueda
        self._search_options_button = Gtk.MenuButton()
        self._search_options_button.set_icon_name("view-more-symbolic")
        self._search_options_button.set_tooltip_text("Search options")
        self._search_options_button.add_css_class("flat")
        self._setup_search_options_menu()
        search_box.append(self._search_options_button)

        self.append(search_box)

        # Estado de búsqueda
        self._search_mode = "name"  # name, regex, content
        self._search_results: list[Path] = []
        self._is_searching = False

        # ScrolledWindow para el árbol
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        # ListBox para archivos
        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list_box.add_css_class("file-tree-sidebar")
        scrolled.set_child(self._list_box)

        self.append(scrolled)

    def _load_tree(self):
        """Carga el árbol desde el directorio raíz."""
        self._path_label.set_text(self._root_path.name or str(self._root_path))
        self._path_label.set_tooltip_text(str(self._root_path))
        self._update_favorites_menu()  # Actualizar estado del botón favoritos

        # Limpiar lista actual
        self._clear_list_box()

        # Si hay búsqueda activa, mostrar resultados
        if self._is_searching and self._search_results:
            self._show_search_results()
        else:
            # Cargar recursivamente
            self._load_directory_recursive(self._root_path, 0)

    def _clear_list_box(self):
        """Limpia todas las filas del list box."""
        while True:
            row = self._list_box.get_row_at_index(0)
            if row is None:
                break
            self._list_box.remove(row)

    def _setup_search_options_menu(self):
        """Configura el menú de opciones de búsqueda."""
        menu = Gio.Menu()
        menu.append("By Name", "search.mode_name")
        menu.append("By Regex", "search.mode_regex")
        menu.append("By Content (grep)", "search.mode_content")

        action_group = Gio.SimpleActionGroup()

        name_action = Gio.SimpleAction.new("mode_name", None)
        name_action.connect("activate", lambda a, p: self._set_search_mode("name"))
        action_group.add_action(name_action)

        regex_action = Gio.SimpleAction.new("mode_regex", None)
        regex_action.connect("activate", lambda a, p: self._set_search_mode("regex"))
        action_group.add_action(regex_action)

        content_action = Gio.SimpleAction.new("mode_content", None)
        content_action.connect("activate", lambda a, p: self._set_search_mode("content"))
        action_group.add_action(content_action)

        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.insert_action_group("search", action_group)
        self._search_options_button.set_popover(popover)

    def _set_search_mode(self, mode: str):
        """Cambia el modo de búsqueda."""
        self._search_mode = mode
        placeholders = {
            "name": "Search files...",
            "regex": "Search regex pattern...",
            "content": "Search in content...",
        }
        self._search_entry.set_placeholder_text(placeholders.get(mode, "Search..."))
        # Re-ejecutar búsqueda si hay texto
        query = self._search_entry.get_text().strip()
        if query:
            self._perform_search(query)

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        """Maneja cambios en el search entry."""
        query = entry.get_text().strip()
        if query:
            self._perform_search(query)
        else:
            self._is_searching = False
            self._search_results = []
            self._load_tree()

    def _on_search_stopped(self, entry: Gtk.SearchEntry):
        """Limpia la búsqueda."""
        self._is_searching = False
        self._search_results = []
        self._search_entry.set_text("")
        self._load_tree()

    def _perform_search(self, query: str):
        """Ejecuta la búsqueda según el modo."""
        self._is_searching = True

        if self._search_mode == "name":
            self._search_results = self._search_by_name(query)
        elif self._search_mode == "regex":
            self._search_results = self._search_by_regex(query)
        elif self._search_mode == "content":
            self._search_results = self._search_by_content(query)
        else:
            self._search_results = []

        self._clear_list_box()
        self._show_search_results()

    def _search_by_name(self, query: str) -> list[Path]:
        """Busca archivos por nombre usando find."""
        try:
            result = subprocess.run(
                ["find", str(self._root_path), "-name", f"*{query}*", "-not", "-path", "*/.*"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            paths = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    path = Path(line)
                    if path.exists() and path != self._root_path:
                        paths.append(path)
            return paths[:100]  # Limitar resultados
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _search_by_regex(self, query: str) -> list[Path]:
        """Busca archivos por patrón regex."""
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            return []

        results = []
        try:
            for path in self._root_path.rglob("*"):
                if path.name.startswith("."):
                    continue
                if pattern.search(path.name):
                    results.append(path)
                if len(results) >= 100:
                    break
        except (PermissionError, OSError):
            pass
        return results

    def _search_by_content(self, query: str) -> list[Path]:
        """Busca en contenido de archivos usando grep."""
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", "-i", "--include=*", query, str(self._root_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            paths = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    path = Path(line)
                    if path.exists() and not any(p.startswith(".") for p in path.parts):
                        paths.append(path)
            return paths[:100]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _show_search_results(self):
        """Muestra los resultados de búsqueda."""
        if not self._search_results:
            # Mostrar mensaje de no resultados
            row = self._create_error_row("No results found", 0)
            self._list_box.append(row)
            return

        for path in self._search_results:
            row = SearchResultRow(path, self._root_path)
            row.connect("copy-requested", self._on_copy_requested)
            row.connect("paste-requested", self._on_paste_requested)
            row.connect("rename-requested", self._on_rename_requested)
            row.connect("delete-requested", self._on_delete_requested)
            row.connect("copy-path-requested", self._on_copy_path_requested)
            row.connect("copy-relative-path-requested", self._on_copy_relative_path_requested)
            row.connect("navigate-requested", self._on_navigate_requested)
            self._list_box.append(row)

    def _on_navigate_requested(self, row, path: Path):
        """Navega a la ubicación del archivo."""
        parent = path.parent if path.is_file() else path
        if parent.exists():
            self._root_path = parent
            self._expanded_dirs.clear()
            self._is_searching = False
            self._search_results = []
            self._search_entry.set_text("")
            self._load_tree()

    def _load_directory_recursive(self, path: Path, depth: int):
        """Carga un directorio y sus hijos expandidos recursivamente."""
        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            if depth == 0:
                row = self._create_error_row("Permission denied", depth)
                self._list_box.append(row)
            return

        for entry in entries:
            # Ignorar archivos ocultos
            if entry.name.startswith("."):
                continue

            is_dir = entry.is_dir()
            is_expanded = str(entry) in self._expanded_dirs

            row = FileTreeRow(entry, depth, is_expanded)
            row.connect("toggle-expand", self._on_toggle_expand)
            row.connect("copy-requested", self._on_copy_requested)
            row.connect("paste-requested", self._on_paste_requested)
            row.connect("rename-requested", self._on_rename_requested)
            row.connect("delete-requested", self._on_delete_requested)
            row.connect("copy-path-requested", self._on_copy_path_requested)
            row.connect("copy-relative-path-requested", self._on_copy_relative_path_requested)
            row.connect("add-to-favorites-requested", self._on_add_to_favorites_requested)
            row.connect("create-folder-requested", self._on_create_folder_requested)
            self._list_box.append(row)

            # Si es directorio expandido, cargar hijos
            if is_dir and is_expanded:
                self._load_directory_recursive(entry, depth + 1)

    def _create_error_row(self, message: str, depth: int) -> Gtk.ListBoxRow:
        """Crea una fila de error."""
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(4 + depth * 16)
        box.set_margin_end(4)
        box.set_margin_top(2)
        box.set_margin_bottom(2)

        label = Gtk.Label(label=message)
        label.add_css_class("dim-label")
        box.append(label)

        row.set_child(box)
        return row

    def _on_toggle_expand(self, row, path: Path, expanded: bool):
        """Maneja el toggle de expansión de un directorio."""
        path_str = str(path)
        if expanded:
            self._expanded_dirs.add(path_str)
        else:
            # Remover este y todos los subdirectorios expandidos
            self._expanded_dirs = {p for p in self._expanded_dirs
                                   if not p.startswith(path_str)}
        self._load_tree()

    def _on_home_clicked(self, button: Gtk.Button):
        """Va al directorio home."""
        self._root_path = Path.home()
        self._expanded_dirs.clear()
        self._load_tree()

    def _on_up_clicked(self, button: Gtk.Button):
        """Sube un nivel en el directorio."""
        parent = self._root_path.parent
        if parent != self._root_path:
            self._root_path = parent
            self._expanded_dirs.clear()
            self._load_tree()

    def _on_collapse_all(self, button: Gtk.Button):
        """Colapsa todos los directorios."""
        self._expanded_dirs.clear()
        self._load_tree()

    def copy_path(self, path: Path):
        """Copia un path al clipboard interno."""
        self._clipboard_path = str(path)
        # También copiar al clipboard del sistema
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(str(path))

    def paste_path(self, destination: Path):
        """Pega el archivo/carpeta copiado en el destino."""
        if not self._clipboard_path:
            return

        import shutil
        source = Path(self._clipboard_path)
        if not source.exists():
            return

        # Destino es el directorio donde pegar
        if destination.is_file():
            destination = destination.parent

        target = destination / source.name

        # Si ya existe, agregar sufijo
        counter = 1
        original_target = target
        while target.exists():
            if source.is_dir():
                target = destination / f"{original_target.stem}_{counter}"
            else:
                target = destination / f"{original_target.stem}_{counter}{original_target.suffix}"
            counter += 1

        try:
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            self._load_tree()
        except (PermissionError, OSError) as e:
            print(f"Error copying: {e}")

    def rename_path(self, path: Path, new_name: str):
        """Renombra un archivo o carpeta."""
        if not new_name or new_name == path.name:
            return

        new_path = path.parent / new_name
        try:
            path.rename(new_path)
            self._load_tree()
        except (PermissionError, OSError) as e:
            print(f"Error renaming: {e}")

    def delete_path(self, path: Path):
        """Mueve un archivo o carpeta a ~/.trash."""
        import shutil

        # Crear directorio trash si no existe
        trash_dir = Path.home() / ".trash"
        trash_dir.mkdir(exist_ok=True)

        # Destino en trash
        target = trash_dir / path.name

        # Si ya existe, agregar sufijo con timestamp
        if target.exists():
            import time
            timestamp = int(time.time())
            if path.is_dir():
                target = trash_dir / f"{path.name}_{timestamp}"
            else:
                target = trash_dir / f"{path.stem}_{timestamp}{path.suffix}"

        try:
            shutil.move(str(path), str(target))
            self._load_tree()
        except (PermissionError, OSError) as e:
            print(f"Error moving to trash: {e}")

    def has_clipboard(self) -> bool:
        """Retorna si hay algo en el clipboard."""
        return self._clipboard_path is not None

    # --- Favoritos ---

    def _load_favorites(self) -> list[str]:
        """Carga la lista de favoritos desde el archivo de configuración."""
        try:
            if self._FAVORITES_FILE.exists():
                with open(self._FAVORITES_FILE) as f:
                    data = json.load(f)
                    return data.get("favorites", [])
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def _save_favorites(self):
        """Guarda la lista de favoritos en el archivo de configuración."""
        try:
            self._FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self._FAVORITES_FILE, "w") as f:
                json.dump({"favorites": self._favorites}, f, indent=2)
        except OSError as e:
            print(f"Error saving favorites: {e}")

    def _update_favorites_menu(self):
        """Actualiza el menú de favoritos."""
        # Crear popover con contenido personalizado
        popover = Gtk.Popover()
        popover.set_has_arrow(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        # Botón agregar actual a favoritos
        current_path_str = str(self._root_path)
        is_favorite = current_path_str in self._favorites

        add_btn = Gtk.Button()
        add_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_btn_box.set_margin_start(8)
        add_btn_box.set_margin_end(8)

        if is_favorite:
            add_btn_box.append(Gtk.Image.new_from_icon_name("starred-symbolic"))
            add_btn_box.append(Gtk.Label(label="Remove from favorites"))
            add_btn.connect("clicked", self._on_remove_current_favorite, popover)
        else:
            add_btn_box.append(Gtk.Image.new_from_icon_name("non-starred-symbolic"))
            add_btn_box.append(Gtk.Label(label="Add to favorites"))
            add_btn.connect("clicked", self._on_add_current_favorite, popover)

        add_btn.set_child(add_btn_box)
        add_btn.add_css_class("flat")
        box.append(add_btn)

        # Separador si hay favoritos
        if self._favorites:
            box.append(Gtk.Separator())

            # Lista de favoritos
            for fav_path in self._favorites:
                fav_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

                # Botón para navegar al favorito
                fav_btn = Gtk.Button()
                fav_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                fav_btn_box.set_margin_start(8)
                fav_btn_box.set_margin_end(4)

                fav_btn_box.append(Gtk.Image.new_from_icon_name("folder-symbolic"))
                fav_label = Gtk.Label(label=Path(fav_path).name or fav_path)
                fav_label.set_tooltip_text(fav_path)
                fav_label.set_ellipsize(3)
                fav_label.set_max_width_chars(20)
                fav_label.set_hexpand(True)
                fav_label.set_xalign(0)
                fav_btn_box.append(fav_label)

                fav_btn.set_child(fav_btn_box)
                fav_btn.add_css_class("flat")
                fav_btn.set_hexpand(True)
                fav_btn.connect("clicked", self._on_favorite_clicked, fav_path, popover)
                fav_row.append(fav_btn)

                # Botón para eliminar favorito
                delete_btn = Gtk.Button()
                delete_btn.set_icon_name("user-trash-symbolic")
                delete_btn.add_css_class("flat")
                delete_btn.set_tooltip_text("Remove from favorites")
                delete_btn.connect("clicked", self._on_remove_favorite_clicked, fav_path, popover)
                fav_row.append(delete_btn)

                box.append(fav_row)

        popover.set_child(box)
        self._favorites_button.set_popover(popover)

    def _on_add_current_favorite(self, button: Gtk.Button, popover: Gtk.Popover):
        """Agrega el path actual a favoritos."""
        current_path = str(self._root_path)
        if current_path not in self._favorites:
            self._favorites.append(current_path)
            self._save_favorites()
            self._update_favorites_menu()
        popover.popdown()

    def _on_remove_current_favorite(self, button: Gtk.Button, popover: Gtk.Popover):
        """Elimina el path actual de favoritos."""
        current_path = str(self._root_path)
        if current_path in self._favorites:
            self._favorites.remove(current_path)
            self._save_favorites()
            self._update_favorites_menu()
        popover.popdown()

    def _on_favorite_clicked(self, button: Gtk.Button, fav_path: str, popover: Gtk.Popover):
        """Navega a un favorito."""
        path = Path(fav_path)
        if path.exists() and path.is_dir():
            self._root_path = path
            self._expanded_dirs.clear()
            self._load_tree()
            self._update_favorites_menu()
        popover.popdown()

    def _on_remove_favorite_clicked(self, button: Gtk.Button, fav_path: str, popover: Gtk.Popover):
        """Elimina un favorito de la lista."""
        if fav_path in self._favorites:
            self._favorites.remove(fav_path)
            self._save_favorites()
            self._update_favorites_menu()
        popover.popdown()

    def _on_add_to_favorites_requested(self, row, path: Path):
        """Agrega una carpeta a favoritos desde el menú contextual."""
        path_str = str(path)
        if path_str not in self._favorites:
            self._favorites.append(path_str)
            self._save_favorites()
            self._update_favorites_menu()

    def _on_copy_requested(self, row, path: Path):
        """Maneja solicitud de copiar archivo/carpeta."""
        self.copy_path(path)

    def _on_paste_requested(self, row, path: Path):
        """Maneja solicitud de pegar."""
        self.paste_path(path)

    def _on_rename_requested(self, row, path: Path):
        """Muestra diálogo para renombrar."""
        root = self.get_root()

        dialog = Adw.MessageDialog(
            heading="Rename",
            body=f"Enter new name for '{path.name}':",
        )

        if root:
            dialog.set_transient_for(root)

        entry = Gtk.Entry()
        entry.set_text(path.name)
        entry.connect("activate", lambda e: dialog.response("rename"))
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("rename", "Rename")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("rename")

        def on_response(dialog, response):
            if response == "rename":
                new_name = entry.get_text().strip()
                self.rename_path(path, new_name)

        dialog.connect("response", on_response)
        dialog.present()

    def _on_delete_requested(self, row, path: Path):
        """Muestra diálogo de confirmación para eliminar."""
        root = self.get_root()

        if path.is_dir():
            body = "This will permanently delete this folder and all its contents."
        else:
            body = "This will permanently delete this file."
        dialog = Adw.MessageDialog(
            heading=f"Delete {path.name}?",
            body=body,
        )

        if root:
            dialog.set_transient_for(root)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(dialog, response):
            if response == "delete":
                self.delete_path(path)

        dialog.connect("response", on_response)
        dialog.present()

    def _on_copy_path_requested(self, row, path: Path):
        """Copia el path absoluto al clipboard."""
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(str(path.absolute()))

    def _on_copy_relative_path_requested(self, row, path: Path):
        """Copia el path relativo al clipboard."""
        try:
            relative = path.relative_to(self._root_path)
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(str(relative))
        except ValueError:
            # Si no es relativo, copiar absoluto
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(str(path))

    def _on_create_folder_requested(self, row, path: Path):
        """Muestra diálogo para crear una nueva carpeta."""
        root = self.get_root()

        dialog = Adw.MessageDialog(
            heading="New Folder",
            body="Enter name for the new folder:",
        )

        if root:
            dialog.set_transient_for(root)

        entry = Gtk.Entry()
        entry.set_text("New Folder")
        entry.select_region(0, -1)  # Seleccionar todo el texto
        entry.connect("activate", lambda e: dialog.response("create"))
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")

        def on_response(dialog, response):
            if response == "create":
                folder_name = entry.get_text().strip()
                if folder_name:
                    self._create_folder(path, folder_name)

        dialog.connect("response", on_response)
        dialog.present()

    def _create_folder(self, parent_path: Path, folder_name: str):
        """Crea una nueva carpeta."""
        new_folder = parent_path / folder_name

        # Si ya existe, agregar sufijo
        counter = 1
        original_name = folder_name
        while new_folder.exists():
            folder_name = f"{original_name}_{counter}"
            new_folder = parent_path / folder_name
            counter += 1

        try:
            new_folder.mkdir(parents=False, exist_ok=False)
            # Expandir el directorio padre para mostrar la nueva carpeta
            self._expanded_dirs.add(str(parent_path))
            self._load_tree()
        except (PermissionError, OSError) as e:
            print(f"Error creating folder: {e}")


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

        # Box horizontal con indentación
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(4 + depth * 16)  # Indentación por nivel
        box.set_margin_end(4)
        box.set_margin_top(1)
        box.set_margin_bottom(1)

        if self.is_directory:
            # Flecha de expansión para directorios
            self._arrow = Gtk.Image()
            self._update_arrow()
            box.append(self._arrow)

            # Icono de carpeta
            folder_icon = Gtk.Image.new_from_icon_name(
                "folder-open-symbolic" if expanded else "folder-symbolic"
            )
            folder_icon.set_pixel_size(14)
            box.append(folder_icon)

            # Nombre clickeable
            label = Gtk.Label(label=path.name)
            label.set_ellipsize(3)
            label.set_hexpand(True)
            label.set_xalign(0)
            box.append(label)

            # Hacer clickeable toda la fila para expandir/colapsar
            click = Gtk.GestureClick()
            click.connect("pressed", self._on_clicked)
            self.add_controller(click)
        else:
            # Espaciador para alinear con carpetas
            spacer = Gtk.Box()
            spacer.set_size_request(14, -1)
            box.append(spacer)

            # Icono de archivo
            file_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
            file_icon.set_pixel_size(14)
            box.append(file_icon)

            # Nombre
            label = Gtk.Label(label=path.name)
            label.set_ellipsize(3)
            label.set_hexpand(True)
            label.set_xalign(0)
            box.append(label)

        self.set_child(box)

        # Configurar drag source para arrastrar el path
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.COPY)
        drag_source.connect("prepare", self._on_drag_prepare)
        drag_source.connect("drag-begin", self._on_drag_begin)
        self.add_controller(drag_source)

        # Menú contextual con click derecho
        right_click = Gtk.GestureClick()
        right_click.set_button(3)  # Botón derecho
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
        # Crear menú
        menu = Gio.Menu()

        # Sección Copy/Paste
        copy_paste_section = Gio.Menu()
        copy_paste_section.append("Copy", "file.copy")
        copy_paste_section.append("Paste", "file.paste")
        menu.append_section(None, copy_paste_section)

        # Sección Copy Path
        path_section = Gio.Menu()
        path_section.append("Copy Path", "file.copy_path")
        path_section.append("Copy Relative Path", "file.copy_relative_path")
        menu.append_section(None, path_section)

        # Sección Favorites y Create (solo para directorios)
        if self.is_directory:
            dir_section = Gio.Menu()
            dir_section.append("New Folder", "file.create_folder")
            dir_section.append("Add to Favorites", "file.add_favorite")
            menu.append_section(None, dir_section)

        # Sección Rename/Delete
        edit_section = Gio.Menu()
        edit_section.append("Rename", "file.rename")
        edit_section.append("Delete", "file.delete")
        menu.append_section(None, edit_section)

        # Crear acciones
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

        # Crear popover
        self._popover = Gtk.PopoverMenu.new_from_model(menu)
        self._popover.set_parent(self)
        self._popover.insert_action_group("file", action_group)
        self._popover.set_has_arrow(False)

        # Posicionar en el punto del click
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

        # Box horizontal
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(2)
        box.set_margin_bottom(2)

        # Icono
        icon_name = "folder-symbolic" if self.is_directory else "text-x-generic-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(14)
        box.append(icon)

        # Box vertical para nombre y path
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text_box.set_hexpand(True)

        # Nombre del archivo
        name_label = Gtk.Label(label=path.name)
        name_label.set_ellipsize(3)
        name_label.set_xalign(0)
        text_box.append(name_label)

        # Path relativo
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

        # Botón para navegar a la ubicación
        nav_btn = Gtk.Button()
        nav_btn.set_icon_name("find-location-symbolic")
        nav_btn.set_tooltip_text("Go to location")
        nav_btn.add_css_class("flat")
        nav_btn.set_valign(Gtk.Align.CENTER)
        nav_btn.connect("clicked", self._on_navigate_clicked)
        box.append(nav_btn)

        self.set_child(box)

        # Menú contextual
        right_click = Gtk.GestureClick()
        right_click.set_button(3)
        right_click.connect("pressed", self._on_right_click)
        self.add_controller(right_click)

        # Drag source
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

        # Sección Copy/Paste
        copy_paste_section = Gio.Menu()
        copy_paste_section.append("Copy", "file.copy")
        copy_paste_section.append("Paste", "file.paste")
        menu.append_section(None, copy_paste_section)

        # Sección Copy Path
        path_section = Gio.Menu()
        path_section.append("Copy Path", "file.copy_path")
        path_section.append("Copy Relative Path", "file.copy_relative_path")
        menu.append_section(None, path_section)

        # Sección Navigate
        nav_section = Gio.Menu()
        nav_section.append("Go to Location", "file.navigate")
        menu.append_section(None, nav_section)

        # Sección Rename/Delete
        edit_section = Gio.Menu()
        edit_section.append("Rename", "file.rename")
        edit_section.append("Delete", "file.delete")
        menu.append_section(None, edit_section)

        # Crear acciones
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

        # Crear popover
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
