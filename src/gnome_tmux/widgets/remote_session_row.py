"""
remote_session_row.py - Widget para sesiones remotas SSH

Autor: Homero Thompson del Lago del Terror
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk

from ..tmux_client import Session, Window


class RemoteWindowRow(Adw.ActionRow):
    """Fila que representa una ventana de tmux remota."""

    __gtype_name__ = "RemoteWindowRow"

    __gsignals__ = {
        "window-selected": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, int, str, str, str),  # session_name, window_index, host, user, port
        ),
    }

    def __init__(
        self, session_name: str, window: Window, host: str, user: str, port: str
    ):
        super().__init__()

        self.session_name = session_name
        self.window = window
        self.host = host
        self.user = user
        self.port = port

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

        # Conectar activación
        self.connect("activated", self._on_activated)

    def _on_activated(self, row):
        """Emite señal cuando se selecciona la ventana."""
        self.emit(
            "window-selected",
            self.session_name,
            self.window.index,
            self.host,
            self.user,
            self.port,
        )


class RemoteSessionRow(Adw.ExpanderRow):
    """Fila expandible que representa una sesión remota de tmux con sus ventanas."""

    __gtype_name__ = "RemoteSessionRow"

    __gsignals__ = {
        "session-selected": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, str, str, str),  # session_name, host, user, port
        ),
        "window-selected": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, int, str, str, str),  # session_name, window_index, host, user, port
        ),
        "rename-requested": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, str, str, str),  # session_name, host, user, port
        ),
        "kill-requested": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, str, str, str),  # session_name, host, user, port
        ),
        "new-window-requested": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (str, str, str, str),  # session_name, host, user, port
        ),
    }

    def __init__(
        self, session: Session, host: str, user: str, port: str, connected: bool = True
    ):
        super().__init__()

        self.session = session
        self.host = host
        self.user = user
        self.port = port
        self.connected = connected

        # Título: nombre de sesión @ host
        display_host = host if port == "22" else f"{host}:{port}"
        self.set_title(session.name)
        self.set_subtitle(f"{user}@{display_host}")
        self.set_title_lines(1)
        self.set_subtitle_lines(1)

        # Icono de red (verde si conectado/attached)
        if session.attached:
            icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
            icon.add_css_class("success")
            icon.set_tooltip_text("Session attached")
        else:
            icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
            if connected:
                icon.set_tooltip_text("Remote session")
            else:
                icon.add_css_class("dim-label")
                icon.set_tooltip_text("Disconnected")
        self.add_prefix(icon)

        # Box compacto para botones de acción (igual que SessionRow local)
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        actions_box.set_valign(Gtk.Align.CENTER)
        actions_box.add_css_class("linked")

        # Botón eliminar sesión tmux
        kill_button = Gtk.Button()
        kill_button.set_icon_name("user-trash-symbolic")
        kill_button.add_css_class("flat")
        kill_button.add_css_class("error")
        kill_button.set_tooltip_text("Kill remote session")
        kill_button.connect("clicked", self._on_kill_clicked)
        actions_box.append(kill_button)

        # Botón editar nombre
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
            window_row = RemoteWindowRow(session.name, window, host, user, port)
            window_row.connect("window-selected", self._on_window_selected)
            self.add_row(window_row)

    def _on_new_window_clicked(self, button: Gtk.Button):
        """Emite señal para crear nueva ventana."""
        self.emit("new-window-requested", self.session.name, self.host, self.user, self.port)

    def _on_edit_clicked(self, button: Gtk.Button):
        """Emite señal de renombrar."""
        self.emit("rename-requested", self.session.name, self.host, self.user, self.port)

    def _on_kill_clicked(self, button: Gtk.Button):
        """Emite señal de eliminar sesión."""
        self.emit("kill-requested", self.session.name, self.host, self.user, self.port)

    def _on_window_selected(
        self,
        row: RemoteWindowRow,
        session_name: str,
        window_index: int,
        host: str,
        user: str,
        port: str,
    ):
        """Propaga la señal de ventana seleccionada."""
        self.emit("window-selected", session_name, window_index, host, user, port)
