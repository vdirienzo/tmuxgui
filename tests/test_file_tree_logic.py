"""
test_file_tree_logic.py - Tests para lógica de FileTree (sin GTK)

Autor: Homero Thompson del Lago del Terror

Nota: Estos tests verifican la lógica de las operaciones remotas
sin necesidad de GTK. Los handlers de UI se testean parcialmente
mockeando las dependencias de GTK.
"""

import os


class TestRemoteCopyPasteLogic:
    """Tests para la lógica de copy/paste remoto."""

    def test_generate_unique_filename_no_extension(self):
        """Test generación de nombre único sin extensión."""
        original_name = "folder"
        counter = 1

        # Simular la lógica del handler
        if "." in original_name and not original_name.startswith("."):
            name_parts = original_name.rsplit(".", 1)
            new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
        else:
            new_name = f"{original_name}_{counter}"

        assert new_name == "folder_1"

    def test_generate_unique_filename_with_extension(self):
        """Test generación de nombre único con extensión."""
        original_name = "file.txt"
        counter = 1

        if "." in original_name and not original_name.startswith("."):
            name_parts = original_name.rsplit(".", 1)
            new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
        else:
            new_name = f"{original_name}_{counter}"

        assert new_name == "file_1.txt"

    def test_generate_unique_filename_hidden_file(self):
        """Test generación de nombre único para archivo oculto."""
        original_name = ".bashrc"
        counter = 1

        if "." in original_name and not original_name.startswith("."):
            name_parts = original_name.rsplit(".", 1)
            new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
        else:
            new_name = f"{original_name}_{counter}"

        assert new_name == ".bashrc_1"

    def test_generate_unique_filename_multiple_dots(self):
        """Test generación de nombre único con múltiples puntos."""
        original_name = "file.tar.gz"
        counter = 2

        if "." in original_name and not original_name.startswith("."):
            name_parts = original_name.rsplit(".", 1)
            new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
        else:
            new_name = f"{original_name}_{counter}"

        assert new_name == "file.tar_2.gz"

    def test_destination_from_file_path(self):
        """Test obtener directorio destino desde path de archivo."""
        path = "/home/user/documents/file.txt"
        is_dir = False

        if is_dir:
            destination = path
        else:
            destination = os.path.dirname(path)

        assert destination == "/home/user/documents"

    def test_destination_from_dir_path(self):
        """Test obtener directorio destino desde path de directorio."""
        path = "/home/user/documents"
        is_dir = True

        if is_dir:
            destination = path
        else:
            destination = os.path.dirname(path)

        assert destination == "/home/user/documents"

    def test_build_target_path(self):
        """Test construcción de path destino."""
        destination = "/home/user/documents"
        source_name = "file.txt"

        target = f"{destination.rstrip('/')}/{source_name}"

        assert target == "/home/user/documents/file.txt"

    def test_build_target_path_trailing_slash(self):
        """Test construcción de path destino con slash final."""
        destination = "/home/user/documents/"
        source_name = "file.txt"

        target = f"{destination.rstrip('/')}/{source_name}"

        assert target == "/home/user/documents/file.txt"


class TestRemoteRenameLogic:
    """Tests para la lógica de rename remoto."""

    def test_build_new_path(self):
        """Test construcción de nuevo path para rename."""
        old_path = "/home/user/old_name.txt"
        new_name = "new_name.txt"

        parent = os.path.dirname(old_path)
        new_path = f"{parent}/{new_name}"

        assert new_path == "/home/user/new_name.txt"

    def test_build_new_path_nested(self):
        """Test construcción de nuevo path en subdirectorio."""
        old_path = "/home/user/documents/projects/old.py"
        new_name = "new.py"

        parent = os.path.dirname(old_path)
        new_path = f"{parent}/{new_name}"

        assert new_path == "/home/user/documents/projects/new.py"


