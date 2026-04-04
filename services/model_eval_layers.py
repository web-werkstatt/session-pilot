"""
Sprint E2: Model Eval Layers — LLM-Judge, SWE-Metriken, Human-Override.
Erweitert das E1-Eval-Modul um drei Bewertungs-Layer mit klarer Prioritaet.
"""
import json

from services.db_service import execute
from services.model_eval_service import (
    DEFAULT_CRITERIA,
    compute_total_score,
    ensure_eval_schema,
    _enrich_scores,
)


# --- Layer-Management ---

def set_judge_scores(run_id, model_side, scores):
    """Setzt LLM-Judge-Scores fuer eine Modell-Seite (upsert).

    Args:
        run_id: Eval-Run-ID.
        model_side: 'a' oder 'b'.
        scores: list of dicts [{criterion_key, score, rationale?, confidence?}].

    Returns:
        dict mit judge_total_score und den gespeicherten Scores.
    """
    ensure_eval_schema()
    _validate_model_side(model_side)
    enriched = _enrich_scores(scores)

    for s in enriched:
        execute(
            """INSERT INTO eval_judge_scores
                   (eval_run_id, model_side, criterion_key, score, rationale, confidence)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (eval_run_id, model_side, criterion_key)
               DO UPDATE SET score = EXCLUDED.score, rationale = EXCLUDED.rationale,
                             confidence = EXCLUDED.confidence""",
            (run_id, model_side, s["criterion_key"], s["score"],
             s.get("rationale"), s.get("confidence")),
        )

    persisted = _load_weighted_layer_scores("eval_judge_scores", run_id, model_side)
    judge_total = compute_total_score(persisted)
    col = f"judge_total_score_{model_side}"
    execute(f"UPDATE eval_runs SET {col} = %s WHERE id = %s", (judge_total, run_id))

    _recompute_final(run_id, model_side)

    return {"judge_total_score": judge_total, "scores": persisted}


def set_swe_metrics(run_id, model_side, metrics):
    """Setzt SWE-Metriken fuer eine Modell-Seite (upsert).

    Args:
        run_id: Eval-Run-ID.
        model_side: 'a' oder 'b'.
        metrics: dict mit tests_passed, tests_failed, files_changed, etc.

    Returns:
        dict mit den gespeicherten Metriken.
    """
    ensure_eval_schema()
    _validate_model_side(model_side)

    fields = ("tests_passed", "tests_failed", "files_changed",
              "lines_added", "lines_removed", "lint_warnings",
              "type_errors", "build_success")
    values = {k: metrics.get(k) for k in fields}
    extra = {k: v for k, v in metrics.items() if k not in fields}

    execute(
        """INSERT INTO eval_swe_metrics
               (eval_run_id, model_side, tests_passed, tests_failed, files_changed,
                lines_added, lines_removed, lint_warnings, type_errors, build_success, extra)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (eval_run_id, model_side)
           DO UPDATE SET tests_passed = EXCLUDED.tests_passed,
               tests_failed = EXCLUDED.tests_failed,
               files_changed = EXCLUDED.files_changed,
               lines_added = EXCLUDED.lines_added,
               lines_removed = EXCLUDED.lines_removed,
               lint_warnings = EXCLUDED.lint_warnings,
               type_errors = EXCLUDED.type_errors,
               build_success = EXCLUDED.build_success,
               extra = EXCLUDED.extra""",
        (run_id, model_side,
         values["tests_passed"], values["tests_failed"], values["files_changed"],
         values["lines_added"], values["lines_removed"], values["lint_warnings"],
         values["type_errors"], values["build_success"],
         json.dumps(extra) if extra else None),
    )
    result = dict(values)
    if extra:
        result["extra"] = extra
    return result


def set_human_scores(run_id, model_side, scores):
    """Setzt Human-Override-Scores fuer eine Modell-Seite (upsert).

    Args:
        run_id: Eval-Run-ID.
        model_side: 'a' oder 'b'.
        scores: list of dicts [{criterion_key, score, comment?}].

    Returns:
        dict mit human_total_score und den gespeicherten Scores.
    """
    ensure_eval_schema()
    _validate_model_side(model_side)
    enriched = _enrich_scores(scores)

    for s in enriched:
        execute(
            """INSERT INTO eval_human_scores
                   (eval_run_id, model_side, criterion_key, score, comment)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (eval_run_id, model_side, criterion_key)
               DO UPDATE SET score = EXCLUDED.score, comment = EXCLUDED.comment""",
            (run_id, model_side, s["criterion_key"], s["score"], s.get("comment")),
        )

    persisted = _load_weighted_layer_scores("eval_human_scores", run_id, model_side)
    human_total = compute_total_score(persisted)
    col = f"human_total_score_{model_side}"
    execute(f"UPDATE eval_runs SET {col} = %s WHERE id = %s", (human_total, run_id))

    _recompute_final(run_id, model_side)

    return {"human_total_score": human_total, "scores": persisted}


