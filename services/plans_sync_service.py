"""
Plans-Sync-Orchestrator (Sprint sprint-plan-discovery, Commit 3).

Wrappt plan_discovery_service.discover_plans() und importiert die
Ergebnisse in project_plans via 4-stufige Upsert-Logik:
  1. Lookup via source_path                           -> UPDATE
  2. Lookup via filename + project_name (Alt-Row)     -> Migration
  3. Lookup via content_hash (Alt-Row, Filename-Drift) -> Migration
  4. Kein Match                                       -> INSERT (neutrale Defaults)

Schutz-Mechanismen:
  - Modul-Lock _SYNC_LOCK (non-blocking): plan_scan_lock_skipped
  - 60-s-Cooldown; bei duration_ms > 5000 auf 15 min angehoben
    (plan_scan_circuit_open)
  - Bulk-Transaktion: alle Upserts in einem COMMIT, Rollback bei Fehler
  - Kollisions-Guard bei Filename-Migration (project_name-Mismatch ->
    plan_scan_filename_collision, kein Auto-Umhaengen)
  - Thread-local is_scanning()-Flag fuer Notification-Suppression

Details: sprints/sprint-plan-discovery.md (Basis + Nachtraege 1-4).
"""
import logging
import threading
import time
from datetime import datetime, timezone

from services.db_service import (
    ensure_plan_source_schema,
    ensure_plan_workflow_schema,
    ensure_plans_schema,
    get_conn,
    put_conn,
)
from services.plan_discovery_service import discover_plans

logger = logging.getLogger(__name__)

_SYNC_LOCK = threading.Lock()
_NEXT_ALLOWED_AT = 0.0
_COOLDOWN_SEC = 60.0
_CIRCUIT_COOLDOWN_SEC = 900.0
_CIRCUIT_THRESHOLD_MS = 5000

_scan_state = threading.local()


def is_scanning() -> bool:
    """True, wenn im aktuellen Thread gerade ein plan_scan laeuft.

    Exponiert als Notification-Suppression-Gate: zukuenftige Callsites in
    notification_checker/add_notification koennen das Flag pruefen, um
    waehrend eines Scans nicht zu fluten.
    """
    return bool(getattr(_scan_state, "active", False))


def scan_all_plans(exclusions=None):
    """Wrappt discover_plans und ergaenzt dashboard-spezifische Felder.

    Excluded-Dateien (excluded_by != None) werden aus dem DB-Schreibpfad
    gefiltert, nicht aus der Preview. Preview-Endpoints rufen
    discover_plans() direkt.
    """
    from services.plans_import import (
        detect_category,
        detect_project,
        extract_context,
        extract_title,
    )

    records = discover_plans(exclusions=exclusions)
    enriched = []
    for rec in records:
        if rec.get("excluded_by"):
            continue
        content = rec.get("content") or ""
        title = extract_title(content) or rec["filename"].replace(".md", "").replace("-", " ").title()
        project_name = rec.get("project_name")
        # Legacy-claude_plans: project_name aus Content ableiten, wenn nicht
        # per Pfad bestimmbar. Multi-Source behaelt den Pfad-basierten Wert.
        if rec.get("source_kind") == "claude_plans" and not project_name:
            project_name = detect_project(content)
        enriched.append({
            **rec,
            "project_name": project_name,
            "title": title,
            "context_summary": extract_context(content),
            "category": detect_category(content, title),
            "created_at": datetime.fromtimestamp(rec["mtime"], tz=timezone.utc),
        })
    return enriched


# ---------------------------------------------------------------------------
# 4-stufige Upsert-Logik
# ---------------------------------------------------------------------------

def _legacy_session_fields(plan):
    """Fuer source_kind='claude_plans' (Legacy-Single-Source): Session-UUID
    und Auto-Status via detect_status_from_sessions. Fuer alle anderen
    Scan-Quellen neutrale Defaults gemaess Sprint-Plan (Nachtrag 1)."""
    if plan.get("source_kind") != "claude_plans":
        return None, "unknown"
    from services.plans_import import (
        detect_status_from_sessions,
        find_related_session,
    )
    session_uuid = find_related_session(plan["project_name"], plan["mtime"])
    auto_status = detect_status_from_sessions(
        plan["project_name"], plan["created_at"],
    )
    return session_uuid, auto_status


