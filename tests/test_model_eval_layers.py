"""
Sprint E2: Abnahmetests fuer Eval-Layer (Judge, SWE, Human, Final).
Laeuft ohne Postgres (In-Memory-Fake via conftest_eval.py).
"""
import json
import pytest

from services.model_eval_service import DEFAULT_CRITERIA


# --- Helper ---

def _full_scores(base_score=4):
    """Erzeugt vollstaendige Scores fuer alle V1-Kriterien."""
    return [{"criterion_key": c["key"], "score": base_score} for c in DEFAULT_CRITERIA]


def _create_base_run(mock_eval_db):
    """Helper: erstellt einen E1-Run und gibt die ID zurueck."""
    from services.model_eval_service import create_eval_run
    result = create_eval_run("E2 Base Task", "claude-opus-4-6", _full_scores(3))
    return result["id"]


# --- E2-1: Judge-Scores ---

class TestJudgeScores:
    def test_set_judge_scores(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores
        run_id = _create_base_run(mock_eval_db)
        scores = [
            {"criterion_key": c["key"], "score": 4, "rationale": f"Gut bei {c['label']}"}
            for c in DEFAULT_CRITERIA
        ]
        result = set_judge_scores(run_id, "a", scores)
        assert result["judge_total_score"] == 80.0
        assert len(result["scores"]) == 6

    def test_judge_scores_with_confidence(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores
        run_id = _create_base_run(mock_eval_db)
        scores = [
            {"criterion_key": "scope_treue", "score": 5, "rationale": "Perfekt", "confidence": 0.95},
        ]
        result = set_judge_scores(run_id, "a", scores)
        assert result["scores"][0]["weight"] == 20

    def test_judge_partial_update_recomputes_total_from_full_persisted_layer(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores
        run_id = _create_base_run(mock_eval_db)

        set_judge_scores(run_id, "a", _full_scores(4))
        result = set_judge_scores(run_id, "a", [
            {"criterion_key": "scope_treue", "score": 5, "rationale": "besser"},
        ])

        assert result["judge_total_score"] == 84.0
        scope = next(s for s in result["scores"] if s["criterion_key"] == "scope_treue")
        assert scope["score"] == 5

    def test_judge_invalid_criterion_rejected(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores
        run_id = _create_base_run(mock_eval_db)
        with pytest.raises(ValueError, match="Unbekanntes Kriterium"):
            set_judge_scores(run_id, "a", [{"criterion_key": "bogus", "score": 3}])

    def test_judge_invalid_side_rejected(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores
        run_id = _create_base_run(mock_eval_db)
        with pytest.raises(ValueError, match="model_side"):
            set_judge_scores(run_id, "x", _full_scores(4))


# --- E2-2: SWE-Metriken ---

class TestSWEMetrics:
    def test_set_swe_metrics(self, mock_eval_db):
        from services.model_eval_layers import set_swe_metrics
        run_id = _create_base_run(mock_eval_db)
        result = set_swe_metrics(run_id, "a", {
            "tests_passed": 42, "tests_failed": 2,
            "files_changed": 5, "lines_added": 120, "lines_removed": 30,
            "lint_warnings": 0, "type_errors": 0, "build_success": True,
        })
        assert result["tests_passed"] == 42
        assert result["build_success"] is True

    def test_swe_metrics_with_extra(self, mock_eval_db):
        from services.model_eval_layers import set_swe_metrics
        run_id = _create_base_run(mock_eval_db)
        result = set_swe_metrics(run_id, "a", {
            "tests_passed": 10, "coverage_pct": 87.5,
        })
        assert result["tests_passed"] == 10
        assert result["extra"]["coverage_pct"] == 87.5

    def test_swe_metrics_in_detail(self, mock_eval_db):
        from services.model_eval_service import get_eval_run
        from services.model_eval_layers import set_swe_metrics
        run_id = _create_base_run(mock_eval_db)
        set_swe_metrics(run_id, "a", {"tests_passed": 7, "tests_failed": 1})
        run = get_eval_run(run_id)
        assert run["swe_metrics_a"] is not None
        assert run["swe_metrics_a"]["tests_passed"] == 7
        assert run["swe_metrics_b"] is None


# --- E2-3: Human-Override ---

class TestHumanScores:
    def test_set_human_scores(self, mock_eval_db):
        from services.model_eval_layers import set_human_scores
        run_id = _create_base_run(mock_eval_db)
        scores = [{"criterion_key": c["key"], "score": 5, "comment": "Override"} for c in DEFAULT_CRITERIA]
        result = set_human_scores(run_id, "a", scores)
        assert result["human_total_score"] == 100.0

    def test_human_partial_override(self, mock_eval_db):
        from services.model_eval_layers import set_human_scores
        run_id = _create_base_run(mock_eval_db)
        result = set_human_scores(run_id, "a", [
            {"criterion_key": "scope_treue", "score": 5, "comment": "Besser als Judge"},
        ])
        assert result["human_total_score"] == 20.0

    def test_human_partial_update_recomputes_total_from_full_persisted_layer(self, mock_eval_db):
        from services.model_eval_layers import set_human_scores
        run_id = _create_base_run(mock_eval_db)

        set_human_scores(run_id, "a", _full_scores(4))
        result = set_human_scores(run_id, "a", [
            {"criterion_key": "scope_treue", "score": 5, "comment": "override"},
        ])

        assert result["human_total_score"] == 84.0
        scope = next(s for s in result["scores"] if s["criterion_key"] == "scope_treue")
        assert scope["score"] == 5


# --- E2-4: Final-Score Layer-Prioritaet ---

class TestFinalScores:
    def test_final_without_layers_equals_original(self, mock_eval_db):
        from services.model_eval_layers import compute_final_scores
        run_id = _create_base_run(mock_eval_db)
        result = compute_final_scores(run_id, "a")
        assert result["final_total_score"] == 60.0
        assert all(s["source"] == "original" for s in result["scores"])

    def test_judge_overrides_original(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores, compute_final_scores
        run_id = _create_base_run(mock_eval_db)
        set_judge_scores(run_id, "a", _full_scores(4))
        result = compute_final_scores(run_id, "a")
        assert result["final_total_score"] == 80.0
        assert all(s["source"] == "judge" for s in result["scores"])

    def test_human_overrides_judge(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores, set_human_scores, compute_final_scores
        run_id = _create_base_run(mock_eval_db)
        set_judge_scores(run_id, "a", _full_scores(4))
        set_human_scores(run_id, "a", _full_scores(5))
        result = compute_final_scores(run_id, "a")
        assert result["final_total_score"] == 100.0
        assert all(s["source"] == "human" for s in result["scores"])

    def test_mixed_layers(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores, set_human_scores, compute_final_scores
        run_id = _create_base_run(mock_eval_db)
        set_judge_scores(run_id, "a", [{"criterion_key": "scope_treue", "score": 4}])
        set_human_scores(run_id, "a", [{"criterion_key": "root_cause", "score": 5}])

        result = compute_final_scores(run_id, "a")
        source_map = {s["criterion_key"]: s["source"] for s in result["scores"]}
        score_map = {s["criterion_key"]: s["score"] for s in result["scores"]}

        assert source_map["scope_treue"] == "judge"
        assert score_map["scope_treue"] == 4
        assert source_map["root_cause"] == "human"
        assert score_map["root_cause"] == 5
        assert source_map["diff_quality"] == "original"
        assert score_map["diff_quality"] == 3

    def test_human_overrides_same_criterion_as_judge(self, mock_eval_db):
        from services.model_eval_layers import set_judge_scores, set_human_scores, compute_final_scores
        run_id = _create_base_run(mock_eval_db)
        set_judge_scores(run_id, "a", [{"criterion_key": "scope_treue", "score": 2}])
        set_human_scores(run_id, "a", [{"criterion_key": "scope_treue", "score": 5}])

        result = compute_final_scores(run_id, "a")
        scope = next(s for s in result["scores"] if s["criterion_key"] == "scope_treue")
        assert scope["score"] == 5
        assert scope["source"] == "human"

    def test_final_scores_include_default_criteria_even_if_original_missing(self, mock_eval_db):
        from services.model_eval_service import create_eval_run
        from services.model_eval_layers import compute_final_scores

        partial_scores = _full_scores(3)[:-1]
        result = create_eval_run("Partial Original", "claude-opus-4-6", partial_scores)

        final = compute_final_scores(result["id"], "a")
        assert len(final["scores"]) == len(DEFAULT_CRITERIA)

        followup = next(s for s in final["scores"] if s["criterion_key"] == "followup_needed")
        assert followup["score"] == 0
        assert followup["source"] == "original"
        assert final["final_total_score"] == 51.0

    def test_final_scores_in_get_eval_run(self, mock_eval_db):
        from services.model_eval_service import get_eval_run
        from services.model_eval_layers import set_judge_scores
        run_id = _create_base_run(mock_eval_db)
        set_judge_scores(run_id, "a", _full_scores(4))
        run = get_eval_run(run_id)
        assert run["final_total_score_a"] == 80.0
        assert run["final_scores_a"] is not None
        assert len(run["final_scores_a"]) == 6
        assert all(s["source"] == "judge" for s in run["final_scores_a"])
        assert run["judge_scores_a"] is not None
        assert run["judge_total_score_a"] == 80.0

    def test_get_eval_run_returns_persisted_layer_totals(self, mock_eval_db):
        from services.model_eval_service import get_eval_run
        from services.model_eval_layers import set_judge_scores, set_human_scores
        run_id = _create_base_run(mock_eval_db)

        set_judge_scores(run_id, "a", _full_scores(4))
        set_human_scores(run_id, "a", [{"criterion_key": "scope_treue", "score": 5}])

        run = get_eval_run(run_id)
        assert run["judge_total_score_a"] == 80.0
        assert run["human_total_score_a"] == 20.0
        assert run["judge_total_score_b"] is None
        assert run["human_total_score_b"] is None


# --- E2-5: API-Endpoints ---

class TestE2API:
    def test_put_judge_scores(self, client, mock_eval_db):
        resp = client.post("/api/eval/runs",
                           data=json.dumps({"task_title": "Judge Test", "model_a": "claude-opus-4-6", "scores_a": _full_scores(3)}),
                           content_type="application/json")
        run_id = resp.get_json()["id"]

        r = client.put(f"/api/eval/runs/{run_id}/judge-scores",
                       data=json.dumps({"model_side": "a", "scores": _full_scores(4)}),
                       content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["judge_total_score"] == 80.0

    def test_put_swe_metrics(self, client, mock_eval_db):
        resp = client.post("/api/eval/runs",
                           data=json.dumps({"task_title": "SWE Test", "model_a": "model-x", "scores_a": _full_scores(3)}),
                           content_type="application/json")
        run_id = resp.get_json()["id"]

        r = client.put(f"/api/eval/runs/{run_id}/swe-metrics",
                       data=json.dumps({"model_side": "a", "metrics": {"tests_passed": 10, "tests_failed": 0, "build_success": True}}),
                       content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["tests_passed"] == 10

    def test_put_human_scores(self, client, mock_eval_db):
        resp = client.post("/api/eval/runs",
                           data=json.dumps({"task_title": "Human Test", "model_a": "model-y", "scores_a": _full_scores(3)}),
                           content_type="application/json")
        run_id = resp.get_json()["id"]

        r = client.put(f"/api/eval/runs/{run_id}/human-scores",
                       data=json.dumps({"model_side": "a", "scores": [{"criterion_key": "scope_treue", "score": 5}]}),
                       content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["human_total_score"] == 20.0

    def test_get_final_scores(self, client, mock_eval_db):
        resp = client.post("/api/eval/runs",
                           data=json.dumps({"task_title": "Final Test", "model_a": "model-z", "scores_a": _full_scores(3)}),
                           content_type="application/json")
        run_id = resp.get_json()["id"]

        r = client.get(f"/api/eval/runs/{run_id}/final-scores?model_side=a")
        assert r.status_code == 200
        d = r.get_json()
        assert d["final_total_score"] == 60.0
        assert len(d["scores"]) == 6

    def test_put_judge_scores_validation(self, client, mock_eval_db):
        r = client.put("/api/eval/runs/1/judge-scores",
                       data=json.dumps({"model_side": "a"}),
                       content_type="application/json")
        assert r.status_code == 400

    def test_put_swe_metrics_validation(self, client, mock_eval_db):
        r = client.put("/api/eval/runs/1/swe-metrics",
                       data=json.dumps({"model_side": "a"}),
                       content_type="application/json")
        assert r.status_code == 400

    def test_get_run_with_all_layers(self, client, mock_eval_db):
        resp = client.post("/api/eval/runs",
                           data=json.dumps({"task_title": "Full Layer Test", "model_a": "claude-opus-4-6", "scores_a": _full_scores(3)}),
                           content_type="application/json")
        run_id = resp.get_json()["id"]

        client.put(f"/api/eval/runs/{run_id}/judge-scores",
                   data=json.dumps({"model_side": "a", "scores": _full_scores(4)}),
                   content_type="application/json")
        client.put(f"/api/eval/runs/{run_id}/swe-metrics",
                   data=json.dumps({"model_side": "a", "metrics": {"tests_passed": 5}}),
                   content_type="application/json")
        client.put(f"/api/eval/runs/{run_id}/human-scores",
                   data=json.dumps({"model_side": "a", "scores": [{"criterion_key": "scope_treue", "score": 5}]}),
                   content_type="application/json")

        r = client.get(f"/api/eval/runs/{run_id}")
        assert r.status_code == 200
        d = r.get_json()

        assert d["scores_a"] is not None
        assert d["judge_scores_a"] is not None
        assert d["human_scores_a"] is not None
        assert d["swe_metrics_a"] is not None
        assert d["final_scores_a"] is not None
        assert d["final_total_score_a"] is not None

        source_map = {s["criterion_key"]: s["source"] for s in d["final_scores_a"]}
        assert source_map["scope_treue"] == "human"
        assert source_map["root_cause"] == "judge"
