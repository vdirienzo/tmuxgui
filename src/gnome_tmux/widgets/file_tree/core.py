"""
file_tree.py - Widget de árbol de archivos estilo VS Code

Autor: Homero Thompson del Lago del Terror
"""

import os
import re
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore

from .local import FileTreeRow, SearchResultRow
from .remote import RemoteFileTreeRow, RemoteSearchResultRow
from .ui import FavoritesManager


class FileTree(Gtk.Box):
    """Widget de árbol de archivos con navegación estilo VS Code."""

    __gtype_name__ = "FileTree"

    __gsignals__ = {
        # Signal: (filename, success)
        "download-complete": (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
    }

    # Archivo de configuración para favoritos
    _FAVORITES_FILE = Path.home() / ".config" / "gnome-tmux" / "favorites.json"

    def __init__(self, root_path: str | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._root_path = Path(root_path or os.environ.get("HOME", "/"))
        self._expanded_dirs: set[str] = set()  # Directorios expandidos
        self._clipboard_path: str | None = None  # Path copiado al clipboard
        self._favorites_manager = FavoritesManager(self._FAVORITES_FILE)

        # Remote mode support
        self._remote_client = None  # RemoteTmuxClient when in remote mode
        self._remote_root: str | None = None  # Remote root path
        self._is_remote = False
        self._remote_clipboard_path: str | None = None  # Path copiado en remoto

        self._setup_ui()
        self._load_tree()

    def set_remote_mode(self, client, root_path: str | None = None):
        """Cambia a modo remoto usando el cliente SSH proporcionado."""
        self._remote_client = client
        self._is_remote = True
        self._expanded_dirs.clear()
        self._remote_root = root_path  # Puede ser None inicialmente
        self._remote_retry_count = 0

        # Intentar cargar, si falla programar reintentos
        self._try_load_remote_tree()

    def _try_load_remote_tree(self):
        """Intenta cargar el árbol remoto, reintentando si la conexión no está lista."""
        from gi.repository import GLib

        if not self._remote_client:
            return

        # Verificar si la conexión está lista
        is_conn = self._remote_client.is_connected()

        if not is_conn:
            self._remote_retry_count += 1
            if self._remote_retry_count <= 120:  # Máximo 120 intentos (60 segundos)
                # Mostrar mensaje de espera
                self._show_connecting_message()
                # Reintentar en 500ms
                GLib.timeout_add(500, self._retry_load_remote)
                return
            else:
                # Timeout - mostrar error
                self._load_tree()
                return

        # Conexión lista - obtener home si no tenemos root
        if not self._remote_root:
            self._remote_root = self._remote_client.get_home_dir()
            if not self._remote_root:
                self._remote_root = "/"

        self._load_tree()

    def _retry_load_remote(self) -> bool:
        """Callback para reintentar carga remota."""
        if self._is_remote and self._remote_client:
            self._try_load_remote_tree()
        return False  # No repetir el timeout

    def _show_connecting_message(self):
        """Muestra mensaje de conexión en progreso."""
        if self._remote_client:
            host_label = f"{self._remote_client.user}@{self._remote_client.host}"
            self._path_label.set_text(f"[{host_label}] Connecting...")
            self._path_label.set_tooltip_text("Waiting for SSH connection...")

        self._clear_list_box()
        row = self._create_info_row("Waiting for SSH connection...", 0)
        self._list_box.append(row)

    def _create_info_row(self, message: str, depth: int) -> Gtk.ListBoxRow:
        """Crea una fila informativa."""
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(4 + depth * 16)
        box.set_margin_end(4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        spinner = Gtk.Spinner()
        spinner.start()
        box.append(spinner)

        label = Gtk.Label(label=message)
        label.add_css_class("dim-label")
        box.append(label)

        row.set_child(box)
        return row

    def set_local_mode(self, root_path: str | None = None):
        """Vuelve al modo local."""
        self._remote_client = None
        self._is_remote = False
        self._remote_root = None
        self._expanded_dirs.clear()

        if root_path:
            self._root_path = Path(root_path)
        else:
            self._root_path = Path.home()

        self._load_tree()

    @property
    def is_remote(self) -> bool:
        """Retorna True si está en modo remoto."""
        return self._is_remote

    @property
    def current_root(self) -> str:
        """Retorna el root actual (local o remoto)."""
        if self._is_remote:
            return self._remote_root or "/"
        return str(self._root_path)

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
        # Crear popover inicial
        self._update_favorites_popover()
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
        if self._is_remote:
            # Modo remoto
            if not self._remote_root:
                # No pudimos obtener el root - mostrar error
                self._path_label.set_text("[Remote] Connection failed")
                self._path_label.set_tooltip_text("Could not connect to remote host")
                self._clear_list_box()
                row = self._create_error_row("SSH connection not established", 0)
                self._list_box.append(row)
                return

            root_name = os.path.basename(self._remote_root) or self._remote_root
            host_label = f"{self._remote_client.user}@{self._remote_client.host}"
            self._path_label.set_text(f"[{host_label}] {root_name}")
            self._path_label.set_tooltip_text(f"{host_label}:{self._remote_root}")
        else:
            # Modo local
            self._path_label.set_text(self._root_path.name or str(self._root_path))
            self._path_label.set_tooltip_text(str(self._root_path))

        self._update_favorites_popover()  # Actualizar estado del botón favoritos

        # Limpiar lista actual
        self._clear_list_box()

        # Si hay búsqueda activa, mostrar resultados
        if self._is_searching and self._search_results:
            self._show_search_results()
        else:
            # Cargar recursivamente
            if self._is_remote:
                self._load_remote_directory_recursive(self._remote_root, 0)
            else:
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

        if self._is_remote:
            # Búsqueda remota
            self._search_results = self._search_remote(query)
        else:
            # Búsqueda local
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

    def _search_remote(self, query: str) -> list:
        """Busca archivos en el servidor remoto."""
        if not self._remote_client:
            return []

        mode = "name" if self._search_mode in ("name", "regex") else "content"
        results = self._remote_client.search_files(self._remote_root, query, mode)

        # Convertir a paths remotos (strings en vez de Path objects)
        return results

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
        except (PermissionError, OSError) as e:
            logger.debug(f"Permission error during regex search: {e}")
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

        if self._is_remote:
            # Resultados remotos (strings)
            for path_str in self._search_results:
                name = os.path.basename(path_str)
                is_dir = self._remote_client.is_dir(path_str) if self._remote_client else False
                row = RemoteSearchResultRow(path_str, name, is_dir, self._remote_root)
                row.connect("navigate-requested", self._on_remote_navigate_requested)
                row.connect("copy-path-requested", self._on_remote_copy_path_requested)
                self._list_box.append(row)
        else:
            # Resultados locales (Path objects)
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

    def _on_remote_navigate_requested(self, row, path: str):
        """Navega a la ubicación de un archivo remoto."""
        parent = os.path.dirname(path)
        if parent:
            self._remote_root = parent
            self._expanded_dirs.clear()
            self._is_searching = False
            self._search_results = []
            self._search_entry.set_text("")
            self._load_tree()

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

    def _load_remote_directory_recursive(self, path: str, depth: int):
        """Carga un directorio remoto y sus hijos expandidos recursivamente."""
        if not self._remote_client:
            return

        entries = self._remote_client.list_dir(path)

        if entries is None:
            if depth == 0:
                row = self._create_error_row("Connection error or permission denied", depth)
                self._list_box.append(row)
            return

        if len(entries) == 0 and depth == 0:
            row = self._create_error_row("Directory is empty", depth)
            self._list_box.append(row)
            return

        for entry in entries:
            name = entry["name"]
            is_dir = entry["is_dir"]
            is_hidden = entry.get("is_hidden", False)
            full_path = f"{path.rstrip('/')}/{name}"
            is_expanded = full_path in self._expanded_dirs

            row = RemoteFileTreeRow(full_path, name, is_dir, depth, is_expanded, is_hidden)
            row.connect("toggle-expand", self._on_remote_toggle_expand)
            row.connect("copy-path-requested", self._on_remote_copy_path_requested)
            row.connect("download-requested", self._on_download_requested)
            row.connect("rename-requested", self._on_remote_rename_requested)
            row.connect("delete-requested", self._on_remote_delete_requested)
            row.connect("create-folder-requested", self._on_remote_create_folder_requested)
            row.connect("copy-requested", self._on_remote_copy_requested)
            row.connect("paste-requested", self._on_remote_paste_requested)
            self._list_box.append(row)

            # Si es directorio expandido, cargar hijos
            if is_dir and is_expanded:
                self._load_remote_directory_recursive(full_path, depth + 1)

    def _on_remote_toggle_expand(self, row, path: str, expanded: bool):
        """Maneja el toggle de expansión de un directorio remoto."""
        if expanded:
            self._expanded_dirs.add(path)
        else:
            # Remover este y todos los subdirectorios expandidos
            self._expanded_dirs = {p for p in self._expanded_dirs if not p.startswith(path)}
        self._load_tree()

    def _on_remote_copy_path_requested(self, row, path: str):
        """Copia el path remoto al clipboard."""
        if self._remote_client:
            full_path = f"{self._remote_client.user}@{self._remote_client.host}:{path}"
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(full_path)

    def _on_download_requested(self, row, remote_path: str):
        """Descarga un archivo remoto a ~/Downloads."""
        import threading

        if not self._remote_client:
            return

        # Obtener nombre del archivo
        filename = os.path.basename(remote_path)

        # Destino: ~/Downloads
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)
        local_path = downloads_dir / filename

        # Si ya existe, agregar sufijo
        counter = 1
        original_path = local_path
        while local_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            local_path = downloads_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        # Descargar en thread separado para no bloquear UI
        def do_download():
            success = self._remote_client.download_file(remote_path, str(local_path))
            # Notificar en el hilo principal
            from gi.repository import GLib

            GLib.idle_add(self._on_download_finished, filename, success, str(local_path))

        thread = threading.Thread(target=do_download, daemon=True)
        thread.start()

    def _on_download_finished(self, filename: str, success: bool, local_path: str):
        """Callback cuando termina la descarga."""
        self.emit("download-complete", filename, success)
        return False

    def _on_remote_rename_requested(self, row, path: str):
        """Muestra diálogo para renombrar archivo/carpeta remoto."""
        name = os.path.basename(path)
        root = self.get_root()

        dialog = Adw.MessageDialog(
            heading="Rename",
            body=f"Enter new name for '{name}':",
        )

        if root:
            dialog.set_transient_for(root)

        entry = Gtk.Entry()
        entry.set_text(name)
        entry.connect("activate", lambda e: dialog.response("rename"))
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("rename", "Rename")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("rename")

        def on_response(dialog, response):
            if response == "rename":
                new_name = entry.get_text().strip()
                if new_name and new_name != name:
                    parent = os.path.dirname(path)
                    new_path = f"{parent}/{new_name}"
                    if self._remote_client and self._remote_client.rename_file(path, new_path):
                        self._load_tree()

        dialog.connect("response", on_response)
        dialog.present()

    def _on_remote_delete_requested(self, row, path: str):
        """Muestra diálogo de confirmación para eliminar archivo/carpeta remoto."""
        name = os.path.basename(path)
        root = self.get_root()

        is_dir = self._remote_client.is_dir(path) if self._remote_client else False
        if is_dir:
            body = (
                "This will permanently delete this folder and all its "
                "contents on the remote server."
            )
        else:
            body = "This will permanently delete this file on the remote server."

        dialog = Adw.MessageDialog(
            heading=f"Delete {name}?",
            body=body,
        )

        if root:
            dialog.set_transient_for(root)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(dialog, response):
            if response == "delete":
                if self._remote_client and self._remote_client.delete_file(path):
                    self._load_tree()

        dialog.connect("response", on_response)
        dialog.present()

    def _on_remote_create_folder_requested(self, row, path: str):
        """Muestra diálogo para crear una nueva carpeta remota."""
        root = self.get_root()

        dialog = Adw.MessageDialog(
            heading="New Folder",
            body="Enter name for the new folder:",
        )

        if root:
            dialog.set_transient_for(root)

        entry = Gtk.Entry()
        entry.set_text("New Folder")
        entry.select_region(0, -1)
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
                    new_path = f"{path.rstrip('/')}/{folder_name}"
                    if self._remote_client and self._remote_client.create_directory(new_path):
                        # Expandir el directorio padre para mostrar la nueva carpeta
                        self._expanded_dirs.add(path)
                        self._load_tree()

        dialog.connect("response", on_response)
        dialog.present()

    def _on_remote_copy_requested(self, row, path: str):
        """Copia un archivo/carpeta remoto al clipboard interno."""
        self._remote_clipboard_path = path

    def _on_remote_paste_requested(self, row, path: str):
        """Pega el archivo/carpeta copiado en el destino remoto."""
        if not self._remote_clipboard_path or not self._remote_client:
            return

        source = self._remote_clipboard_path
        source_name = os.path.basename(source)

        # Destino es el directorio donde pegar
        if self._remote_client.is_dir(path):
            destination = path
        else:
            destination = os.path.dirname(path)

        target = f"{destination.rstrip('/')}/{source_name}"

        # Si ya existe, agregar sufijo
        counter = 1
        original_name = source_name
        while self._remote_client.file_exists(target):
            # Separar nombre y extensión
            if "." in original_name and not original_name.startswith("."):
                name_parts = original_name.rsplit(".", 1)
                new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                new_name = f"{original_name}_{counter}"
            target = f"{destination.rstrip('/')}/{new_name}"
            counter += 1

        if self._remote_client.copy_file(source, target):
            # Expandir el directorio destino para mostrar el archivo copiado
            self._expanded_dirs.add(destination)
            self._load_tree()

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
            self._expanded_dirs = {p for p in self._expanded_dirs if not p.startswith(path_str)}
        self._load_tree()

    def _on_home_clicked(self, button: Gtk.Button):
        """Va al directorio home."""
        self._expanded_dirs.clear()
        if self._is_remote and self._remote_client:
            self._remote_root = self._remote_client.get_home_dir() or "/"
        else:
            self._root_path = Path.home()
        self._load_tree()

    def _on_up_clicked(self, button: Gtk.Button):
        """Sube un nivel en el directorio."""
        self._expanded_dirs.clear()
        if self._is_remote:
            if self._remote_root and self._remote_root != "/":
                remote_parent = os.path.dirname(self._remote_root.rstrip("/"))
                self._remote_root = remote_parent or "/"
                self._load_tree()
        else:
            local_parent = self._root_path.parent
            if local_parent != self._root_path:
                self._root_path = local_parent
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
            logger.error(f"Error copying: {e}")

    def rename_path(self, path: Path, new_name: str):
        """Renombra un archivo o carpeta."""
        if not new_name or new_name == path.name:
            return

        new_path = path.parent / new_name
        try:
            path.rename(new_path)
            self._load_tree()
        except (PermissionError, OSError) as e:
            logger.error(f"Error renaming: {e}")

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
            logger.error(f"Error moving to trash: {e}")

    def has_clipboard(self) -> bool:
        """Retorna si hay algo en el clipboard."""
        return self._clipboard_path is not None

    # --- Favoritos ---
    def _on_add_to_favorites_requested(self, row, path: Path):
        """Agrega una carpeta a favoritos desde el menú contextual."""
        self._favorites_manager.add(str(path))

        self._update_favorites_popover()
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
            logger.error(f"Error creating folder: {e}")

    def _update_favorites_popover(self):
        """Actualiza el popover de favoritos."""
        def on_navigate(fav_path: str):
            """Callback cuando se navega a un favorito."""
            path = Path(fav_path)
            if path.exists() and path.is_dir():
                self._root_path = path
                self._expanded_dirs.clear()
                self._load_tree()
                self._update_favorites_popover()

        current_path = str(self._root_path)
        popover = self._favorites_manager.create_popover(current_path, on_navigate)
        self._favorites_button.set_popover(popover)