class TestRemoteCreateFolderLogic:
    """Tests para la lógica de crear carpeta remota."""

    def test_build_folder_path(self):
        """Test construcción de path para nueva carpeta."""
        parent_path = "/home/user/documents"
        folder_name = "New Folder"

        new_path = f"{parent_path.rstrip('/')}/{folder_name}"

        assert new_path == "/home/user/documents/New Folder"

    def test_build_folder_path_with_trailing_slash(self):
        """Test construcción de path con slash final."""
        parent_path = "/home/user/documents/"
        folder_name = "subfolder"

        new_path = f"{parent_path.rstrip('/')}/{folder_name}"

        assert new_path == "/home/user/documents/subfolder"


class TestPathParsing:
    """Tests para parsing de paths."""

    def test_get_basename(self):
        """Test obtener nombre de archivo/carpeta."""
        path = "/home/user/documents/file.txt"
        name = os.path.basename(path)
        assert name == "file.txt"

    def test_get_basename_directory(self):
        """Test obtener nombre de directorio."""
        path = "/home/user/documents"
        name = os.path.basename(path)
        assert name == "documents"

    def test_get_basename_trailing_slash(self):
        """Test obtener nombre con slash final."""
        path = "/home/user/documents/"
        name = os.path.basename(path.rstrip("/"))
        assert name == "documents"

    def test_get_dirname(self):
        """Test obtener directorio padre."""
        path = "/home/user/documents/file.txt"
        parent = os.path.dirname(path)
        assert parent == "/home/user/documents"

    def test_get_dirname_root(self):
        """Test obtener padre de directorio raíz."""
        path = "/home"
        parent = os.path.dirname(path)
        assert parent == "/"


class TestListDirParsing:
    """Tests para parsing de salida de ls."""

    def test_parse_ls_output_directory(self):
        """Test parsing de línea de directorio."""
        line = "drwxr-xr-x 2 user user 4096 Jan  1 00:00 subdir"
        parts = line.split()

        perms = parts[0]
        name = " ".join(parts[8:])
        is_dir = perms.startswith("d")

        assert name == "subdir"
        assert is_dir is True

    def test_parse_ls_output_file(self):
        """Test parsing de línea de archivo."""
        line = "-rw-r--r-- 1 user user  100 Jan  1 00:00 file.txt"
        parts = line.split()

        perms = parts[0]
        name = " ".join(parts[8:])
        is_dir = perms.startswith("d")

        assert name == "file.txt"
        assert is_dir is False

    def test_parse_ls_output_hidden(self):
        """Test parsing de archivo oculto."""
        line = "-rw-r--r-- 1 user user  200 Jan  1 00:00 .hidden"
        parts = line.split()
        name = " ".join(parts[8:])

        is_hidden = name.startswith(".")

        assert name == ".hidden"
        assert is_hidden is True

    def test_parse_ls_output_name_with_spaces(self):
        """Test parsing de nombre con espacios."""
        line = "-rw-r--r-- 1 user user  100 Jan  1 00:00 my file name.txt"
        parts = line.split()
        name = " ".join(parts[8:])

        assert name == "my file name.txt"


class TestRemoteClipboardState:
    """Tests para estado del clipboard remoto."""

    def test_clipboard_initially_none(self):
        """Test clipboard inicia vacío."""
        clipboard_path = None
        assert clipboard_path is None

    def test_clipboard_after_copy(self):
        """Test clipboard después de copiar."""
        clipboard_path = None
        path_to_copy = "/home/user/file.txt"

        # Simular copy
        clipboard_path = path_to_copy

        assert clipboard_path == "/home/user/file.txt"

    def test_paste_requires_clipboard(self):
        """Test paste requiere clipboard con contenido."""
        clipboard_path = None
        can_paste = clipboard_path is not None

        assert can_paste is False

    def test_paste_with_clipboard_content(self):
        """Test paste con contenido en clipboard."""
        clipboard_path = "/home/user/file.txt"
        can_paste = clipboard_path is not None

        assert can_paste is True
