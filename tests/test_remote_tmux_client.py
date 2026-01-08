"""
test_remote_tmux_client.py - Tests para RemoteTmuxClient

Autor: Homero Thompson del Lago del Terror
"""

import subprocess
from unittest.mock import MagicMock

from src.gnome_tmux.tmux_client import RemoteTmuxClient


class TestRemoteTmuxClientInit:
    """Tests para inicialización de RemoteTmuxClient."""

    def test_init_default_port(self):
        """Test inicialización con puerto por defecto."""
        client = RemoteTmuxClient(host="myhost", user="myuser")
        assert client.host == "myhost"
        assert client.user == "myuser"
        assert client.port == "22"

    def test_init_custom_port(self):
        """Test inicialización con puerto personalizado."""
        client = RemoteTmuxClient(host="myhost", user="myuser", port="2222")
        assert client.port == "2222"


class TestRemoteTmuxClientConnection:
    """Tests para verificación de conexión."""

    def test_is_connected_no_socket(self, mock_path_exists):
        """Test is_connected retorna False si no existe socket."""
        mock_path_exists.return_value = False
        client = RemoteTmuxClient(host="test", user="user")

        assert client.is_connected() is False

    def test_is_connected_socket_exists_check_fails(
        self, mock_path_exists, mock_subprocess_run
    ):
        """Test is_connected retorna False si ssh check falla."""
        mock_path_exists.return_value = True
        mock_subprocess_run.return_value = MagicMock(returncode=1)

        client = RemoteTmuxClient(host="test", user="user")
        assert client.is_connected() is False

    def test_is_connected_success(self, mock_path_exists, mock_subprocess_run):
        """Test is_connected retorna True si todo está ok."""
        mock_path_exists.return_value = True
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        client = RemoteTmuxClient(host="test", user="user")
        assert client.is_connected() is True


class TestRemoteTmuxClientRenameFile:
    """Tests para rename_file."""

    def test_rename_file_not_connected(self, remote_client_disconnected):
        """Test rename_file retorna False si no hay conexión."""
        result = remote_client_disconnected.rename_file("/old/path", "/new/path")
        assert result is False

    def test_rename_file_success(self, remote_client_connected, successful_ssh_result):
        """Test rename_file exitoso."""
        client, mock_run = remote_client_connected
        mock_run.return_value = successful_ssh_result

        result = client.rename_file("/home/user/old.txt", "/home/user/new.txt")

        assert result is True
        # Verificar que se llamó con mv
        calls = mock_run.call_args_list
        mv_call = [c for c in calls if "mv" in str(c)]
        assert len(mv_call) > 0

    def test_rename_file_failure(self, remote_client_connected, failed_ssh_result):
        """Test rename_file fallido."""
        client, mock_run = remote_client_connected
        mock_run.return_value = failed_ssh_result

        result = client.rename_file("/home/user/old.txt", "/home/user/new.txt")
        assert result is False


class TestRemoteTmuxClientDeleteFile:
    """Tests para delete_file."""

    def test_delete_file_not_connected(self, remote_client_disconnected):
        """Test delete_file retorna False si no hay conexión."""
        result = remote_client_disconnected.delete_file("/path/to/file")
        assert result is False

    def test_delete_file_success(self, remote_client_connected, successful_ssh_result):
        """Test delete_file exitoso."""
        client, mock_run = remote_client_connected
        mock_run.return_value = successful_ssh_result

        result = client.delete_file("/home/user/file.txt")

        assert result is True
        # Verificar que se llamó con rm -rf
        calls = mock_run.call_args_list
        rm_call = [c for c in calls if "rm -rf" in str(c)]
        assert len(rm_call) > 0

    def test_delete_file_failure(self, remote_client_connected, failed_ssh_result):
        """Test delete_file fallido."""
        client, mock_run = remote_client_connected
        mock_run.return_value = failed_ssh_result

        result = client.delete_file("/home/user/file.txt")
        assert result is False


class TestRemoteTmuxClientCreateDirectory:
    """Tests para create_directory."""

    def test_create_directory_not_connected(self, remote_client_disconnected):
        """Test create_directory retorna False si no hay conexión."""
        result = remote_client_disconnected.create_directory("/new/dir")
        assert result is False

    def test_create_directory_success(
        self, remote_client_connected, successful_ssh_result
    ):
        """Test create_directory exitoso."""
        client, mock_run = remote_client_connected
        mock_run.return_value = successful_ssh_result

        result = client.create_directory("/home/user/newdir")

        assert result is True
        # Verificar que se llamó con mkdir -p
        calls = mock_run.call_args_list
        mkdir_call = [c for c in calls if "mkdir -p" in str(c)]
        assert len(mkdir_call) > 0

    def test_create_directory_failure(
        self, remote_client_connected, failed_ssh_result
    ):
        """Test create_directory fallido."""
        client, mock_run = remote_client_connected
        mock_run.return_value = failed_ssh_result

        result = client.create_directory("/home/user/newdir")
        assert result is False


