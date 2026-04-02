"""
Unit-Tests fuer services/notification_service.py

Testet CRUD, Dedup-Logik, Overflow-Handling und Thread-Safety.
Nutzt tmp_path statt echtes Filesystem.
"""
import json
import os
import time
import threading
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_notification_file(tmp_path):
    """Patcht den Dateipfad auf eine temporaere Datei."""
    return patch(
        "services.notification_service.NOTIFICATIONS_FILE",
        str(tmp_path / "notifications.json"),
    )


# ---------------------------------------------------------------------------
# load / save basics
# ---------------------------------------------------------------------------

class TestLoadSave:

    def test_load_returns_empty_on_missing_file(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import load_notifications
            assert load_notifications() == []

    def test_save_then_load(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import load_notifications, save_notifications
            data = [{"id": "abc", "title": "Test", "read": False}]
            save_notifications(data)
            loaded = load_notifications()
            assert len(loaded) == 1
            assert loaded[0]["id"] == "abc"

    def test_load_handles_corrupt_json(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import load_notifications
            fpath = tmp_path / "notifications.json"
            fpath.write_text("{broken json!!!")
            assert load_notifications() == []


# ---------------------------------------------------------------------------
# add_notification + Dedup
# ---------------------------------------------------------------------------

class TestAddNotification:

    def test_add_creates_notification(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import add_notification, load_notifications
            result = add_notification("test_type", "info", "Title", "Message")
            assert result is not None
            assert result["type"] == "test_type"
            assert result["title"] == "Title"
            assert result["read"] is False
            loaded = load_notifications()
            assert len(loaded) == 1

    def test_dedup_blocks_same_notification(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import add_notification
            r1 = add_notification("container_down", "error", "Down", "Msg", container="web")
            r2 = add_notification("container_down", "error", "Down", "Msg", container="web")
            assert r1 is not None
            assert r2 is None  # Duplicate blocked

    def test_dedup_allows_different_container(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import add_notification
            r1 = add_notification("container_down", "error", "Down", "Msg", container="web")
            r2 = add_notification("container_down", "error", "Down", "Msg", container="db")
            assert r1 is not None
            assert r2 is not None  # Different container, allowed

    def test_notification_has_id_and_timestamp(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import add_notification
            result = add_notification("info", "info", "Test", "Msg")
            assert "id" in result
            assert len(result["id"]) == 12  # 6-byte hex
            assert "created_at" in result


# ---------------------------------------------------------------------------
# mark_read / mark_all_read / dismiss
# ---------------------------------------------------------------------------

class TestReadAndDismiss:

    def test_mark_read_returns_true(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import add_notification, mark_read
            n = add_notification("test", "info", "T", "M")
            assert mark_read(n["id"]) is True

    def test_mark_read_nonexistent_returns_false(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import mark_read
            assert mark_read("nonexistent") is False

    def test_mark_all_read(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import (
                add_notification, mark_all_read, get_unread_count,
            )
            add_notification("a", "info", "T1", "M1")
            add_notification("b", "info", "T2", "M2")
            assert get_unread_count() == 2
            mark_all_read()
            assert get_unread_count() == 0

    def test_dismiss_removes_notification(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import (
                add_notification, dismiss, load_notifications,
            )
            n = add_notification("test", "info", "T", "M")
            dismiss(n["id"])
            assert len(load_notifications()) == 0


# ---------------------------------------------------------------------------
# Overflow handling
# ---------------------------------------------------------------------------

class TestOverflow:

    def test_save_truncates_to_max(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import save_notifications, load_notifications
            big_list = [{"id": f"n{i}", "title": f"T{i}"} for i in range(250)]
            save_notifications(big_list)
            loaded = load_notifications()
            assert len(loaded) <= 200  # MAX_NOTIFICATIONS


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:

    def test_concurrent_adds_no_crash(self, tmp_path):
        with _patch_notification_file(tmp_path):
            from services.notification_service import add_notification, load_notifications
            errors = []

            def add_many(start):
                try:
                    for i in range(10):
                        add_notification(
                            f"type_{start}_{i}", "info",
                            f"Title {start}-{i}", "Message",
                            project=f"proj-{start}-{i}",
                        )
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=add_many, args=(t,)) for t in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0, f"Errors during concurrent adds: {errors}"
            loaded = load_notifications()
            assert len(loaded) > 0
