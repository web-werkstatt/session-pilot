"""
SPEC-COPILOT-CHAT-PERPLEXITY-001: Copilot-Chat Service.
Persistenz, LLM-Aufruf und Verlauf fuer freien Chat mit Perplexity.
"""
import json
import os
import threading
import uuid
from datetime import datetime, timezone

from services.cost_service import calculate_cost
from services.db_service import execute
from services.perplexity_service import (
    query_perplexity,
    PerplexityConfigError,
    PerplexityRequestError,
    PerplexityAPIError,
)

COPILOT_SYSTEM_PROMPT = (
    "Du bist Perplexity, ein technischer Copilot, der bei Architektur, "
    "Spezifikationen und Code-Reviews hilft. Antworte kompakt und "
    "technisch-pragmatisch auf Deutsch."
)

# --- Schema ---

_schema_ready = False
_schema_lock = threading.Lock()
_schema_migrations_ready = False


def _first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
            continue
        if isinstance(value, list) and value:
            return value
        if value:
            return value
    return None


def _compact_marker_context(data):
    checks = data.get("checks")
    if not isinstance(checks, list):
        checks = []
    compact = {
        "project_id": _first_non_empty(data.get("project_id")),
        "marker_id": _first_non_empty(data.get("marker_id")),
        "plan_id": _first_non_empty(data.get("plan_id")),
        "plan_title": _first_non_empty(data.get("plan_title")),
        "sprint_tag": _first_non_empty(data.get("sprint_tag")),
        "spec_tag": _first_non_empty(data.get("spec_tag")),
        "titel": _first_non_empty(data.get("titel")),
        "status": _first_non_empty(data.get("status")),
        "ziel": _first_non_empty(data.get("ziel")),
        "naechster_schritt": _first_non_empty(data.get("naechster_schritt")),
        "risiko": _first_non_empty(data.get("risiko")),
        "checks": [str(item).strip() for item in checks if str(item).strip()],
        "prompt": _first_non_empty(data.get("prompt")),
        "prompt_suggestion": _first_non_empty(data.get("prompt_suggestion")),
        "last_session": _first_non_empty(data.get("last_session")),
        "updated_at": _first_non_empty(data.get("updated_at")),
    }
    return {key: value for key, value in compact.items() if value not in (None, "", [])}


def _resolve_plan_title(plan_id):
    try:
        numeric_plan_id = int(str(plan_id).strip())
    except Exception:
        return None

    try:
        row = execute(
            "SELECT title FROM project_plans WHERE id = %s",
            (numeric_plan_id,),
            fetchone=True,
        )
    except Exception:
        return None

    if not row:
        return None
    return _first_non_empty(row.get("title"))


def build_marker_chat_context(project_id=None, marker_id=None, handoff_path=None,
                              context_path=None, frontend_context=None):
    """Baut kompakten Marker-Kontext fuer den LLM-Call.

    Wahrheitsquelle ist handoff.md. marker-context.md liefert den aktiven Fokus.
    frontend_context wird nur als Zusatz/Fallback verwendet.
    """
    from services.copilot_marker_service import (
        _get_handoff_path,
        get_marker_context,
        read_marker_context,
    )
    from services.workflow_core_service import get_marker as core_get_marker

    frontend = frontend_context if isinstance(frontend_context, dict) else {}
    marker_meta = {}

    try:
        if project_id:
            marker_meta = read_marker_context(project_id=project_id, context_path=context_path)
        elif context_path:
            marker_meta = read_marker_context(context_path=context_path)
    except FileNotFoundError:
        marker_meta = {}
    except Exception:
        marker_meta = {}

    resolved_project_id = _first_non_empty(project_id, marker_meta.get("project_id"), frontend.get("project_id"))
    resolved_marker_id = _first_non_empty(marker_id, marker_meta.get("marker_id"), frontend.get("marker_id"))
    resolved_handoff_path = handoff_path or (_get_handoff_path(resolved_project_id) if resolved_project_id else None)

    handoff_marker = None
    if resolved_marker_id:
        try:
            # DB-first: Marker aus Core lesen
            if resolved_project_id:
                candidate = core_get_marker(resolved_project_id, resolved_marker_id)
                if candidate:
                    handoff_marker = {
                        "marker_id": candidate.marker_id,
                        "plan_id": candidate.plan_id,
                        "sprint_tag": candidate.sprint_tag,
                        "spec_tag": candidate.spec_tag,
                        "titel": candidate.titel,
                        "status": candidate.status,
                        "ziel": candidate.ziel,
                        "naechster_schritt": candidate.naechster_schritt,
                        "risiko": candidate.risiko,
                        "checks": candidate.checks,
                        "prompt": candidate.prompt,
                        "prompt_suggestion": candidate.prompt_suggestion,
                        "last_session": candidate.last_session,
                        "updated_at": candidate.updated_at,
                    }
                else:
                    handoff_marker = get_marker_context(resolved_project_id, resolved_marker_id)
        except Exception:
            handoff_marker = None

    merged = {}
    for source in (frontend, marker_meta, handoff_marker or {}):
        if not isinstance(source, dict):
            continue
        merged.update({k: v for k, v in source.items() if v not in (None, "", [])})

    if resolved_project_id:
        merged["project_id"] = resolved_project_id
    if resolved_marker_id:
        merged["marker_id"] = resolved_marker_id
    resolved_plan_id = _first_non_empty(
        merged.get("plan_id"),
        marker_meta.get("plan_id"),
        frontend.get("plan_id"),
    )
    if resolved_plan_id:
        merged["plan_id"] = resolved_plan_id
        plan_title = _resolve_plan_title(resolved_plan_id)
        if plan_title:
            merged["plan_title"] = plan_title

    return _compact_marker_context(merged)