class TestRemoteTmuxClientCopyFile:
    """Tests para copy_file."""

    def test_copy_file_not_connected(self, remote_client_disconnected):
        """Test copy_file retorna False si no hay conexión."""
        result = remote_client_disconnected.copy_file("/src", "/dst")
        assert result is False

    def test_copy_file_success(self, remote_client_connected, successful_ssh_result):
        """Test copy_file exitoso."""
        client, mock_run = remote_client_connected
        mock_run.return_value = successful_ssh_result

        result = client.copy_file("/home/user/file.txt", "/home/user/file_copy.txt")

        assert result is True
        # Verificar que se llamó con cp -r
        calls = mock_run.call_args_list
        cp_call = [c for c in calls if "cp -r" in str(c)]
        assert len(cp_call) > 0

    def test_copy_file_failure(self, remote_client_connected, failed_ssh_result):
        """Test copy_file fallido."""
        client, mock_run = remote_client_connected
        mock_run.return_value = failed_ssh_result

        result = client.copy_file("/src", "/dst")
        assert result is False


class TestRemoteTmuxClientFileExists:
    """Tests para file_exists."""

    def test_file_exists_not_connected(self, remote_client_disconnected):
        """Test file_exists retorna False si no hay conexión."""
        result = remote_client_disconnected.file_exists("/path")
        assert result is False

    def test_file_exists_true(self, remote_client_connected):
        """Test file_exists retorna True si el archivo existe."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = "yes"
        mock_run.return_value = result

        assert client.file_exists("/home/user/file.txt") is True

    def test_file_exists_false(self, remote_client_connected):
        """Test file_exists retorna False si el archivo no existe."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = "no"
        mock_run.return_value = result

        assert client.file_exists("/home/user/noexist.txt") is False


class TestRemoteTmuxClientIsDir:
    """Tests para is_dir."""

    def test_is_dir_not_connected(self, remote_client_disconnected):
        """Test is_dir retorna False si no hay conexión."""
        result = remote_client_disconnected.is_dir("/path")
        assert result is False

    def test_is_dir_true(self, remote_client_connected):
        """Test is_dir retorna True si es directorio."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = "yes"
        mock_run.return_value = result

        assert client.is_dir("/home/user/dir") is True

    def test_is_dir_false(self, remote_client_connected):
        """Test is_dir retorna False si no es directorio."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = "no"
        mock_run.return_value = result

        assert client.is_dir("/home/user/file.txt") is False


class TestRemoteTmuxClientListDir:
    """Tests para list_dir."""

    def test_list_dir_not_connected(self, remote_client_disconnected):
        """Test list_dir retorna None si no hay conexión."""
        result = remote_client_disconnected.list_dir("/path")
        assert result is None

    def test_list_dir_success(self, remote_client_connected):
        """Test list_dir retorna lista de entradas."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = """total 8
drwxr-xr-x 2 user user 4096 Jan  1 00:00 subdir
-rw-r--r-- 1 user user  100 Jan  1 00:00 file.txt
-rw-r--r-- 1 user user  200 Jan  1 00:00 .hidden
"""
        mock_run.return_value = result

        entries = client.list_dir("/home/user")

        assert entries is not None
        assert len(entries) == 3
        # Directorios primero
        assert entries[0]["name"] == "subdir"
        assert entries[0]["is_dir"] is True

    def test_list_dir_failure(self, remote_client_connected):
        """Test list_dir retorna None si falla."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 1
        result.stdout = ""
        mock_run.return_value = result

        entries = client.list_dir("/nonexistent")
        assert entries is None


class TestRemoteTmuxClientSearchFiles:
    """Tests para search_files."""

    def test_search_files_not_connected(self, remote_client_disconnected):
        """Test search_files retorna lista vacía si no hay conexión."""
        result = remote_client_disconnected.search_files("/path", "query")
        assert result == []

    def test_search_files_by_name(self, remote_client_connected):
        """Test search_files por nombre."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = "/home/user/test.txt\n/home/user/dir/test2.txt\n"
        mock_run.return_value = result

        files = client.search_files("/home/user", "test", mode="name")

        assert len(files) == 2
        assert "/home/user/test.txt" in files

    def test_search_files_by_content(self, remote_client_connected):
        """Test search_files por contenido."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = "/home/user/file1.py\n/home/user/file2.py\n"
        mock_run.return_value = result

        files = client.search_files("/home/user", "import", mode="content")

        assert len(files) == 2

    def test_search_files_no_results(self, remote_client_connected):
        """Test search_files sin resultados."""
        client, mock_run = remote_client_connected
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 1
        result.stdout = ""
        mock_run.return_value = result

        files = client.search_files("/home/user", "nonexistent")
        assert files == []
