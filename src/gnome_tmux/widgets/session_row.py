"""
session_row.py - Widget de árbol para sesiones y ventanas de tmux

Autor: Homero Thompson del Lago del Terror
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GObject, Gtk

from ..tmux_client import Session, Window


class WindowRow(Adw.ActionRow):
    """Fila que representa una ventana de tmux."""

    __gtype_name__ = "WindowRow"

    __gsignals__ = {
        "window-selected": (GObject.SignalFlags.RUN_FIRST, None, (str, int)),
        "rename-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, int, str)),
        "exit-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, int)),
        "swap-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, int, int)),
    }

    def __init__(self, session_name: str, window: Window):
        super().__init__()

        self.session_name = session_name
        self.window = window

        # Título: índice y nombre (resaltado si está activa)
        title = f"{window.index}: {window.name}"
        if window.active:
            self.set_title(f"<b>{title}</b>")
            self.set_use_markup(True)
            self.add_css_class("accent")
        else:
            self.set_title(title)
        self.set_activatable(True)
        self.set_title_lines(1)
        self.set_subtitle_lines(0)

        # Icono de drag (al inicio)
        drag_icon = Gtk.Image.new_from_icon_name("list-drag-handle-symbolic")
        drag_icon.set_opacity(0.5)
        self.add_prefix(drag_icon)

        # Botón de editar nombre
        edit_button = Gtk.Button()
        edit_button.set_icon_name("document-edit-symbolic")
        edit_button.set_valign(Gtk.Align.CENTER)
        edit_button.add_css_class("flat")
        edit_button.set_tooltip_text("Rename window")
        edit_button.connect("clicked", self._on_edit_clicked)
        self.add_suffix(edit_button)

        # Botón de cerrar ventana (exit limpio)
        exit_button = Gtk.Button()
        exit_button.set_icon_name("window-close-symbolic")
        exit_button.set_valign(Gtk.Align.CENTER)
        exit_button.add_css_class("flat")
        exit_button.set_tooltip_text("Exit window")
        exit_button.connect("clicked", self._on_exit_clicked)
        self.add_suffix(exit_button)

        # Conectar activación
        self.connect("activated", self._on_activated)

        # Drag source
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect("prepare", self._on_drag_prepare)
        drag_source.connect("drag-begin", self._on_drag_begin)
        self.add_controller(drag_source)

        # Drop target
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop_target.connect("drop", self._on_drop)
        drop_target.connect("enter", self._on_drag_enter)
        drop_target.connect("leave", self._on_drag_leave)
        self.add_controller(drop_target)

    def _on_drag_prepare(self, source, x, y):
        """Prepara datos para el drag."""
        # Formato: session_name:window_index
        data = f"{self.session_name}:{self.window.index}"
        return Gdk.ContentProvider.new_for_value(data)

    def _on_drag_begin(self, source, drag):
        """Configura el aspecto visual del drag."""
        self.add_css_class("dim-label")

    def _on_drop(self, target, value, x, y) -> bool:
        """Maneja el drop de otra ventana."""
        self.remove_css_class("suggested-action")
        if not isinstance(value, str) or ":" not in value:
            return False

        parts = value.split(":")
        if len(parts) != 2:
            return False

        src_session = parts[0]
        try:
            src_index = int(parts[1])
        except ValueError:
            return False

        # Solo permitir swap dentro de la misma sesión
        if src_session != self.session_name:
            return False

        # No hacer nada si es la misma ventana
        if src_index == self.window.index:
            return False

        # Emitir señal de swap
        self.emit("swap-requested", self.session_name, src_index, self.window.index)
        return True

    def _on_drag_enter(self, target, x, y):
        """Resalta cuando hay un drag sobre esta fila."""
        self.add_css_class("suggested-action")
        return Gdk.DragAction.MOVE

    def _on_drag_leave(self, target):
        """Quita el resaltado cuando sale el drag."""
        self.remove_css_class("suggested-action")

    def _on_activated(self, row):
        """Emite señal cuando se selecciona la ventana."""
        self.emit("window-selected", self.session_name, self.window.index)

    def _on_edit_clicked(self, button: Gtk.Button):
        """Emite señal para renombrar."""
        self.emit("rename-requested", self.session_name, self.window.index, self.window.name)

    def _on_exit_clicked(self, button: Gtk.Button):
        """Emite señal para cerrar ventana."""
        self.emit("exit-requested", self.session_name, self.window.index)


class SessionRow(Adw.ExpanderRow):
    """Fila expandible que representa una sesión de tmux con sus ventanas."""

    __gtype_name__ = "SessionRow"

    __gsignals__ = {
        "delete-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "rename-session-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "rename-window-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, int, str)),
        "window-selected": (GObject.SignalFlags.RUN_FIRST, None, (str, int)),
        "new-window-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "exit-window-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, int)),
        "swap-windows-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, int, int)),
    }

    def __init__(self, session: Session):
        super().__init__()

        self.session = session

        # Título (sin subtítulo para ser más compacto)
        self.set_title(session.name)
        self.set_title_lines(1)
        self.set_subtitle_lines(0)

        # Icono de sesión (cambia si está activa)
        if session.attached:
            icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
            icon.add_css_class("success")
            icon.set_tooltip_text("Session attached")
        else:
            icon = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
        self.add_prefix(icon)

        # Box compacto para botones de acción
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        actions_box.set_valign(Gtk.Align.CENTER)
        actions_box.add_css_class("linked")

        # Botón de eliminar
        delete_button = Gtk.Button()
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.add_css_class("flat")
        delete_button.add_css_class("error")
        delete_button.set_tooltip_text("Delete session")
        delete_button.connect("clicked", self._on_delete_clicked)
        actions_box.append(delete_button)

        # Botón de editar nombre de sesión
        edit_button = Gtk.Button()
        edit_button.set_icon_name("document-edit-symbolic")
        edit_button.add_css_class("flat")
        edit_button.set_tooltip_text("Rename session")
        edit_button.connect("clicked", self._on_edit_clicked)
        actions_box.append(edit_button)

        # Botón de nueva ventana
        new_window_button = Gtk.Button()
        new_window_button.set_icon_name("list-add-symbolic")
        new_window_button.add_css_class("flat")
        new_window_button.set_tooltip_text("New window")
        new_window_button.connect("clicked", self._on_new_window_clicked)
        actions_box.append(new_window_button)

        self.add_suffix(actions_box)

        # Agregar ventanas como filas hijas
        for window in session.windows:
            window_row = WindowRow(session.name, window)
            window_row.connect("window-selected", self._on_window_selected)
            window_row.connect("rename-requested", self._on_window_rename_requested)
            window_row.connect("exit-requested", self._on_window_exit_requested)
            window_row.connect("swap-requested", self._on_window_swap_requested)
            self.add_row(window_row)

    def _on_new_window_clicked(self, button: Gtk.Button):
        """Emite señal para crear nueva ventana."""
        self.emit("new-window-requested", self.session.name)

    def _on_edit_clicked(self, button: Gtk.Button):
        """Emite señal para renombrar sesión."""
        self.emit("rename-session-requested", self.session.name)

    def _on_delete_clicked(self, button: Gtk.Button):
        """Emite señal de eliminar."""
        self.emit("delete-requested", self.session.name)

    def _on_window_selected(self, row: WindowRow, session_name: str, window_index: int):
        """Propaga la señal de ventana seleccionada."""
        self.emit("window-selected", session_name, window_index)

    def _on_window_rename_requested(
        self, row: WindowRow, session_name: str, window_index: int, current_name: str
    ):
        """Propaga la señal de renombrar ventana."""
        self.emit("rename-window-requested", session_name, window_index, current_name)

    def _on_window_exit_requested(
        self, row: WindowRow, session_name: str, window_index: int
    ):
        """Propaga la señal de cerrar ventana."""
        self.emit("exit-window-requested", session_name, window_index)

    def _on_window_swap_requested(
        self, row: WindowRow, session_name: str, src_index: int, dst_index: int
    ):
        """Propaga la señal de intercambiar ventanas."""
        self.emit("swap-windows-requested", session_name, src_index, dst_index)
