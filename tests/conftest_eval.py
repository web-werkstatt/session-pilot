"""
Eval-spezifische Test-Fixtures (ausgelagert aus conftest.py wegen Zeilenlimit).
Wird von conftest.py via pytest_plugins geladen.
"""
import pytest
from datetime import datetime, timezone


@pytest.fixture
def mock_eval_db(monkeypatch):
    """In-Memory-Fake fuer model_eval_service + model_eval_layers ohne Postgres."""
    import services.model_eval_service as mes
    import services.model_eval_layers as mel

    runs = {}
    scores = []
    judge_scores = []
    human_scores = []
    swe_metrics = []
    next_run_id = 1
    next_id = 1

    def fake_execute(query, params=None, fetch=False, fetchone=False):
        nonlocal next_run_id, next_id
        q = " ".join(str(query).lower().split())
        params = params or ()

        # --- eval_runs INSERT ---
        if "insert into eval_runs" in q:
            run = {
                "id": next_run_id,
                "task_title": params[0],
                "task_description": params[1],
                "project_id": params[2],
                "model_a": params[3],
                "model_b": params[4],
                "total_score_a": params[5],
                "total_score_b": params[6],
                "winner": params[7],
                "notes": params[8],
                "created_by": params[9],
                "created_at": datetime.now(timezone.utc),
            }
            runs[next_run_id] = run
            next_run_id += 1
            return {"id": run["id"], "created_at": run["created_at"]} if fetchone else None

        # --- eval_runs UPDATE ---
        if "update eval_runs set" in q and "where id = %s" in q:
            run_id = params[-1]
            run = runs.get(run_id)
            if run:
                set_part = q.split("set ", 1)[1].split(" where", 1)[0].strip()
                cols = [c.strip().split(" = ")[0] for c in set_part.split(", ")]
                for idx, col in enumerate(cols):
                    if idx < len(params) - 1:
                        run[col] = params[idx]
            return None

        # --- eval_scores ---
        if "insert into eval_scores" in q:
            s = {
                "id": next_id, "eval_run_id": params[0], "model_side": params[1],
                "criterion_key": params[2], "score": params[3],
                "weight": params[4], "comment": params[5] if len(params) > 5 else None,
            }
            scores.append(s)
            next_id += 1
            return None

        # --- eval_judge_scores (INSERT/UPSERT) ---
        if "insert into eval_judge_scores" in q:
            key = (params[0], params[1], params[2])
            judge_scores[:] = [j for j in judge_scores
                               if (j["eval_run_id"], j["model_side"], j["criterion_key"]) != key]
            judge_scores.append({
                "id": next_id, "eval_run_id": params[0], "model_side": params[1],
                "criterion_key": params[2], "score": params[3],
                "rationale": params[4] if len(params) > 4 else None,
                "confidence": params[5] if len(params) > 5 else None,
            })
            next_id += 1
            return None

        # --- eval_human_scores (INSERT/UPSERT) ---
        if "insert into eval_human_scores" in q:
            key = (params[0], params[1], params[2])
            human_scores[:] = [h for h in human_scores
                               if (h["eval_run_id"], h["model_side"], h["criterion_key"]) != key]
            human_scores.append({
                "id": next_id, "eval_run_id": params[0], "model_side": params[1],
                "criterion_key": params[2], "score": params[3],
                "comment": params[4] if len(params) > 4 else None,
            })
            next_id += 1
            return None

        # --- eval_swe_metrics (INSERT/UPSERT) ---
        if "insert into eval_swe_metrics" in q:
            key = (params[0], params[1])
            swe_metrics[:] = [m for m in swe_metrics
                              if (m["eval_run_id"], m["model_side"]) != key]
            swe_metrics.append({
                "id": next_id, "eval_run_id": params[0], "model_side": params[1],
                "tests_passed": params[2], "tests_failed": params[3],
                "files_changed": params[4], "lines_added": params[5],
                "lines_removed": params[6], "lint_warnings": params[7],
                "type_errors": params[8], "build_success": params[9],
                "extra": params[10] if len(params) > 10 else None,
            })
            next_id += 1
            return None

        # --- SELECT: eval_runs by id ---
        if "from eval_runs where id = %s" in q:
            run = runs.get(params[0])
            if not run:
                return None if fetchone else []
            return dict(run) if fetchone else [dict(run)]

        # --- SELECT: eval_runs list ---
        if "from eval_runs" in q and "select" in q:
            filtered = list(runs.values())
            if "project_id = %s" in q:
                pid = params[0]
                filtered = [r for r in filtered if r["project_id"] == pid]
            filtered.sort(key=lambda r: r["created_at"], reverse=True)
            limit_val = params[-1] if params else 50
            if isinstance(limit_val, int):
                filtered = filtered[:limit_val]
            return [dict(r) for r in filtered] if fetch else None

        # --- SELECT: eval_scores ---
        if "from eval_scores" in q and "eval_run_id = %s" in q:
            rid = params[0]
            found = [dict(s) for s in scores if s["eval_run_id"] == rid]
            if "model_side = %s" in q:
                found = [s for s in found if s["model_side"] == params[1]]
            return found if fetch else None

        # --- SELECT: eval_judge_scores ---
        if "from eval_judge_scores" in q and "eval_run_id = %s" in q:
            rid = params[0]
            found = [dict(s) for s in judge_scores if s["eval_run_id"] == rid]
            if "model_side = %s" in q:
                found = [s for s in found if s["model_side"] == params[1]]
            return found if fetch else None

        # --- SELECT: eval_human_scores ---
        if "from eval_human_scores" in q and "eval_run_id = %s" in q:
            rid = params[0]
            found = [dict(s) for s in human_scores if s["eval_run_id"] == rid]
            if "model_side = %s" in q:
                found = [s for s in found if s["model_side"] == params[1]]
            return found if fetch else None

        # --- SELECT: eval_swe_metrics ---
        if "from eval_swe_metrics" in q and "eval_run_id = %s" in q:
            rid = params[0]
            found = [dict(m) for m in swe_metrics if m["eval_run_id"] == rid]
            return found if fetch else None

        return [] if fetch else None

    monkeypatch.setattr(mes, "execute", fake_execute)
    monkeypatch.setattr(mes, "ensure_eval_schema", lambda: None)
    monkeypatch.setattr(mes, "_schema_ready", True)
    monkeypatch.setattr(mel, "execute", fake_execute)
    monkeypatch.setattr(mel, "ensure_eval_schema", lambda: None)
    return {
        "runs": runs, "scores": scores,
        "judge_scores": judge_scores, "human_scores": human_scores,
        "swe_metrics": swe_metrics,
    }
