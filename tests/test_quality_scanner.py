"""
SPEC-QUALITY-SCANNER-MVP-001: Abnahmetests fuer Quality Scanner MVP.
Deckt R1-R9, R12 ab.
"""
import json
import os
import shutil
import tempfile

import pytest

from auto_coder.config import IGNORE_DIRS, LEVELS, SCORE_WEIGHTS
from auto_coder.report import Issue, QualityReport, calculate_score, issue_id, load_report, save_report
from auto_coder.scanner import ProjectQualityScanner


# --- Fixtures ---

@pytest.fixture
def scanner():
    return ProjectQualityScanner()


@pytest.fixture
def tmp_project(tmp_path):
    """Minimales Projekt-Verzeichnis fuer Tests."""
    # Eine Python-Datei
    (tmp_path / "app.py").write_text("def main():\n    pass\n")
    # CLAUDE.md als Projekt-Indikator
    (tmp_path / "CLAUDE.md").write_text("# Test\n")
    return str(tmp_path)


@pytest.fixture
def project_dashboard_path():
    """Pfad zum echten project_dashboard."""
    return "/mnt/projects/project_dashboard"


# --- R1: CLI scan einzelnes Projekt ---

class TestR1SingleScan:
    def test_scan_produces_report(self, scanner, tmp_project):
        report = scanner.scan(tmp_project)
        assert isinstance(report, QualityReport)
        assert report.project != ""
        assert report.scanned_at != ""
        assert report.score in ("A", "B", "C", "D", "F")
        assert 0 <= report.score_numeric <= 100

    def test_scan_writes_report_json(self, scanner, tmp_project):
        scanner.scan(tmp_project)
        report_path = os.path.join(tmp_project, ".quality", "report.json")
        assert os.path.exists(report_path)
        with open(report_path) as f:
            data = json.load(f)
        assert "project" in data
        assert "scanned_at" in data
        assert "score" in data
        assert "issues" in data

    def test_scan_resolves_project_name(self, scanner):
        """Projektnamen ohne Pfad werden gegen PROJECTS_ROOT aufgeloest."""
        report = scanner.scan("project_dashboard")
        assert report.project == "project_dashboard"
        assert report.summary.get("total_issues", 0) > 0


# --- R3: Report-Schema ---

class TestR3ReportSchema:
    def test_top_level_fields(self, scanner, tmp_project):
        scanner.scan(tmp_project)
        report_path = os.path.join(tmp_project, ".quality", "report.json")
        with open(report_path) as f:
            data = json.load(f)

        required = ["project", "scanned_at", "score", "score_numeric",
                     "summary", "tests", "issues", "history"]
        for field in required:
            assert field in data, f"Feld '{field}' fehlt im Report"

    def test_summary_fields(self, scanner, tmp_project):
        scanner.scan(tmp_project)
        report_path = os.path.join(tmp_project, ".quality", "report.json")
        with open(report_path) as f:
            data = json.load(f)

        summary = data["summary"]
        for field in ["total_issues", "errors", "warnings", "info", "skipped_checks"]:
            assert field in summary, f"Feld '{field}' fehlt in summary"

    def test_score_numeric_is_int(self, scanner, tmp_project):
        scanner.scan(tmp_project)
        report_path = os.path.join(tmp_project, ".quality", "report.json")
        with open(report_path) as f:
            data = json.load(f)
        assert isinstance(data["score_numeric"], int)


# --- R4: Score-Berechnung ---

class TestR4ScoreCalculation:
    def test_empty_issues_give_100(self):
        letter, score = calculate_score([])
        assert score == 100
        assert letter == "A"

    def test_score_decrements_by_weight(self):
        issues = [Issue(id="t-001", level="warning", category="file_size",
                        title="test", files=["a.py"])]
        letter, score = calculate_score(issues)
        assert score == 100 + SCORE_WEIGHTS["file_size"]  # 100 - 2 = 98

    def test_errors_count_double(self):
        issues = [Issue(id="t-001", level="error", category="architecture",
                        title="test", files=["a.py"])]
        letter, score = calculate_score(issues)
        # error: weight * 2 = -5 * 2 = -10
        assert score == 90

    def test_score_minimum_is_zero(self):
        issues = [Issue(id=f"t-{i:03d}", level="error", category="architecture",
                        title="test", files=["a.py"]) for i in range(50)]
        _, score = calculate_score(issues)
        assert score == 0

    def test_level_score_consistency(self):
        for target_score in [95, 82, 65, 45, 10]:
            # Create enough issues to reach target
            issues = []
            n = (100 - target_score) // 2  # file_size weight is -2
            for i in range(n):
                issues.append(Issue(id=f"t-{i:03d}", level="warning",
                                    category="file_size", title="t", files=["a.py"]))
            letter, score = calculate_score(issues)
            # Verify level matches score
            expected_level = "F"
            for grade, threshold in LEVELS:
                if score >= threshold:
                    expected_level = grade
                    break
            assert letter == expected_level, f"Score {score} should be {expected_level}, got {letter}"

    def test_ignored_issues_not_counted(self):
        issues = [Issue(id="t-001", level="error", category="architecture",
                        title="test", files=["a.py"], status="ignored")]
        _, score = calculate_score(issues)
        assert score == 100


