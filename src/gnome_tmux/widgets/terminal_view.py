"""
terminal_view.py - Widget de terminal VTE para tmux

Autor: Homero Thompson del Lago del Terror
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Vte", "3.91")

import os

from gi.repository import Gdk, GLib, GObject, Gtk, Vte


class TerminalView(Gtk.Box):
    """Widget que contiene un terminal VTE para sesiones tmux."""

    __gtype_name__ = "TerminalView"

    __gsignals__ = {
        "session-ended": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._current_session: str | None = None
        self._pid: int | None = None

        # Scrolled window para el terminal
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        # Terminal VTE
        self.terminal = Vte.Terminal()
        self.terminal.set_scroll_on_output(True)
        self.terminal.set_scroll_on_keystroke(True)
        self.terminal.set_scrollback_lines(10000)

        # Fuente
        self.terminal.set_font_scale(1.0)

        # Conectar señales
        self.terminal.connect("child-exited", self._on_child_exited)

        scrolled.set_child(self.terminal)
        self.append(scrolled)

        # Drop target para recibir paths de archivos
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_drop)
        self.terminal.add_controller(drop_target)

        # Keyboard controller para Ctrl+Shift+V (paste) y Ctrl+Shift+C (copy)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.terminal.add_controller(key_controller)

        # Estado vacío inicial
        self._show_empty_state()

    def _show_empty_state(self):
        """Muestra mensaje cuando no hay sesión seleccionada."""
        # El terminal ya está vacío, solo mostrar mensaje de bienvenida
        self.terminal.feed(b"\r\n  Select a session from the sidebar to attach\r\n")

    def attach_session(self, session_name: str, tmux_command: list[str]):
        """Adjunta el terminal a una sesión de tmux."""
        # Si ya hay un proceso, esperar a que termine
        if self._pid is not None:
            self.terminal.reset(True, True)

        self._current_session = session_name

        # Spawn tmux attach
        self.terminal.spawn_async(
            pty_flags=Vte.PtyFlags.DEFAULT,
            working_directory=os.environ.get("HOME", "/"),
            argv=tmux_command,
            envv=None,
            spawn_flags=GLib.SpawnFlags.DEFAULT,
            child_setup=None,
            timeout=-1,
            cancellable=None,
            callback=self._on_spawn_complete,
            user_data=session_name,
        )

    def _on_spawn_complete(self, terminal, pid, error, session_name):
        """Callback cuando el proceso se inicia."""
        if error:
            self.terminal.feed(f"\r\n  Error: {error.message}\r\n".encode())
            self._pid = None
        else:
            self._pid = pid

    def _on_child_exited(self, terminal, status):
        """Callback cuando el proceso termina."""
        self._pid = None
        self._current_session = None
        self.terminal.feed(b"\r\n  Session ended. Select another session.\r\n")
        self.emit("session-ended")

    def detach(self):
        """Desconecta del terminal actual."""
        if self._pid is not None:
            # Enviar Ctrl+B d para detach de tmux
            self.terminal.feed_child(b"\x02d")

    @property
    def current_session(self) -> str | None:
        """Retorna el nombre de la sesión actual."""
        return self._current_session

    def grab_focus(self):
        """Da foco al terminal."""
        self.terminal.grab_focus()

    def _on_drop(self, drop_target, value, x, y) -> bool:
        """Maneja el drop de un path de archivo."""
        if isinstance(value, str) and value:
            # Escapar espacios y caracteres especiales en el path
            escaped_path = value.replace("\\", "\\\\").replace(" ", "\\ ")
            escaped_path = escaped_path.replace("'", "\\'").replace('"', '\\"')
            # Insertar el path en el terminal
            self.terminal.feed_child(escaped_path.encode("utf-8"))
            self.terminal.grab_focus()
            return True
        return False

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        """Maneja atajos de teclado del terminal."""
        # Verificar Ctrl+Shift
        ctrl_shift = Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK
        if (state & ctrl_shift) == ctrl_shift:
            # Ctrl+Shift+V = Paste
            if keyval == Gdk.KEY_V or keyval == Gdk.KEY_v:
                self._paste_from_clipboard()
                return True
            # Ctrl+Shift+C = Copy
            if keyval == Gdk.KEY_C or keyval == Gdk.KEY_c:
                self._copy_to_clipboard()
                return True
        return False

    def _paste_from_clipboard(self):
        """Pega el contenido del clipboard en el terminal."""
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_text_ready)

    def _on_clipboard_text_ready(self, clipboard, result):
        """Callback cuando el texto del clipboard está listo."""
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self.terminal.feed_child(text.encode("utf-8"))
        except Exception:
            pass  # Ignorar errores de clipboard

    def _copy_to_clipboard(self):
        """Copia la selección del terminal al clipboard."""
        if self.terminal.get_has_selection():
            self.terminal.copy_clipboard_format(Vte.Format.TEXT)
