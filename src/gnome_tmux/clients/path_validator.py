"""
path_validator.py - Validación de paths para operaciones remotas

Autor: Homero Thompson del Lago del Terror
"""

from pathlib import PurePosixPath


class PathValidator:
    """Valida paths para prevenir path traversal y accesos no autorizados."""

    # Directorios críticos del sistema que no deben modificarse
    PROTECTED_DIRS = {
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/lib",
        "/lib64",
        "/proc",
        "/root",
        "/sbin",
        "/sys",
        "/usr",
        "/var",
    }

    @classmethod
    def validate_remote_path(cls, path: str) -> tuple[bool, str]:
        """
        Valida un path remoto antes de operaciones destructivas.

        Args:
            path: Path a validar

        Returns:
            (valido: bool, razon: str)
        """
        # Normalizar path
        try:
            normalized = str(PurePosixPath(path))
        except ValueError:
            return False, "Path inválido"

        # Verificar path traversal (..)
        if ".." in normalized:
            return False, "Path traversal detectado (..)"

        # Verificar directorios protegidos
        for protected in cls.PROTECTED_DIRS:
            if normalized == protected or normalized.startswith(protected + "/"):
                # Permitir subdirectorios de /home y /tmp
                if not (normalized.startswith("/home/") or normalized.startswith("/tmp/")):
                    return False, f"Directorio protegido: {protected}"

        # Verificar caracteres peligrosos
        dangerous_chars = [";", "|", "&", "$", "`", "\n", "\r"]
        for char in dangerous_chars:
            if char in path:
                return False, f"Carácter peligroso detectado: {repr(char)}"

        return True, "OK"

    @classmethod
    def is_safe_for_deletion(cls, path: str) -> bool:
        """Verifica si es seguro eliminar el path."""
        valid, _ = cls.validate_remote_path(path)
        if not valid:
            return False

        # No permitir eliminar raíz de home
        if path.rstrip("/") in ["/home", "/tmp"]:
            return False

        return True
