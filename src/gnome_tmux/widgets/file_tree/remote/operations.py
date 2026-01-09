"""
operations.py - Operaciones de archivos remotos via SSH

Autor: Homero Thompson del Lago del Terror
"""

import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import GLib

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore

if TYPE_CHECKING:
    from ....clients import RemoteTmuxClient


class RemoteFileOperations:
    """Operaciones de archivos en servidores remotos."""

    def __init__(self, client: "RemoteTmuxClient"):
        """
        Inicializa operaciones remotas.

        Args:
            client: Cliente SSH remoto
        """
        self._client = client
        self._clipboard_path: str | None = None

    def copy_path(self, path: str):
        """Copia un path remoto al clipboard."""
        self._clipboard_path = path
        logger.debug(f"Copiado al clipboard remoto: {path}")

    def has_clipboard(self) -> bool:
        """Retorna si hay algo en el clipboard remoto."""
        return self._clipboard_path is not None

    def paste_file(
        self,
        destination: str,
        on_success: Callable[[], None],
    ) -> bool:
        """
        Pega archivo copiado en destino remoto.

        Args:
            destination: Path destino
            on_success: Callback cuando termine exitosamente

        Returns:
            True si inicia la operación
        """
        if not self._clipboard_path or not self._client:
            return False

        source = self._clipboard_path
        source_name = os.path.basename(source)

        # Determinar directorio destino
        if self._client.is_dir(destination):
            dest_dir = destination
        else:
            dest_dir = os.path.dirname(destination)

        target = f"{dest_dir.rstrip('/')}/{source_name}"

        # Manejar colisiones de nombres
        counter = 1
        original_name = source_name
        while self._client.file_exists(target):
            if "." in original_name and not original_name.startswith("."):
                name_parts = original_name.rsplit(".", 1)
                new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                new_name = f"{original_name}_{counter}"
            target = f"{dest_dir.rstrip('/')}/{new_name}"
            counter += 1

        logger.info(f"📋 Pegando remoto: {source} → {target}")
        if self._client.copy_file(source, target):
            logger.info(f"✅ Copiado exitosamente en {self._client.host}")
            on_success()
            return True
        else:
            logger.error("❌ Error copiando archivo remoto")
            return False

    def download_file(
        self,
        remote_path: str,
        on_complete: Callable[[str, bool, str], None],
    ):
        """
        Descarga archivo remoto a ~/Downloads.

        Args:
            remote_path: Path remoto a descargar
            on_complete: Callback(filename, success, local_path)
        """
        filename = os.path.basename(remote_path)
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)
        local_path = downloads_dir / filename

        # Manejar colisiones
        counter = 1
        original_path = local_path
        while local_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            local_path = downloads_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        # Descargar en thread separado
        def do_download():
            logger.info(f"⬇️  Descargando {filename} desde {self._client.host}")
            success = self._client.download_file(remote_path, str(local_path))

            if success:
                logger.info(f"✅ Descargado a {local_path}")
            else:
                logger.error(f"❌ Error descargando {filename}")

            GLib.idle_add(on_complete, filename, success, str(local_path))

        thread = threading.Thread(target=do_download, daemon=True)
        thread.start()

    def rename_file(
        self,
        old_path: str,
        new_name: str,
        on_success: Callable[[], None],
    ) -> bool:
        """
        Renombra archivo remoto.

        Args:
            old_path: Path actual
            new_name: Nombre nuevo
            on_success: Callback si exitoso

        Returns:
            True si exitoso
        """
        old_name = os.path.basename(old_path)
        if not new_name or new_name == old_name:
            return False

        parent = os.path.dirname(old_path)
        new_path = f"{parent}/{new_name}"

        if self._client.rename_file(old_path, new_path):
            on_success()
            return True
        return False

    def delete_file(self, path: str, on_success: Callable[[], None]) -> bool:
        """
        Elimina archivo remoto.

        Args:
            path: Path a eliminar
            on_success: Callback si exitoso

        Returns:
            True si exitoso
        """
        if self._client.delete_file(path):
            on_success()
            return True
        return False

    def create_directory(
        self,
        parent_path: str,
        folder_name: str,
        on_success: Callable[[str], None],
    ) -> bool:
        """
        Crea directorio remoto.

        Args:
            parent_path: Directorio padre
            folder_name: Nombre de la carpeta
            on_success: Callback con el path creado

        Returns:
            True si exitoso
        """
        new_path = f"{parent_path.rstrip('/')}/{folder_name}"

        if self._client.create_directory(new_path):
            on_success(parent_path)
            return True
        return False
