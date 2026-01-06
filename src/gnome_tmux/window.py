"""
window.py - Ventana principal de gnome-tmux

Autor: Homero Thompson del Lago del Terror
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, GObject, Gtk

from .tmux_client import TmuxClient
from .widgets import FileTree, SessionRow, TerminalView


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

        self.set_title("gnome-tmux")
        self.set_default_size(1000, 700)

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
        title_widget = Adw.WindowTitle(title="gnome-tmux", subtitle="tmux session manager")
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

        # Botón refresh
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
        # Contenedor con drag handle
        file_tree_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header minimalista con drag handle
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.set_margin_start(8)
        header.set_margin_end(8)
        header.set_margin_top(4)
        header.set_margin_bottom(4)

        # Drag handle en un box para añadir controller
        drag_handle_box = Gtk.Box()
        drag_handle = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        drag_handle.set_opacity(0.5)
        drag_handle.set_tooltip_text("Drag to reorder")
        drag_handle_box.append(drag_handle)
        header.append(drag_handle_box)

        # Drag source SOLO en el drag handle
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect(
            "prepare", lambda s, x, y: Gdk.ContentProvider.new_for_value("filetree")
        )
        drag_handle_box.add_controller(drag_source)

        label = Gtk.Label(label="Files")
        label.add_css_class("dim-label")
        header.append(label)

        file_tree_box.append(header)
        file_tree_box.append(Gtk.Separator())

        # Widget FileTree
        self.file_tree_widget = FileTree()
        self.file_tree_widget.set_vexpand(True)
        file_tree_box.append(self.file_tree_widget)

        # Drop target solo en el header para recibir otras secciones
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop_target.connect("drop", self._on_sidebar_section_drop)
        drop_target.connect("enter", self._on_sidebar_section_enter)
        drop_target.connect("leave", self._on_sidebar_section_leave)
        header.add_controller(drop_target)

        self._file_tree_box = file_tree_box
        self._file_tree_header = header
        return file_tree_box

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
        """Actualiza la lista de sesiones."""
        # Guardar estado de expansión actual (solo si ya hay filas)
        index = 0
        while True:
            row = self.sessions_list.get_row_at_index(index)
            if row is None:
                break
            if index == 0 and self._expanded_sessions is None:
                # Primera vez que hay filas, inicializar el set
                self._expanded_sessions = set()
            if isinstance(row, SessionRow):
                if row.get_expanded():
                    self._expanded_sessions.add(row.session.name)
                elif row.session.name in self._expanded_sessions:
                    self._expanded_sessions.discard(row.session.name)
            index += 1

        # Limpiar lista actual
        while True:
            row = self.sessions_list.get_row_at_index(0)
            if row is None:
                break
            self.sessions_list.remove(row)

        # Verificar si tmux está disponible
        if not self.tmux.is_available:
            self._show_error_placeholder("tmux not installed")
            return

        # Obtener sesiones
        sessions = self.tmux.list_sessions()

        # Agregar filas
        for session in sessions:
            row = SessionRow(session)
            row.connect("delete-requested", self._on_delete_requested)
            row.connect("window-selected", self._on_window_selected)
            row.connect("rename-session-requested", self._on_rename_session_requested)
            row.connect("rename-window-requested", self._on_rename_window_requested)
            row.connect("new-window-requested", self._on_new_window_requested)
            row.connect("exit-window-requested", self._on_exit_window_requested)
            row.connect("swap-windows-requested", self._on_swap_windows_requested)
            # Restaurar estado de expansión
            if self._expanded_sessions is None:
                # Primera carga: expandir sesiones activas
                if session.attached:
                    row.set_expanded(True)
            elif session.name in self._expanded_sessions:
                row.set_expanded(True)
            self.sessions_list.append(row)

        # Inicializar el set si es la primera carga
        if self._expanded_sessions is None:
            self._expanded_sessions = set(s.name for s in sessions if s.attached)

    def _show_error_placeholder(self, message: str):
        """Muestra un mensaje de error en el placeholder."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_top(24)
        box.set_margin_bottom(24)

        icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("error")
        box.append(icon)

        label = Gtk.Label(label=message)
        label.add_css_class("error")
        box.append(label)

        self.sessions_list.set_placeholder(box)

    def _on_new_session_clicked(self, button: Gtk.Button):
        """Muestra diálogo para crear nueva sesión."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="New Session",
            body="Enter a name for the new tmux session:",
        )

        # Entry para el nombre
        entry = Gtk.Entry()
        entry.set_placeholder_text("session-name")
        entry.connect("activate", lambda e: dialog.response("create"))
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")

        dialog.connect("response", self._on_new_session_response, entry)
        dialog.present()

    def _on_new_session_response(self, dialog: Adw.MessageDialog, response: str, entry: Gtk.Entry):
        """Maneja la respuesta del diálogo de nueva sesión."""
        dialog.close()
        if response == "create":
            name = entry.get_text().strip()
            if name:
                if self.tmux.create_session(name):
                    self._refresh_sessions()
                    # Auto-attach a la nueva sesión
                    GLib.idle_add(self._attach_to_session, name)
                else:
                    self._show_toast("Failed to create session")

    def _attach_to_session(self, name: str, window_index: int | None = None):
        """Adjunta al terminal a una sesión/ventana."""
        command = self.tmux.get_attach_command(name, window_index)
        self.terminal_view.attach_session(name, command)
        self.terminal_view.grab_focus()
        return False

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
        entry.connect("activate", lambda e: dialog.response("rename"))
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("rename", "Rename")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("rename")

        dialog.connect("response", self._on_rename_session_response, session_name, entry)
        dialog.present()

    def _on_rename_session_response(self, dialog, response: str, old_name: str, entry: Gtk.Entry):
        """Maneja la respuesta del diálogo de renombrar sesión."""
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
        entry.connect("activate", lambda e: dialog.response("rename"))
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
        entry.connect("activate", lambda e: dialog.response("create"))
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")

        dialog.connect("response", self._on_new_window_response, session_name, entry)
        dialog.present()

    def _on_new_window_response(self, dialog, response: str, session_name: str, entry: Gtk.Entry):
        """Maneja la respuesta del diálogo de nueva ventana."""
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

    def do_close_request(self) -> bool:
        """Maneja el cierre de la ventana."""
        if self._refresh_timeout_id is not None:
            GLib.source_remove(self._refresh_timeout_id)
            self._refresh_timeout_id = None
        return False
