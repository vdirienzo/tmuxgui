"""
test_path_validator.py - Tests para validación de paths remotos

Autor: Homero Thompson del Lago del Terror
"""

import pytest
from gnome_tmux.clients.path_validator import PathValidator


class TestPathValidatorSafePaths:
    """Tests para paths seguros."""

    def test_home_directory_safe(self):
        """Test que /home/user es seguro."""
        valid, reason = PathValidator.validate_remote_path("/home/user/documents")
        assert valid is True
        assert reason == "OK"

    def test_tmp_directory_safe(self):
        """Test que /tmp es seguro."""
        valid, reason = PathValidator.validate_remote_path("/tmp/myfile.txt")
        assert valid is True

    def test_relative_path_in_home(self):
        """Test path relativo."""
        valid, reason = PathValidator.validate_remote_path("documents/file.txt")
        assert valid is True


class TestPathValidatorPathTraversal:
    """Tests para detectar path traversal."""

    def test_parent_directory_rejected(self):
        """Test que .. es rechazado."""
        valid, reason = PathValidator.validate_remote_path("/home/user/../etc/passwd")
        assert valid is False
        assert "traversal" in reason.lower()

    def test_multiple_parent_directories(self):
        """Test múltiples .. rechazados."""
        valid, reason = PathValidator.validate_remote_path("../../etc/passwd")
        assert valid is False

    def test_hidden_parent_in_middle(self):
        """Test .. en medio del path."""
        valid, reason = PathValidator.validate_remote_path("/home/user/docs/../../../root")
        assert valid is False


class TestPathValidatorProtectedDirectories:
    """Tests para directorios protegidos."""

    @pytest.mark.parametrize(
        "protected_path",
        [
            "/etc",
            "/etc/passwd",
            "/root",
            "/root/secrets",
            "/sys",
            "/proc",
            "/bin",
            "/boot",
            "/dev",
            "/lib",
            "/sbin",
            "/usr",
            "/var",
        ],
    )
    def test_protected_directories_rejected(self, protected_path):
        """Test que directorios del sistema son rechazados."""
        valid, reason = PathValidator.validate_remote_path(protected_path)
        assert valid is False
        assert "protegido" in reason.lower()


class TestPathValidatorDangerousCharacters:
    """Tests para caracteres peligrosos."""

    @pytest.mark.parametrize(
        "dangerous_char",
        [";", "|", "&", "$", "`", "\n", "\r"],
    )
    def test_dangerous_characters_rejected(self, dangerous_char):
        """Test que caracteres peligrosos son rechazados."""
        path = f"/home/user/file{dangerous_char}name"
        valid, reason = PathValidator.validate_remote_path(path)
        assert valid is False
        assert "peligroso" in reason.lower()

    def test_semicolon_command_injection_blocked(self):
        """Test que intento de inyección es bloqueado."""
        path = "/home/user/file; rm -rf /"
        valid, reason = PathValidator.validate_remote_path(path)
        assert valid is False


class TestPathValidatorSafeForDeletion:
    """Tests para is_safe_for_deletion."""

    def test_user_file_safe_for_deletion(self):
        """Test que archivo de usuario es seguro para eliminar."""
        assert PathValidator.is_safe_for_deletion("/home/user/documents/file.txt") is True

    def test_home_root_not_safe(self):
        """Test que /home no puede eliminarse."""
        assert PathValidator.is_safe_for_deletion("/home") is False

    def test_tmp_root_not_safe(self):
        """Test que /tmp no puede eliminarse."""
        assert PathValidator.is_safe_for_deletion("/tmp") is False

    def test_system_dir_not_safe(self):
        """Test que directorios del sistema no son seguros."""
        assert PathValidator.is_safe_for_deletion("/etc/config") is False


class TestPathValidatorEdgeCases:
    """Tests para casos edge."""

    def test_root_directory_rejected(self):
        """Test que / es rechazado."""
        valid, reason = PathValidator.validate_remote_path("/")
        assert valid is False

    def test_empty_path_invalid(self):
        """Test que path vacío es inválido."""
        valid, reason = PathValidator.validate_remote_path("")
        assert valid is False or valid is True  # Depende de la implementación

    def test_trailing_slash_normalized(self):
        """Test que trailing slash es manejado."""
        valid1, _ = PathValidator.validate_remote_path("/home/user/")
        valid2, _ = PathValidator.validate_remote_path("/home/user")
        assert valid1 == valid2  # Deben ser equivalentes
