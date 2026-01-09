"""
test_local_operations.py - Tests para operaciones de archivos locales

Autor: Homero Thompson del Lago del Terror
"""

# Mock gi antes de importar
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.modules["gi"] = MagicMock()
sys.modules["gi.repository"] = MagicMock()

from gnome_tmux.widgets.file_tree.local.operations import LocalFileOperations


@pytest.fixture
def operations():
    """Fixture para LocalFileOperations."""
    return LocalFileOperations()


@pytest.fixture
def temp_dir(tmp_path):
    """Directorio temporal para tests."""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    return test_dir


class TestCopyPath:
    """Tests para copy_path."""

    def test_copy_path_sets_clipboard(self, operations, temp_dir):
        """Test que copy_path guarda el path."""
        test_file = temp_dir / "file.txt"
        test_file.write_text("content")

        operations.copy_path(test_file)

        assert operations._clipboard_path == str(test_file)
        assert operations.has_clipboard() is True


class TestPastePath:
    """Tests para paste_path."""

    def test_paste_file_to_directory(self, operations, temp_dir):
        """Test pegar archivo en directorio."""
        source = temp_dir / "source.txt"
        source.write_text("test content")
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        operations._clipboard_path = str(source)
        result = operations.paste_path(dest_dir)

        assert result is not None
        assert (dest_dir / "source.txt").exists()
        assert (dest_dir / "source.txt").read_text() == "test content"

    def test_paste_with_name_collision(self, operations, temp_dir):
        """Test pegar con nombre existente agrega sufijo."""
        source = temp_dir / "file.txt"
        source.write_text("original")
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()
        (dest_dir / "file.txt").write_text("existing")

        operations._clipboard_path = str(source)
        result = operations.paste_path(dest_dir)

        assert result is not None
        assert (dest_dir / "file_1.txt").exists()

    def test_paste_directory(self, operations, temp_dir):
        """Test pegar directorio completo."""
        source_dir = temp_dir / "source_folder"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        operations._clipboard_path = str(source_dir)
        result = operations.paste_path(dest_dir)

        assert result is not None
        assert (dest_dir / "source_folder").is_dir()
        assert (dest_dir / "source_folder" / "file1.txt").exists()

    def test_paste_no_clipboard(self, operations, temp_dir):
        """Test que paste sin clipboard retorna None."""
        result = operations.paste_path(temp_dir)
        assert result is None


class TestRenamePath:
    """Tests para rename_path."""

    def test_rename_file_success(self, operations, temp_dir):
        """Test renombrar archivo exitosamente."""
        file = temp_dir / "old_name.txt"
        file.write_text("content")

        result = operations.rename_path(file, "new_name.txt")

        assert result is True
        assert not file.exists()
        assert (temp_dir / "new_name.txt").exists()

    def test_rename_with_same_name(self, operations, temp_dir):
        """Test renombrar con el mismo nombre retorna False."""
        file = temp_dir / "file.txt"
        file.write_text("content")

        result = operations.rename_path(file, "file.txt")

        assert result is False
        assert file.exists()

    def test_rename_empty_name(self, operations, temp_dir):
        """Test renombrar con nombre vacío retorna False."""
        file = temp_dir / "file.txt"
        file.write_text("content")

        result = operations.rename_path(file, "")

        assert result is False


class TestDeletePath:
    """Tests para delete_path."""

    def test_delete_file_to_trash(self, operations, temp_dir):
        """Test que delete mueve a ~/.trash."""
        file = temp_dir / "to_delete.txt"
        file.write_text("content")

        result = operations.delete_path(file)

        assert result is True
        assert not file.exists()
        trash = Path.home() / ".trash"
        assert any(f.name.startswith("to_delete") for f in trash.iterdir())

    def test_delete_directory(self, operations, temp_dir):
        """Test eliminar directorio."""
        folder = temp_dir / "folder"
        folder.mkdir()
        (folder / "file.txt").write_text("content")

        result = operations.delete_path(folder)

        assert result is True
        assert not folder.exists()


class TestClipboardOperations:
    """Tests para clipboard."""

    def test_has_clipboard_initially_false(self, operations):
        """Test que clipboard está vacío inicialmente."""
        assert operations.has_clipboard() is False

    def test_has_clipboard_after_copy(self, operations, temp_dir):
        """Test que has_clipboard retorna True después de copiar."""
        file = temp_dir / "file.txt"
        file.write_text("content")

        operations.copy_path(file)

        assert operations.has_clipboard() is True

    def test_clear_clipboard(self, operations, temp_dir):
        """Test que clear_clipboard limpia."""
        file = temp_dir / "file.txt"
        file.write_text("content")

        operations.copy_path(file)
        operations.clear_clipboard()

        assert operations.has_clipboard() is False
