"""
tmux_client.py - Wrapper subprocess para comandos tmux

Autor: Homero Thompson del Lago del Terror
"""

import shutil
import subprocess
from dataclasses import dataclass, field


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
        self._tmux_path = shutil.which("tmux")

    @property
    def is_available(self) -> bool:
        """Verifica si tmux está instalado."""
        return self._tmux_path is not None

    def has_server(self) -> bool:
        """Verifica si hay un servidor tmux corriendo."""
        if not self.is_available:
            return False
        result = subprocess.run(
            ["tmux", "has-session"],
            capture_output=True,
        )
        return result.returncode == 0

    def list_sessions(self) -> list[Session]:
        """Lista todas las sesiones de tmux con sus ventanas."""
        if not self.has_server():
            return []

        # Obtener sesiones
        fmt = "#{session_name}:#{session_windows}:#{session_attached}"
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", fmt],
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
        result = subprocess.run(
            ["tmux", "list-windows", "-t", session_name, "-F", fmt],
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

        result = subprocess.run(
            ["tmux", "new-session", "-d", "-s", name],
            capture_output=True,
        )
        return result.returncode == 0

    def kill_session(self, name: str) -> bool:
        """Elimina una sesión de tmux."""
        if not self.is_available:
            return False

        result = subprocess.run(
            ["tmux", "kill-session", "-t", name],
            capture_output=True,
        )
        return result.returncode == 0

    def get_attach_command(self, session_name: str, window_index: int | None = None) -> list[str]:
        """Retorna el comando para adjuntar a una sesión/ventana."""
        if window_index is not None:
            target = f"{session_name}:{window_index}"
        else:
            target = session_name
        return ["tmux", "attach-session", "-t", target]

    def rename_session(self, old_name: str, new_name: str) -> bool:
        """Renombra una sesión de tmux."""
        if not self.is_available or not new_name:
            return False

        result = subprocess.run(
            ["tmux", "rename-session", "-t", old_name, new_name],
            capture_output=True,
        )
        return result.returncode == 0

    def rename_window(self, session_name: str, window_index: int, new_name: str) -> bool:
        """Renombra una ventana de tmux."""
        if not self.is_available or not new_name:
            return False

        target = f"{session_name}:{window_index}"
        result = subprocess.run(
            ["tmux", "rename-window", "-t", target, new_name],
            capture_output=True,
        )
        return result.returncode == 0

    def create_window(self, session_name: str, window_name: str | None = None) -> bool:
        """Crea una nueva ventana en una sesión."""
        if not self.is_available:
            return False

        cmd = ["tmux", "new-window", "-t", session_name]
        if window_name:
            cmd.extend(["-n", window_name])

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def exit_window(self, session_name: str, window_index: int) -> bool:
        """Envía exit a una ventana (cierre limpio)."""
        if not self.is_available:
            return False

        target = f"{session_name}:{window_index}"
        result = subprocess.run(
            ["tmux", "send-keys", "-t", target, "exit", "Enter"],
            capture_output=True,
        )
        return result.returncode == 0

    def split_horizontal(self, target: str | None = None) -> bool:
        """Divide el panel horizontalmente (paneles lado a lado)."""
        if not self.is_available:
            return False

        cmd = ["tmux", "split-window", "-h"]
        if target:
            cmd.extend(["-t", target])

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def split_vertical(self, target: str | None = None) -> bool:
        """Divide el panel verticalmente (paneles apilados)."""
        if not self.is_available:
            return False

        cmd = ["tmux", "split-window", "-v"]
        if target:
            cmd.extend(["-t", target])

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def swap_windows(self, session_name: str, src_index: int, dst_index: int) -> bool:
        """Intercambia dos ventanas dentro de una sesión."""
        if not self.is_available:
            return False

        src = f"{session_name}:{src_index}"
        dst = f"{session_name}:{dst_index}"
        result = subprocess.run(
            ["tmux", "swap-window", "-s", src, "-t", dst],
            capture_output=True,
        )
        return result.returncode == 0
