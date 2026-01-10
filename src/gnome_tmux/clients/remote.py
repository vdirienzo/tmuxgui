"""
remote.py - Cliente tmux remoto via SSH

Autor: Homero Thompson del Lago del Terror
"""

import shlex
import subprocess
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore

from .models import Session, Window, get_ssh_control_path
from .parsers import (
    SESSION_FORMAT,
    WINDOW_FORMAT,
    parse_sessions_output,
    parse_windows_output,
)


class RemoteTmuxClient:
    """Cliente para interactuar con tmux en un servidor remoto via SSH."""

    def __init__(self, host: str, user: str, port: str = "22"):
        self.host = host
        self.user = user
        self.port = port
        self._control_path = get_ssh_control_path(host, user, port)
        # Caché de sesiones con TTL de 5 segundos
        self._sessions_cache: list[Session] | None = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 5.0  # segundos
        logger.debug(f"RemoteTmuxClient creado para {user}@{host}:{port}")

    def _get_ssh_base(self) -> list[str]:
        """Retorna el comando base SSH con ControlMaster."""
        return [
            "ssh",
            "-p",
            self.port,
            "-o",
            "ControlMaster=no",
            "-o",
            f"ControlPath={self._control_path}",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=2",
            f"{self.user}@{self.host}",
        ]

    def _run_remote(
        self, tmux_args: list[str], timeout: float = 3.0
    ) -> subprocess.CompletedProcess:
        """Ejecuta un comando tmux remoto via SSH."""
        if not Path(self._control_path).exists():
            return subprocess.CompletedProcess([], 1, "", "no connection")

        escaped_args = [shlex.quote(arg) for arg in tmux_args]
        remote_cmd = "tmux " + " ".join(escaped_args)
        cmd = self._get_ssh_base() + [remote_cmd]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, 1, "", "timeout")

    def _run_ssh_command(self, command: str, timeout: float = 5.0) -> subprocess.CompletedProcess:
        """Ejecuta un comando SSH genérico (no tmux)."""
        if not Path(self._control_path).exists():
            return subprocess.CompletedProcess([], 1, "", "no connection")

        cmd = self._get_ssh_base() + [command]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, 1, "", "timeout")

    def is_connected(self) -> bool:
        """Verifica si hay una conexión SSH activa (ControlMaster)."""
        socket_path = Path(self._control_path)
        if not socket_path.exists():
            return False

        cmd = [
            "ssh",
            "-O",
            "check",
            "-o",
            f"ControlPath={self._control_path}",
            f"{self.user}@{self.host}",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    def is_tmux_available(self) -> bool:
        """Verifica si tmux está instalado en el servidor remoto."""
        if not self.is_connected():
            logger.debug(f"No hay conexión SSH activa a {self.host}")
            return False
        cmd = self._get_ssh_base() + ["command -v tmux"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            available = result.returncode == 0 and "tmux" in result.stdout
            if not available:
                logger.warning(f"tmux no está instalado en {self.host}")
            return available
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout verificando tmux en {self.host}")
            return False

    def has_server(self) -> bool:
        """Verifica si hay un servidor tmux corriendo en el remoto."""
        if not self.is_connected():
            return False
        result = self._run_remote(["has-session"])
        return result.returncode == 0

    def list_sessions(self) -> list[Session]:
        """Lista sesiones con caché TTL de 5 segundos."""
        import time

        now = time.time()

        # Retornar caché si es válido
        if self._sessions_cache is not None and (now - self._cache_time) < self._cache_ttl:
            return self._sessions_cache

        # Fetch fresh
        result = self._run_remote(["list-sessions", "-F", SESSION_FORMAT])

        if result.returncode != 0:
            return []

        sessions = parse_sessions_output(result.stdout)
        for session in sessions:
            session.windows = self._list_windows(session.name)

        # Actualizar caché
        self._sessions_cache = sessions
        self._cache_time = now
        return sessions

    def invalidate_cache(self):
        """Invalida el caché de sesiones (llamar después de modificaciones)."""
        self._sessions_cache = None

    def _list_windows(self, session_name: str) -> list[Window]:
        """Lista las ventanas de una sesión remota."""
        result = self._run_remote(["list-windows", "-t", session_name, "-F", WINDOW_FORMAT])

        if result.returncode != 0:
            return []

        return parse_windows_output(result.stdout)

    def get_attach_command(self, session_name: str, window_index: int | None = None) -> list[str]:
        """Retorna el comando para adjuntar a una sesión/ventana remota."""
        target = f"{session_name}:{window_index}" if window_index is not None else session_name

        return [
            "ssh",
            "-p",
            self.port,
            "-o",
            "ControlMaster=auto",
            "-o",
            f"ControlPath={self._control_path}",
            "-o",
            "ControlPersist=600",
            "-t",
            f"{self.user}@{self.host}",
            "tmux",
            "attach-session",
            "-t",
            target,
        ]

    def get_new_session_command(self, session_name: str) -> list[str]:
        """Retorna el comando para crear y adjuntar a una nueva sesión."""
        socket_dir = Path(self._control_path).parent
        socket_dir.mkdir(parents=True, exist_ok=True)

        return [
            "ssh",
            "-p",
            self.port,
            "-o",
            "ControlMaster=auto",
            "-o",
            f"ControlPath={self._control_path}",
            "-o",
            "ControlPersist=600",
            "-t",
            f"{self.user}@{self.host}",
            "tmux",
            "new-session",
            "-A",
            "-s",
            session_name,
        ]

    def rename_session(self, old_name: str, new_name: str) -> bool:
        """Renombra una sesión remota."""
        if not new_name:
            return False
        result = self._run_remote(["rename-session", "-t", old_name, new_name])
        return result.returncode == 0

    def kill_session(self, name: str) -> bool:
        """Elimina una sesión remota."""
        result = self._run_remote(["kill-session", "-t", name])
        return result.returncode == 0

    def create_window(self, session_name: str, window_name: str | None = None) -> bool:
        """Crea una nueva ventana en una sesión remota."""
        cmd = ["new-window", "-t", session_name]
        if window_name:
            cmd.extend(["-n", window_name])
        result = self._run_remote(cmd)
        return result.returncode == 0

    def close_connection(self, force: bool = False):
        """Cierra la conexión SSH ControlMaster."""
        socket_path = Path(self._control_path)
        if not socket_path.exists():
            return

        logger.info(f"Cerrando conexión SSH a {self.user}@{self.host}:{self.port}")

        cmd = [
            "ssh",
            "-O",
            "exit",
            "-o",
            f"ControlPath={self._control_path}",
            f"{self.user}@{self.host}",
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=2)
            logger.debug(f"Conexión SSH cerrada exitosamente para {self.host}")
        except Exception as e:
            logger.debug(f"Error al cerrar conexión SSH para {self.host}: {e}")

        if force and socket_path.exists():
            try:
                socket_path.unlink()
            except Exception as e:
                logger.debug(f"Error removing socket: {e}")

    # --- File Operations (delegados a RemoteFileOperations) ---
    # Estos métodos se mantienen por compatibilidad pero delegan internamente

    def get_home_dir(self) -> str | None:
        """Obtiene el directorio home del usuario remoto."""
        if not self.is_connected():
            return None
        result = self._run_ssh_command("echo $HOME")
        if result.returncode == 0 and result.stdout:
            return str(result.stdout).strip()
        return None

    def list_dir(self, path: str) -> list[dict] | None:
        """Lista el contenido de un directorio remoto."""
        if not self.is_connected():
            return None

        cmd = f"ls -Al {path!r} 2>&1"
        result = self._run_ssh_command(cmd)

        if result.returncode != 0:
            return None

        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line or line.startswith("total"):
                continue

            parts = line.split()
            if len(parts) < 9:
                if len(parts) >= 8:
                    perms = parts[0]
                    name = " ".join(parts[7:])
                else:
                    continue
            else:
                perms = parts[0]
                name = " ".join(parts[8:])

            if name in (".", ".."):
                continue

            entries.append(
                {
                    "name": name,
                    "is_dir": perms.startswith("d"),
                    "size": 0,
                    "mtime": 0,
                    "is_hidden": name.startswith("."),
                }
            )

        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return entries

    def file_exists(self, path: str) -> bool:
        """Verifica si un archivo o directorio existe en el remoto."""
        if not self.is_connected():
            return False
        result = self._run_ssh_command(f"test -e {path!r} && echo yes || echo no")
        return result.returncode == 0 and "yes" in result.stdout

    def is_dir(self, path: str) -> bool:
        """Verifica si un path es un directorio en el remoto."""
        if not self.is_connected():
            return False
        result = self._run_ssh_command(f"test -d {path!r} && echo yes || echo no")
        return result.returncode == 0 and "yes" in result.stdout

    def rename_file(self, old_path: str, new_path: str) -> bool:
        """Renombra un archivo o directorio en el servidor remoto."""
        if not self.is_connected():
            return False

        logger.info(f"Renombrando en {self.host}: {old_path} → {new_path}")
        cmd = f"mv {old_path!r} {new_path!r}"
        result = self._run_ssh_command(cmd)
        success = result.returncode == 0

        if not success:
            logger.error(f"Error renombrando en {self.host}: {result.stderr}")

        return success

    def delete_file(self, path: str) -> bool:
        """Elimina un archivo o directorio en el servidor remoto."""
        if not self.is_connected():
            return False

        # Validación crítica antes de eliminar
        from .path_validator import PathValidator

        if not PathValidator.is_safe_for_deletion(path):
            logger.warning(
                f"⚠️  Intento bloqueado de eliminar path no seguro: {path} en {self.host}"
            )
            return False

        logger.info(f"🗑️  Eliminando en {self.host}: {path}")
        cmd = f"rm -rf {path!r}"
        result = self._run_ssh_command(cmd)
        success = result.returncode == 0

        if success:
            logger.info(f"✅ Eliminado exitosamente: {path}")
        else:
            logger.error(f"❌ Error eliminando {path} en {self.host}: {result.stderr}")

        return success

    def create_directory(self, path: str) -> bool:
        """Crea un directorio en el servidor remoto."""
        if not self.is_connected():
            return False
        cmd = f"mkdir -p {path!r}"
        result = self._run_ssh_command(cmd)
        return result.returncode == 0

    def copy_file(self, src_path: str, dst_path: str) -> bool:
        """Copia un archivo o directorio en el servidor remoto."""
        if not self.is_connected():
            return False
        cmd = f"cp -r {src_path!r} {dst_path!r}"
        result = self._run_ssh_command(cmd)
        return result.returncode == 0

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Descarga un archivo del servidor remoto usando scp."""
        if not self.is_connected():
            return False

        cmd = [
            "scp",
            "-P",
            self.port,
            "-o",
            f"ControlPath={self._control_path}",
            "-o",
            "ControlMaster=no",
            f"{self.user}@{self.host}:{remote_path}",
            local_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def search_files(self, root: str, query: str, mode: str = "name") -> list[str]:
        """Busca archivos en el servidor remoto."""
        if not self.is_connected():
            return []

        if mode == "name":
            cmd = f"find {root!r} -name '*{query}*' -not -path '*/.*' 2>/dev/null | head -100"
        elif mode == "content":
            cmd = f"grep -r -l -i {query!r} {root!r} 2>/dev/null | head -100"
        else:
            return []

        result = self._run_ssh_command(cmd, timeout=10.0)
        if result.returncode != 0 or not result.stdout.strip():
            return []

        return [line for line in result.stdout.strip().split("\n") if line]