def _upsert_step1_source_path(cur, plan, stats) -> bool:
    """Schritt 1: Match via source_path -> UPDATE. True wenn erledigt.

    Status + session_uuid werden im UPDATE NICHT ueberschrieben (User
    koennte sie manuell gesetzt haben). Bei unchanged + status='draft' +
    claude_plans-Quelle wird der Status per detect_status_from_sessions
    neu bewertet (Verhalten aus der Legacy-sync_plans-Logik).
    """
    cur.execute(
        """SELECT id, content_hash, status, project_name FROM project_plans
           WHERE source_path = %s""",
        (plan["source_path"],),
    )
    row = cur.fetchone()
    if not row:
        return False
    plan_id = row["id"]
    old_hash = row.get("content_hash")
    old_status = row.get("status")
    old_project = row.get("project_name")

    if old_hash == plan["content_hash"]:
        # Datei unveraendert — aber evtl. Struktur-Felder nachfuehren:
        #   - project_name: rekonziliert, wenn neue Discovery einen Wert
        #     liefert und der DB-Wert NULL ist (Legacy-Repair)
        #   - status: Draft-Re-Evaluation fuer claude_plans wie gehabt
        reconcile_project = (
            plan.get("project_name") is not None and old_project is None
        )
        if old_status == "draft" and plan.get("source_kind") == "claude_plans":
            session_uuid, new_status = _legacy_session_fields(plan)
            if new_status != "draft" or reconcile_project:
                cur.execute(
                    """UPDATE project_plans
                       SET status=%s,
                           project_name=COALESCE(%s, project_name),
                           session_uuid=COALESCE(%s, session_uuid),
                           updated_at=NOW()
                       WHERE id=%s""",
                    (new_status, plan.get("project_name"), session_uuid, plan_id),
                )
                stats["updated"] += 1
                return True
        if reconcile_project:
            cur.execute(
                """UPDATE project_plans
                   SET project_name=%s, updated_at=NOW()
                   WHERE id=%s""",
                (plan["project_name"], plan_id),
            )
            stats["updated"] += 1
            return True
        stats["unchanged"] += 1
        return True

    # Datei geaendert: Content-Felder neu, Status/session_uuid beibehalten
    session_uuid, _ = _legacy_session_fields(plan)
    cur.execute(
        """UPDATE project_plans
           SET title=%s, project_name=%s, content=%s, context_summary=%s,
               category=%s, file_hash=%s, file_mtime=%s, content_hash=%s,
               session_uuid=COALESCE(%s, session_uuid),
               updated_at=NOW()
           WHERE id=%s""",
        (plan["title"], plan["project_name"], plan["content"],
         plan["context_summary"], plan["category"],
         plan["content_hash"], plan["mtime"], plan["content_hash"],
         session_uuid, plan_id),
    )
    stats["updated"] += 1
    return True


def _upsert_step2_filename_migration(cur, plan, stats) -> bool:
    """Schritt 2: Match via filename+project_name bei source_path IS NULL.

    Kollisions-Guard: wenn filename existiert, aber KEIN Kandidat mit
    passendem project_name, wird NICHT migriert — Skip + Collision-Log.
    """
    cur.execute(
        """SELECT id, project_name FROM project_plans
           WHERE filename=%s AND source_path IS NULL
           ORDER BY id ASC""",
        (plan["filename"],),
    )
    candidates = cur.fetchall()
    if not candidates:
        return False

    matched_id = None
    for cand in candidates:
        if cand.get("project_name") == plan["project_name"]:
            matched_id = cand["id"]
            break

    if matched_id is None:
        logger.warning(
            "plan_scan_filename_collision filename=%s path=%s existing_projects=%s",
            plan["filename"], plan["source_path"],
            [c.get("project_name") for c in candidates],
        )
        stats["skipped"] += 1
        return True

    cur.execute(
        """UPDATE project_plans
           SET source_path=%s, source_kind=%s, content_hash=%s,
               title=%s, content=%s, context_summary=%s, category=%s,
               file_hash=%s, file_mtime=%s, updated_at=NOW()
           WHERE id=%s""",
        (plan["source_path"], plan["source_kind"], plan["content_hash"],
         plan["title"], plan["content"], plan["context_summary"],
         plan["category"], plan["content_hash"], plan["mtime"], matched_id),
    )
    stats["migrated"] += 1
    if len(candidates) > 1:
        logger.warning(
            "ambiguous filename migration filename=%s matched=%d remaining=%d",
            plan["filename"], matched_id, len(candidates) - 1,
        )
    return True


