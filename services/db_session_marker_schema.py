"""
Sprint SB - Ausgelagerte Schema-Sicherung fuer Session-Marker-Bindung.
"""
import threading


_session_marker_ready = False
_session_marker_lock = threading.Lock()


def ensure_session_marker_schema_impl(execute):
    """Idempotente Migration: marker_id + marker_handoff_path + Index."""
    global _session_marker_ready
    if _session_marker_ready:
        return
    with _session_marker_lock:
        if _session_marker_ready:
            return
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS marker_id VARCHAR(120)")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS marker_handoff_path TEXT")
        execute("CREATE INDEX IF NOT EXISTS idx_sessions_marker_id ON sessions(marker_id)")
        _session_marker_ready = True