def _build_marker_context_message(marker_context):
    if not marker_context:
        return None
    return (
        "Aktiver Marker-Kontext aus marker-context.md und handoff.md "
        "(handoff.md ist fuehrende Wahrheit):\n```json\n"
        + json.dumps(marker_context, indent=2, ensure_ascii=False)
        + "\n```"
    )


def ensure_copilot_schema():
    """Erstellt copilot_runs Tabelle falls nicht vorhanden."""
    global _schema_ready
    global _schema_migrations_ready
    if _schema_ready:
        if not _schema_migrations_ready:
            _ensure_copilot_run_migrations()
        return
    with _schema_lock:
        if _schema_ready:
            if not _schema_migrations_ready:
                _ensure_copilot_run_migrations()
            return
        execute("""
            CREATE TABLE IF NOT EXISTS copilot_runs (
                id SERIAL PRIMARY KEY,
                project_id VARCHAR(200),
                thread_id VARCHAR(100),
                user_message TEXT NOT NULL,
                assistant_reply TEXT,
                model VARCHAR(100),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                error_info TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_runs_project ON copilot_runs(project_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_runs_thread ON copilot_runs(thread_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_runs_created ON copilot_runs(created_at DESC)")
        _ensure_copilot_run_migrations()
        _schema_ready = True


def _ensure_copilot_run_migrations():
    """Sichert nachtraegliche Copilot-Run-Spalten/Indizes ab."""
    global _schema_migrations_ready
    try:
        execute("ALTER TABLE copilot_runs ADD COLUMN plan_id INTEGER")
    except Exception:
        pass
    try:
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_runs_plan ON copilot_runs(plan_id)")
    except Exception:
        pass
    try:
        execute("ALTER TABLE copilot_runs ADD COLUMN images JSONB")
    except Exception:
        pass
    try:
        execute("ALTER TABLE copilot_runs ADD COLUMN input_tokens INTEGER")
    except Exception:
        pass
    try:
        execute("ALTER TABLE copilot_runs ADD COLUMN output_tokens INTEGER")
    except Exception:
        pass
    try:
        execute("ALTER TABLE copilot_runs ADD COLUMN total_tokens INTEGER")
    except Exception:
        pass
    try:
        execute("ALTER TABLE copilot_runs ADD COLUMN cost_usd NUMERIC(10,6)")
    except Exception:
        pass
    _schema_migrations_ready = True


# --- Chat ---

def call_copilot(message, project_id=None, thread_id=None, context=None, plan_id=None,
                 images=None, context_path=None):
    """Sendet eine Nachricht an Perplexity und persistiert das Ergebnis.

    Args:
        message: User-Nachricht (Pflicht, nicht leer).
        project_id: Optionaler Projektname fuer Zuordnung.
        thread_id: Optionaler Thread-Identifikator. Wird generiert wenn leer.
        context: Optionales dict das als Kontext mitgesendet wird.
        plan_id: Optionale Plan-ID fuer Plan-Kontext-Bindung (Sprint E M5).
        images: Optionale Liste angehaengter Bilder.

    Returns:
        dict mit reply, project_id, thread_id, plan_id, copilot_run_id, model, status, created_at.
    """
    ensure_copilot_schema()

    if not thread_id:
        thread_id = str(uuid.uuid4())[:8]

    # Messages-Array bauen
    messages = [{"role": "system", "content": COPILOT_SYSTEM_PROMPT}]

    # Thread-Historie laden fuer Konversationskontext
    history = list_copilot_runs(thread_id=thread_id, limit=20)
    for run in history:
        if run["user_message"]:
            messages.append({"role": "user", "content": run["user_message"]})
        if run["assistant_reply"]:
            messages.append({"role": "assistant", "content": run["assistant_reply"]})

    marker_context = build_marker_chat_context(
        project_id=project_id,
        marker_id=context.get("marker_id") if isinstance(context, dict) else None,
        context_path=context_path,
        frontend_context=context,
    )

    # Optionalen Kontext einfuegen
    context_payload = marker_context or (context if isinstance(context, dict) else None)
    if context_payload:
        context_text = _build_marker_context_message(context_payload)
        messages.append({"role": "user", "content": context_text})
        messages.append({"role": "assistant", "content": "Verstanden, ich habe den Projektkontext erhalten."})

    # Aktuelle Nachricht
    messages.append({"role": "user", "content": message})

    # LLM aufrufen
    started = datetime.now(timezone.utc)
    try:
        result = query_perplexity(messages=messages, temperature=0.3)
        reply = result.get("content", "")
        model = result.get("model", "")
        usage = result.get("usage", {}) or {}
        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        if total_tokens is None and (input_tokens is not None or output_tokens is not None):
            total_tokens = int(input_tokens or 0) + int(output_tokens or 0)
        cost_usd = calculate_cost(model, input_tokens, output_tokens) if (input_tokens or output_tokens) else None

        return _save_run(
            project_id, thread_id, message, reply, model, "success", None, plan_id, images,
            input_tokens=input_tokens, output_tokens=output_tokens,
            total_tokens=total_tokens, cost_usd=cost_usd,
        )

    except PerplexityConfigError as e:
        return _save_run(project_id, thread_id, message, None, None, "failure",
                         f"Config-Fehler: {e}", plan_id, images)
    except (PerplexityRequestError, PerplexityAPIError) as e:
        return _save_run(project_id, thread_id, message, None, None, "failure",
                         f"LLM-Fehler: {e}", plan_id, images)
    except Exception as e:
        return _save_run(project_id, thread_id, message, None, None, "failure",
                         f"Unerwarteter Fehler: {e}", plan_id, images)


def _save_run(project_id, thread_id, user_message, assistant_reply, model, status, error_info,
              plan_id=None, images=None, input_tokens=None, output_tokens=None,
              total_tokens=None, cost_usd=None):
    """Persistiert einen Copilot-Run."""
    ensure_copilot_schema()

    row = execute(
        """INSERT INTO copilot_runs
               (project_id, thread_id, user_message, assistant_reply, model, status, error_info,
                plan_id, images, input_tokens, output_tokens, total_tokens, cost_usd)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (
            project_id, thread_id, user_message, assistant_reply, model, status, error_info,
            plan_id, json.dumps(images) if images is not None else None,
            input_tokens, output_tokens, total_tokens, cost_usd,
        ),
        fetchone=True,
    )

    return {
        "reply": assistant_reply,
        "project_id": project_id,
        "thread_id": thread_id,
        "plan_id": plan_id,
        "copilot_run_id": row["id"],
        "model": model,
        "status": status,
        "error_info": error_info,
        "images": images,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": float(cost_usd) if cost_usd is not None else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


# --- Verlauf ---

def list_copilot_runs(project_id=None, thread_id=None, plan_id=None, limit=50):
    """Laedt Copilot-Runs, gefiltert nach project_id, thread_id und/oder plan_id."""
    ensure_copilot_schema()

    conditions = []
    params = []

    if project_id:
        conditions.append("project_id = %s")
        params.append(project_id)
    if thread_id:
        conditions.append("thread_id = %s")
        params.append(thread_id)
    if plan_id is not None:
        conditions.append("plan_id = %s")
        params.append(plan_id)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(min(limit, 200))

    rows = execute(
        f"""SELECT id, project_id, thread_id, plan_id, user_message, assistant_reply,
                   images, model, status, error_info, input_tokens, output_tokens,
                   total_tokens, cost_usd, created_at
            FROM copilot_runs
            {where}
            ORDER BY created_at ASC
            LIMIT %s""",
        tuple(params),
        fetch=True,
    ) or []

    def _parse_images(value):
        if value in (None, ""):
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return None
        return value

    return [
        {
            "id": r["id"],
            "project_id": r.get("project_id"),
            "thread_id": r.get("thread_id"),
            "plan_id": r.get("plan_id"),
            "user_message": r.get("user_message"),
            "assistant_reply": r.get("assistant_reply"),
            "images": _parse_images(r.get("images")),
            "model": r.get("model"),
            "status": r["status"],
            "error_info": r.get("error_info"),
            "input_tokens": r.get("input_tokens"),
            "output_tokens": r.get("output_tokens"),
            "total_tokens": r.get("total_tokens"),
            "cost_usd": float(r["cost_usd"]) if r.get("cost_usd") is not None else None,
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
        }
        for r in rows
    ]