def _upsert_step3_content_hash_migration(cur, plan, stats) -> bool:
    """Schritt 3: Match via content_hash bei source_path IS NULL.

    Nur wenn zusaetzlich project_name matcht — Inhalts-Gleichheit
    allein reicht nicht (verschiedene Projekte koennen identischen
    Platzhalter-Content haben).
    """
    cur.execute(
        """SELECT id, project_name, filename FROM project_plans
           WHERE content_hash = %s AND source_path IS NULL
           LIMIT 1""",
        (plan["content_hash"],),
    )
    row = cur.fetchone()
    if not row:
        return False
    if row.get("project_name") != plan["project_name"]:
        return False

    cur.execute(
        """UPDATE project_plans
           SET source_path=%s, source_kind=%s, filename=%s,
               title=%s, content=%s, context_summary=%s,
               category=%s, file_hash=%s, file_mtime=%s,
               updated_at=NOW()
           WHERE id=%s""",
        (plan["source_path"], plan["source_kind"], plan["filename"],
         plan["title"], plan["content"], plan["context_summary"],
         plan["category"], plan["content_hash"], plan["mtime"], row["id"]),
    )
    stats["migrated"] += 1
    logger.info(
        "plan_scan_content_migration from=%s to=%s path=%s",
        row.get("filename"), plan["filename"], plan["source_path"],
    )
    return True


