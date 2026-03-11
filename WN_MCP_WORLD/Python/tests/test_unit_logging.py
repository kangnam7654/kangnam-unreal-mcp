"""Unit tests for mcp_logging package.

Tests logging initialization, level control, ring buffer, cleanup, and Agent tools.
No UE connection required.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_logger():
    """Remove wn_mcp_world logger handlers before/after each test."""
    import mcp_logging
    root = logging.getLogger("wn_mcp_world")
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    mcp_logging._ring_handler = None
    mcp_logging._file_handler = None
    yield
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    mcp_logging._ring_handler = None
    mcp_logging._file_handler = None


@pytest.fixture
def tmp_log_dir(tmp_path):
    """Provide a temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def tmp_settings(tmp_path):
    """Create a temporary Settings.ini and return its path."""
    settings_path = tmp_path / "Settings.ini"
    settings_path.write_text(
        "[Logging]\n"
        "LOG_LEVEL = DEBUG\n"
        "LOG_RETENTION_DAYS = 7\n"
        "MAX_LOG_FILES = 3\n"
        "LOG_AUTO_CLEANUP = true\n",
        encoding="utf-8",
    )
    return settings_path


# ---------------------------------------------------------------------------
# config tests
# ---------------------------------------------------------------------------


class TestConfig:

    def test_parse_level_all(self):
        from mcp_logging.config import parse_level, MISC

        assert parse_level("MISC") == MISC
        assert parse_level("DEBUG") == 10
        assert parse_level("INFO") == 20
        assert parse_level("WARNING") == 30
        assert parse_level("ERROR") == 40

    def test_parse_level_case_insensitive(self):
        from mcp_logging.config import parse_level

        assert parse_level("debug") == 10
        assert parse_level("Info") == 20
        assert parse_level("misc") == 5

    def test_parse_level_unknown_defaults_to_info(self):
        from mcp_logging.config import parse_level

        assert parse_level("UNKNOWN") == 20

    def test_load_settings_with_file(self, tmp_settings):
        from mcp_logging.config import load_settings

        with patch("mcp_logging.config.SETTINGS_PATH", tmp_settings):
            settings = load_settings()

        assert settings["log_level"] == "DEBUG"
        assert settings["max_log_files"] == "3"

    def test_load_settings_without_file(self, tmp_path):
        from mcp_logging.config import load_settings

        missing = tmp_path / "nonexistent.ini"
        with patch("mcp_logging.config.SETTINGS_PATH", missing):
            settings = load_settings()

        assert settings["log_level"] == "MISC"
        assert settings["max_log_files"] == "2"


# ---------------------------------------------------------------------------
# RingBufferHandler tests
# ---------------------------------------------------------------------------


class TestRingBufferHandler:

    def test_emit_stores_entry(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=10)
        record = logging.LogRecord(
            "wn_mcp_world.test", logging.INFO, "", 0, "hello", (), None,
        )
        handler.emit(record)

        assert handler.total_count == 1
        entries = handler.get_entries(count=10, min_level=logging.INFO)
        assert len(entries) == 1
        assert entries[0]["message"] == "hello"
        assert entries[0]["logger"] == "test"
        assert entries[0]["level"] == "INFO"

    def test_maxlen_enforced(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=3)
        for i in range(5):
            record = logging.LogRecord(
                "wn_mcp_world", logging.INFO, "", 0, f"msg{i}", (), None,
            )
            handler.emit(record)

        assert handler.total_count == 3
        entries = handler.get_entries(count=10, min_level=logging.INFO)
        assert [e["message"] for e in entries] == ["msg4", "msg3", "msg2"]

    def test_get_entries_level_filter(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=100)
        for level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]:
            record = logging.LogRecord(
                "wn_mcp_world", level, "", 0, f"level-{level}", (), None,
            )
            handler.emit(record)

        errors = handler.get_entries(count=10, min_level=logging.ERROR)
        assert len(errors) == 1
        assert errors[0]["level"] == "ERROR"

        warnings = handler.get_entries(count=10, min_level=logging.WARNING)
        assert len(warnings) == 2

    def test_get_entries_keyword_filter(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=100)
        for msg in ["spawn_actor called", "delete_actor called", "connected"]:
            record = logging.LogRecord(
                "wn_mcp_world", logging.INFO, "", 0, msg, (), None,
            )
            handler.emit(record)

        result = handler.get_entries(count=10, min_level=logging.INFO, keyword="actor")
        assert len(result) == 2

    def test_get_entries_keyword_case_insensitive(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=100)
        record = logging.LogRecord(
            "wn_mcp_world", logging.INFO, "", 0, "SPAWN_ACTOR", (), None,
        )
        handler.emit(record)

        result = handler.get_entries(count=10, min_level=logging.INFO, keyword="spawn_actor")
        assert len(result) == 1

    def test_get_entries_count_limit(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=100)
        for i in range(10):
            record = logging.LogRecord(
                "wn_mcp_world", logging.INFO, "", 0, f"msg{i}", (), None,
            )
            handler.emit(record)

        result = handler.get_entries(count=3, min_level=logging.INFO)
        assert len(result) == 3

    def test_get_entries_newest_first(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=100)
        for i in range(3):
            record = logging.LogRecord(
                "wn_mcp_world", logging.INFO, "", 0, f"msg{i}", (), None,
            )
            handler.emit(record)

        entries = handler.get_entries(count=10, min_level=logging.INFO)
        assert entries[0]["message"] == "msg2"
        assert entries[2]["message"] == "msg0"

    def test_logger_name_strip_prefix(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=10)

        record = logging.LogRecord(
            "wn_mcp_world.ue_connection", logging.INFO, "", 0, "test", (), None,
        )
        handler.emit(record)

        assert handler.get_entries(count=1, min_level=0)[0]["logger"] == "ue_connection"

    def test_root_logger_name_becomes_server(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=10)

        record = logging.LogRecord(
            "wn_mcp_world", logging.INFO, "", 0, "test", (), None,
        )
        handler.emit(record)

        assert handler.get_entries(count=1, min_level=0)[0]["logger"] == "server"

    def test_get_entries_with_total_atomic(self):
        from mcp_logging.ring_buffer import RingBufferHandler

        handler = RingBufferHandler(maxlen=100)
        for i in range(5):
            record = logging.LogRecord(
                "wn_mcp_world", logging.INFO, "", 0, f"msg{i}", (), None,
            )
            handler.emit(record)

        entries, total = handler.get_entries_with_total(count=3, min_level=logging.INFO)
        assert total == 5
        assert len(entries) == 3
        assert entries[0]["message"] == "msg4"


