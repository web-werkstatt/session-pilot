"""Scanner-Orchestrator: Fuehrt alle Checks aus und erstellt Report."""

import os
from datetime import datetime, timezone

from auto_coder.checks.architecture import ArchitectureCheck
from auto_coder.checks.complexity import ComplexityCheck
from auto_coder.checks.css_quality import CSSQualityCheck
from auto_coder.checks.duplication import DuplicationCheck
from auto_coder.checks.file_sizes import FileSizeCheck
from auto_coder.checks.js_quality import JSQualityCheck
from auto_coder.checks.tests import TestCheck
from auto_coder.config import IGNORE_DIRS, PROJECTS_ROOT
from auto_coder.report import (
    QualityReport,
    TestResult,
    calculate_score,
    save_report,
)


class ProjectQualityScanner:
    """Orchestriert alle Quality Checks fuer ein oder mehrere Projekte."""

    def __init__(self):
        self.checks = [
            FileSizeCheck(),
            DuplicationCheck(),
            ComplexityCheck(),
            CSSQualityCheck(),
            JSQualityCheck(),
            ArchitectureCheck(),
            TestCheck(),
        ]

    def scan(self, project_path: str) -> QualityReport:
        """Scannt ein Projekt und erzeugt Quality Report."""
        project_path = os.path.abspath(project_path)
        project_name = os.path.basename(project_path)

        issues = []
        skipped = []
        for check in self.checks:
            if check.is_applicable(project_path):
                found = check.run(project_path)
                issues.extend(found)
            else:
                skipped.append(check.name)

        score_letter, score_num = calculate_score(issues)
        now = datetime.now(timezone.utc).isoformat()

        errors = sum(1 for i in issues if i.level == "error")
        warnings = sum(1 for i in issues if i.level == "warning")
        infos = sum(1 for i in issues if i.level == "info")

        report = QualityReport(
            project=project_name,
            scanned_at=now,
            score=score_letter,
            score_numeric=score_num,
            summary={
                "total_issues": len(issues),
                "errors": errors,
                "warnings": warnings,
                "info": infos,
                "skipped_checks": skipped,
            },
            tests=TestResult(),
            issues=issues,
            history=[],
        )

        # Vorherige History laden
        from auto_coder.report import load_report
        prev = load_report(project_path)
        if prev:
            report.history = prev.history

        save_report(project_path, report)
        return report

    def scan_all(self) -> list[QualityReport]:
        """Scannt alle Projekte unter PROJECTS_ROOT."""
        reports = []
        for project_path in self._discover_projects():
            try:
                reports.append(self.scan(project_path))
            except Exception as e:
                print(f"  Fehler bei {project_path}: {e}")
        return reports

    @staticmethod
    def _discover_projects() -> list[str]:
        """Findet alle Projekte unter PROJECTS_ROOT."""
        projects = []
        if not os.path.isdir(PROJECTS_ROOT):
            return projects
        for entry in sorted(os.listdir(PROJECTS_ROOT)):
            path = os.path.join(PROJECTS_ROOT, entry)
            if not os.path.isdir(path):
                continue
            if entry in IGNORE_DIRS or entry.startswith("."):
                continue
            # Projekt erkennen: hat .git, package.json, pyproject.toml, oder app.py
            indicators = [".git", "package.json", "pyproject.toml", "app.py",
                          "setup.py", "Cargo.toml", "go.mod", "CLAUDE.md"]
            if any(os.path.exists(os.path.join(path, ind)) for ind in indicators):
                projects.append(path)
        return projects
