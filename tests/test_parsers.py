"""
test_parsers.py - Tests para parsers de output de tmux

Autor: Homero Thompson del Lago del Terror
"""

from gnome_tmux.clients.parsers import (
    SESSION_FORMAT,
    WINDOW_FORMAT,
    parse_session_line,
    parse_sessions_output,
    parse_window_line,
    parse_windows_output,
)


class TestParseSessionLine:
    """Tests para parse_session_line."""

    def test_parse_valid_line(self):
        """Test parsear línea válida."""
        line = "dev:3:1"
        session = parse_session_line(line)

        assert session is not None
        assert session.name == "dev"
        assert session.window_count == 3
        assert session.attached is True

    def test_parse_not_attached(self):
        """Test attached=0."""
        line = "bg:1:0"
        session = parse_session_line(line)

        assert session is not None
        assert session.attached is False

    def test_parse_empty_line(self):
        """Test línea vacía retorna None."""
        assert parse_session_line("") is None

    def test_parse_insufficient_parts(self):
        """Test línea con < 3 partes retorna None."""
        assert parse_session_line("only:two") is None

    def test_parse_invalid_number(self):
        """Test window_count inválido retorna None."""
        assert parse_session_line("name:notanumber:1") is None


class TestParseWindowLine:
    """Tests para parse_window_line."""

    def test_parse_valid_line(self):
        """Test parsear línea válida."""
        line = "0:bash:1"
        window = parse_window_line(line)

        assert window is not None
        assert window.index == 0
        assert window.name == "bash"
        assert window.active is True

    def test_parse_inactive_window(self):
        """Test active=0."""
        line = "1:vim:0"
        window = parse_window_line(line)

        assert window is not None
        assert window.active is False

    def test_parse_empty_line(self):
        """Test línea vacía retorna None."""
        assert parse_window_line("") is None

    def test_parse_insufficient_parts(self):
        """Test línea con < 3 partes retorna None."""
        assert parse_window_line("0:bash") is None

    def test_parse_invalid_index(self):
        """Test índice inválido retorna None."""
        assert parse_window_line("notanum:bash:1") is None


class TestFormatConstants:
    """Tests para constantes de formato."""

    def test_session_format_defined(self):
        """Test que SESSION_FORMAT está definido."""
        assert SESSION_FORMAT == "#{session_name}:#{session_windows}:#{session_attached}"

    def test_window_format_defined(self):
        """Test que WINDOW_FORMAT está definido."""
        assert WINDOW_FORMAT == "#{window_index}:#{window_name}:#{window_active}"


class TestParseSessionsOutput:
    """Tests para parse_sessions_output."""

    def test_parse_single_session(self):
        """Test parsear una sesión."""
        output = "mysession:1:0:2026-01-09 19:00:00"

        sessions = parse_sessions_output(output)

        assert len(sessions) == 1
        assert sessions[0].name == "mysession"
        assert sessions[0].window_count == 1
        assert sessions[0].attached is False

    def test_parse_attached_session(self):
        """Test sesión attached (attached=1)."""
        output = "dev:3:1:2026-01-09 19:00:00"

        sessions = parse_sessions_output(output)

        assert len(sessions) == 1
        assert sessions[0].name == "dev"
        assert sessions[0].window_count == 3
        assert sessions[0].attached is True

    def test_parse_multiple_sessions(self):
        """Test múltiples sesiones."""
        output = """session1:1:0:2026-01-09 19:00:00
session2:5:1:2026-01-09 19:01:00
session3:2:0:2026-01-09 19:02:00"""

        sessions = parse_sessions_output(output)

        assert len(sessions) == 3
        assert sessions[0].name == "session1"
        assert sessions[1].name == "session2"
        assert sessions[1].attached is True
        assert sessions[2].name == "session3"

    def test_parse_empty_output(self):
        """Test output vacío."""
        sessions = parse_sessions_output("")
        assert sessions == []

    def test_parse_malformed_line_skipped(self):
        """Test que líneas malformadas se saltan."""
        output = """good:2:0:2026-01-09 19:00:00
badline
another-good:1:1:2026-01-09 19:01:00"""

        sessions = parse_sessions_output(output)

        assert len(sessions) == 2
        assert sessions[0].name == "good"
        assert sessions[1].name == "another-good"


class TestParseWindowsOutput:
    """Tests para parse_windows_output."""

    def test_parse_single_window(self):
        """Test parsear una ventana."""
        output = "0:bash:1"

        windows = parse_windows_output(output)

        assert len(windows) == 1
        assert windows[0].index == 0
        assert windows[0].name == "bash"
        assert windows[0].active is True

    def test_parse_inactive_window(self):
        """Test ventana inactive (active=0)."""
        output = "1:vim:0"

        windows = parse_windows_output(output)

        assert len(windows) == 1
        assert windows[0].index == 1
        assert windows[0].name == "vim"
        assert windows[0].active is False

    def test_parse_multiple_windows(self):
        """Test múltiples ventanas."""
        output = """0:bash:0
1:vim:1
2:htop:0"""

        windows = parse_windows_output(output)

        assert len(windows) == 3
        assert windows[0].index == 0
        assert windows[1].index == 1
        assert windows[1].active is True
        assert windows[2].index == 2

    def test_parse_empty_output(self):
        """Test output vacío."""
        windows = parse_windows_output("")
        assert windows == []

    def test_parse_malformed_line_skipped(self):
        """Test líneas malformadas se saltan."""
        output = """0:bash:1
invalid
2:vim:0"""

        windows = parse_windows_output(output)

        assert len(windows) == 2
        assert windows[0].index == 0
        assert windows[1].index == 2

    def test_window_index_conversion(self):
        """Test que índices se convierten a int correctamente."""
        output = "5:window5:0"

        windows = parse_windows_output(output)

        assert windows[0].index == 5
        assert isinstance(windows[0].index, int)
