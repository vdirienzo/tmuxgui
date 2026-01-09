"""
test_models.py - Tests para modelos de datos

Autor: Homero Thompson del Lago del Terror
"""

from pathlib import Path
from unittest.mock import patch

from gnome_tmux.clients.models import Session, Window, get_ssh_control_path, is_flatpak


class TestSession:
    """Tests para dataclass Session."""

    def test_session_creation(self):
        """Test crear sesión con todos los campos."""
        session = Session(
            name="dev",
            window_count=3,
            attached=True,
        )

        assert session.name == "dev"
        assert session.window_count == 3
        assert session.attached is True

    def test_session_not_attached(self):
        """Test sesión no attached."""
        session = Session(name="bg", window_count=1, attached=False)

        assert session.attached is False


class TestWindow:
    """Tests para dataclass Window."""

    def test_window_creation(self):
        """Test crear ventana."""
        window = Window(index=0, name="bash", active=True)

        assert window.index == 0
        assert window.name == "bash"
        assert window.active is True

    def test_window_inactive(self):
        """Test ventana inactiva."""
        window = Window(index=1, name="vim", active=False)

        assert window.active is False


class TestGetSSHControlPath:
    """Tests para get_ssh_control_path."""

    def test_creates_directory_if_not_exists(self):
        """Test que crea el directorio si no existe."""
        path = get_ssh_control_path("testhost", "testuser", "22")

        socket_dir = Path.home() / ".ssh" / "gnome-tmux-sockets"
        assert socket_dir.exists()
        assert socket_dir.is_dir()

    def test_returns_correct_path(self):
        """Test que retorna el path correcto."""
        path = get_ssh_control_path("myhost", "myuser", "2222")

        expected = str(Path.home() / ".ssh" / "gnome-tmux-sockets" / "myuser@myhost-2222")
        assert path == expected

    def test_path_includes_all_components(self):
        """Test que incluye host, user y port."""
        path = get_ssh_control_path("192.168.1.10", "admin", "custom_port")

        assert "admin" in path
        assert "192.168.1.10" in path
        assert "custom_port" in path


class TestIsFlatpak:
    """Tests para is_flatpak."""

    def test_flatpak_detected(self):
        """Test detecta cuando está en flatpak."""
        with patch("os.path.exists", return_value=True):
            assert is_flatpak() is True

    def test_not_flatpak(self):
        """Test detecta cuando NO está en flatpak."""
        with patch("os.path.exists", return_value=False):
            assert is_flatpak() is False
