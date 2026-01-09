"""
favorites.py - Gestión de favoritos para file tree

Autor: Homero Thompson del Lago del Terror
"""

import json
from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore


class FavoritesManager:
    """Gestor de favoritos para navegación rápida."""

    def __init__(self, config_file: Path):
        """
        Inicializa el gestor de favoritos.

        Args:
            config_file: Ruta al archivo de configuración JSON
        """
        self._config_file = config_file
        self._favorites: list[str] = []
        self._load()

    def _load(self):
        """Carga la lista de favoritos desde el archivo."""
        try:
            if self._config_file.exists():
                with open(self._config_file) as f:
                    data = json.load(f)
                    favorites = data.get("favorites", [])
                    if isinstance(favorites, list):
                        self._favorites = [str(f) for f in favorites]
                        logger.debug(f"Loaded {len(self._favorites)} favorites")
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Error loading favorites: {e}")
            self._favorites = []

    def _save(self):
        """Guarda la lista de favoritos."""
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w") as f:
                json.dump({"favorites": self._favorites}, f, indent=2)
            logger.debug(f"Saved {len(self._favorites)} favorites")
        except OSError as e:
            logger.error(f"Error saving favorites: {e}")

    def get_favorites(self) -> list[str]:
        """Retorna la lista de favoritos."""
        return self._favorites.copy()

    def add(self, path: str) -> bool:
        """
        Agrega un path a favoritos.

        Returns:
            True si se agregó, False si ya existía
        """
        if path not in self._favorites:
            self._favorites.append(path)
            self._save()
            logger.info(f"⭐ Agregado a favoritos: {path}")
            return True
        return False

    def remove(self, path: str) -> bool:
        """
        Elimina un path de favoritos.

        Returns:
            True si se eliminó, False si no existía
        """
        if path in self._favorites:
            self._favorites.remove(path)
            self._save()
            logger.info(f"❌ Eliminado de favoritos: {path}")
            return True
        return False

    def is_favorite(self, path: str) -> bool:
        """Verifica si un path está en favoritos."""
        return path in self._favorites

    def create_popover(
        self,
        current_path: str,
        on_navigate: Callable[[str], None],
    ) -> Gtk.Popover:
        """
        Crea el popover de favoritos.

        Args:
            current_path: Path actual para marcar como favorito
            on_navigate: Callback para navegar a un favorito

        Returns:
            Popover configurado
        """
        popover = Gtk.Popover()
        popover.set_has_arrow(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        # Botón agregar/quitar actual
        is_fav = self.is_favorite(current_path)

        add_btn = Gtk.Button()
        add_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_btn_box.set_margin_start(8)
        add_btn_box.set_margin_end(8)

        if is_fav:
            add_btn_box.append(Gtk.Image.new_from_icon_name("starred-symbolic"))
            add_btn_box.append(Gtk.Label(label="Remove from favorites"))
            add_btn.connect(
                "clicked",
                lambda b: self._on_toggle_current(current_path, False, popover, on_navigate),
            )
        else:
            add_btn_box.append(Gtk.Image.new_from_icon_name("non-starred-symbolic"))
            add_btn_box.append(Gtk.Label(label="Add to favorites"))
            add_btn.connect(
                "clicked",
                lambda b: self._on_toggle_current(current_path, True, popover, on_navigate),
            )

        add_btn.set_child(add_btn_box)
        add_btn.add_css_class("flat")
        box.append(add_btn)

        # Lista de favoritos
        if self._favorites:
            box.append(Gtk.Separator())

            for fav_path in self._favorites:
                fav_row = self._create_favorite_row(fav_path, popover, on_navigate)
                box.append(fav_row)

        popover.set_child(box)
        return popover

    def _create_favorite_row(
        self,
        fav_path: str,
        popover: Gtk.Popover,
        on_navigate: Callable[[str], None],
    ) -> Gtk.Box:
        """Crea una fila de favorito."""
        fav_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # Botón navegar
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
        fav_btn.connect(
            "clicked",
            lambda b: self._on_navigate_to_favorite(fav_path, popover, on_navigate),
        )
        fav_row.append(fav_btn)

        # Botón eliminar
        delete_btn = Gtk.Button()
        delete_btn.set_icon_name("user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.set_tooltip_text("Remove from favorites")
        delete_btn.connect(
            "clicked",
            lambda b: self._on_remove_favorite(fav_path, popover, on_navigate),
        )
        fav_row.append(delete_btn)

        return fav_row

    def _on_toggle_current(
        self,
        path: str,
        add: bool,
        popover: Gtk.Popover,
        on_navigate: Callable[[str], None],
    ):
        """Agrega o quita el path actual de favoritos."""
        if add:
            self.add(path)
        else:
            self.remove(path)

        # Recrear el popover
        new_popover = self.create_popover(path, on_navigate)
        button = popover.get_parent()
        if button:
            button.set_popover(new_popover)  # type: ignore
        popover.popdown()

    def _on_navigate_to_favorite(
        self,
        fav_path: str,
        popover: Gtk.Popover,
        on_navigate: Callable[[str], None],
    ):
        """Navega a un favorito."""
        path = Path(fav_path)
        if path.exists() and path.is_dir():
            logger.info(f"📂 Navegando a favorito: {fav_path}")
            on_navigate(fav_path)
        else:
            logger.warning(f"Favorito no existe: {fav_path}")
        popover.popdown()

    def _on_remove_favorite(
        self,
        fav_path: str,
        popover: Gtk.Popover,
        on_navigate: Callable[[str], None],
    ):
        """Elimina un favorito."""
        if self.remove(fav_path):
            # Recrear el popover
            button = popover.get_parent()
            if button:
                # Obtener current_path del parent button (FileTree)
                # Simplemente reconstruimos el menu
                parent_widget = button.get_parent()
                if hasattr(parent_widget, "_root_path"):
                    current = str(parent_widget._root_path)  # type: ignore
                    new_popover = self.create_popover(current, on_navigate)
                    button.set_popover(new_popover)  # type: ignore
        popover.popdown()
