"""
Sprint E1/E2: Model Eval Service — gewichtete Scorecard fuer AI-Coding-Runs.
E1: Basis-Scores, E2: LLM-Judge + SWE-Metriken + Human-Override.
Persistiert Eval-Runs in PostgreSQL, berechnet total_score als gewichtete Summe.
"""
import threading

from services.db_service import execute

# --- Kriterien V1 (Gewichte muessen 100 ergeben) ---

DEFAULT_CRITERIA = [
    {"key": "scope_treue", "label": "Scope-Treue", "weight": 20},
    {"key": "root_cause", "label": "Root-Cause-Treffer", "weight": 20},
    {"key": "diff_quality", "label": "Diff-Qualität", "weight": 15},
    {"key": "test_discipline", "label": "Test-Disziplin", "weight": 15},
    {"key": "brownfield_safety", "label": "Brownfield-Sicherheit", "weight": 15},
    {"key": "followup_needed", "label": "Follow-up-Bedarf", "weight": 15},
]

CRITERIA_KEYS = [c["key"] for c in DEFAULT_CRITERIA]
MAX_SCORE = 5

# --- Schema ---

_schema_ready = False
_schema_lock = threading.Lock()


def ensure_eval_schema():
    """Erstellt eval_runs und eval_scores Tabellen falls nicht vorhanden."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        execute("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                id SERIAL PRIMARY KEY,
                task_title VARCHAR(300) NOT NULL,
                task_description TEXT,
                project_id VARCHAR(200),
                model_a VARCHAR(100) NOT NULL,
                model_b VARCHAR(100),
                total_score_a NUMERIC(5,2),
                total_score_b NUMERIC(5,2),
                winner VARCHAR(10),
                notes TEXT,
                created_by VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("""
            CREATE TABLE IF NOT EXISTS eval_scores (
                id SERIAL PRIMARY KEY,
                eval_run_id INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                model_side CHAR(1) NOT NULL CHECK (model_side IN ('a', 'b')),
                criterion_key VARCHAR(50) NOT NULL,
                score SMALLINT NOT NULL CHECK (score >= 0 AND score <= 5),
                weight SMALLINT NOT NULL CHECK (weight > 0),
                comment TEXT,
                UNIQUE (eval_run_id, model_side, criterion_key)
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_eval_runs_project ON eval_runs(project_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_eval_runs_created ON eval_runs(created_at DESC)")
        execute("CREATE INDEX IF NOT EXISTS idx_eval_scores_run ON eval_scores(eval_run_id)")
        # E2: Judge-Scores, SWE-Metriken, Human-Overrides
        execute("""
            CREATE TABLE IF NOT EXISTS eval_judge_scores (
                id SERIAL PRIMARY KEY,
                eval_run_id INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                model_side CHAR(1) NOT NULL CHECK (model_side IN ('a', 'b')),
                criterion_key VARCHAR(50) NOT NULL,
                score SMALLINT NOT NULL CHECK (score >= 0 AND score <= 5),
                rationale TEXT,
                confidence NUMERIC(3,2) CHECK (confidence >= 0 AND confidence <= 1),
                UNIQUE (eval_run_id, model_side, criterion_key)
            )
        """)
        execute("""
            CREATE TABLE IF NOT EXISTS eval_swe_metrics (
                id SERIAL PRIMARY KEY,
                eval_run_id INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                model_side CHAR(1) NOT NULL CHECK (model_side IN ('a', 'b')),
                tests_passed INTEGER DEFAULT 0,
                tests_failed INTEGER DEFAULT 0,
                files_changed INTEGER DEFAULT 0,
                lines_added INTEGER DEFAULT 0,
                lines_removed INTEGER DEFAULT 0,
                lint_warnings INTEGER DEFAULT 0,
                type_errors INTEGER DEFAULT 0,
                build_success BOOLEAN,
                extra JSONB,
                UNIQUE (eval_run_id, model_side)
            )
        """)
        execute("""
            CREATE TABLE IF NOT EXISTS eval_human_scores (
                id SERIAL PRIMARY KEY,
                eval_run_id INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                model_side CHAR(1) NOT NULL CHECK (model_side IN ('a', 'b')),
                criterion_key VARCHAR(50) NOT NULL,
                score SMALLINT NOT NULL CHECK (score >= 0 AND score <= 5),
                comment TEXT,
                UNIQUE (eval_run_id, model_side, criterion_key)
            )
        """)
        # E2: Zusatz-Spalten auf eval_runs (idempotent via try/except)
        for col in ("judge_total_score_a", "judge_total_score_b",
                     "human_total_score_a", "human_total_score_b",
                     "final_total_score_a", "final_total_score_b"):
            try:
                execute(f"ALTER TABLE eval_runs ADD COLUMN {col} NUMERIC(5,2)")
            except Exception:
                pass
        _schema_ready = True


# --- Score-Berechnung ---

def compute_total_score(scores):
    """Berechnet gewichtete Summe: sum((score / 5.0) * weight).

    Args:
        scores: list of dicts mit 'score' (0-5) und 'weight'.
    Returns:
        float gerundet auf 2 Stellen, max 100.
    """
    if not scores:
        return 0.0
    total = sum((s["score"] / MAX_SCORE) * s["weight"] for s in scores)
    return round(total, 2)


def determine_winner(total_a, total_b):
    """Bestimmt Gewinner: 'a', 'b' oder 'tie'."""
    if total_a is None or total_b is None:
        return None
    diff = abs(total_a - total_b)
    if diff < 1.0:
        return "tie"
    return "a" if total_a > total_b else "b"


# --- CRUD ---

def create_eval_run(task_title, model_a, scores_a, model_b=None, scores_b=None,
                    task_description=None, project_id=None, notes=None, created_by=None):
    """Erstellt einen Eval-Run mit Scores fuer ein oder zwei Modelle.

    Args:
        task_title: Kurztitel der Aufgabe (Pflicht).
        model_a: Modellname A (Pflicht).
        scores_a: list of dicts [{criterion_key, score, comment?}, ...].
        model_b: Optionaler Modellname B fuer Vergleich.
        scores_b: Scores fuer Modell B (Pflicht wenn model_b gesetzt).
        task_description: Optionale ausfuehrliche Aufgabenbeschreibung.
        project_id: Optionale Projekt-Zuordnung.
        notes: Optionale Freitext-Notizen.
        created_by: Optionaler Ersteller.

    Returns:
        dict mit Run-Daten inkl. berechneten Scores.
    """
    ensure_eval_schema()

    # Modi-Validierung: model_b und scores_b muessen konsistent sein
    if model_b and not scores_b:
        raise ValueError("scores_b ist erforderlich wenn model_b gesetzt ist")
    if scores_b and not model_b:
        raise ValueError("model_b ist erforderlich wenn scores_b gesetzt ist")

    # Scores validieren und anreichern
    enriched_a = _enrich_scores(scores_a)
    total_a = compute_total_score(enriched_a)

    total_b = None
    enriched_b = None
    if model_b and scores_b:
        enriched_b = _enrich_scores(scores_b)
        total_b = compute_total_score(enriched_b)

    winner = determine_winner(total_a, total_b)

    row = execute(
        """INSERT INTO eval_runs
               (task_title, task_description, project_id, model_a, model_b,
                total_score_a, total_score_b, winner, notes, created_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id, created_at""",
        (task_title, task_description, project_id, model_a, model_b,
         total_a, total_b, winner, notes, created_by),
        fetchone=True,
    )
    run_id = row["id"]

    # Scores persistieren
    _insert_scores(run_id, "a", enriched_a)
    if enriched_b:
        _insert_scores(run_id, "b", enriched_b)

    return {
        "id": run_id,
        "task_title": task_title,
        "task_description": task_description,
        "project_id": project_id,
        "model_a": model_a,
        "model_b": model_b,
        "scores_a": enriched_a,
        "scores_b": enriched_b,
        "total_score_a": total_a,
        "total_score_b": total_b,
        "winner": winner,
        "notes": notes,
        "created_by": created_by,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def list_eval_runs(project_id=None, limit=50):
    """Listet Eval-Runs, optional gefiltert nach Projekt."""
    ensure_eval_schema()

    conditions = []
    params = []
    if project_id:
        conditions.append("project_id = %s")
        params.append(project_id)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(min(limit, 200))

    rows = execute(
        f"""SELECT id, task_title, task_description, project_id,
                   model_a, model_b, total_score_a, total_score_b,
                   winner, notes, created_by, created_at
            FROM eval_runs
            {where}
            ORDER BY created_at DESC
            LIMIT %s""",
        tuple(params),
        fetch=True,
    ) or []

    return [_format_run_row(r) for r in rows]


def get_eval_run(run_id):
    """Laedt einen einzelnen Eval-Run inkl. aller Scores und E2-Layer."""
    ensure_eval_schema()

    row = execute(
        """SELECT id, task_title, task_description, project_id,
                  model_a, model_b, total_score_a, total_score_b,
                  judge_total_score_a, judge_total_score_b,
                  human_total_score_a, human_total_score_b,
                  final_total_score_a, final_total_score_b,
                  winner, notes, created_by, created_at
           FROM eval_runs WHERE id = %s""",
        (run_id,),
        fetchone=True,
    )
    if not row:
        return None

    result = _format_run_row(row)

    # E1: Original-Scores
    scores = execute(
        """SELECT model_side, criterion_key, score, weight, comment
           FROM eval_scores WHERE eval_run_id = %s
           ORDER BY model_side, criterion_key""",
        (run_id,),
        fetch=True,
    ) or []

    result["scores_a"] = [
        {"criterion_key": s["criterion_key"], "score": s["score"],
         "weight": s["weight"], "comment": s.get("comment")}
        for s in scores if s["model_side"] == "a"
    ]
    result["scores_b"] = [
        {"criterion_key": s["criterion_key"], "score": s["score"],
         "weight": s["weight"], "comment": s.get("comment")}
        for s in scores if s["model_side"] == "b"
    ] or None

    # E2: Alle Layer laden (judge, human, swe, final)
    from services.model_eval_layers import load_all_layers, compute_final_scores
    layers = load_all_layers(run_id)
    result.update(layers)

    for side in ("a", "b"):
        if result.get(f"scores_{side}"):
            final = compute_final_scores(run_id, side)
            result[f"final_scores_{side}"] = final["scores"]
            result[f"final_total_score_{side}"] = final["final_total_score"]
        else:
            result[f"final_scores_{side}"] = None
            result[f"final_total_score_{side}"] = None

    return result


def get_criteria():
    """Gibt die V1-Kriterien-Definition zurueck."""
    return list(DEFAULT_CRITERIA)


# --- Helpers ---

def _enrich_scores(scores):
    """Validiert und reichert Scores mit Gewichten aus DEFAULT_CRITERIA an."""
    weight_map = {c["key"]: c["weight"] for c in DEFAULT_CRITERIA}
    enriched = []
    for s in scores:
        key = s.get("criterion_key") or s.get("key")
        if key not in weight_map:
            raise ValueError(f"Unbekanntes Kriterium: {key}")
        score_val = int(s["score"])
        if score_val < 0 or score_val > MAX_SCORE:
            raise ValueError(f"Score muss 0-{MAX_SCORE} sein, war {score_val}")
        enriched.append({
            "criterion_key": key,
            "score": score_val,
            "weight": weight_map[key],
            "comment": s.get("comment"),
        })
    return enriched


def _insert_scores(run_id, side, scores):
    """Persistiert Score-Eintraege fuer eine Modell-Seite."""
    for s in scores:
        execute(
            """INSERT INTO eval_scores (eval_run_id, model_side, criterion_key, score, weight, comment)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (run_id, side, s["criterion_key"], s["score"], s["weight"], s.get("comment")),
        )


def _format_run_row(r):
    """Formatiert eine DB-Row zu einem API-tauglichen dict."""
    return {
        "id": r["id"],
        "task_title": r["task_title"],
        "task_description": r.get("task_description"),
        "project_id": r.get("project_id"),
        "model_a": r["model_a"],
        "model_b": r.get("model_b"),
        "total_score_a": float(r["total_score_a"]) if r.get("total_score_a") is not None else None,
        "total_score_b": float(r["total_score_b"]) if r.get("total_score_b") is not None else None,
        "judge_total_score_a": float(r["judge_total_score_a"]) if r.get("judge_total_score_a") is not None else None,
        "judge_total_score_b": float(r["judge_total_score_b"]) if r.get("judge_total_score_b") is not None else None,
        "human_total_score_a": float(r["human_total_score_a"]) if r.get("human_total_score_a") is not None else None,
        "human_total_score_b": float(r["human_total_score_b"]) if r.get("human_total_score_b") is not None else None,
        "final_total_score_a": float(r["final_total_score_a"]) if r.get("final_total_score_a") is not None else None,
        "final_total_score_b": float(r["final_total_score_b"]) if r.get("final_total_score_b") is not None else None,
        "winner": r.get("winner"),
        "notes": r.get("notes"),
        "created_by": r.get("created_by"),
        "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
    }
