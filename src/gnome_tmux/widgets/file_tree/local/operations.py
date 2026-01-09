"""
operations.py - Operaciones de archivos locales (copy, paste, delete, rename)

Autor: Homero Thompson del Lago del Terror
"""

import shutil
import time
from pathlib import Path

from gi.repository import Gdk

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore


class LocalFileOperations:
    """Operaciones de archivos locales."""

    def __init__(self):
        self._clipboard_path: str | None = None

    def copy_path(self, path: Path):
        """Copia un path al clipboard interno."""
        self._clipboard_path = str(path)
        logger.debug(f"Copiado al clipboard: {path}")
        # También copiar al clipboard del sistema
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(str(path))

    def paste_path(self, destination: Path) -> Path | None:
        """
        Pega el archivo/carpeta copiado en el destino.

        Returns:
            Path del archivo copiado o None si falla
        """
        if not self._clipboard_path:
            return None

        source = Path(self._clipboard_path)
        if not source.exists():
            return None

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
            logger.info(f"📋 Pegando {source} → {target}")
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            logger.info(f"✅ Copiado exitosamente a {target}")
            return target
        except (PermissionError, OSError) as e:
            logger.error(f"❌ Error copying {source} to {target}: {e}")
            return None

    def rename_path(self, path: Path, new_name: str) -> bool:
        """
        Renombra un archivo o carpeta.

        Returns:
            True si exitoso, False si falla
        """
        if not new_name or new_name == path.name:
            return False

        new_path = path.parent / new_name
        try:
            logger.info(f"✏️  Renombrando {path.name} → {new_name}")
            path.rename(new_path)
            logger.debug(f"Renombrado exitosamente: {new_path}")
            return True
        except (PermissionError, OSError) as e:
            logger.error(f"❌ Error renaming {path} to {new_name}: {e}")
            return False

    def delete_path(self, path: Path) -> bool:
        """
        Mueve un archivo o carpeta a ~/.trash.

        Returns:
            True si exitoso, False si falla
        """
        # Crear directorio trash si no existe
        trash_dir = Path.home() / ".trash"
        trash_dir.mkdir(exist_ok=True)

        # Destino en trash
        target = trash_dir / path.name

        # Si ya existe, agregar sufijo con timestamp
        if target.exists():
            timestamp = int(time.time())
            if path.is_dir():
                target = trash_dir / f"{path.name}_{timestamp}"
            else:
                target = trash_dir / f"{path.stem}_{timestamp}{path.suffix}"

        try:
            logger.info(f"🗑️  Moviendo a trash: {path}")
            shutil.move(str(path), str(target))
            logger.debug(f"Movido a trash: {target}")
            return True
        except (PermissionError, OSError) as e:
            logger.error(f"❌ Error moving {path} to trash: {e}")
            return False

    def has_clipboard(self) -> bool:
        """Retorna si hay algo en el clipboard."""
        return self._clipboard_path is not None

    def clear_clipboard(self):
        """Limpia el clipboard."""
        self._clipboard_path = None
