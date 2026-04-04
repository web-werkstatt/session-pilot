"""
Sprint E1/E2: Abnahmetests fuer Model Eval Service + Layers.
E1: Score-Berechnung, CRUD, API-Endpoints, Validierung.
E2: Judge-Scores, SWE-Metriken, Human-Override, Final-Score-Berechnung.
Laeuft ohne Postgres (In-Memory-Fake in conftest).
"""
import json
import pytest

from services.model_eval_service import (
    compute_total_score,
    determine_winner,
    DEFAULT_CRITERIA,
    CRITERIA_KEYS,
    MAX_SCORE,
)


# --- Helper ---

def _full_scores(base_score=4):
    """Erzeugt vollstaendige Scores fuer alle V1-Kriterien."""
    return [{"criterion_key": c["key"], "score": base_score} for c in DEFAULT_CRITERIA]


# --- E1-1: Kriterien-Definition ---

class TestCriteriaDefinition:
    def test_weights_sum_to_100(self):
        total = sum(c["weight"] for c in DEFAULT_CRITERIA)
        assert total == 100

    def test_six_criteria_in_v1(self):
        assert len(DEFAULT_CRITERIA) == 6

    def test_all_keys_unique(self):
        assert len(CRITERIA_KEYS) == len(set(CRITERIA_KEYS))

    def test_max_score_is_5(self):
        assert MAX_SCORE == 5


# --- E1-2: Score-Berechnung ---

class TestScoreComputation:
    def test_perfect_score(self):
        scores = [{"score": 5, "weight": c["weight"]} for c in DEFAULT_CRITERIA]
        assert compute_total_score(scores) == 100.0

    def test_zero_score(self):
        scores = [{"score": 0, "weight": c["weight"]} for c in DEFAULT_CRITERIA]
        assert compute_total_score(scores) == 0.0

    def test_mid_score(self):
        # score 3/5 * weight fuer jedes Kriterium = 60% von 100
        scores = [{"score": 3, "weight": c["weight"]} for c in DEFAULT_CRITERIA]
        assert compute_total_score(scores) == 60.0

    def test_mixed_scores(self):
        scores = [
            {"score": 5, "weight": 20},
            {"score": 3, "weight": 20},
            {"score": 4, "weight": 15},
            {"score": 2, "weight": 15},
            {"score": 5, "weight": 15},
            {"score": 1, "weight": 15},
        ]
        expected = round(
            (5/5)*20 + (3/5)*20 + (4/5)*15 + (2/5)*15 + (5/5)*15 + (1/5)*15,
            2
        )
        assert compute_total_score(scores) == expected

    def test_empty_scores(self):
        assert compute_total_score([]) == 0.0

    def test_score_always_in_0_100_range(self):
        """Bereichsinvariante: beliebige gueltige Scores landen in [0, 100]."""
        import itertools
        # Stichprobe: jede Kombination von Score-Werten 0 und 5 fuer 6 Kriterien
        weights = [c["weight"] for c in DEFAULT_CRITERIA]
        for combo in itertools.product([0, 1, 3, 5], repeat=len(DEFAULT_CRITERIA)):
            scores = [{"score": s, "weight": w} for s, w in zip(combo, weights)]
            total = compute_total_score(scores)
            assert 0.0 <= total <= 100.0, f"Score {total} ausserhalb [0,100] bei {combo}"

    def test_partial_scores_below_max(self):
        """Partial-Scores (nicht alle Kriterien) geben < 100 auch bei perfekten Noten."""
        partial = [{"score": 5, "weight": DEFAULT_CRITERIA[0]["weight"]}]
        total = compute_total_score(partial)
        assert total == DEFAULT_CRITERIA[0]["weight"]  # 20.0, nicht 100
        assert total < 100.0

    def test_determine_winner_a(self):
        assert determine_winner(80.0, 60.0) == "a"

    def test_determine_winner_b(self):
        assert determine_winner(50.0, 75.0) == "b"

    def test_determine_winner_tie(self):
        assert determine_winner(72.0, 72.5) == "tie"

    def test_determine_winner_none_b(self):
        assert determine_winner(80.0, None) is None

    def test_determine_winner_none_a(self):
        assert determine_winner(None, 60.0) is None

    def test_determine_winner_both_none(self):
        assert determine_winner(None, None) is None

    def test_determine_winner_tie_at_threshold(self):
        """Differenz < 1.0 ist Tie, >= 1.0 hat Gewinner."""
        assert determine_winner(70.0, 70.99) == "tie"
        assert determine_winner(70.0, 71.01) == "b"


