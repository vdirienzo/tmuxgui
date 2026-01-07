"""
window.py - Ventana principal de gnome-tmux

Autor: Homero Thompson del Lago del Terror
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, GObject, Gtk

from .remote_hosts import RemoteHost, remote_hosts_manager
from .themes import theme_manager
from .tmux_client import RemoteTmuxClient, TmuxClient
from .widgets import FileTree, SessionRow, TerminalView
from .widgets.remote_session_row import RemoteSessionRow


class MainWindow(Adw.ApplicationWindow):
    """Ventana principal de gnome-tmux."""

    def __init__(self, app: Adw.Application):
        super().__init__(application=app)

        self.tmux = TmuxClient()
        self._refresh_timeout_id: int | None = None
        self._sidebar_position: int = 250  # Guardar posición para restore
        self._file_tree_position: int = 250  # Posición del file tree sidebar
        self._expanded_sessions: set[str] | None = None  # None = primera carga
        self._animation: Adw.TimedAnimation | None = None
        self._file_tree_animation: Adw.TimedAnimation | None = None
        # Track remote connections: {f"{user}@{host}:{port}": RemoteTmuxClient}
        self._remote_clients: dict[str, RemoteTmuxClient] = {}
        self._closing = False  # Flag para indicar que la app se está cerrando

        self.set_title("TmuxGUI")
        self.set_default_size(1000, 700)

        # Aplicar tema guardado
        theme_manager.apply_saved_theme()

        # Layout principal
        self._setup_ui()

        # Cargar sesiones
        self._refresh_sessions()

        # Auto-refresh cada 5 segundos
        self._refresh_timeout_id = GLib.timeout_add_seconds(5, self._on_refresh_timeout)

    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        # ToolbarView como contenedor principal
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(title="TmuxGUI")
        header.set_title_widget(title_widget)

        # Botón toggle sidebar
        self.sidebar_button = Gtk.ToggleButton()
        self.sidebar_button.set_icon_name("sidebar-show-symbolic")
        self.sidebar_button.set_tooltip_text("Toggle sidebar (F9)")
        self.sidebar_button.set_active(True)
        self.sidebar_button.connect("toggled", self._on_sidebar_toggled)
        header.pack_start(self.sidebar_button)

        # Botón toggle file tree (al lado del sidebar)
        self.file_tree_button = Gtk.ToggleButton()
        self.file_tree_button.set_icon_name("folder-open-symbolic")
        self.file_tree_button.set_tooltip_text("Toggle file browser (F10)")
        self.file_tree_button.set_active(True)  # Abierto por defecto
        self.file_tree_button.connect("toggled", self._on_file_tree_toggled)
        header.pack_start(self.file_tree_button)

        # Botón de ayuda (derecha)
        help_button = Gtk.Button()
        help_button.set_icon_name("help-about-symbolic")
        help_button.set_tooltip_text("Help & About")
        help_button.connect("clicked", self._on_help_clicked)
        header.pack_end(help_button)

        # Botón de temas (derecha, antes de ayuda)
        theme_button = Gtk.Button()
        theme_button.set_icon_name("applications-graphics-symbolic")
        theme_button.set_tooltip_text("Change theme")
        theme_button.connect("clicked", self._on_theme_clicked)
        header.pack_end(theme_button)

        # CSS personalizado
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .rotate-90 { -gtk-icon-transform: rotate(90deg); }

            /* Filas compactas del sidebar */
            .navigation-sidebar row {
                min-height: 24px;
                padding-top: 0;
                padding-bottom: 0;
                font-size: 11px;
            }
            .navigation-sidebar row > box {
                min-height: 24px;
            }
            .navigation-sidebar row label {
                font-size: 11px;
            }

            /* File tree sidebar */
            .file-tree-sidebar row {
                min-height: 24px;
                padding-top: 0;
                padding-bottom: 0;
            }
            .file-tree-sidebar label {
                font-size: 11px;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        toolbar_view.add_top_bar(header)

        # Toast overlay para notificaciones
        self.toast_overlay = Adw.ToastOverlay()

        # Paned principal: sidebars izquierda + terminal
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.paned.set_shrink_start_child(False)
        self.paned.set_shrink_end_child(False)
        self.paned.set_position(250)  # Ancho inicial del sidebar

        # Contenedor izquierdo: sessions + file tree (vertical)
        self.left_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.left_paned.set_shrink_start_child(False)
        self.left_paned.set_shrink_end_child(False)

        # Sidebar de sesiones (arriba)
        self.sidebar = self._create_sidebar()
        self.left_paned.set_start_child(self.sidebar)

        # File tree sidebar (abajo, visible por defecto ocupando 80%)
        self.file_tree = self._create_file_tree()
        self.file_tree.set_visible(True)
        self.left_paned.set_end_child(self.file_tree)

        # Establecer posición inicial después de que la ventana se renderice
        # Sessions ocupa 20%, file tree 80%
        GLib.idle_add(self._set_initial_file_tree_position)

        self.paned.set_start_child(self.left_paned)

        # Content: Terminal (derecha)
        self.terminal_view = TerminalView()
        self.terminal_view.connect("session-ended", self._on_session_ended)
        self.paned.set_end_child(self.terminal_view)

        self.toast_overlay.set_child(self.paned)
        toolbar_view.set_content(self.toast_overlay)

        # Keyboard shortcut F9 para toggle sidebar
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Motion controller para mostrar sidebar al llegar al borde izquierdo
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self._on_mouse_motion)
        self.add_controller(motion_controller)

    def _create_sidebar(self) -> Gtk.Widget:
        """Crea el sidebar con lista de sesiones."""
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header del sidebar con drag handle
        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_title(False)
        sidebar_header.set_show_end_title_buttons(False)
        sidebar_header.add_css_class("flat")

        # Drag handle para reordenar secciones (en un box para poder añadir controllers)
        drag_handle_box = Gtk.Box()
        drag_handle = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        drag_handle.set_opacity(0.5)
        drag_handle.set_tooltip_text("Drag to reorder")
        drag_handle_box.append(drag_handle)
        sidebar_header.pack_start(drag_handle_box)

        # Drag source SOLO en el drag handle
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect(
            "prepare", lambda s, x, y: Gdk.ContentProvider.new_for_value("sessions")
        )
        drag_handle_box.add_controller(drag_source)

        # Botón nueva sesión
        new_btn = Gtk.Button()
        new_btn.set_icon_name("list-add-symbolic")
        new_btn.set_tooltip_text("New session")
        new_btn.connect("clicked", self._on_new_session_clicked)
        sidebar_header.pack_start(new_btn)

        # Botón split horizontal (paneles lado a lado)
        split_h_button = Gtk.Button()
        split_h_button.set_icon_name("view-dual-symbolic")
        split_h_button.set_tooltip_text("Split horizontally")
        split_h_button.connect("clicked", self._on_split_horizontal)
        sidebar_header.pack_start(split_h_button)

        # Botón split vertical (paneles apilados)
        split_v_button = Gtk.Button()
        split_v_icon = Gtk.Image.new_from_icon_name("view-dual-symbolic")
        split_v_icon.add_css_class("rotate-90")
        split_v_button.set_child(split_v_icon)
        split_v_button.set_tooltip_text("Split vertically")
        split_v_button.connect("clicked", self._on_split_vertical)
        sidebar_header.pack_start(split_v_button)

        # Botón refresh (derecha)
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh sessions")
        refresh_btn.connect("clicked", lambda b: self._refresh_sessions())
        sidebar_header.pack_end(refresh_btn)

        sidebar_box.append(sidebar_header)

        # Lista de sesiones
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.sessions_list = Gtk.ListBox()
        self.sessions_list.add_css_class("navigation-sidebar")
        self.sessions_list.set_selection_mode(Gtk.SelectionMode.NONE)

        # Placeholder cuando no hay sesiones
        self.sessions_list.set_placeholder(self._create_empty_placeholder())

        scrolled.set_child(self.sessions_list)
        sidebar_box.append(scrolled)

        # Drop target solo en el header para recibir otras secciones
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop_target.connect("drop", self._on_sidebar_section_drop)
        drop_target.connect("enter", self._on_sidebar_section_enter)
        drop_target.connect("leave", self._on_sidebar_section_leave)
        sidebar_header.add_controller(drop_target)

        self._sidebar_box = sidebar_box
        self._sidebar_header = sidebar_header
        return sidebar_box

    def _create_file_tree(self) -> Gtk.Widget:
        """Crea el sidebar del árbol de archivos."""
        # Widget FileTree directamente (sin header separado)
        self.file_tree_widget = FileTree()
        self.file_tree_widget.set_vexpand(True)

        # Drag source en el drag handle del FileTree
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect(
            "prepare", lambda s, x, y: Gdk.ContentProvider.new_for_value("filetree")
        )
        self.file_tree_widget.drag_handle_box.add_controller(drag_source)

        # Drop target en el drag handle para recibir otras secciones
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop_target.connect("drop", self._on_sidebar_section_drop)
        drop_target.connect("enter", self._on_sidebar_section_enter)
        drop_target.connect("leave", self._on_sidebar_section_leave)
        self.file_tree_widget.drag_handle_box.add_controller(drop_target)

        self._file_tree_box = self.file_tree_widget
        self._file_tree_header = self.file_tree_widget.drag_handle_box
        return self.file_tree_widget

    def _create_empty_placeholder(self) -> Gtk.Widget:
        """Crea el placeholder para cuando no hay sesiones."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(12)
        box.set_margin_end(12)

        icon = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("dim-label")
        box.append(icon)

        label = Gtk.Label(label="No sessions")
        label.add_css_class("dim-label")
        label.add_css_class("title-3")
        box.append(label)

        sublabel = Gtk.Label(label="Click + to create one")
        sublabel.add_css_class("dim-label")
        box.append(sublabel)

        return box

    def _refresh_sessions(self):
        """Actualiza la lista de sesiones (locales y remotas)."""
        # Guardar estado de expansión y separar filas locales de remotas
        remote_rows = []
        index = 0
        while True:
            row = self.sessions_list.get_row_at_index(index)
            if row is None:
                break
            if index == 0 and self._expanded_sessions is None:
                self._expanded_sessions = set()
            if isinstance(row, RemoteSessionRow):
                key = f"remote:{row.user}@{row.host}:{row.session.name}"
                if row.get_expanded():
                    self._expanded_sessions.add(key)
                elif key in self._expanded_sessions:
                    self._expanded_sessions.discard(key)
                remote_rows.append(row)
            elif isinstance(row, SessionRow):
                key = f"local:{row.session.name}"
                if row.get_expanded():
                    self._expanded_sessions.add(key)
                elif key in self._expanded_sessions:
                    self._expanded_sessions.discard(key)
            index += 1

        # Limpiar solo filas locales (mantener remotas hasta que lleguen datos nuevos)
        index = 0
        while True:
            row = self.sessions_list.get_row_at_index(index)
            if row is None:
                break
            if isinstance(row, SessionRow):
                self.sessions_list.remove(row)
            else:
                index += 1

        # Verificar si tmux está disponible
        if not self.tmux.is_available:
            self._show_error_placeholder("tmux not installed")
            return

        # Obtener sesiones locales (rápido, no bloquea)
        sessions = self.tmux.list_sessions()

        # Agregar filas de sesiones locales AL INICIO (antes de las remotas)
        for i, session in enumerate(sessions):
            row = SessionRow(session)
            row.connect("delete-requested", self._on_delete_requested)
            row.connect("window-selected", self._on_window_selected)
            row.connect("rename-session-requested", self._on_rename_session_requested)
            row.connect("rename-window-requested", self._on_rename_window_requested)
            row.connect("new-window-requested", self._on_new_window_requested)
            row.connect("exit-window-requested", self._on_exit_window_requested)
            row.connect("swap-windows-requested", self._on_swap_windows_requested)
            # Restaurar estado de expansión
            key = f"local:{session.name}"
            if self._expanded_sessions is None:
                if session.attached:
                    row.set_expanded(True)
            elif key in self._expanded_sessions:
                row.set_expanded(True)
            self.sessions_list.insert(row, i)

        # Inicializar el set si es la primera carga
        if self._expanded_sessions is None:
            self._expanded_sessions = set(f"local:{s.name}" for s in sessions if s.attached)

        # Cargar sesiones remotas en background (no bloquea UI)
        if self._remote_clients:
            self._refresh_remote_sessions_async()

    def _refresh_remote_sessions_async(self):
        """Carga sesiones remotas en un thread separado."""
        import threading

        # Copiar clientes para evitar modificaciones durante el thread
        clients_snapshot = list(self._remote_clients.items())

        def fetch_remote():
            if self._closing:
                return

            results = []
            hosts_without_tmux = []

            for client_key, client in clients_snapshot:
                if self._closing:
                    return
                try:
                    # Verificar si tmux está disponible en el host remoto
                    if client.is_connected() and not client.is_tmux_available():
                        hosts_without_tmux.append(f"{client.user}@{client.host}")
                        continue

                    remote_sessions = client.list_sessions()
                    results.append((client, remote_sessions))
                except Exception:
                    pass  # Ignorar errores de conexión

            if self._closing:
                return

            # Actualizar UI en el hilo principal
            GLib.idle_add(self._add_remote_sessions_to_ui, results, hosts_without_tmux)

        thread = threading.Thread(target=fetch_remote, daemon=True)
        thread.start()

    def _add_remote_sessions_to_ui(self, results: list, hosts_without_tmux: list = None):
        """Agrega sesiones remotas a la UI (llamar desde hilo principal)."""
        if self._closing:
            return False

        # Mostrar toast si hay hosts sin tmux instalado
        if hosts_without_tmux:
            for host in hosts_without_tmux:
                self._show_toast(f"tmux not installed on {host}")

        # Primero eliminar todas las filas remotas existentes
        index = 0
        while True:
            row = self.sessions_list.get_row_at_index(index)
            if row is None:
                break
            if isinstance(row, RemoteSessionRow):
                self.sessions_list.remove(row)
            else:
                index += 1

        # Agregar las nuevas filas remotas
        for client, remote_sessions in results:
            for session in remote_sessions:
                row = RemoteSessionRow(
                    session=session,
                    host=client.host,
                    user=client.user,
                    port=client.port,
                    connected=True,
                )
                row.connect("window-selected", self._on_remote_window_selected)
                row.connect("rename-requested", self._on_remote_rename_requested)
                row.connect("kill-requested", self._on_remote_kill_requested)
                row.connect("new-window-requested", self._on_remote_new_window_requested)
                # Restaurar estado de expansión
                key = f"remote:{client.user}@{client.host}:{session.name}"
                if self._expanded_sessions and key in self._expanded_sessions:
                    row.set_expanded(True)
                self.sessions_list.append(row)

        return False  # No repetir

    def _show_error_placeholder(self, message: str):
        """Muestra un mensaje de error en el placeholder."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(12)
        box.set_margin_end(12)

        icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("error")
        box.append(icon)

        title = Gtk.Label(label=message)
        title.add_css_class("error")
        title.add_css_class("title-3")
        box.append(title)

        # Si es error de tmux no instalado, mostrar instrucciones
        if "tmux" in message.lower() and "install" in message.lower():
            subtitle = Gtk.Label(
                label="tmux is required to run this application.\nInstall it using your package manager:"
            )
            subtitle.add_css_class("dim-label")
            subtitle.set_justify(Gtk.Justification.CENTER)
            box.append(subtitle)

            # Comandos de instalación
            commands_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            commands_box.set_margin_top(8)

            install_cmds = [
                ("Debian/Ubuntu:", "sudo apt install tmux"),
                ("Fedora:", "sudo dnf install tmux"),
                ("Arch:", "sudo pacman -S tmux"),
            ]

            for distro, cmd in install_cmds:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.set_halign(Gtk.Align.CENTER)

                distro_label = Gtk.Label(label=distro)
                distro_label.add_css_class("dim-label")
                distro_label.set_xalign(1)
                distro_label.set_size_request(100, -1)
                row.append(distro_label)

                cmd_label = Gtk.Label(label=cmd)
                cmd_label.add_css_class("monospace")
                cmd_label.set_xalign(0)
                cmd_label.set_selectable(True)
                row.append(cmd_label)

                commands_box.append(row)

            box.append(commands_box)

            # Nota sobre reiniciar
            restart_label = Gtk.Label(label="Restart the application after installing tmux.")
            restart_label.add_css_class("dim-label")
            restart_label.set_margin_top(12)
            box.append(restart_label)

        self.sessions_list.set_placeholder(box)

    def _on_new_session_clicked(self, button: Gtk.Button):
        """Muestra diálogo para crear nueva sesión o conectar a remota."""
        dialog = Adw.Window(transient_for=self)
        dialog.set_title("Sessions")
        dialog.set_default_size(420, 500)
        dialog.set_modal(True)

        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        dialog.set_content(toolbar_view)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header)

        # Scroll para contenido
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Contenido
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        # Grupo: Sesión Local
        local_group = Adw.PreferencesGroup(title="Local Session")

        local_row = Adw.ActionRow(
            title="Create local session",
            subtitle="Start a new tmux session on this machine"
        )
        local_row.set_activatable(True)
        local_icon = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
        local_row.add_prefix(local_icon)
        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        local_row.add_suffix(arrow)
        local_row.connect("activated", lambda r: self._show_create_local_dialog(dialog))
        local_group.add(local_row)

        content.append(local_group)

        # Grupo: Conexiones Remotas Guardadas
        saved_hosts = remote_hosts_manager.get_hosts()

        remote_group = Adw.PreferencesGroup(title="Remote Connections")

        if saved_hosts:
            for host in saved_hosts:
                port_suffix = f":{host.port}" if host.port != "22" else ""
                host_row = Adw.ActionRow(
                    title=host.name,
                    subtitle=f"{host.user}@{host.host}{port_suffix}"
                )
                host_row.set_activatable(True)

                # Icono de servidor
                server_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
                host_row.add_prefix(server_icon)

                # Botón editar
                edit_btn = Gtk.Button()
                edit_btn.set_icon_name("document-edit-symbolic")
                edit_btn.set_valign(Gtk.Align.CENTER)
                edit_btn.add_css_class("flat")
                edit_btn.set_tooltip_text("Edit connection")
                edit_btn.connect(
                    "clicked", lambda b, h=host: self._show_edit_host_dialog(dialog, h)
                )
                host_row.add_suffix(edit_btn)

                # Botón eliminar
                delete_btn = Gtk.Button()
                delete_btn.set_icon_name("user-trash-symbolic")
                delete_btn.set_valign(Gtk.Align.CENTER)
                delete_btn.add_css_class("flat")
                delete_btn.add_css_class("error")
                delete_btn.set_tooltip_text("Delete connection")
                delete_btn.connect(
                    "clicked",
                    lambda b, h=host, d=dialog: self._confirm_delete_host(d, h)
                )
                host_row.add_suffix(delete_btn)

                # Flecha para conectar
                connect_arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
                host_row.add_suffix(connect_arrow)

                # Click para conectar
                host_row.connect(
                    "activated",
                    lambda r, h=host: self._show_connect_to_host_dialog(dialog, h)
                )
                remote_group.add(host_row)
        else:
            # Placeholder si no hay hosts
            empty_row = Adw.ActionRow(
                title="No saved connections",
                subtitle="Add a remote connection to get started"
            )
            empty_row.set_sensitive(False)
            empty_icon = Gtk.Image.new_from_icon_name("network-offline-symbolic")
            empty_icon.add_css_class("dim-label")
            empty_row.add_prefix(empty_icon)
            remote_group.add(empty_row)

        # Botón agregar nueva conexión
        add_row = Adw.ActionRow(
            title="Add new connection",
            subtitle="Configure a new remote server"
        )
        add_row.set_activatable(True)
        add_row.add_css_class("accent")
        add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        add_row.add_prefix(add_icon)
        add_arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        add_row.add_suffix(add_arrow)
        add_row.connect("activated", lambda r: self._show_add_host_dialog(dialog))
        remote_group.add(add_row)

        content.append(remote_group)

        scrolled.set_child(content)
        toolbar_view.set_content(scrolled)

        dialog.present()

    def _show_create_local_dialog(self, parent_dialog):
        """Muestra diálogo para crear sesión local."""
        dialog = Adw.MessageDialog(
            transient_for=parent_dialog,
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
            dlg.close()
            if response == "create":
                name = entry.get_text().strip()
                if name:
                    parent_dialog.set_focus(None)
                    parent_dialog.close()
                    if self.tmux.create_session(name):
                        self._refresh_sessions()
                        GLib.idle_add(self._attach_to_session, name)
                    else:
                        self._show_toast("Failed to create session")

        dialog.connect("response", on_response)
        dialog.present()

    def _show_add_host_dialog(self, parent_dialog):
        """Muestra diálogo para agregar nueva conexión remota."""
        dialog = Adw.Window(transient_for=parent_dialog)
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
                self._show_toast("Name, host and user are required")
                return

            from datetime import datetime, timezone
            new_host = RemoteHost(
                name=name,
                host=host,
                user=user,
                port=port,
                last_used=datetime.now(timezone.utc).isoformat()
            )
            remote_hosts_manager.add_host(new_host)

            dialog.set_focus(None)
            dialog.close()
            parent_dialog.set_focus(None)
            parent_dialog.close()
            # Reabrir diálogo principal para mostrar el nuevo host
            self._on_new_session_clicked(None)

        save_btn.connect("clicked", on_save_clicked)
        dialog.present()
        name_entry.grab_focus()

    def _show_edit_host_dialog(self, parent_dialog, host: RemoteHost):
        """Muestra diálogo para editar una conexión remota."""
        dialog = Adw.Window(transient_for=parent_dialog)
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
                self._show_toast("Name, host and user are required")
                return

            # Eliminar viejo y agregar nuevo
            remote_hosts_manager.remove_host(host.host, host.user, host.port)

            from datetime import datetime, timezone
            updated_host = RemoteHost(
                name=name,
                host=new_host_addr,
                user=user,
                port=port,
                last_used=datetime.now(timezone.utc).isoformat()
            )
            remote_hosts_manager.add_host(updated_host)

            dialog.set_focus(None)
            dialog.close()
            parent_dialog.set_focus(None)
            parent_dialog.close()
            # Reabrir diálogo principal para mostrar cambios
            self._on_new_session_clicked(None)

        save_btn.connect("clicked", on_save_clicked)
        dialog.present()

    def _confirm_delete_host(self, parent_dialog, host: RemoteHost):
        """Confirma eliminación de un host guardado."""
        dialog = Adw.MessageDialog(
            transient_for=parent_dialog,
            heading="Delete Connection?",
            body=f"Are you sure you want to delete '{host.name}'?\n"
                 f"({host.user}@{host.host})",
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(dlg, response):
            dlg.close()
            if response == "delete":
                remote_hosts_manager.remove_host(host.host, host.user, host.port)
                parent_dialog.close()
                # Reabrir diálogo principal
                self._on_new_session_clicked(None)

        dialog.connect("response", on_response)
        dialog.present()

    def _show_connect_to_host_dialog(self, parent_dialog, host: RemoteHost):
        """Muestra diálogo para conectar a un host guardado."""
        dialog = Adw.Window(transient_for=parent_dialog)
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

        group = Adw.PreferencesGroup(
            title="Session",
            description=f"Connect to {host.user}@{host.host}"
        )

        name_entry = Adw.EntryRow(title="Session name")
        name_entry.set_text("")
        group.add(name_entry)

        attach_row = Adw.SwitchRow(
            title="Attach to existing",
            subtitle="Connect to an existing session instead of creating new"
        )
        group.add(attach_row)

        # Ocultar nombre si attach está activo
        def on_attach_toggled(row, _pspec):
            name_entry.set_sensitive(not row.get_active())

        attach_row.connect("notify::active", on_attach_toggled)

        content.append(group)
        toolbar_view.set_content(content)

        def on_connect_clicked(btn):
            dialog.set_focus(None)
            dialog.close()
            parent_dialog.set_focus(None)
            parent_dialog.close()

            if attach_row.get_active():
                self._attach_remote_existing(host.host, host.user, host.port)
            else:
                name = name_entry.get_text().strip()
                if not name:
                    self._show_toast("Session name is required")
                    return
                self._create_remote_session(name, host.host, host.user, host.port)

        connect_btn.connect("clicked", on_connect_clicked)
        name_entry.connect(
            "apply", lambda e: [dialog.set_focus(None), on_connect_clicked(connect_btn)]
        )

        dialog.present()
        name_entry.grab_focus()

    def _attach_to_session(self, name: str, window_index: int | None = None):
        """Adjunta al terminal a una sesión/ventana."""
        command = self.tmux.get_attach_command(name, window_index)
        self.terminal_view.attach_session(name, command)
        self.terminal_view.grab_focus()
        return False

    def _get_remote_client(self, host: str, user: str, port: str) -> RemoteTmuxClient:
        """Obtiene o crea un cliente remoto para el host dado."""
        key = f"{user}@{host}:{port}"
        if key not in self._remote_clients:
            self._remote_clients[key] = RemoteTmuxClient(host, user, port)
        return self._remote_clients[key]

    def _create_remote_session(self, name: str, host: str, user: str, port: str):
        """Crea una sesión en un servidor remoto via SSH."""
        from datetime import datetime, timezone

        client = self._get_remote_client(host, user, port)
        command = client.get_new_session_command(name)

        # Ejecutar en el terminal (maneja password prompts)
        self.terminal_view.attach_session(f"{name}@{host}", command)
        self.terminal_view.grab_focus()

        # Guardar host para uso futuro
        remote_host = RemoteHost(
            name=name,
            host=host,
            user=user,
            port=port,
            last_used=datetime.now(timezone.utc).isoformat()
        )
        remote_hosts_manager.add_host(remote_host)

        # Refresh que reintenta hasta encontrar sesiones
        self._schedule_remote_refresh_until_sessions_found(host, user, port)

    def _attach_remote_existing(self, host: str, user: str, port: str):
        """Muestra diálogo para seleccionar sesión remota existente."""
        from datetime import datetime, timezone

        # Guardar host para uso futuro
        remote_host = RemoteHost(
            name=f"{user}@{host}",
            host=host,
            user=user,
            port=port,
            last_used=datetime.now(timezone.utc).isoformat()
        )
        remote_hosts_manager.add_host(remote_host)

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Attach to Remote Session",
            body=f"Enter the session name on {host}:",
        )

        entry = Gtk.Entry()
        entry.set_placeholder_text("session-name")
        entry.connect("activate", lambda e: [dialog.set_focus(None), dialog.response("attach")])
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("attach", "Attach")
        dialog.set_response_appearance("attach", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("attach")

        def on_response(dlg, response):
            dlg.set_focus(None)
            dlg.close()
            if response == "attach":
                name = entry.get_text().strip()
                if name:
                    self._attach_remote_session(host, user, port, name)

        dialog.connect("response", on_response)
        dialog.present()

    def _attach_remote_session(
        self, host: str, user: str, port: str, session_name: str, window_index: int | None = None
    ):
        """Adjunta el terminal a una sesión remota via SSH."""
        client = self._get_remote_client(host, user, port)
        command = client.get_attach_command(session_name, window_index)

        display_name = f"{session_name}@{host}"
        if window_index is not None:
            display_name += f":{window_index}"

        self.terminal_view.attach_session(display_name, command)
        self.terminal_view.grab_focus()

        # Refresh para actualizar lista
        self._schedule_remote_refresh_until_sessions_found(host, user, port)

    def _schedule_remote_refresh_until_sessions_found(
        self, host: str, user: str, port: str
    ):
        """Programa refreshes hasta encontrar sesiones del host remoto."""
        import threading

        state = {"found": False}
        key = f"{user}@{host}:{port}"

        def do_check():
            """Ejecuta el check en background y programa el siguiente."""
            if self._closing or state["found"]:
                return False

            if key not in self._remote_clients:
                return False

            # Ejecutar check en background thread
            def background_check():
                if self._closing or state["found"]:
                    return

                client = self._remote_clients.get(key)
                if not client:
                    return

                sessions = client.list_sessions()

                if self._closing:
                    return

                if sessions:
                    state["found"] = True
                    GLib.idle_add(self._refresh_sessions)

            thread = threading.Thread(target=background_check, daemon=True)
            thread.start()

            return True  # Continuar polling hasta que found=True

        # Polling cada 2 segundos hasta encontrar sesiones
        if not self._closing:
            GLib.timeout_add(2000, do_check)

    def _on_remote_window_selected(
        self, row, session_name: str, window_index: int, host: str, user: str, port: str
    ):
        """Conecta a una ventana remota seleccionada."""
        self._attach_remote_session(host, user, port, session_name, window_index)

    def _on_remote_new_window_requested(
        self, row, session_name: str, host: str, user: str, port: str
    ):
        """Muestra diálogo para crear nueva ventana remota."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="New Window",
            body=f"Enter a name for the new window in '{session_name}' on {host}:",
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
                window_name = entry.get_text().strip() or None
                client = self._get_remote_client(host, user, port)
                if client.create_window(session_name, window_name):
                    self._refresh_sessions()
                else:
                    self._show_toast("Failed to create remote window")

        dialog.connect("response", on_response)
        dialog.present()

    def _on_remote_rename_requested(self, row, name: str, host: str, user: str, port: str):
        """Muestra diálogo para renombrar sesión remota."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Rename Remote Session",
            body=f"Enter new name for '{name}' on {host}:",
        )

        entry = Gtk.Entry()
        entry.set_text(name)
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
                if new_name and new_name != name:
                    client = self._get_remote_client(host, user, port)
                    if client.rename_session(name, new_name):
                        self._refresh_sessions()
                    else:
                        self._show_toast("Failed to rename remote session")

        dialog.connect("response", on_response)
        dialog.present()

    def _on_remote_kill_requested(self, row, name: str, host: str, user: str, port: str):
        """Confirma y elimina una sesión remota."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Kill Remote Session?",
            body=f"Are you sure you want to kill '{name}' on {host}?\n"
                 "This will terminate all processes in the session.",
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("kill", "Kill")
        dialog.set_response_appearance("kill", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(dlg, response):
            dlg.close()
            if response == "kill":
                client = self._get_remote_client(host, user, port)
                if client.kill_session(name):
                    self._refresh_sessions()
                else:
                    self._show_toast("Failed to kill remote session")

        dialog.connect("response", on_response)
        dialog.present()

    def _on_window_selected(self, row, session_name: str, window_index: int):
        """Maneja la selección de una ventana específica."""
        self._attach_to_session(session_name, window_index)
        # Refresh con pequeño delay para que tmux procese el attach
        GLib.timeout_add(150, self._refresh_sessions)

    def _on_rename_session_requested(self, row, session_name: str):
        """Muestra diálogo para renombrar sesión."""
        dialog = Adw.MessageDialog(
            transient_for=self,
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

        dialog.connect("response", self._on_rename_session_response, session_name, entry)
        dialog.present()

    def _on_rename_session_response(self, dialog, response: str, old_name: str, entry: Gtk.Entry):
        """Maneja la respuesta del diálogo de renombrar sesión."""
        dialog.set_focus(None)
        dialog.close()
        if response == "rename":
            new_name = entry.get_text().strip()
            if new_name and new_name != old_name:
                if self.tmux.rename_session(old_name, new_name):
                    self._refresh_sessions()
                else:
                    self._show_toast("Failed to rename session")

    def _on_rename_window_requested(
        self, row, session_name: str, window_index: int, current_name: str
    ):
        """Muestra diálogo para renombrar ventana."""
        dialog = Adw.MessageDialog(
            transient_for=self,
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

        dialog.connect(
            "response", self._on_rename_window_response, session_name, window_index, entry
        )
        dialog.present()

    def _on_rename_window_response(
        self, dialog, response: str, session_name: str, window_index: int, entry: Gtk.Entry
    ):
        """Maneja la respuesta del diálogo de renombrar ventana."""
        dialog.set_focus(None)
        dialog.close()
        if response == "rename":
            new_name = entry.get_text().strip()
            if new_name:
                if self.tmux.rename_window(session_name, window_index, new_name):
                    self._refresh_sessions()
                else:
                    self._show_toast("Failed to rename window")

    def _on_new_window_requested(self, row, session_name: str):
        """Muestra diálogo para crear nueva ventana."""
        dialog = Adw.MessageDialog(
            transient_for=self,
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

        dialog.connect("response", self._on_new_window_response, session_name, entry)
        dialog.present()

    def _on_new_window_response(self, dialog, response: str, session_name: str, entry: Gtk.Entry):
        """Maneja la respuesta del diálogo de nueva ventana."""
        dialog.set_focus(None)
        dialog.close()
        if response == "create":
            name = entry.get_text().strip() or None
            if self.tmux.create_window(session_name, name):
                self._refresh_sessions()
            else:
                self._show_toast("Failed to create window")

    def _on_exit_window_requested(self, row, session_name: str, window_index: int):
        """Envía exit a una ventana (cierre limpio)."""
        self.tmux.exit_window(session_name, window_index)
        # Refresh rápido + respaldo para shells lentos
        GLib.timeout_add(150, self._refresh_sessions)
        GLib.timeout_add(1000, self._refresh_sessions)

    def _on_swap_windows_requested(self, row, session_name: str, src_index: int, dst_index: int):
        """Intercambia dos ventanas."""
        if self.tmux.swap_windows(session_name, src_index, dst_index):
            self._refresh_sessions()
        else:
            self._show_toast("Failed to swap windows")

    def _on_delete_requested(self, row: SessionRow, session_name: str):
        """Maneja la solicitud de eliminar una sesión."""
        body = (
            f"Are you sure you want to delete '{session_name}'?\n"
            "This will terminate all processes in the session."
        )
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Session?",
            body=body,
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect("response", self._on_delete_response, session_name)
        dialog.present()

    def _on_delete_response(self, dialog: Adw.MessageDialog, response: str, session_name: str):
        """Maneja la confirmación de eliminar sesión."""
        dialog.close()
        if response == "delete":
            if self.tmux.kill_session(session_name):
                self._refresh_sessions()
            else:
                self._show_toast("Failed to delete session")

    def _on_session_ended(self, terminal_view: TerminalView):
        """Maneja cuando termina una sesión en el terminal."""
        self._refresh_sessions()

    def _on_refresh_timeout(self) -> bool:
        """Callback del timeout de auto-refresh."""
        if self._closing:
            return False  # Detener el timeout
        self._refresh_sessions()
        return True

    def _show_toast(self, message: str):
        """Muestra un toast con un mensaje."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _on_sidebar_toggled(self, button: Gtk.ToggleButton):
        """Maneja el toggle del sidebar con animación."""
        # Cancelar animación previa si existe
        if self._animation is not None:
            self._animation.pause()
            self._animation = None

        if button.get_active():
            # Mostrar sidebar con animación
            self.left_paned.set_visible(True)
            # Calcular ancho natural del sidebar
            natural_width = self._get_sidebar_natural_width()
            self._animate_sidebar(0, natural_width)
        else:
            # Ocultar sidebar sin animación
            self._sidebar_position = self.paned.get_position()
            self.paned.set_position(0)
            self.left_paned.set_visible(False)

    def _on_file_tree_toggled(self, button: Gtk.ToggleButton):
        """Maneja el toggle del file tree sidebar."""
        # Cancelar animación previa si existe
        if self._file_tree_animation is not None:
            self._file_tree_animation.pause()
            self._file_tree_animation = None

        if button.get_active():
            # Mostrar file tree con animación
            self.file_tree.set_visible(True)
            # Altura del left_paned
            left_paned_height = self.left_paned.get_height()
            # Sessions 30%, file tree 70%
            target_pos = int(left_paned_height * 0.3)
            self._animate_file_tree(left_paned_height, target_pos)
        else:
            # Ocultar file tree sin animación
            self._file_tree_position = self.left_paned.get_position()
            # Mover el paned al final para ocultar
            self.left_paned.set_position(self.left_paned.get_height())
            self.file_tree.set_visible(False)

    def _set_initial_file_tree_position(self) -> bool:
        """Establece la posición inicial del file tree (sessions 30%, file tree 70%)."""
        left_paned_height = self.left_paned.get_height()
        if left_paned_height > 0:
            # Sessions ocupa 30% arriba, file tree 70% abajo
            self.left_paned.set_position(int(left_paned_height * 0.3))
            return False  # No repetir
        return True  # Reintentar si aún no tiene altura

    def _get_sidebar_natural_width(self) -> int:
        """Calcula el ancho natural del sidebar basado en su contenido."""
        # Obtener el tamaño preferido del sidebar
        min_size, natural_size = self.sidebar.get_preferred_size()
        natural_width = natural_size.width if natural_size else 220
        # Si hay una posición guardada, usarla como referencia
        if self._sidebar_position > 0:
            return max(natural_width, self._sidebar_position, 220)
        # Usar el ancho natural con margen, mínimo 220 para los botones
        return max(natural_width, 220)

    def _animate_sidebar(self, from_pos: int, to_pos: int, hide_after: bool = False):
        """Anima la posición del sidebar."""
        target = Adw.CallbackAnimationTarget.new(self._on_animation_value)
        self._animation = Adw.TimedAnimation.new(
            self.paned,
            from_pos,
            to_pos,
            250,  # duración en ms
            target,
        )
        self._animation.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        if hide_after:
            self._animation.connect("done", self._on_hide_animation_done)
        self._animation.play()

    def _animate_file_tree(self, from_pos: int, to_pos: int):
        """Anima la posición del file tree sidebar."""
        target = Adw.CallbackAnimationTarget.new(self._on_file_tree_animation_value)
        self._file_tree_animation = Adw.TimedAnimation.new(
            self.left_paned,
            from_pos,
            to_pos,
            250,  # duración en ms
            target,
        )
        self._file_tree_animation.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        self._file_tree_animation.play()

    def _on_animation_value(self, value: float):
        """Callback de la animación para actualizar posición."""
        self.paned.set_position(int(value))

    def _on_file_tree_animation_value(self, value: float):
        """Callback de la animación para actualizar posición del file tree."""
        self.left_paned.set_position(int(value))

    def _on_hide_animation_done(self, animation):
        """Oculta el sidebar después de la animación de cierre."""
        self.left_paned.set_visible(False)

    def _on_mouse_motion(self, controller, x: float, y: float):
        """Muestra el sidebar cuando el cursor llega al borde izquierdo."""
        # Si el sidebar está oculto y el cursor está en el borde izquierdo
        if not self.sidebar_button.get_active() and x <= 5:
            self.sidebar_button.set_active(True)

    def _on_split_horizontal(self, button: Gtk.Button):
        """Divide el panel actual horizontalmente (lado a lado)."""
        current = self.terminal_view.current_session
        if current:
            self.tmux.split_horizontal()
        else:
            self._show_toast("Select a session and window first")

    def _on_split_vertical(self, button: Gtk.Button):
        """Divide el panel actual verticalmente (apilados)."""
        current = self.terminal_view.current_session
        if current:
            self.tmux.split_vertical()
        else:
            self._show_toast("Select a session and window first")

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        """Maneja atajos de teclado."""
        if keyval == Gdk.KEY_F9:
            self.sidebar_button.set_active(not self.sidebar_button.get_active())
            return True
        if keyval == Gdk.KEY_F10:
            self.file_tree_button.set_active(not self.file_tree_button.get_active())
            return True
        return False

    def _on_sidebar_section_drop(self, target, value, x, y) -> bool:
        """Intercambia las secciones del sidebar."""
        if not isinstance(value, str):
            return False

        # Determinar cuál header recibió el drop
        target_widget = target.get_widget()

        # Si sessions header recibe filetree o filetree header recibe sessions, intercambiar
        is_sessions_target = target_widget == self._sidebar_header
        is_filetree_target = target_widget == self._file_tree_header
        is_filetree_source = value == "filetree"
        is_sessions_source = value == "sessions"

        # Solo intercambiar si son secciones diferentes
        should_swap = (
            (is_sessions_target and is_filetree_source)
            or (is_filetree_target and is_sessions_source)
        )
        if should_swap:
            self._swap_sidebar_sections()
            return True

        return False

    def _on_sidebar_section_enter(self, target, x, y):
        """Resalta cuando hay drag sobre una sección."""
        target.get_widget().add_css_class("suggested-action")
        return Gdk.DragAction.MOVE

    def _on_sidebar_section_leave(self, target):
        """Quita resaltado al salir el drag."""
        target.get_widget().remove_css_class("suggested-action")

    def _swap_sidebar_sections(self):
        """Intercambia las posiciones de sessions y file tree."""
        # Obtener las secciones actuales
        start_child = self.left_paned.get_start_child()
        end_child = self.left_paned.get_end_child()

        # Guardar posición actual para invertirla
        current_pos = self.left_paned.get_position()
        total_height = self.left_paned.get_height()

        # Desconectar hijos
        self.left_paned.set_start_child(None)
        self.left_paned.set_end_child(None)

        # Intercambiar
        self.left_paned.set_start_child(end_child)
        self.left_paned.set_end_child(start_child)

        # Invertir la posición (si sessions ocupaba 30%, ahora ocupa 70%)
        if total_height > 0:
            new_pos = total_height - current_pos
            self.left_paned.set_position(new_pos)

    def _on_help_clicked(self, button: Gtk.Button):
        """Muestra el diálogo de ayuda."""
        dialog = Adw.Window(transient_for=self)
        dialog.set_title("Help - TmuxGUI")
        dialog.set_default_size(500, 600)
        dialog.set_modal(True)

        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        dialog.set_content(toolbar_view)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header)

        # Scroll principal
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Contenido
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # Logo y título
        logo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        logo_box.set_halign(Gtk.Align.CENTER)

        logo = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
        logo.set_pixel_size(64)
        logo_box.append(logo)

        title = Gtk.Label(label="TmuxGUI")
        title.add_css_class("title-1")
        logo_box.append(title)

        version = Gtk.Label(label="Version 0.4.1")
        version.add_css_class("dim-label")
        logo_box.append(version)

        subtitle = Gtk.Label(label="GNOME native frontend for tmux")
        subtitle.add_css_class("dim-label")
        logo_box.append(subtitle)

        content.append(logo_box)
        content.append(Gtk.Separator())

        # Sección: Features
        features_group = Adw.PreferencesGroup(title="Features")

        features = [
            ("Session Management", "Create, rename, delete tmux sessions"),
            ("Window Management", "Create, rename, close and reorder windows"),
            ("Remote Sessions", "Connect to remote hosts via SSH"),
            ("Integrated Terminal", "VTE terminal with full tmux support"),
            ("File Browser", "Navigate filesystem with CRUD operations"),
            ("Drag and Drop", "Drag files/folders to terminal, reorder sections"),
        ]

        for title_text, desc in features:
            row = Adw.ActionRow(title=title_text, subtitle=desc)
            row.set_activatable(False)
            features_group.add(row)

        content.append(features_group)

        # Sección: Keyboard Shortcuts
        shortcuts_group = Adw.PreferencesGroup(title="Keyboard Shortcuts")

        shortcuts = [
            ("F9", "Toggle sessions sidebar"),
            ("F10", "Toggle file browser"),
            ("Ctrl+B d", "Detach from tmux session"),
            ("Ctrl+B c", "Create new window (in tmux)"),
            ("Ctrl+B n / p", "Next / Previous window"),
            ("Ctrl+B %", "Split pane horizontally"),
            ("Ctrl+B \"", "Split pane vertically"),
        ]

        for shortcut, desc in shortcuts:
            row = Adw.ActionRow(title=shortcut, subtitle=desc)
            row.set_activatable(False)
            shortcuts_group.add(row)

        content.append(shortcuts_group)

        # Sección: Usage Tips
        tips_group = Adw.PreferencesGroup(title="Quick Start")

        tips = [
            ("1. Create a session", "Click + button for local or remote sessions"),
            ("2. Remote hosts", "Save SSH connections for quick access"),
            ("3. Select a window", "Click on any window to attach terminal"),
            ("4. Drag to terminal", "Drag files/folders to paste their path"),
            ("5. Detach", "Press Ctrl+B d to detach from session"),
        ]

        for tip_title, tip_desc in tips:
            row = Adw.ActionRow(title=tip_title, subtitle=tip_desc)
            row.set_activatable(False)
            tips_group.add(row)

        content.append(tips_group)

        content.append(Gtk.Separator())

        # Sección: About
        about_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        about_box.set_halign(Gtk.Align.CENTER)

        author_label = Gtk.Label(label="Author")
        author_label.add_css_class("heading")
        about_box.append(author_label)

        author_name = Gtk.Label(label="Homero Thompson del Lago del Terror")
        about_box.append(author_name)

        content.append(about_box)

        # Copyright
        copyright_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        copyright_box.set_halign(Gtk.Align.CENTER)
        copyright_box.set_margin_top(12)

        copyright_label = Gtk.Label(label="Copyright 2026")
        copyright_label.add_css_class("dim-label")
        copyright_box.append(copyright_label)

        license_label = Gtk.Label(label="MIT License")
        license_label.add_css_class("dim-label")
        copyright_box.append(license_label)

        github_label = Gtk.Label(label="github.com/vdirienzo/gnome-tmux")
        github_label.add_css_class("dim-label")
        copyright_box.append(github_label)

        content.append(copyright_box)

        scrolled.set_child(content)
        toolbar_view.set_content(scrolled)

        dialog.present()

    def _on_theme_clicked(self, button: Gtk.Button):
        """Muestra el diálogo de selección de tema."""
        dialog = Adw.Window(transient_for=self)
        dialog.set_title("Theme")
        dialog.set_default_size(350, 450)
        dialog.set_modal(True)

        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        dialog.set_content(toolbar_view)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header)

        # Scroll
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Contenido
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        # Grupo de temas
        themes_group = Adw.PreferencesGroup(title="Select Theme")

        current_theme = theme_manager.get_current_theme()
        themes = theme_manager.get_available_themes()

        # Crear un grupo de check buttons
        first_check = None
        for theme_id, theme_data in themes.items():
            row = Adw.ActionRow(title=theme_data["name"])
            row.set_activatable(True)

            check = Gtk.CheckButton()
            check.set_active(theme_id == current_theme)
            if first_check is None:
                first_check = check
            else:
                check.set_group(first_check)

            check.connect("toggled", self._on_theme_toggled, theme_id)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            themes_group.add(row)

        content.append(themes_group)

        scrolled.set_child(content)
        toolbar_view.set_content(scrolled)

        dialog.present()

    def _on_theme_toggled(self, check: Gtk.CheckButton, theme_id: str):
        """Aplica el tema seleccionado."""
        if check.get_active():
            theme_manager.apply_theme(theme_id)

    def do_close_request(self) -> bool:
        """Maneja el cierre de la ventana."""
        import os
        import signal

        # Marcar que estamos cerrando para detener threads de polling
        self._closing = True

        # Cancelar auto-refresh
        if self._refresh_timeout_id is not None:
            GLib.source_remove(self._refresh_timeout_id)
            self._refresh_timeout_id = None

        # Matar proceso del terminal VTE si existe
        if hasattr(self, 'terminal_view') and self.terminal_view._pid is not None:
            try:
                os.kill(self.terminal_view._pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass

        # Cerrar conexiones SSH (forzar cierre)
        for client in self._remote_clients.values():
            client.close_connection(force=True)
        self._remote_clients.clear()

        # Forzar salida del proceso para evitar que threads bloqueen
        GLib.timeout_add(500, lambda: os._exit(0))

        return False
