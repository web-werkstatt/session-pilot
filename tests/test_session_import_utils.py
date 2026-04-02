"""
Unit-Tests fuer services/session_import_utils.py

Reine Utility-Funktionen ohne DB/IO-Abhaengigkeiten.
"""
import pytest
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# parse_ts
# ---------------------------------------------------------------------------

class TestParseTs:

    def test_iso_with_z(self):
        from services.session_import_utils import parse_ts
        result = parse_ts("2026-04-01T10:30:00Z")
        assert result.year == 2026
        assert result.month == 4
        assert result.hour == 10
        assert result.tzinfo is not None

    def test_iso_with_offset(self):
        from services.session_import_utils import parse_ts
        result = parse_ts("2026-04-01T10:30:00+02:00")
        assert result is not None
        assert result.year == 2026

    def test_none_returns_none(self):
        from services.session_import_utils import parse_ts
        assert parse_ts(None) is None

    def test_empty_string_returns_none(self):
        from services.session_import_utils import parse_ts
        assert parse_ts("") is None

    def test_invalid_string_returns_none(self):
        from services.session_import_utils import parse_ts
        assert parse_ts("not-a-date") is None


# ---------------------------------------------------------------------------
# create_session_meta
# ---------------------------------------------------------------------------

class TestCreateSessionMeta:

    def test_default_meta_has_required_keys(self):
        from services.session_import_utils import create_session_meta
        meta = create_session_meta()
        assert meta["session_uuid"] is None
        assert meta["total_input_tokens"] == 0
        assert meta["total_output_tokens"] == 0
        assert meta["user_message_count"] == 0
        assert meta["assistant_message_count"] == 0
        assert meta["duration_ms"] == 0

    def test_cache_tokens_included_by_default(self):
        from services.session_import_utils import create_session_meta
        meta = create_session_meta(include_cache_tokens=True)
        assert "cache_read_tokens" in meta
        assert "cache_creation_tokens" in meta

    def test_cache_tokens_excluded(self):
        from services.session_import_utils import create_session_meta
        meta = create_session_meta(include_cache_tokens=False)
        assert "cache_read_tokens" not in meta
        assert "cache_creation_tokens" not in meta


# ---------------------------------------------------------------------------
# update_time_range
# ---------------------------------------------------------------------------

class TestUpdateTimeRange:

    def test_first_timestamp_sets_both(self):
        from services.session_import_utils import create_session_meta, update_time_range
        meta = create_session_meta()
        ts = datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
        update_time_range(meta, ts)
        assert meta["started_at"] == ts
        assert meta["ended_at"] == ts

    def test_earlier_timestamp_updates_started(self):
        from services.session_import_utils import create_session_meta, update_time_range
        meta = create_session_meta()
        ts1 = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
        update_time_range(meta, ts1)
        update_time_range(meta, ts2)
        assert meta["started_at"] == ts2
        assert meta["ended_at"] == ts1

    def test_none_timestamp_is_noop(self):
        from services.session_import_utils import create_session_meta, update_time_range
        meta = create_session_meta()
        update_time_range(meta, None)
        assert meta["started_at"] is None


# ---------------------------------------------------------------------------
# sanitize_content_json
# ---------------------------------------------------------------------------

class TestSanitizeContentJson:

    def test_valid_json_passthrough(self):
        from services.session_import_utils import sanitize_content_json
        result = sanitize_content_json('{"key": "value"}')
        assert result is not None
        assert "key" in result

    def test_strips_null_bytes(self):
        from services.session_import_utils import sanitize_content_json
        # \x00 is the actual null byte that gets stripped
        dirty = '{"text": "hello' + '\x00' + 'world"}'
        result = sanitize_content_json(dirty)
        assert result is not None
        assert '\x00' not in result

    def test_none_input_returns_none(self):
        from services.session_import_utils import sanitize_content_json
        assert sanitize_content_json(None) is None

    def test_empty_string_returns_none(self):
        from services.session_import_utils import sanitize_content_json
        assert sanitize_content_json("") is None

    def test_invalid_json_returns_none(self):
        from services.session_import_utils import sanitize_content_json
        assert sanitize_content_json("not json") is None
