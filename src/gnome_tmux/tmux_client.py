"""
tmux_client.py - Wrapper subprocess para comandos tmux

Autor: Homero Thompson del Lago del Terror
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def is_flatpak() -> bool:
    """Detecta si está corriendo en un sandbox de Flatpak."""
    return os.path.exists("/.flatpak-info")


def get_ssh_control_path(host: str, user: str, port: str) -> str:
    """Retorna el path para SSH ControlMaster socket."""
    socket_dir = Path.home() / ".ssh" / "gnome-tmux-sockets"
    socket_dir.mkdir(parents=True, exist_ok=True)
    return str(socket_dir / f"{user}@{host}-{port}")


@dataclass
class Window:
    """Representa una ventana de tmux."""

    index: int
    name: str
    active: bool


@dataclass
class Session:
    """Representa una sesión de tmux."""

    name: str
    window_count: int
    attached: bool
    windows: list[Window] = field(default_factory=list)


class TmuxClient:
    """Cliente para interactuar con tmux via subprocess."""

    def __init__(self):
        self._is_flatpak = is_flatpak()
        if self._is_flatpak:
            # En Flatpak, usar el tmux del host
            self._tmux_path = "tmux"  # Se ejecuta via flatpak-spawn
        else:
            self._tmux_path = shutil.which("tmux")

    def _run_tmux(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        """Ejecuta un comando tmux, usando flatpak-spawn si está en Flatpak."""
        if self._is_flatpak:
            cmd = ["flatpak-spawn", "--host", "tmux"] + args
        else:
            cmd = ["tmux"] + args
        return subprocess.run(cmd, **kwargs)

    @property
    def is_available(self) -> bool:
        """Verifica si tmux está instalado."""
        if self._is_flatpak:
            # En Flatpak, asumimos que el host tiene tmux
            return True
        return self._tmux_path is not None

    def has_server(self) -> bool:
        """Verifica si hay un servidor tmux corriendo."""
        if not self.is_available:
            return False
        result = self._run_tmux(["has-session"], capture_output=True)
        return result.returncode == 0

    def list_sessions(self) -> list[Session]:
        """Lista todas las sesiones de tmux con sus ventanas."""
        if not self.has_server():
            return []

        # Obtener sesiones
        fmt = "#{session_name}:#{session_windows}:#{session_attached}"
        result = self._run_tmux(
            ["list-sessions", "-F", fmt],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return []

        sessions = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                session = Session(
                    name=parts[0],
                    window_count=int(parts[1]),
                    attached=parts[2] == "1",
                    windows=[],
                )
                # Obtener ventanas de esta sesión
                session.windows = self._list_windows(session.name)
                sessions.append(session)
        return sessions

    def _list_windows(self, session_name: str) -> list[Window]:
        """Lista las ventanas de una sesión."""
        fmt = "#{window_index}:#{window_name}:#{window_active}"
        result = self._run_tmux(
            ["list-windows", "-t", session_name, "-F", fmt],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return []

        windows = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                windows.append(
                    Window(
                        index=int(parts[0]),
                        name=parts[1],
                        active=parts[2] == "1",
                    )
                )
        return windows

    def create_session(self, name: str) -> bool:
        """Crea una nueva sesión de tmux."""
        if not self.is_available:
            return False

        # Validar nombre
        if not name or ":" in name or "." in name:
            return False

        result = self._run_tmux(
            ["new-session", "-d", "-s", name],
            capture_output=True,
        )
        return result.returncode == 0

    def kill_session(self, name: str) -> bool:
        """Elimina una sesión de tmux."""
        if not self.is_available:
            return False

        result = self._run_tmux(
            ["kill-session", "-t", name],
            capture_output=True,
        )
        return result.returncode == 0

    def get_attach_command(self, session_name: str, window_index: int | None = None) -> list[str]:
        """Retorna el comando para adjuntar a una sesión/ventana."""
        if window_index is not None:
            target = f"{session_name}:{window_index}"
        else:
            target = session_name

        if self._is_flatpak:
            # Pasar TERM para que tmux funcione correctamente
            return [
                "flatpak-spawn", "--host",
                "--env=TERM=xterm-256color",
                "tmux", "attach-session", "-t", target
            ]
        return ["tmux", "attach-session", "-t", target]

    def rename_session(self, old_name: str, new_name: str) -> bool:
        """Renombra una sesión de tmux."""
        if not self.is_available or not new_name:
            return False

        result = self._run_tmux(
            ["rename-session", "-t", old_name, new_name],
            capture_output=True,
        )
        return result.returncode == 0

    def rename_window(self, session_name: str, window_index: int, new_name: str) -> bool:
        """Renombra una ventana de tmux."""
        if not self.is_available or not new_name:
            return False

        target = f"{session_name}:{window_index}"
        result = self._run_tmux(
            ["rename-window", "-t", target, new_name],
            capture_output=True,
        )
        return result.returncode == 0

    def create_window(self, session_name: str, window_name: str | None = None) -> bool:
        """Crea una nueva ventana en una sesión."""
        if not self.is_available:
            return False

        cmd = ["new-window", "-t", session_name]
        if window_name:
            cmd.extend(["-n", window_name])

        result = self._run_tmux(cmd, capture_output=True)
        return result.returncode == 0

    def exit_window(self, session_name: str, window_index: int) -> bool:
        """Envía exit a una ventana (cierre limpio)."""
        if not self.is_available:
            return False

        target = f"{session_name}:{window_index}"
        result = self._run_tmux(
            ["send-keys", "-t", target, "exit", "Enter"],
            capture_output=True,
        )
        return result.returncode == 0

    def split_horizontal(self, target: str | None = None) -> bool:
        """Divide el panel horizontalmente (paneles lado a lado)."""
        if not self.is_available:
            return False

        cmd = ["split-window", "-h"]
        if target:
            cmd.extend(["-t", target])

        result = self._run_tmux(cmd, capture_output=True)
        return result.returncode == 0

    def split_vertical(self, target: str | None = None) -> bool:
        """Divide el panel verticalmente (paneles apilados)."""
        if not self.is_available:
            return False

        cmd = ["split-window", "-v"]
        if target:
            cmd.extend(["-t", target])

        result = self._run_tmux(cmd, capture_output=True)
        return result.returncode == 0

    def swap_windows(self, session_name: str, src_index: int, dst_index: int) -> bool:
        """Intercambia dos ventanas dentro de una sesión."""
        if not self.is_available:
            return False

        src = f"{session_name}:{src_index}"
        dst = f"{session_name}:{dst_index}"
        result = self._run_tmux(
            ["swap-window", "-s", src, "-t", dst],
            capture_output=True,
        )
        return result.returncode == 0


class RemoteTmuxClient:
    """Cliente para interactuar con tmux en un servidor remoto via SSH."""

    def __init__(self, host: str, user: str, port: str = "22"):
        self.host = host
        self.user = user
        self.port = port
        self._control_path = get_ssh_control_path(host, user, port)

    def _get_ssh_base(self) -> list[str]:
        """Retorna el comando base SSH con ControlMaster para comandos background."""
        return [
            "ssh",
            "-p", self.port,
            "-o", "ControlMaster=no",  # Solo usar socket existente, no crear
            "-o", f"ControlPath={self._control_path}",
            "-o", "BatchMode=yes",  # No pedir password, fallar si no hay conexión
            "-o", "ConnectTimeout=2",
            f"{self.user}@{self.host}",
        ]

    def _run_remote(
        self, tmux_args: list[str], timeout: float = 3.0
    ) -> subprocess.CompletedProcess:
        """Ejecuta un comando tmux remoto via SSH."""
        # Solo ejecutar si hay socket (conexión existente)
        if not Path(self._control_path).exists():
            return subprocess.CompletedProcess([], 1, "", "no connection")

        # Construir comando remoto - escapar comillas en argumentos
        import shlex
        escaped_args = [shlex.quote(arg) for arg in tmux_args]
        remote_cmd = "tmux " + " ".join(escaped_args)
        cmd = self._get_ssh_base() + [remote_cmd]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, 1, "", "timeout")

    def is_connected(self) -> bool:
        """Verifica si hay una conexión SSH activa (ControlMaster)."""
        # Check if socket exists
        socket_path = Path(self._control_path)
        if not socket_path.exists():
            return False

        # Quick check with ssh -O check
        cmd = [
            "ssh", "-O", "check",
            "-o", f"ControlPath={self._control_path}",
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
            return False
        # Ejecutar 'which tmux' o 'command -v tmux' en el remoto
        cmd = self._get_ssh_base() + ["command -v tmux"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            return result.returncode == 0 and "tmux" in result.stdout
        except subprocess.TimeoutExpired:
            return False

    def has_server(self) -> bool:
        """Verifica si hay un servidor tmux corriendo en el remoto."""
        if not self.is_connected():
            return False
        result = self._run_remote(["has-session"])
        return result.returncode == 0

    def list_sessions(self) -> list[Session]:
        """Lista todas las sesiones de tmux en el servidor remoto."""
        fmt = "#{session_name}:#{session_windows}:#{session_attached}"
        result = self._run_remote(["list-sessions", "-F", fmt])

        if result.returncode != 0:
            return []

        sessions = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                session = Session(
                    name=parts[0],
                    window_count=int(parts[1]),
                    attached=parts[2] == "1",
                    windows=[],
                )
                session.windows = self._list_windows(session.name)
                sessions.append(session)

        return sessions

    def _list_windows(self, session_name: str) -> list[Window]:
        """Lista las ventanas de una sesión remota."""
        fmt = "#{window_index}:#{window_name}:#{window_active}"
        result = self._run_remote(["list-windows", "-t", session_name, "-F", fmt])

        if result.returncode != 0:
            return []

        windows = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                windows.append(
                    Window(
                        index=int(parts[0]),
                        name=parts[1],
                        active=parts[2] == "1",
                    )
                )
        return windows

    def get_attach_command(self, session_name: str, window_index: int | None = None) -> list[str]:
        """Retorna el comando para adjuntar a una sesión/ventana remota."""
        if window_index is not None:
            target = f"{session_name}:{window_index}"
        else:
            target = session_name

        return [
            "ssh",
            "-p", self.port,
            "-o", "ControlMaster=auto",
            "-o", f"ControlPath={self._control_path}",
            "-o", "ControlPersist=600",
            "-t",
            f"{self.user}@{self.host}",
            "tmux", "attach-session", "-t", target,
        ]

    def get_new_session_command(self, session_name: str) -> list[str]:
        """Retorna el comando para crear y adjuntar a una nueva sesión."""
        # Asegurar que el directorio del socket exista
        socket_dir = Path(self._control_path).parent
        socket_dir.mkdir(parents=True, exist_ok=True)

        return [
            "ssh",
            "-p", self.port,
            "-o", "ControlMaster=auto",
            "-o", f"ControlPath={self._control_path}",
            "-o", "ControlPersist=600",
            "-t",
            f"{self.user}@{self.host}",
            "tmux", "new-session", "-A", "-s", session_name,
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

        # Intentar cierre graceful primero
        cmd = [
            "ssh", "-O", "exit",
            "-o", f"ControlPath={self._control_path}",
            f"{self.user}@{self.host}",
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=2)
        except Exception:
            pass

        # Si force=True y el socket aún existe, eliminarlo directamente
        if force and socket_path.exists():
            try:
                socket_path.unlink()
            except Exception:
                pass

    # --- File Operations ---

    def _run_ssh_command(
        self, command: str, timeout: float = 5.0
    ) -> subprocess.CompletedProcess:
        """Ejecuta un comando SSH genérico (no tmux)."""
        if not Path(self._control_path).exists():
            return subprocess.CompletedProcess([], 1, "", "no connection")

        cmd = self._get_ssh_base() + [command]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, 1, "", "timeout")

    def get_home_dir(self) -> str | None:
        """Obtiene el directorio home del usuario remoto."""
        if not self.is_connected():
            return None
        result = self._run_ssh_command("echo $HOME")
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def list_dir(self, path: str) -> list[dict] | None:
        """
        Lista el contenido de un directorio remoto.
        Retorna lista de dicts con: name, is_dir, size, mtime
        """
        if not self.is_connected():
            return None

        # Usar ls con formato parseable
        # -A: no mostrar . y ..
        # -l: formato largo
        # Intentar sin --time-style primero (más compatible)
        cmd = f"ls -Al {path!r} 2>&1"
        result = self._run_ssh_command(cmd)


        if result.returncode != 0:
            return None

        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line or line.startswith("total"):
                continue

            # Formato: -rw-r--r-- 1 user group size date time name
            # o: drwxr-xr-x 2 user group size date time name
            parts = line.split()
            if len(parts) < 9:
                # Intentar con menos columnas (sin grupo en algunos sistemas)
                if len(parts) >= 8:
                    perms = parts[0]
                    name = " ".join(parts[7:])  # El nombre puede tener espacios
                else:
                    continue
            else:
                perms = parts[0]
                # El nombre empieza en la columna 8 (índice 8) y puede tener espacios
                name = " ".join(parts[8:])

            # Ignorar algunos archivos ocultos especiales, pero mostrar el resto
            if name in (".", ".."):
                continue

            entries.append({
                "name": name,
                "is_dir": perms.startswith("d"),
                "size": 0,
                "mtime": 0,
                "is_hidden": name.startswith("."),
            })


        # Ordenar: directorios primero, luego por nombre
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
        cmd = f"mv {old_path!r} {new_path!r}"
        result = self._run_ssh_command(cmd)
        return result.returncode == 0

    def delete_file(self, path: str) -> bool:
        """Elimina un archivo o directorio en el servidor remoto."""
        if not self.is_connected():
            return False
        # Usar rm -rf para directorios, rm para archivos
        cmd = f"rm -rf {path!r}"
        result = self._run_ssh_command(cmd)
        return result.returncode == 0

    def create_directory(self, path: str) -> bool:
        """Crea un directorio en el servidor remoto."""
        if not self.is_connected():
            return False
        cmd = f"mkdir -p {path!r}"
        result = self._run_ssh_command(cmd)
        return result.returncode == 0

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Descarga un archivo del servidor remoto usando scp.
        Retorna True si tuvo éxito.
        """
        if not self.is_connected():
            return False

        # Usar scp con el ControlMaster existente
        cmd = [
            "scp",
            "-P", self.port,
            "-o", f"ControlPath={self._control_path}",
            "-o", "ControlMaster=no",
            f"{self.user}@{self.host}:{remote_path}",
            local_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def search_files(self, root: str, query: str, mode: str = "name") -> list[str]:
        """
        Busca archivos en el servidor remoto.
        mode: 'name' (por nombre), 'content' (grep en contenido)
        """
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
