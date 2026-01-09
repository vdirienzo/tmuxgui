"""
conftest.py - Fixtures para pytest

Autor: Homero Thompson del Lago del Terror
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_subprocess_run():
    """Mock para subprocess.run."""
    with patch("subprocess.run") as mock:
        yield mock


@pytest.fixture
def mock_path_exists():
    """Mock para Path.exists."""
    with patch("pathlib.Path.exists") as mock:
        yield mock


@pytest.fixture
def successful_ssh_result():
    """Resultado exitoso de comando SSH."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


@pytest.fixture
def failed_ssh_result():
    """Resultado fallido de comando SSH."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 1
    result.stdout = ""
    result.stderr = "error"
    return result


@pytest.fixture
def remote_client_connected(mock_subprocess_run, mock_path_exists):
    """RemoteTmuxClient con conexión activa mockeada."""
    from gnome_tmux.clients import RemoteTmuxClient

    # Socket existe
    mock_path_exists.return_value = True

    # ssh -O check retorna exitoso
    check_result = MagicMock(spec=subprocess.CompletedProcess)
    check_result.returncode = 0
    mock_subprocess_run.return_value = check_result

    client = RemoteTmuxClient(host="testhost", user="testuser", port="22")
    return client, mock_subprocess_run


@pytest.fixture
def remote_client_disconnected(mock_path_exists):
    """RemoteTmuxClient sin conexión."""
    from gnome_tmux.clients import RemoteTmuxClient

    # Socket no existe
    mock_path_exists.return_value = False

    client = RemoteTmuxClient(host="testhost", user="testuser", port="22")
    return client
