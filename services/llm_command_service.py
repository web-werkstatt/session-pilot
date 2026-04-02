"""
Sprint D: LLM Command Hub Service.
Laedt Markdown-Commands, fuehrt sie via Perplexity-Connector aus,
persistiert Ergebnisse in DB.
"""
import json
import os
import re
from datetime import datetime, timezone

import yaml

from config import PROJECTS_DIR
from services.db_service import execute
from services.perplexity_service import (
    query_perplexity,
    PerplexityConfigError,
    PerplexityRequestError,
    PerplexityAPIError,
)

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

# --- Schema ---

_schema_ready = False

import threading
_schema_lock = threading.Lock()


def ensure_llm_commands_schema():
    """Erstellt command_runs Tabelle falls nicht vorhanden."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        execute("""
            CREATE TABLE IF NOT EXISTS command_runs (
                id SERIAL PRIMARY KEY,
                command_id VARCHAR(100) NOT NULL,
                input_context JSONB DEFAULT '{}'::jsonb,
                user_text TEXT,
                output_text TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                error_info TEXT,
                model VARCHAR(100),
                duration_ms INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_command_runs_command_id ON command_runs(command_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_command_runs_created_at ON command_runs(created_at DESC)")
        _schema_ready = True


# --- Command Loader/Parser ---

def load_command(command_id):
    """Laedt einen Command aus prompts/<command_id>.md.

    Returns:
        dict mit command_id, title, purpose, parameters, prompt_body.
        None wenn nicht gefunden oder parse-fehlerhaft.
    """
    path = os.path.join(PROMPTS_DIR, f"{command_id}.md")
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return _parse_command(content)


def list_commands():
    """Listet alle verfuegbaren Commands aus dem prompts/ Verzeichnis."""
    if not os.path.isdir(PROMPTS_DIR):
        return []

    commands = []
    for fname in sorted(os.listdir(PROMPTS_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(PROMPTS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        cmd = _parse_command(content)
        if cmd:
            commands.append({
                "command_id": cmd["command_id"],
                "title": cmd["title"],
                "purpose": cmd["purpose"],
                "parameters": cmd["parameters"],
            })
    return commands


def _parse_command(content):
    """Parst Markdown-Command mit YAML-Frontmatter und Prompt-Body."""
    # Frontmatter extrahieren (--- ... ---)
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None

    try:
        meta = yaml.safe_load(match.group(1))
    except Exception:
        return None

    if not isinstance(meta, dict) or "command_id" not in meta:
        return None

    prompt_body = match.group(2).strip()

    return {
        "command_id": meta["command_id"],
        "title": meta.get("title", meta["command_id"]),
        "purpose": meta.get("purpose", ""),
        "parameters": meta.get("parameters", []),
        "data_sources": meta.get("data_sources", []),
        "prompt_body": prompt_body,
    }


# --- Context Resolver ---

def _resolve_context(command, context):
    """Laedt Daten basierend auf Command-data_sources und fuellt den Prompt."""
    project = context.get("project", "")
    plan_id = context.get("plan_id", "")
    prompt = command["prompt_body"]

    # Platzhalter ersetzen
    prompt = prompt.replace("{{project}}", str(project))
    prompt = prompt.replace("{{plan_id}}", str(plan_id))

    # Gate-Daten laden
    if "{{gate_data}}" in prompt:
        gate_data = _fetch_gate_data(project)
        prompt = prompt.replace("{{gate_data}}", json.dumps(gate_data, indent=2, ensure_ascii=False))

    # Quality-Daten laden
    if "{{quality_data}}" in prompt:
        quality_data = _fetch_quality_data(project)
        prompt = prompt.replace("{{quality_data}}", json.dumps(quality_data, indent=2, ensure_ascii=False))

    # Handoff-Daten laden
    if "{{handoff_data}}" in prompt and plan_id:
        handoff_data = _fetch_handoff_data(plan_id)
        prompt = prompt.replace("{{handoff_data}}", handoff_data)

    # Sections-Daten laden
    if "{{sections_data}}" in prompt and plan_id:
        sections_data = _fetch_sections_data(plan_id)
        prompt = prompt.replace("{{sections_data}}", json.dumps(sections_data, indent=2, ensure_ascii=False))

    return prompt


def _fetch_gate_data(project):
    """Laedt Governance-Gate-Daten fuer ein Projekt."""
    try:
        from services.governance_service import get_governance_gate
        return get_governance_gate(project)
    except Exception as e:
        return {"error": str(e)}


def _fetch_quality_data(project):
    """Laedt Quality-Report-Daten (Zusammenfassung + Top-Issues)."""
    report_path = os.path.join(PROJECTS_DIR, project, ".quality", "report.json")
    if not os.path.exists(report_path):
        return {"error": "Kein Quality-Report vorhanden"}
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Nur relevante Felder + Top-20 Issues nach Severity
        issues = data.get("issues", [])
        top_issues = sorted(issues, key=lambda i: {"error": 0, "warning": 1, "info": 2}.get(i.get("level", "info"), 3))[:20]
        return {
            "score": data.get("score"),
            "score_numeric": data.get("score_numeric"),
            "summary": data.get("summary"),
            "top_issues": [
                {"id": i["id"], "level": i["level"], "category": i["category"],
                 "title": i["title"], "files": i.get("files", [])}
                for i in top_issues
            ],
        }
    except (json.JSONDecodeError, OSError) as e:
        return {"error": str(e)}


def _fetch_handoff_data(plan_id):
    """Laedt Projekt-Handoff-Markdown. Ermittelt project_name aus plan_id."""
    try:
        from services.db_service import execute
        from services.project_handoff_service import write_handoff
        row = execute(
            "SELECT project_name FROM project_plans WHERE id = %s",
            (int(plan_id),), fetchone=True,
        )
        if not row or not row.get("project_name"):
            return "(Kein Projekt fuer diesen Plan)"
        _, md = write_handoff(row["project_name"])
        return md or "(Kein Handoff vorhanden)"
    except Exception as e:
        return f"(Handoff-Fehler: {e})"


def _fetch_sections_data(plan_id):
    """Laedt plan_sections fuer einen Plan."""
    try:
        from services.plan_section_service import list_plan_sections
        sections = list_plan_sections(int(plan_id))
        return [
            {"id": s["id"], "kind": s["kind"], "title": s["title"],
             "status": s.get("status"), "spec_ref": s.get("spec_ref"),
             "summary": s.get("summary")}
            for s in sections
        ]
    except Exception as e:
        return {"error": str(e)}


# --- Run Command ---

def run_command(command_id, context, user_text=None):
    """Fuehrt einen Command aus: Laden, Prompt bauen, LLM aufrufen, persistieren.

    Returns:
        dict mit run_id, command_id, output_text, status, error_info, duration_ms.
    """
    ensure_llm_commands_schema()

    # 1. Command laden
    command = load_command(command_id)
    if not command:
        return _save_run(command_id, context, user_text, None, "failure",
                         f"Command '{command_id}' nicht gefunden", None, None)

    # 2. Parameter validieren
    for param in command.get("parameters", []):
        if param.get("required") and not context.get(param["name"]):
            return _save_run(command_id, context, user_text, None, "failure",
                             f"Parameter '{param['name']}' ist erforderlich", None, None)

    # 3. Prompt zusammensetzen
    prompt = _resolve_context(command, context)
    if user_text:
        prompt += f"\n\nZusaetzlicher Kontext vom Benutzer:\n{user_text}"

    # 4. LLM aufrufen
    started = datetime.now(timezone.utc)
    try:
        result = query_perplexity(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)
        output_text = result.get("content", "")
        model = result.get("model", "")

        return _save_run(command_id, context, user_text, output_text,
                         "success", None, model, duration_ms)

    except PerplexityConfigError as e:
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return _save_run(command_id, context, user_text, None, "failure",
                         f"Config-Fehler: {e}", None, duration_ms)
    except (PerplexityRequestError, PerplexityAPIError) as e:
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return _save_run(command_id, context, user_text, None, "failure",
                         f"LLM-Fehler: {e}", None, duration_ms)
    except Exception as e:
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return _save_run(command_id, context, user_text, None, "failure",
                         f"Unerwarteter Fehler: {e}", None, duration_ms)


def _save_run(command_id, context, user_text, output_text, status, error_info, model, duration_ms):
    """Persistiert einen Command-Run und gibt das Ergebnis zurueck."""
    ensure_llm_commands_schema()

    row = execute(
        """INSERT INTO command_runs
               (command_id, input_context, user_text, output_text, status, error_info, model, duration_ms)
           VALUES (%s, %s::jsonb, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (command_id, json.dumps(context, ensure_ascii=False), user_text,
         output_text, status, error_info, model, duration_ms),
        fetchone=True,
    )

    return {
        "run_id": row["id"],
        "command_id": command_id,
        "output_text": output_text,
        "status": status,
        "error_info": error_info,
        "model": model,
        "duration_ms": duration_ms,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def get_recent_runs(limit=20):
    """Laedt die letzten Command-Runs."""
    ensure_llm_commands_schema()
    rows = execute(
        """SELECT id, command_id, input_context, output_text, status, error_info,
                  model, duration_ms, created_at
           FROM command_runs
           ORDER BY created_at DESC
           LIMIT %s""",
        (limit,),
        fetch=True,
    ) or []
    return [
        {
            "run_id": r["id"],
            "command_id": r["command_id"],
            "input_context": r.get("input_context") or {},
            "output_text": r.get("output_text"),
            "status": r["status"],
            "error_info": r.get("error_info"),
            "model": r.get("model"),
            "duration_ms": r.get("duration_ms"),
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
        }
        for r in rows
    ]
