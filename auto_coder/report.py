"""Datenklassen und Persistenz fuer Quality Reports."""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

from auto_coder.config import (
    LEVELS,
    MAX_HISTORY_ENTRIES,
    QUALITY_DIR,
    REPORT_FILE,
    SCORE_WEIGHTS,
)


@dataclass
class Issue:
    id: str
    level: str  # error, warning, info
    category: str
    title: str
    files: list[str] = field(default_factory=list)
    fix_prompt: str = ""
    status: str = "open"  # open, fixed, ignored
    fixed_at: Optional[str] = None


@dataclass
class TestResult:
    status: str = "skipped"  # passed, failed, skipped
    coverage: Optional[float] = None
    failed_suites: list[str] = field(default_factory=list)


@dataclass
class QualityReport:
    project: str
    scanned_at: str = ""
    score: str = "F"
    score_numeric: int = 0
    summary: dict = field(default_factory=dict)
    tests: TestResult = field(default_factory=TestResult)
    issues: list[Issue] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


def issue_id(category: str, index: int) -> str:
    """Generiert Issue-ID wie 'dup-001', 'complexity-002'."""
    prefix_map = {
        "duplication": "dup",
        "complexity": "cplx",
        "file_size": "size",
        "css_tokens": "css",
        "css_undefined": "cssu",
        "architecture": "arch",
        "test_failure": "test",
        "js_quality": "js",
    }
    prefix = prefix_map.get(category, category[:4])
    return f"{prefix}-{index:03d}"


def calculate_score(issues: list[Issue]) -> tuple[str, int]:
    """Berechnet Score aus Issues und Weights. Startet bei 100."""
    score = 100
    for issue in issues:
        if issue.status == "ignored":
            continue
        weight = SCORE_WEIGHTS.get(issue.category, -1)
        if issue.level == "error":
            score += weight * 2
        else:
            score += weight
    score = max(0, min(100, score))
    letter = "F"
    for grade, threshold in LEVELS:
        if score >= threshold:
            letter = grade
            break
    return letter, score


def load_report(project_path: str) -> Optional[QualityReport]:
    """Laedt .quality/report.json falls vorhanden."""
    path = os.path.join(project_path, QUALITY_DIR, REPORT_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        issues = [Issue(**i) for i in data.get("issues", [])]
        tests = TestResult(**data.get("tests", {}))
        return QualityReport(
            project=data["project"],
            scanned_at=data.get("scanned_at", ""),
            score=data.get("score", "F"),
            score_numeric=data.get("score_numeric", 0),
            summary=data.get("summary", {}),
            tests=tests,
            issues=issues,
            history=data.get("history", []),
        )
    except (json.JSONDecodeError, KeyError):
        return None


def save_report(project_path: str, report: QualityReport) -> str:
    """Schreibt .quality/report.json, fuegt History-Eintrag hinzu."""
    quality_dir = os.path.join(project_path, QUALITY_DIR)
    os.makedirs(quality_dir, exist_ok=True)

    report.history.append({
        "date": report.scanned_at,
        "score": report.score,
        "score_numeric": report.score_numeric,
        "issues_count": len([i for i in report.issues if i.status == "open"]),
    })
    if len(report.history) > MAX_HISTORY_ENTRIES:
        report.history = report.history[-MAX_HISTORY_ENTRIES:]

    path = os.path.join(quality_dir, REPORT_FILE)
    with open(path, "w") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    return path