def _upsert_step4_insert(cur, plan, stats) -> None:
    """Schritt 4: Kein Match -> INSERT.

    Legacy-claude_plans: Auto-Status + session_uuid via
    detect_status_from_sessions/find_related_session (Rueckwaerts-
    kompatibilitaet mit alter sync_plans-Logik).
    Multi-Source-Neuimporte: neutrale Defaults (status='unknown',
    session_uuid=NULL) gemaess Sprint-Plan Nachtrag 1.

    Fehlerfall (z.B. UNIQUE(filename)-Kollision mit Alt-Row, die weder
    Schritt 2 noch 3 matchte): Skip mit Warn-Log, kein Crash.
    """
    session_uuid, auto_status = _legacy_session_fields(plan)
    try:
        cur.execute(
            """INSERT INTO project_plans
               (filename, title, project_name, content, context_summary,
                category, status, session_uuid, file_hash, file_mtime,
                content_hash, source_path, source_kind, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (plan["filename"], plan["title"], plan["project_name"],
             plan["content"], plan["context_summary"], plan["category"],
             auto_status, session_uuid,
             plan["content_hash"], plan["mtime"], plan["content_hash"],
             plan["source_path"], plan["source_kind"], plan["created_at"]),
        )
        stats["inserted"] += 1
    except Exception as exc:  # noqa: BLE001 — Insert-Fehler darf Sync nicht kippen
        logger.warning(
            "plan_scan_insert_failed filename=%s path=%s error=%s",
            plan["filename"], plan["source_path"], exc,
        )
        stats["skipped"] += 1


def _upsert_plan(cur, plan, stats) -> None:
    """Fuehrt 4-stufige Upsert-Logik aus."""
    if _upsert_step1_source_path(cur, plan, stats):
        return
    if _upsert_step2_filename_migration(cur, plan, stats):
        return
    if _upsert_step3_content_hash_migration(cur, plan, stats):
        return
    _upsert_step4_insert(cur, plan, stats)


# ---------------------------------------------------------------------------
# Public Entry: sync_all_plans
# ---------------------------------------------------------------------------

def sync_all_plans(force: bool = False) -> dict:
    """Synchronisiert alle Plan-Quellen (Discovery + Upsert) in project_plans.

    - `force=True` umgeht Cooldown (z.B. fuer /api/plans/sync-now in Commit 4)
    - Modul-Lock verhindert parallele Scans
    - Bulk-Transaktion: rollback bei Fehler, kein halb-importiert-Zustand

    Rueckgabe: Stats-Dict mit inserted, updated, migrated, unchanged,
    skipped, total, duration_ms — oder {'skipped_reason': 'lock'|'cooldown'}.
    """
    from psycopg2 import extras as _extras

    global _NEXT_ALLOWED_AT

    if not _SYNC_LOCK.acquire(blocking=False):
        logger.warning("plan_scan_lock_skipped")
        return {"skipped_reason": "lock"}

    try:
        now = time.monotonic()
        if not force and now < _NEXT_ALLOWED_AT:
            remaining = _NEXT_ALLOWED_AT - now
            logger.info(
                "plan_scan_cooldown_skipped remaining_sec=%.1f", remaining
            )
            return {"skipped_reason": "cooldown", "remaining_sec": remaining}

        _scan_state.active = True
        started = time.monotonic()
        stats = {
            "inserted": 0, "updated": 0, "migrated": 0,
            "unchanged": 0, "skipped": 0, "total": 0,
        }

        ensure_plans_schema()
        ensure_plan_workflow_schema()
        ensure_plan_source_schema()

        plans = scan_all_plans()
        stats["total"] = len(plans)

        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=_extras.RealDictCursor) as cur:
                for idx, plan in enumerate(plans):
                    # Savepoint pro Upsert: lokale Fehler (z.B.
                    # UNIQUE(filename)-Kollision) kippen nicht die gesamte
                    # Bulk-Transaktion. Ohne Savepoint wuerde PostgreSQL
                    # alle folgenden Statements mit "current transaction
                    # is aborted" ablehnen.
                    sp_name = f"plan_sp_{idx}"
                    cur.execute(f"SAVEPOINT {sp_name}")
                    try:
                        _upsert_plan(cur, plan, stats)
                        cur.execute(f"RELEASE SAVEPOINT {sp_name}")
                    except Exception as exc:  # noqa: BLE001
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                        cur.execute(f"RELEASE SAVEPOINT {sp_name}")
                        logger.warning(
                            "plan_scan_upsert_error path=%s error=%s",
                            plan.get("source_path"), exc,
                        )
                        stats["skipped"] += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            put_conn(conn)

        duration_ms = int((time.monotonic() - started) * 1000)
        stats["duration_ms"] = duration_ms

        if duration_ms > _CIRCUIT_THRESHOLD_MS:
            _NEXT_ALLOWED_AT = time.monotonic() + _CIRCUIT_COOLDOWN_SEC
            logger.warning(
                "plan_scan_circuit_open duration_ms=%d cooldown_sec=%d",
                duration_ms, int(_CIRCUIT_COOLDOWN_SEC),
            )
        else:
            _NEXT_ALLOWED_AT = time.monotonic() + _COOLDOWN_SEC

        # Metric-Zeile bewusst WARNING-Level: app.py konfiguriert keinen
        # Logging-Handler, daher filtert Pythons lastResort INFO weg. Der
        # Sprint-Plan (Nachtrag 4) verlangt, dass die Zeile via
        # `rg "plan_scan metrics"` im dashboard.log findbar ist.
        logger.warning(
            "plan_scan metrics inserted=%d updated=%d migrated=%d "
            "unchanged=%d skipped=%d total=%d duration_ms=%d",
            stats["inserted"], stats["updated"], stats["migrated"],
            stats["unchanged"], stats["skipped"], stats["total"], duration_ms,
        )

        return stats
    finally:
        _scan_state.active = False
        _SYNC_LOCK.release()
