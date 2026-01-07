"""
remote_hosts.py - Gestión de hosts remotos para sesiones SSH

Autor: Homero Thompson del Lago del Terror
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from gi.repository import GLib


@dataclass
class RemoteHost:
    """Representa un host remoto para conexiones SSH."""

    name: str  # Nombre descriptivo (ej: "Production Server")
    host: str  # Hostname o IP
    user: str  # Usuario SSH
    port: str = "22"  # Puerto SSH
    last_used: str = ""  # ISO timestamp de último uso


@dataclass
class RemoteHostsConfig:
    """Configuración de hosts remotos."""

    hosts: list[RemoteHost] = field(default_factory=list)


class RemoteHostsManager:
    """Gestiona la persistencia de hosts remotos."""

    def __init__(self):
        self._config_dir = Path(GLib.get_user_config_dir()) / "gnome-tmux"
        self._config_file = self._config_dir / "remote_hosts.json"
        self._hosts: list[RemoteHost] = []
        self._load()

    def _load(self):
        """Carga hosts desde el archivo de configuración."""
        if not self._config_file.exists():
            self._hosts = []
            return

        try:
            data = json.loads(self._config_file.read_text())
            self._hosts = [RemoteHost(**h) for h in data.get("hosts", [])]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._hosts = []

    def _save(self):
        """Guarda hosts en el archivo de configuración."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        data = {"hosts": [asdict(h) for h in self._hosts]}
        self._config_file.write_text(json.dumps(data, indent=2))

    def get_hosts(self) -> list[RemoteHost]:
        """Retorna lista de hosts ordenada por último uso."""
        return sorted(self._hosts, key=lambda h: h.last_used, reverse=True)

    def add_host(self, host: RemoteHost) -> None:
        """Agrega o actualiza un host."""
        # Buscar si ya existe (mismo host+user+port)
        for i, h in enumerate(self._hosts):
            if h.host == host.host and h.user == host.user and h.port == host.port:
                # Actualizar existente
                self._hosts[i] = host
                self._save()
                return

        # Agregar nuevo
        self._hosts.append(host)
        self._save()

    def remove_host(self, host: RemoteHost) -> bool:
        """Elimina un host. Retorna True si se eliminó."""
        for i, h in enumerate(self._hosts):
            if h.host == host.host and h.user == host.user and h.port == host.port:
                del self._hosts[i]
                self._save()
                return True
        return False

    def update_last_used(self, host: str, user: str, port: str) -> None:
        """Actualiza el timestamp de último uso de un host."""
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).isoformat()
        for h in self._hosts:
            if h.host == host and h.user == user and h.port == port:
                h.last_used = timestamp
                self._save()
                return

    def find_host(self, host: str, user: str, port: str) -> RemoteHost | None:
        """Busca un host por sus datos de conexión."""
        for h in self._hosts:
            if h.host == host and h.user == user and h.port == port:
                return h
        return None


# Singleton para uso global
remote_hosts_manager = RemoteHostsManager()
