"""
themes.py - Sistema de temas para TmuxGUI

Autor: Homero Thompson del Lago del Terror
"""

import json
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk

# Directorio de configuración
CONFIG_DIR = Path.home() / ".config" / "tmuxgui"
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Temas disponibles
THEMES = {
    "default": {
        "name": "Default",
        "scheme": Adw.ColorScheme.DEFAULT,
        "css": "",
    },
    "dark": {
        "name": "Dark",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": "",
    },
    "light": {
        "name": "Light",
        "scheme": Adw.ColorScheme.FORCE_LIGHT,
        "css": "",
    },
    "nord": {
        "name": "Nord",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": """
            @define-color accent_bg_color #88c0d0;
            @define-color accent_color #88c0d0;
            @define-color window_bg_color #2e3440;
            @define-color view_bg_color #3b4252;
            @define-color headerbar_bg_color #2e3440;
            @define-color card_bg_color #3b4252;
            @define-color sidebar_bg_color #2e3440;
        """,
    },
    "dracula": {
        "name": "Dracula",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": """
            @define-color accent_bg_color #bd93f9;
            @define-color accent_color #bd93f9;
            @define-color window_bg_color #282a36;
            @define-color view_bg_color #1e1f29;
            @define-color headerbar_bg_color #282a36;
            @define-color card_bg_color #44475a;
            @define-color sidebar_bg_color #21222c;
        """,
    },
    "gruvbox": {
        "name": "Gruvbox",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": """
            @define-color accent_bg_color #d79921;
            @define-color accent_color #fabd2f;
            @define-color window_bg_color #282828;
            @define-color view_bg_color #1d2021;
            @define-color headerbar_bg_color #282828;
            @define-color card_bg_color #3c3836;
            @define-color sidebar_bg_color #1d2021;
        """,
    },
    "catppuccin": {
        "name": "Catppuccin",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": """
            @define-color accent_bg_color #cba6f7;
            @define-color accent_color #cba6f7;
            @define-color window_bg_color #1e1e2e;
            @define-color view_bg_color #181825;
            @define-color headerbar_bg_color #1e1e2e;
            @define-color card_bg_color #313244;
            @define-color sidebar_bg_color #181825;
        """,
    },
    "tokyo-night": {
        "name": "Tokyo Night",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": """
            @define-color accent_bg_color #7aa2f7;
            @define-color accent_color #7aa2f7;
            @define-color window_bg_color #1a1b26;
            @define-color view_bg_color #16161e;
            @define-color headerbar_bg_color #1a1b26;
            @define-color card_bg_color #24283b;
            @define-color sidebar_bg_color #16161e;
        """,
    },
    "solarized-dark": {
        "name": "Solarized Dark",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": """
            @define-color accent_bg_color #268bd2;
            @define-color accent_color #268bd2;
            @define-color window_bg_color #002b36;
            @define-color view_bg_color #073642;
            @define-color headerbar_bg_color #002b36;
            @define-color card_bg_color #073642;
            @define-color sidebar_bg_color #002b36;
        """,
    },
    "monokai": {
        "name": "Monokai",
        "scheme": Adw.ColorScheme.FORCE_DARK,
        "css": """
            @define-color accent_bg_color #a6e22e;
            @define-color accent_color #a6e22e;
            @define-color window_bg_color #272822;
            @define-color view_bg_color #1e1f1c;
            @define-color headerbar_bg_color #272822;
            @define-color card_bg_color #3e3d32;
            @define-color sidebar_bg_color #1e1f1c;
        """,
    },
}


class ThemeManager:
    """Gestor de temas de la aplicación."""

    def __init__(self):
        self._css_provider: Gtk.CssProvider | None = None
        self._current_theme = "default"
        self._load_settings()

    def _load_settings(self):
        """Carga la configuración guardada."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    settings = json.load(f)
                    self._current_theme = settings.get("theme", "default")
            except (json.JSONDecodeError, OSError):
                pass

    def _save_settings(self):
        """Guarda la configuración."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"theme": self._current_theme}, f)

    def get_current_theme(self) -> str:
        """Retorna el tema actual."""
        return self._current_theme

    def get_available_themes(self) -> dict:
        """Retorna los temas disponibles."""
        return THEMES

    def apply_theme(self, theme_id: str):
        """Aplica un tema."""
        if theme_id not in THEMES:
            return

        theme = THEMES[theme_id]
        self._current_theme = theme_id

        # Aplicar esquema de colores
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(theme["scheme"])

        # Remover CSS anterior si existe
        if self._css_provider is not None:
            Gtk.StyleContext.remove_provider_for_display(
                Gdk.Display.get_default(),
                self._css_provider,
            )
            self._css_provider = None

        # Aplicar CSS del tema si tiene
        if theme["css"]:
            self._css_provider = Gtk.CssProvider()
            self._css_provider.load_from_string(theme["css"])
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                self._css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
            )

        # Guardar preferencia
        self._save_settings()

    def apply_saved_theme(self):
        """Aplica el tema guardado en la configuración."""
        self.apply_theme(self._current_theme)


# Instancia global
theme_manager = ThemeManager()