# --- E1-3: Service CRUD (mit Fake-DB) ---

class TestEvalRunCRUD:
    def test_create_single_model(self, mock_eval_db):
        from services.model_eval_service import create_eval_run
        result = create_eval_run(
            task_title="Fix Auth Bug",
            model_a="claude-opus-4-6",
            scores_a=_full_scores(4),
            project_id="test_proj",
        )
        assert result["id"] == 1
        assert result["task_title"] == "Fix Auth Bug"
        assert result["model_a"] == "claude-opus-4-6"
        assert result["total_score_a"] == 80.0  # 4/5 * 100
        assert result["model_b"] is None
        assert result["total_score_b"] is None
        assert result["winner"] is None
        assert result["created_at"] is not None

    def test_create_dual_model(self, mock_eval_db):
        from services.model_eval_service import create_eval_run
        result = create_eval_run(
            task_title="Refactor DB Layer",
            model_a="claude-opus-4-6",
            scores_a=_full_scores(5),
            model_b="codex-mini",
            scores_b=_full_scores(3),
        )
        assert result["total_score_a"] == 100.0
        assert result["total_score_b"] == 60.0
        assert result["winner"] == "a"

    def test_create_tie(self, mock_eval_db):
        from services.model_eval_service import create_eval_run
        result = create_eval_run(
            task_title="Simple Fix",
            model_a="model-x",
            scores_a=_full_scores(4),
            model_b="model-y",
            scores_b=_full_scores(4),
        )
        assert result["winner"] == "tie"

    def test_list_runs(self, mock_eval_db):
        from services.model_eval_service import create_eval_run, list_eval_runs
        create_eval_run("Task 1", "model-a", _full_scores(3))
        create_eval_run("Task 2", "model-b", _full_scores(4), project_id="proj_x")
        runs = list_eval_runs()
        assert len(runs) == 2

    def test_list_runs_filter_project(self, mock_eval_db):
        from services.model_eval_service import create_eval_run, list_eval_runs
        create_eval_run("Task 1", "model-a", _full_scores(3), project_id="proj_a")
        create_eval_run("Task 2", "model-b", _full_scores(4), project_id="proj_b")
        runs = list_eval_runs(project_id="proj_a")
        assert len(runs) == 1
        assert runs[0]["project_id"] == "proj_a"

    def test_get_run(self, mock_eval_db):
        from services.model_eval_service import create_eval_run, get_eval_run
        created = create_eval_run("Detail Task", "model-a", _full_scores(5))
        run = get_eval_run(created["id"])
        assert run is not None
        assert run["task_title"] == "Detail Task"
        assert len(run["scores_a"]) == 6

    def test_get_run_not_found(self, mock_eval_db):
        from services.model_eval_service import get_eval_run
        assert get_eval_run(9999) is None

    def test_invalid_criterion_rejected(self, mock_eval_db):
        from services.model_eval_service import create_eval_run
        with pytest.raises(ValueError, match="Unbekanntes Kriterium"):
            create_eval_run("Bad", "model-a", [{"criterion_key": "nonexistent", "score": 3}])

    def test_score_out_of_range_rejected(self, mock_eval_db):
        from services.model_eval_service import create_eval_run
        with pytest.raises(ValueError, match="Score muss 0-5"):
            create_eval_run("Bad", "model-a", [{"criterion_key": "scope_treue", "score": 7}])

    def test_model_b_without_scores_b_rejected(self, mock_eval_db):
        """Modi-Guard: model_b ohne scores_b wird im Service abgewiesen."""
        from services.model_eval_service import create_eval_run
        with pytest.raises(ValueError, match="scores_b ist erforderlich"):
            create_eval_run("X", "a", _full_scores(3), model_b="b", scores_b=None)

    def test_scores_b_without_model_b_rejected(self, mock_eval_db):
        """Modi-Guard: scores_b ohne model_b wird im Service abgewiesen."""
        from services.model_eval_service import create_eval_run
        with pytest.raises(ValueError, match="model_b ist erforderlich"):
            create_eval_run("X", "a", _full_scores(3), model_b=None, scores_b=_full_scores(4))

    def test_single_model_returns_no_winner(self, mock_eval_db):
        """Single-Model-Modus: winner ist immer None."""
        from services.model_eval_service import create_eval_run
        result = create_eval_run("Solo", "model-a", _full_scores(5))
        assert result["winner"] is None
        assert result["model_b"] is None
        assert result["total_score_b"] is None
        assert result["scores_b"] is None

    def test_dual_model_always_has_winner_or_tie(self, mock_eval_db):
        """Dual-Model-Modus: winner ist immer 'a', 'b' oder 'tie'."""
        from services.model_eval_service import create_eval_run
        result = create_eval_run("Dual", "a", _full_scores(4), model_b="b", scores_b=_full_scores(3))
        assert result["winner"] in ("a", "b", "tie")


