"""Tests fuer services/tool_profile_adapter_service.py (ADR-001 Prio 6)."""
import os
import tempfile

import pytest

from services.block_marker_parser import get_generated_ranges
from services.tool_profile_adapter_service import (
    TOOL_FILES,
    WRITER_SOURCE,
    apply_update,
    build_dashboard_block,
    preview_update,
    regenerate_all,
)


FIXED_TS = "2026-04-11"


@pytest.fixture
def project_dir():
    """Leeres Projektverzeichnis."""
    with tempfile.TemporaryDirectory(prefix="tool_profile_adapter_") as path:
        yield path


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def test_build_dashboard_block_is_deterministic():
    a = build_dashboard_block("demo", "claude", {"type": "service"}, updated=FIXED_TS)
    b = build_dashboard_block("demo", "claude", {"type": "service"}, updated=FIXED_TS)
    assert a == b
    assert a.startswith("<!-- DASHBOARD-GENERATED:START")
    assert f"source={WRITER_SOURCE}" in a
    assert f"updated={FIXED_TS}" in a
    assert a.rstrip("\n").endswith("<!-- DASHBOARD-GENERATED:END -->")


def test_bootstrap_on_missing_file_creates_claude_md(project_dir):
    result = apply_update(project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS)

    assert result.written is True
    assert result.mode == "bootstrap"
    assert os.path.exists(result.filepath)

    content = _read(result.filepath)
    assert "## Project Dashboard Snapshot" in content
    blocks = get_generated_ranges(result.filepath)
    assert len(blocks) == 1
    assert blocks[0].source == WRITER_SOURCE


def test_bootstrap_preserves_200_manual_lines(project_dir):
    """AK: Bestehende CLAUDE.md mit 200 manuellen Zeilen: nach Update intakt."""
    original_lines = ["# CLAUDE.md", ""]
    original_lines.extend(f"- manuelle Zeile {i}" for i in range(1, 201))
    original_content = "\n".join(original_lines) + "\n"

    target = os.path.join(project_dir, "CLAUDE.md")
    _write(target, original_content)

    result = apply_update(
        project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS
    )
    assert result.written is True
    assert result.mode == "bootstrap"

    updated_content = _read(target)
    # Jede Original-Zeile muss erhalten sein.
    for line in original_lines:
        assert line in updated_content
    # Und der DASHBOARD-GENERATED-Block ist angehaengt.
    assert "<!-- DASHBOARD-GENERATED:START" in updated_content
    assert "<!-- DASHBOARD-GENERATED:END -->" in updated_content
    assert updated_content.index("manuelle Zeile 200") < updated_content.index(
        "<!-- DASHBOARD-GENERATED:START"
    )


def test_second_regenerate_is_idempotent(project_dir):
    """AK: Zweites Regenerate erzeugt keinen Diff."""
    apply_update(project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS)
    first_content = _read(os.path.join(project_dir, "CLAUDE.md"))

    result = apply_update(project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS)
    assert result.mode == "noop"
    assert result.written is False
    assert result.diff == ""

    second_content = _read(os.path.join(project_dir, "CLAUDE.md"))
    assert first_content == second_content


def test_update_replaces_only_generated_block(project_dir):
    """AK: Nach Update bleibt manueller Text intakt, Block wird ersetzt."""
    apply_update(project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS)
    target = os.path.join(project_dir, "CLAUDE.md")

    # Manuellen Text oben drauf
    original = _read(target)
    manual_prefix = "# CLAUDE.md\n\n## Eigene Sektion\n\nManueller Text, geschuetzt.\n\n"
    _write(target, manual_prefix + original)

    # Zweiter Lauf mit neuem Timestamp -> Block muss ersetzt werden
    new_ts = "2026-05-01"
    result = apply_update(
        project_dir, "claude", "demo", {"type": "service"}, updated=new_ts
    )
    assert result.written is True
    assert result.mode == "update"

    updated = _read(target)
    assert "Manueller Text, geschuetzt." in updated
    assert "## Eigene Sektion" in updated
    assert f"updated={new_ts}" in updated
    assert f"updated={FIXED_TS}" not in updated


def test_preview_update_is_dry_run(project_dir):
    target = os.path.join(project_dir, "CLAUDE.md")
    assert not os.path.exists(target)

    result = preview_update(
        project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS
    )
    assert result.mode == "bootstrap"
    assert result.written is False
    assert not os.path.exists(target)
    assert "Project Dashboard Snapshot" in result.diff


def test_preview_diff_is_empty_when_already_up_to_date(project_dir):
    apply_update(project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS)
    result = preview_update(
        project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS
    )
    assert result.mode == "noop"
    assert result.diff == ""
    assert result.written is False


def test_regenerate_all_touches_three_files(project_dir):
    results = regenerate_all(project_dir, "demo", {"type": "service"}, updated=FIXED_TS)
    tools = {r.tool for r in results}
    assert tools == set(TOOL_FILES.keys())

    for r in results:
        assert r.written is True
        assert r.mode == "bootstrap"
        assert os.path.exists(r.filepath)


def test_regenerate_all_dry_run_writes_nothing(project_dir):
    results = regenerate_all(
        project_dir, "demo", {"type": "service"}, updated=FIXED_TS, dry_run=True
    )
    for r in results:
        assert r.written is False
        assert r.mode == "bootstrap"
        assert not os.path.exists(r.filepath)


def test_unknown_tool_is_rejected(project_dir):
    result = apply_update(project_dir, "kilo", "demo", updated=FIXED_TS)
    assert result.error is not None
    assert result.written is False
    assert result.mode == "noop"


def test_existing_foreign_generated_block_is_preserved(project_dir):
    """Fremder DASHBOARD-GENERATED Block (andere source) darf nicht beruehrt werden."""
    target = os.path.join(project_dir, "CLAUDE.md")
    foreign = (
        "# CLAUDE.md\n\n"
        "<!-- DASHBOARD-GENERATED:START source=someone_else updated=2026-03-01 -->\n"
        "## Fremd\n\nFremdblock-Inhalt\n"
        "<!-- DASHBOARD-GENERATED:END -->\n"
    )
    _write(target, foreign)

    result = apply_update(
        project_dir, "claude", "demo", {"type": "service"}, updated=FIXED_TS
    )
    assert result.written is True
    updated = _read(target)
    assert "source=someone_else" in updated
    assert "Fremdblock-Inhalt" in updated
    assert f"source={WRITER_SOURCE}" in updated
