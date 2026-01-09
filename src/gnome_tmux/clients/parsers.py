"""
parsers.py - Funciones de parsing para output de tmux

Autor: Homero Thompson del Lago del Terror
"""

from .models import Session, Window


def parse_session_line(line: str) -> Session | None:
    """
    Parsea una línea de output de tmux list-sessions.
    Formato esperado: name:window_count:attached
    """
    if not line:
        return None

    parts = line.split(":")
    if len(parts) < 3:
        return None

    try:
        return Session(
            name=parts[0],
            window_count=int(parts[1]),
            attached=parts[2] == "1",
            windows=[],
        )
    except (ValueError, IndexError):
        return None


def parse_window_line(line: str) -> Window | None:
    """
    Parsea una línea de output de tmux list-windows.
    Formato esperado: index:name:active
    """
    if not line:
        return None

    parts = line.split(":")
    if len(parts) < 3:
        return None

    try:
        return Window(
            index=int(parts[0]),
            name=parts[1],
            active=parts[2] == "1",
        )
    except (ValueError, IndexError):
        return None


def parse_sessions_output(output: str) -> list[Session]:
    """Parsea el output completo de list-sessions."""
    sessions = []
    for line in output.strip().split("\n"):
        session = parse_session_line(line)
        if session:
            sessions.append(session)
    return sessions


def parse_windows_output(output: str) -> list[Window]:
    """Parsea el output completo de list-windows."""
    windows = []
    for line in output.strip().split("\n"):
        window = parse_window_line(line)
        if window:
            windows.append(window)
    return windows


# Formatos de tmux para queries
SESSION_FORMAT = "#{session_name}:#{session_windows}:#{session_attached}"
WINDOW_FORMAT = "#{window_index}:#{window_name}:#{window_active}"