# --- E1-4: API-Endpoints ---

class TestEvalAPI:
    def test_get_criteria(self, client):
        r = client.get("/api/eval/criteria")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["criteria"]) == 6
        assert sum(c["weight"] for c in d["criteria"]) == 100

    def test_create_run_via_api(self, client, mock_eval_db):
        r = client.post("/api/eval/runs",
                        data=json.dumps({
                            "task_title": "API Test Task",
                            "model_a": "claude-opus-4-6",
                            "scores_a": _full_scores(4),
                            "project_id": "test_proj",
                        }),
                        content_type="application/json")
        assert r.status_code == 201
        d = r.get_json()
        assert d["id"] == 1
        assert d["total_score_a"] == 80.0

    def test_create_run_missing_title(self, client, mock_eval_db):
        r = client.post("/api/eval/runs",
                        data=json.dumps({"model_a": "x", "scores_a": _full_scores(3)}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_create_run_missing_scores(self, client, mock_eval_db):
        r = client.post("/api/eval/runs",
                        data=json.dumps({"task_title": "X", "model_a": "x"}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_create_run_model_b_without_scores(self, client, mock_eval_db):
        r = client.post("/api/eval/runs",
                        data=json.dumps({
                            "task_title": "X",
                            "model_a": "a",
                            "scores_a": _full_scores(3),
                            "model_b": "b",
                        }),
                        content_type="application/json")
        assert r.status_code == 400

    def test_list_runs_via_api(self, client, mock_eval_db):
        # Erst einen Run erstellen
        client.post("/api/eval/runs",
                     data=json.dumps({
                         "task_title": "List Test",
                         "model_a": "model-x",
                         "scores_a": _full_scores(3),
                     }),
                     content_type="application/json")

        r = client.get("/api/eval/runs")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["runs"]) >= 1

    def test_get_run_via_api(self, client, mock_eval_db):
        resp = client.post("/api/eval/runs",
                           data=json.dumps({
                               "task_title": "Detail Test",
                               "model_a": "model-y",
                               "scores_a": _full_scores(5),
                           }),
                           content_type="application/json")
        run_id = resp.get_json()["id"]

        r = client.get(f"/api/eval/runs/{run_id}")
        assert r.status_code == 200
        d = r.get_json()
        assert d["task_title"] == "Detail Test"
        assert len(d["scores_a"]) == 6

    def test_get_run_404(self, client, mock_eval_db):
        r = client.get("/api/eval/runs/9999")
        assert r.status_code == 404


# --- E1-5: UI ---

class TestEvalUI:
    def test_eval_page_renders(self, client):
        r = client.get("/model-eval")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "evalTableBody" in html
        assert "model_eval.js" in html
        assert "model_eval_detail.js" in html
        assert "evalCreateForm" in html

    def test_table_has_layer_columns(self, client):
        """E2: Tabelle zeigt Final-Score und Layer-Spalte."""
        r = client.get("/model-eval")
        html = r.get_data(as_text=True)
        assert "Final A" in html
        assert "Final B" in html
        assert "Layers" in html

    def test_nav_entry_exists(self, client):
        r = client.get("/model-eval")
        html = r.get_data(as_text=True)
        assert 'active_page == \'model_eval\'' in html or 'nav-item active' in html