# ---------------------------------------------------------------------------
# initialize / set_level / get_level / get_recent_entries tests
# ---------------------------------------------------------------------------


class TestInitialize:

    def test_initialize_creates_log_file(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        today = datetime.now().strftime("%Y-%m-%d")
        assert (log_dir / f"mcp_{today}.log").exists()

    def test_initialize_sets_level_from_settings(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        assert mcp_logging.get_level() == "DEBUG"

    def test_set_level(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        result = mcp_logging.set_level("ERROR")
        assert result == "ERROR"
        assert mcp_logging.get_level() == "ERROR"

    def test_set_level_misc(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        result = mcp_logging.set_level("MISC")
        assert result == "MISC"

    def test_get_recent_entries(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        logger = logging.getLogger("wn_mcp_world.test")
        logger.info("test message 1")
        logger.info("test message 2")
        logger.error("error message")

        result = mcp_logging.get_recent_entries(count=10, level="INFO")
        # +1 for "Logging initialized" message
        assert result["returned"] >= 3

        errors = mcp_logging.get_recent_entries(count=10, level="ERROR")
        assert errors["returned"] == 1
        assert errors["entries"][0]["message"] == "error message"

    def test_get_recent_entries_max_200(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        result = mcp_logging.get_recent_entries(count=999)
        assert result["returned"] <= 200 or result["total_in_buffer"] <= 200

    def test_get_recent_entries_before_initialize(self):
        import mcp_logging

        mcp_logging._ring_handler = None
        result = mcp_logging.get_recent_entries()
        assert result["total_in_buffer"] == 0

    def test_initialize_is_idempotent(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()
            mcp_logging.initialize()  # Second call should be no-op

        root = logging.getLogger("wn_mcp_world")
        assert len(root.handlers) == 2  # FileHandler + RingBufferHandler

    def test_get_recent_entries_count_zero_returns_one(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        result = mcp_logging.get_recent_entries(count=0, level="MISC")
        assert result["returned"] >= 1  # At least "Logging initialized"


# ---------------------------------------------------------------------------
# cleanup tests
# ---------------------------------------------------------------------------


class TestCleanup:

    def test_cleanup_by_retention_days(self, tmp_log_dir):
        import mcp_logging

        today = datetime.now()
        for days_ago in [0, 3, 10, 15]:
            date = today - timedelta(days=days_ago)
            (tmp_log_dir / f"mcp_{date.strftime('%Y-%m-%d')}.log").touch()

        with patch.object(mcp_logging, "LOG_DIR", tmp_log_dir):
            mcp_logging.cleanup_old_logs({"log_retention_days": "7", "max_log_files": "0"})

        remaining = list(tmp_log_dir.glob("mcp_*.log"))
        assert len(remaining) == 2  # today + 3 days ago

    def test_cleanup_by_max_files(self, tmp_log_dir):
        import mcp_logging

        today = datetime.now()
        for days_ago in [0, 1, 2, 3, 4]:
            date = today - timedelta(days=days_ago)
            (tmp_log_dir / f"mcp_{date.strftime('%Y-%m-%d')}.log").touch()

        with patch.object(mcp_logging, "LOG_DIR", tmp_log_dir):
            mcp_logging.cleanup_old_logs({"log_retention_days": "999", "max_log_files": "2"})

        remaining = sorted(tmp_log_dir.glob("mcp_*.log"))
        assert len(remaining) == 2

    def test_cleanup_never_deletes_today(self, tmp_log_dir):
        import mcp_logging

        today = datetime.now().strftime("%Y-%m-%d")
        (tmp_log_dir / f"mcp_{today}.log").touch()

        with patch.object(mcp_logging, "LOG_DIR", tmp_log_dir):
            mcp_logging.cleanup_old_logs({"log_retention_days": "0", "max_log_files": "0"})

        assert (tmp_log_dir / f"mcp_{today}.log").exists()


# ---------------------------------------------------------------------------
# Agent tool tests
# ---------------------------------------------------------------------------


class TestLogTools:

    def test_set_log_level_tool(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        from mcp_logging import set_level
        result = set_level("MISC")
        assert result == "MISC"

    def test_get_recent_logs_tool_format(self, tmp_path, tmp_settings):
        import mcp_logging

        log_dir = tmp_path / "logs"
        with (
            patch.object(mcp_logging, "LOG_DIR", log_dir),
            patch("mcp_logging.config.SETTINGS_PATH", tmp_settings),
        ):
            mcp_logging.initialize()

        logger = logging.getLogger("wn_mcp_world.test")
        logger.info("test message")

        result = mcp_logging.get_recent_entries(count=5, level="INFO")

        assert "total_in_buffer" in result
        assert "returned" in result
        assert "filter" in result
        assert "entries" in result
        assert isinstance(result["entries"], list)
        assert all(
            {"timestamp", "level", "logger", "message"} <= set(e.keys())
            for e in result["entries"]
        )
