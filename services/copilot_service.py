"""
SPEC-COPILOT-CHAT-PERPLEXITY-001: Copilot-Chat Service.
Persistenz, LLM-Aufruf und Verlauf fuer freien Chat mit Perplexity.
"""
import json
import threading
import uuid
from datetime import datetime, timezone

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


def ensure_copilot_schema():
    """Erstellt copilot_runs Tabelle falls nicht vorhanden."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
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
        _schema_ready = True


# --- Chat ---

def call_copilot(message, project_id=None, thread_id=None, context=None, plan_id=None):
    """Sendet eine Nachricht an Perplexity und persistiert das Ergebnis.

    Args:
        message: User-Nachricht (Pflicht, nicht leer).
        project_id: Optionaler Projektname fuer Zuordnung.
        thread_id: Optionaler Thread-Identifikator. Wird generiert wenn leer.
        context: Optionales dict das als Kontext mitgesendet wird.
        plan_id: Optionale Plan-ID fuer Plan-Kontext-Bindung (Sprint E M5).

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

    # Optionalen Kontext einfuegen
    if context:
        context_text = "Aktueller Projektkontext:\n```json\n" + json.dumps(context, indent=2, ensure_ascii=False) + "\n```"
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

        return _save_run(project_id, thread_id, message, reply, model, "success", None, plan_id)

    except PerplexityConfigError as e:
        return _save_run(project_id, thread_id, message, None, None, "failure",
                         f"Config-Fehler: {e}", plan_id)
    except (PerplexityRequestError, PerplexityAPIError) as e:
        return _save_run(project_id, thread_id, message, None, None, "failure",
                         f"LLM-Fehler: {e}", plan_id)
    except Exception as e:
        return _save_run(project_id, thread_id, message, None, None, "failure",
                         f"Unerwarteter Fehler: {e}", plan_id)


def _save_run(project_id, thread_id, user_message, assistant_reply, model, status, error_info, plan_id=None):
    """Persistiert einen Copilot-Run."""
    ensure_copilot_schema()

    row = execute(
        """INSERT INTO copilot_runs
               (project_id, thread_id, user_message, assistant_reply, model, status, error_info, plan_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (project_id, thread_id, user_message, assistant_reply, model, status, error_info, plan_id),
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
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


# --- Verlauf ---

def list_copilot_runs(project_id=None, thread_id=None, limit=50):
    """Laedt Copilot-Runs, gefiltert nach project_id und/oder thread_id."""
    ensure_copilot_schema()

    conditions = []
    params = []

    if project_id:
        conditions.append("project_id = %s")
        params.append(project_id)
    if thread_id:
        conditions.append("thread_id = %s")
        params.append(thread_id)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(min(limit, 200))

    rows = execute(
        f"""SELECT id, project_id, thread_id, user_message, assistant_reply,
                   model, status, error_info, created_at
            FROM copilot_runs
            {where}
            ORDER BY created_at ASC
            LIMIT %s""",
        tuple(params),
        fetch=True,
    ) or []

    return [
        {
            "id": r["id"],
            "project_id": r.get("project_id"),
            "thread_id": r.get("thread_id"),
            "user_message": r.get("user_message"),
            "assistant_reply": r.get("assistant_reply"),
            "model": r.get("model"),
            "status": r["status"],
            "error_info": r.get("error_info"),
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
        }
        for r in rows
    ]
