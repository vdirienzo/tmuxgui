#!/usr/bin/env python3
"""
main.py - Entry point de gnome-tmux

Autor: Homero Thompson del Lago del Terror
"""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Vte", "3.91")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Adw, Gdk, Gio, Gtk

from .window import MainWindow

# Application ID (debe coincidir con el .desktop y los iconos)
APP_ID = "io.github.vdirienzo.TmuxGUI"

# Ruta al icono
ICON_PATH = (
    Path(__file__).parent.parent.parent
    / "data" / "icons" / "hicolor" / "512x512" / "apps" / f"{APP_ID}.png"
)


class GnomeTmuxApplication(Adw.Application):
    """Aplicación principal de TmuxGUI."""

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_startup(self):
        """Inicializa la aplicación."""
        Adw.Application.do_startup(self)
        # Cargar icono desde archivo
        if ICON_PATH.exists():
            Gtk.Window.set_default_icon_name(APP_ID)
            # Agregar al theme para que lo encuentre
            display = Gdk.Display.get_default()
            if display:
                icon_theme = Gtk.IconTheme.get_for_display(display)
                icon_theme.add_search_path(str(ICON_PATH.parent.parent.parent.parent))

    def do_activate(self):
        """Activa la aplicación."""
        win = self.props.active_window
        if not win:
            win = MainWindow(self)
        win.present()


def main():
    """Entry point."""
    app = GnomeTmuxApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
