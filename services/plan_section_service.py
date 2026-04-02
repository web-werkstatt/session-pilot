"""
Sprint H: Plan-Sections, Copilot-Threads und Copilot-Messages.
DB-first Struktur fuer Level-2-Cards und Section-gebundenen Chat.
"""
import threading
import time

from services.db_service import execute

# --- Schema ---

_schema_ready = False
_schema_lock = threading.Lock()


def ensure_section_schema():
    """Erstellt plan_sections, copilot_threads, copilot_messages Tabellen."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return

        # plan_sections: Level-2-Cards innerhalb eines Plans
        execute("""
            CREATE TABLE IF NOT EXISTS plan_sections (
                id BIGSERIAL PRIMARY KEY,
                project_id BIGINT,
                plan_id BIGINT NOT NULL,
                parent_section_id BIGINT,
                kind VARCHAR(30) NOT NULL DEFAULT 'section',
                title TEXT NOT NULL,
                slug VARCHAR(160),
                summary TEXT,
                content TEXT,
                status VARCHAR(30) DEFAULT 'backlog',
                workflow_stage VARCHAR(50) DEFAULT 'idea',
                position INT NOT NULL DEFAULT 0,
                spec_ref VARCHAR(120),
                owner_id BIGINT,
                meta JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_plan_sections_plan_pos ON plan_sections(plan_id, position)")
        execute("CREATE INDEX IF NOT EXISTS idx_plan_sections_project ON plan_sections(project_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_plan_sections_kind ON plan_sections(kind, plan_id)")

        # copilot_threads: Chat-Thread pro Section
        execute("""
            CREATE TABLE IF NOT EXISTS copilot_threads (
                id BIGSERIAL PRIMARY KEY,
                project_id BIGINT,
                plan_id BIGINT NOT NULL,
                section_id BIGINT NOT NULL,
                title TEXT,
                status VARCHAR(30) DEFAULT 'open',
                created_by_id BIGINT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_threads_section ON copilot_threads(section_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_threads_plan ON copilot_threads(plan_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_threads_project ON copilot_threads(project_id)")

        # copilot_messages: Messages mit Usage/Kosten
        execute("""
            CREATE TABLE IF NOT EXISTS copilot_messages (
                id BIGSERIAL PRIMARY KEY,
                thread_id BIGINT NOT NULL,
                project_id BIGINT,
                plan_id BIGINT,
                section_id BIGINT,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                images JSONB,
                provider VARCHAR(50),
                model VARCHAR(100),
                input_tokens INT,
                output_tokens INT,
                total_tokens INT,
                cost_usd NUMERIC(10,6),
                duration_ms INT,
                meta JSONB,
                created_by_id BIGINT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_msgs_thread ON copilot_messages(thread_id, created_at)")
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_msgs_section ON copilot_messages(section_id, created_at)")
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_msgs_plan ON copilot_messages(plan_id, created_at)")
        execute("CREATE INDEX IF NOT EXISTS idx_copilot_msgs_project ON copilot_messages(project_id, created_at)")

        _schema_ready = True


# --- plan_sections CRUD ---

VALID_SECTION_KINDS = ("section", "spec")
VALID_SECTION_STATUSES = ("backlog", "ready", "in_progress", "review", "done", "blocked")
VALID_SECTION_STAGES = (
    "idea", "spec_ready", "prompt_ready", "executing",
    "review_pending", "fixed", "done", "blocked",
)


def create_plan_section(plan_id, kind, title, project_id=None, parent_section_id=None,
                        slug=None, summary=None, content=None, status="backlog",
                        workflow_stage="idea", position=None, spec_ref=None,
                        owner_id=None, meta=None):
    """Erstellt eine neue Section/Spec innerhalb eines Plans."""
    ensure_section_schema()

    if kind not in VALID_SECTION_KINDS:
        raise ValueError(f"Ungueltiger kind: {kind}. Erlaubt: {', '.join(VALID_SECTION_KINDS)}")

    # Position automatisch ans Ende setzen
    if position is None:
        row = execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM plan_sections WHERE plan_id = %s",
            (plan_id,), fetchone=True,
        )
        position = row["next_pos"] if row else 0

    import json
    meta_json = json.dumps(meta) if meta else None

    row = execute(
        """INSERT INTO plan_sections
               (project_id, plan_id, parent_section_id, kind, title, slug, summary,
                content, status, workflow_stage, position, spec_ref, owner_id, meta)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (project_id, plan_id, parent_section_id, kind, title, slug, summary,
         content, status, workflow_stage, position, spec_ref, owner_id, meta_json),
        fetchone=True,
    )
    return {"id": row["id"], "created_at": row["created_at"].isoformat()}


def list_plan_sections(plan_id):
    """Listet alle Sections eines Plans, sortiert nach position."""
    ensure_section_schema()

    rows = execute(
        """SELECT id, project_id, plan_id, parent_section_id, kind, title, slug,
                  summary, status, workflow_stage, position, spec_ref, owner_id, meta,
                  created_at, updated_at
           FROM plan_sections
           WHERE plan_id = %s
           ORDER BY position ASC, id ASC""",
        (plan_id,), fetch=True,
    ) or []

    return [_section_to_dict(r) for r in rows]


def get_plan_section(section_id):
    """Laedt eine einzelne Section."""
    ensure_section_schema()
    row = execute(
        """SELECT id, project_id, plan_id, parent_section_id, kind, title, slug,
                  summary, content, status, workflow_stage, position, spec_ref, owner_id, meta,
                  created_at, updated_at
           FROM plan_sections WHERE id = %s""",
        (section_id,), fetchone=True,
    )
    if not row:
        return None
    return _section_to_dict(row)


def update_plan_section(section_id, data):
    """Aktualisiert eine Section (Title, Status, workflow_stage, position, etc.)."""
    ensure_section_schema()

    existing = execute("SELECT id FROM plan_sections WHERE id = %s", (section_id,), fetchone=True)
    if not existing:
        return None

    allowed = {
        "title": str, "slug": str, "summary": str, "content": str,
        "status": str, "workflow_stage": str, "position": int,
        "spec_ref": str, "kind": str,
    }
    updates = []
    params = []

    for field, _ in allowed.items():
        if field in data:
            val = data[field]
            if field == "kind" and val not in VALID_SECTION_KINDS:
                raise ValueError(f"Ungueltiger kind: {val}")
            if field == "status" and val and val not in VALID_SECTION_STATUSES:
                raise ValueError(f"Ungueltiger status: {val}")
            if field == "workflow_stage" and val and val not in VALID_SECTION_STAGES:
                raise ValueError(f"Ungueltiger workflow_stage: {val}")
            updates.append(f"{field} = %s")
            params.append(val)

    if not updates:
        raise ValueError("Keine aktualisierbaren Felder")

    updates.append("updated_at = NOW()")
    params.append(section_id)
    execute(f"UPDATE plan_sections SET {', '.join(updates)} WHERE id = %s", params)

    return get_plan_section(section_id)


def _section_to_dict(row):
    return {
        "id": row["id"],
        "project_id": row.get("project_id"),
        "plan_id": row["plan_id"],
        "parent_section_id": row.get("parent_section_id"),
        "kind": row["kind"],
        "title": row["title"],
        "slug": row.get("slug"),
        "summary": row.get("summary"),
        "content": row.get("content"),
        "status": row.get("status"),
        "workflow_stage": row.get("workflow_stage"),
        "position": row.get("position", 0),
        "spec_ref": row.get("spec_ref"),
        "owner_id": row.get("owner_id"),
        "meta": row.get("meta"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


# --- copilot_threads ---

def get_or_create_thread(project_id, plan_id, section_id, created_by_id=None):
    """Liefert den Thread fuer eine Section. Erstellt einen neuen falls keiner existiert."""
    ensure_section_schema()

    row = execute(
        "SELECT id, created_at, updated_at FROM copilot_threads WHERE section_id = %s ORDER BY created_at ASC LIMIT 1",
        (section_id,), fetchone=True,
    )
    if row:
        return {
            "thread_id": row["id"],
            "project_id": project_id,
            "plan_id": plan_id,
            "section_id": section_id,
            "created": False,
        }

    row = execute(
        """INSERT INTO copilot_threads (project_id, plan_id, section_id, created_by_id)
           VALUES (%s, %s, %s, %s)
           RETURNING id, created_at""",
        (project_id, plan_id, section_id, created_by_id),
        fetchone=True,
    )
    return {
        "thread_id": row["id"],
        "project_id": project_id,
        "plan_id": plan_id,
        "section_id": section_id,
        "created": True,
    }


# --- copilot_messages ---

def create_message(thread_id, role, content, project_id=None, plan_id=None,
                   section_id=None, images=None, provider=None, model=None,
                   input_tokens=None, output_tokens=None, total_tokens=None,
                   cost_usd=None, duration_ms=None, meta=None, created_by_id=None):
    """Speichert eine Chat-Message mit optionalen Usage-/Kostendaten."""
    ensure_section_schema()

    import json
    images_json = json.dumps(images) if images else None
    meta_json = json.dumps(meta) if meta else None

    row = execute(
        """INSERT INTO copilot_messages
               (thread_id, project_id, plan_id, section_id, role, content, images,
                provider, model, input_tokens, output_tokens, total_tokens,
                cost_usd, duration_ms, meta, created_by_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (thread_id, project_id, plan_id, section_id, role, content, images_json,
         provider, model, input_tokens, output_tokens, total_tokens,
         cost_usd, duration_ms, meta_json, created_by_id),
        fetchone=True,
    )
    return {
        "id": row["id"],
        "thread_id": thread_id,
        "role": role,
        "content": content,
        "images": images,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": float(cost_usd) if cost_usd else None,
        "duration_ms": duration_ms,
        "created_at": row["created_at"].isoformat(),
    }


def list_messages(thread_id, limit=50):
    """Laedt Messages eines Threads chronologisch."""
    ensure_section_schema()

    rows = execute(
        """SELECT id, thread_id, role, content, images, provider, model,
                  input_tokens, output_tokens, total_tokens, cost_usd,
                  duration_ms, created_at
           FROM copilot_messages
           WHERE thread_id = %s
           ORDER BY created_at ASC
           LIMIT %s""",
        (thread_id, min(limit, 200)),
        fetch=True,
    ) or []

    return [
        {
            "id": r["id"],
            "thread_id": r["thread_id"],
            "role": r["role"],
            "content": r["content"],
            "images": r.get("images"),
            "provider": r.get("provider"),
            "model": r.get("model"),
            "input_tokens": r.get("input_tokens"),
            "output_tokens": r.get("output_tokens"),
            "total_tokens": r.get("total_tokens"),
            "cost_usd": float(r["cost_usd"]) if r.get("cost_usd") else None,
            "duration_ms": r.get("duration_ms"),
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
        }
        for r in rows
    ]


# --- AI Preview für Cards ---

def get_section_ai_preview(section_id):
    """Liefert Preview-Daten für Section-Cards (last message, count)."""
    ensure_section_schema()

    thread_row = execute(
        "SELECT id FROM copilot_threads WHERE section_id = %s ORDER BY created_at DESC LIMIT 1",
        (section_id,), fetchone=True,
    )
    if not thread_row:
        return None

    tid = thread_row["id"]

    last_msg = execute(
        """SELECT content FROM copilot_messages 
           WHERE thread_id = %s AND role = 'assistant'
           ORDER BY created_at DESC LIMIT 1""",
        (tid,), fetchone=True,
    )

    count_row = execute(
        "SELECT COUNT(*) as cnt FROM copilot_messages WHERE thread_id = %s",
        (tid,), fetchone=True,
    )

    return {
        "message_count": count_row["cnt"] if count_row else 0,
        "last_message": last_msg["content"] if last_msg else None,
    }


# --- Section-Chat (verbindet alles) ---

def chat_with_section(message, project_id, plan_id, section_id, thread_id=None,
                      images=None, created_by_id=None):
    """Sendet eine Nachricht im Kontext einer Section an Perplexity.

    1. Thread holen/erstellen
    2. User-Message speichern
    3. LLM-Call
    4. Assistant-Message mit Usage speichern
    5. Beides zurueckgeben
    """
    from services.perplexity_service import (
        query_perplexity,
        PerplexityConfigError,
        PerplexityRequestError,
        PerplexityAPIError,
    )
    from services.copilot_service import COPILOT_SYSTEM_PROMPT

    ensure_section_schema()

    # 1. Thread
    if thread_id:
        thr = {"thread_id": thread_id, "project_id": project_id,
               "plan_id": plan_id, "section_id": section_id}
    else:
        thr = get_or_create_thread(project_id, plan_id, section_id, created_by_id)
    tid = thr["thread_id"]

    # 2. User-Message speichern
    user_msg = create_message(
        thread_id=tid, role="user", content=message,
        project_id=project_id, plan_id=plan_id, section_id=section_id,
        images=images, created_by_id=created_by_id,
    )

    # 3. LLM-Call vorbereiten
    messages = [{"role": "system", "content": COPILOT_SYSTEM_PROMPT}]

    # Thread-History laden
    history = list_messages(tid, limit=20)
    for msg in history[:-1]:  # letzte (gerade gespeicherte) User-Msg auslassen
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Aktuelle Nachricht mit optionalen Bild-Referenzen
    user_content = message
    if images:
        img_lines = ["\nAngehaengte Bilder:"]
        for img in images:
            img_lines.append(f"- {img.get('filename', 'Bild')}: {img.get('url', '')}")
        user_content += "\n".join(img_lines)
    messages.append({"role": "user", "content": user_content})

    # 4. LLM aufrufen
    start_time = time.time()
    try:
        result = query_perplexity(messages=messages, temperature=0.3)
        duration_ms = int((time.time() - start_time) * 1000)

        reply = result.get("content", "")
        model = result.get("model", "")
        provider = result.get("provider", "perplexity")
        usage = result.get("usage", {})

        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        cost_usd = _estimate_cost(model, input_tokens, output_tokens)

        # 5. Assistant-Message speichern
        asst_msg = create_message(
            thread_id=tid, role="assistant", content=reply,
            project_id=project_id, plan_id=plan_id, section_id=section_id,
            provider=provider, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            total_tokens=total_tokens, cost_usd=cost_usd, duration_ms=duration_ms,
        )

        return {
            "thread_id": tid,
            "section_id": section_id,
            "status": "success",
            "user_message": user_msg,
            "assistant_message": asst_msg,
        }

    except (PerplexityConfigError, PerplexityRequestError, PerplexityAPIError, Exception) as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = create_message(
            thread_id=tid, role="assistant",
            content=f"Fehler: {e}",
            project_id=project_id, plan_id=plan_id, section_id=section_id,
            provider="perplexity", duration_ms=duration_ms,
            meta={"error": True, "error_type": type(e).__name__},
        )
        return {
            "thread_id": tid,
            "section_id": section_id,
            "status": "failure",
            "error": str(e),
            "user_message": user_msg,
            "assistant_message": error_msg,
        }


# Einfaches Pricing pro 1M Tokens
_PRICING = {
    "sonar": {"input": 1.0, "output": 1.0},
    "sonar-pro": {"input": 3.0, "output": 15.0},
    "sonar-reasoning": {"input": 1.0, "output": 5.0},
}


def _estimate_cost(model, input_tokens, output_tokens):
    """Schaetzt Kosten basierend auf Modell und Token-Counts."""
    if not input_tokens and not output_tokens:
        return None
    # Model-Name matchen (z.B. "sonar-pro-..." → "sonar-pro")
    pricing = None
    for key in sorted(_PRICING.keys(), key=len, reverse=True):
        if model and key in model:
            pricing = _PRICING[key]
            break
    if not pricing:
        pricing = _PRICING.get("sonar", {"input": 1.0, "output": 1.0})

    cost = 0.0
    if input_tokens:
        cost += (input_tokens / 1_000_000) * pricing["input"]
    if output_tokens:
        cost += (output_tokens / 1_000_000) * pricing["output"]
    return round(cost, 6)
