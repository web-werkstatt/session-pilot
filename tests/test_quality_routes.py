import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _write_quality_project(base_dir, project_name, *, file_name, modified_at):
    project_dir = os.path.join(base_dir, project_name)
    os.makedirs(os.path.join(project_dir, ".quality"), exist_ok=True)

    report_path = os.path.join(project_dir, ".quality", "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "score": "B",
            "score_numeric": 82,
            "summary": {"errors": 1, "warnings": 2, "info": 0, "total_issues": 3},
            "scanned_at": "2026-04-03T00:00:00+00:00",
        }, f)

    code_path = os.path.join(project_dir, file_name)
    with open(code_path, "w", encoding="utf-8") as f:
        f.write("print('ok')\n")

    ts = modified_at.timestamp()
    os.utime(code_path, (ts, ts))
    return project_dir


def test_quality_projects_only_returns_recently_changed_projects(client, monkeypatch, tmp_path):
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=15)
    stale = now - timedelta(days=140)

    _write_quality_project(str(tmp_path), "recent_project", file_name="app.py", modified_at=recent)
    _write_quality_project(str(tmp_path), "stale_project", file_name="app.py", modified_at=stale)

    monkeypatch.setattr("routes.quality_routes.PROJECTS_DIR", str(tmp_path))

    response = client.get("/api/quality/projects")

    assert response.status_code == 200
    data = response.get_json()
    assert [item["name"] for item in data] == ["recent_project"]


def test_quality_projects_ignores_recent_report_when_project_files_are_stale(client, monkeypatch, tmp_path):
    stale = datetime.now(timezone.utc) - timedelta(days=140)
    project_dir = _write_quality_project(str(tmp_path), "report_only_recent", file_name="main.py", modified_at=stale)

    report_path = os.path.join(project_dir, ".quality", "report.json")
    now_ts = datetime.now(timezone.utc).timestamp()
    os.utime(report_path, (now_ts, now_ts))

    monkeypatch.setattr("routes.quality_routes.PROJECTS_DIR", str(tmp_path))

    response = client.get("/api/quality/projects")

    assert response.status_code == 200
    assert response.get_json() == []