# --- R5: Checks skip when not applicable ---

class TestR5SkipChecks:
    def test_skipped_checks_in_summary(self, scanner, tmp_project):
        report = scanner.scan(tmp_project)
        skipped = report.summary.get("skipped_checks", [])
        # tmp_project hat nur .py, also css_quality und js_quality sollten skippen
        assert "css_quality" in skipped
        assert "js_quality" in skipped


# --- R6: IGNORE_DIRS ---

class TestR6IgnoreDirs:
    def test_no_issues_from_ignored_dirs(self, scanner, project_dashboard_path):
        report = load_report(project_dashboard_path)
        if not report:
            pytest.skip("Kein Report fuer project_dashboard vorhanden")
        for issue in report.issues:
            for f in issue.files:
                for d in IGNORE_DIRS:
                    assert f"/{d}/" not in f, f"Issue {issue.id} referenziert Datei in {d}: {f}"


# --- R7: Issue-Struktur ---

class TestR7IssueStructure:
    def test_issues_have_required_fields(self, scanner, project_dashboard_path):
        report = load_report(project_dashboard_path)
        if not report:
            pytest.skip("Kein Report vorhanden")
        for issue in report.issues:
            assert issue.id, f"Issue ohne id"
            assert issue.level in ("error", "warning", "info"), f"Ungueltig: {issue.level}"
            assert issue.category, f"Issue {issue.id} ohne category"
            assert issue.title, f"Issue {issue.id} ohne title"
            assert isinstance(issue.files, list), f"Issue {issue.id}: files ist keine Liste"

    def test_issue_id_format(self):
        assert issue_id("duplication", 1) == "dup-001"
        assert issue_id("complexity", 42) == "cplx-042"
        assert issue_id("file_size", 3) == "size-003"


# --- R8: fix_prompt ---

class TestR8FixPrompt:
    def test_issues_have_fix_prompt(self, scanner, project_dashboard_path):
        report = load_report(project_dashboard_path)
        if not report:
            pytest.skip("Kein Report vorhanden")
        empty = [i.id for i in report.issues if not i.fix_prompt.strip()]
        assert len(empty) == 0, f"{len(empty)} Issues ohne fix_prompt: {empty[:5]}"


# --- R9: History ---

class TestR9History:
    def test_history_appended_on_save(self, tmp_project):
        report = QualityReport(project="test", scanned_at="2026-01-01T00:00:00Z",
                               score="A", score_numeric=100, summary={}, issues=[])
        save_report(tmp_project, report)
        loaded = load_report(tmp_project)
        assert len(loaded.history) == 1
        assert "scanned_at" in loaded.history[0]
        assert "total_issues" in loaded.history[0]

    def test_history_preserved_across_saves(self, tmp_project):
        for i in range(3):
            report = QualityReport(project="test", scanned_at=f"2026-01-0{i+1}T00:00:00Z",
                                   score="A", score_numeric=100 - i, summary={}, issues=[])
            prev = load_report(tmp_project)
            if prev:
                report.history = prev.history
            save_report(tmp_project, report)
        loaded = load_report(tmp_project)
        assert len(loaded.history) == 3


# --- R12: Module unter 500 Zeilen ---

class TestR12ModuleSize:
    def test_all_modules_under_500_lines(self):
        auto_coder_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auto_coder")
        for root, _, files in os.walk(auto_coder_dir):
            if "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path) as fh:
                        lines = len(fh.readlines())
                    assert lines <= 500, f"{path} hat {lines} Zeilen (Limit: 500)"