def compute_final_scores(run_id, model_side):
    """Berechnet final_scores mit Layer-Prioritaet: human > judge > original.

    Returns:
        dict mit 'scores' (list of {criterion_key, score, weight, source}) und 'final_total_score'.
    """
    ensure_eval_schema()

    originals = _load_layer(
        "eval_scores", run_id, model_side,
        "criterion_key, score, weight",
    )
    judges = _load_layer(
        "eval_judge_scores", run_id, model_side,
        "criterion_key, score",
    )
    humans = _load_layer(
        "eval_human_scores", run_id, model_side,
        "criterion_key, score",
    )

    original_map = {s["criterion_key"]: s["score"] for s in originals}
    judge_map = {s["criterion_key"]: s["score"] for s in judges}
    human_map = {s["criterion_key"]: s["score"] for s in humans}

    final = []
    for criterion in DEFAULT_CRITERIA:
        key = criterion["key"]
        weight = criterion["weight"]
        if key in human_map:
            final.append({"criterion_key": key, "score": human_map[key],
                          "weight": weight, "source": "human"})
        elif key in judge_map:
            final.append({"criterion_key": key, "score": judge_map[key],
                          "weight": weight, "source": "judge"})
        else:
            final.append({"criterion_key": key, "score": original_map.get(key, 0),
                          "weight": weight, "source": "original"})

    final_total = compute_total_score(final)
    return {"scores": final, "final_total_score": final_total}


def load_all_layers(run_id):
    """Laedt alle E2-Layer fuer einen Run (fuer get_eval_run)."""
    result = {}

    # Judge-Scores
    judge = execute(
        """SELECT model_side, criterion_key, score, rationale, confidence
           FROM eval_judge_scores WHERE eval_run_id = %s
           ORDER BY model_side, criterion_key""",
        (run_id,), fetch=True,
    ) or []
    for side in ("a", "b"):
        layer = [
            {"criterion_key": s["criterion_key"], "score": s["score"],
             "rationale": s.get("rationale"),
             "confidence": float(s["confidence"]) if s.get("confidence") is not None else None}
            for s in judge if s["model_side"] == side
        ] or None
        result[f"judge_scores_{side}"] = layer

    # Human-Scores
    human = execute(
        """SELECT model_side, criterion_key, score, comment
           FROM eval_human_scores WHERE eval_run_id = %s
           ORDER BY model_side, criterion_key""",
        (run_id,), fetch=True,
    ) or []
    for side in ("a", "b"):
        layer = [
            {"criterion_key": s["criterion_key"], "score": s["score"],
             "comment": s.get("comment")}
            for s in human if s["model_side"] == side
        ] or None
        result[f"human_scores_{side}"] = layer

    # SWE-Metriken
    swe = execute(
        """SELECT model_side, tests_passed, tests_failed, files_changed,
                  lines_added, lines_removed, lint_warnings, type_errors,
                  build_success, extra
           FROM eval_swe_metrics WHERE eval_run_id = %s""",
        (run_id,), fetch=True,
    ) or []
    for side in ("a", "b"):
        row_swe = next((s for s in swe if s["model_side"] == side), None)
        if row_swe:
            m = {k: row_swe[k] for k in ("tests_passed", "tests_failed", "files_changed",
                 "lines_added", "lines_removed", "lint_warnings", "type_errors", "build_success")}
            extra = row_swe.get("extra")
            if extra:
                if isinstance(extra, str):
                    extra = json.loads(extra)
                m["extra"] = extra
            result[f"swe_metrics_{side}"] = m
        else:
            result[f"swe_metrics_{side}"] = None

    return result


# --- Helpers ---

def _recompute_final(run_id, model_side):
    """Recompute und persistiert final_total_score fuer eine Seite."""
    result = compute_final_scores(run_id, model_side)
    col = f"final_total_score_{model_side}"
    execute(f"UPDATE eval_runs SET {col} = %s WHERE id = %s",
            (result["final_total_score"], run_id))
    return result


def _load_layer(table, run_id, model_side, columns):
    """Laedt Scores einer Layer-Tabelle."""
    rows = execute(
        f"SELECT {columns} FROM {table} WHERE eval_run_id = %s AND model_side = %s",
        (run_id, model_side),
        fetch=True,
    )
    return rows or []


def _load_weighted_layer_scores(table, run_id, model_side):
    """Laedt einen persistierten Judge/Human-Layer inkl. Gewichten."""
    weight_map = {c["key"]: c["weight"] for c in DEFAULT_CRITERIA}
    if table == "eval_judge_scores":
        columns = "criterion_key, score, rationale, confidence"
    elif table == "eval_human_scores":
        columns = "criterion_key, score, comment"
    else:
        raise ValueError(f"ungueltige layer-tabelle: {table}")

    rows = _load_layer(table, run_id, model_side, columns)
    result = []
    for row in rows:
        item = {
            "criterion_key": row["criterion_key"],
            "score": row["score"],
            "weight": weight_map.get(row["criterion_key"], 0),
        }
        if "rationale" in row:
            item["rationale"] = row.get("rationale")
        if "confidence" in row:
            item["confidence"] = row.get("confidence")
        if "comment" in row:
            item["comment"] = row.get("comment")
        result.append(item)
    return result


def _validate_model_side(side):
    if side not in ("a", "b"):
        raise ValueError(f"model_side muss 'a' oder 'b' sein, war '{side}'")
