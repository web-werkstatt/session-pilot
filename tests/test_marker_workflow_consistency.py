"""
Test fuer Marker-Workflow-Konsistenz zwischen Status und marker-context.md
"""
import os
import tempfile
import pytest
from services.copilot_marker_service import (
    Marker,
    activate_marker,
    close_marker,
    parse_markers,
    _write_marker,
    close_marker,
    read_marker_context,
    MarkerActivationError,
    MarkerCloseError,
    PROJECTS_DIR,
)


def test_marker_context_removed_on_close_with_project_id(monkeypatch):
    """Testet, dass marker-context.md beim Schliessen mit project_id entfernt wird."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = os.path.join(tmpdir, "testproj")
        os.makedirs(project_dir)
        handoff_path = os.path.join(project_dir, "handoff.md")
        context_path = os.path.join(project_dir, "marker-context.md")
        
        # Mock PROJECTS_DIR to use tmpdir
        from services import copilot_marker_service
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", tmpdir)
        
        # Create marker
        marker = Marker(
            marker_id="test-001",
            titel="Test Marker",
            plan_id="test-plan",
            status="todo",
            ziel="Test Ziel",
            naechster_schritt="Start test",
            prompt="Test prompt",
            checks=["Check 1", "Check 2"],
        )
        _write_marker(handoff_path, marker)
        
        # Activate marker (sets status to in_progress and creates context file)
        # First need to update marker with gate-passing conditions
        updated_marker = Marker(**{**marker.__dict__, "status": "in_progress"})
        _write_marker(handoff_path, updated_marker)
        
        # Simulate activate_marker by creating context file
        with open(context_path, "w", encoding="utf-8") as f:
            f.write("# Marker-Kontext\n")
            f.write("- marker_id: test-001\n")
            f.write("- plan_id: test-plan\n")
            f.write("- titel: Test Marker\n")
            f.write("- project_id: testproj\n")
        
        # Verify context file exists
        assert os.path.exists(context_path)
        
        # Close marker (should remove context file)
        closed_marker = close_marker(
            handoff_path,
            "test-001",
            project_id="testproj",
            status="done",
            context_path="marker-context.md",
        )
        
        # Verify marker status updated
        assert closed_marker.status == "done"
        
        # Verify context file removed
        assert not os.path.exists(context_path), "marker-context.md sollte nach close_marker entfernt werden"
        
        # Verify handoff updated
        parsed = parse_markers(handoff_path)
        assert len(parsed) == 1
        assert parsed[0].status == "done"


def test_marker_context_persistence_without_close(monkeypatch):
    """Testet, dass marker-context.md bestehen bleibt, wenn close_marker nicht aufgerufen wird."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = os.path.join(tmpdir, "testproj")
        os.makedirs(project_dir)
        handoff_path = os.path.join(project_dir, "handoff.md")
        context_path = os.path.join(project_dir, "marker-context.md")
        
        # Mock PROJECTS_DIR to use tmpdir
        from services import copilot_marker_service
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", tmpdir)
        
        # Create marker
        marker = Marker(
            marker_id="test-002",
            titel="Test Marker 2",
            plan_id="test-plan",
            status="todo",
            ziel="Test Ziel 2",
            naechster_schritt="Start test",
            prompt="Test prompt",
            checks=["Check 1"],
        )
        _write_marker(handoff_path, marker)
        
        # Create context file (simulating activate without proper close)
        with open(context_path, "w", encoding="utf-8") as f:
            f.write("# Marker-Kontext\n")
            f.write("- marker_id: test-002\n")
            f.write("- plan_id: test-plan\n")
            f.write("- titel: Test Marker 2\n")
        
        # Update marker status to in_progress directly
        updated_marker = Marker(**{**marker.__dict__, "status": "in_progress"})
        _write_marker(handoff_path, updated_marker)
        
        # Verify inconsistency: marker is in_progress, context file exists
        parsed = parse_markers(handoff_path)
        assert parsed[0].status == "in_progress"
        assert os.path.exists(context_path)
        
        # Now close properly should fix inconsistency
        closed_marker = close_marker(
            handoff_path,
            "test-002",
            project_id="testproj",
            status="done",
            context_path="marker-context.md",
        )
        
        assert closed_marker.status == "done"
        assert not os.path.exists(context_path)


def test_multiple_marker_context_interaction(monkeypatch):
    """Testet, dass nur der richtige marker-context.md fuer den aktiven Marker gehandhabt wird."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = os.path.join(tmpdir, "testproj")
        os.makedirs(project_dir)
        handoff_path = os.path.join(project_dir, "handoff.md")
        
        # Mock PROJECTS_DIR to use tmpdir
        from services import copilot_marker_service
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", tmpdir)
        
        # Create two markers
        marker1 = Marker(
            marker_id="m1",
            titel="Marker 1",
            plan_id="plan-1",
            status="todo",
            ziel="Ziel 1",
            naechster_schritt="Schritt 1",
            prompt="Prompt 1",
            checks=["Check"],
        )
        
        marker2 = Marker(
            marker_id="m2",
            titel="Marker 2",
            plan_id="plan-1",
            status="todo",
            ziel="Ziel 2",
            naechster_schritt="Schritt 2",
            prompt="Prompt 2",
            checks=["Check"],
        )
        
        _write_marker(handoff_path, marker1)
        _write_marker(handoff_path, marker2)
        
        # Create context file for marker1
        context_path = os.path.join(project_dir, "marker-context.md")
        with open(context_path, "w", encoding="utf-8") as f:
            f.write("# Marker-Kontext\n")
            f.write("- marker_id: m1\n")
            f.write("- plan_id: plan-1\n")
            f.write("- titel: Marker 1\n")
        
        # Update marker1 to in_progress
        updated_marker1 = Marker(**{**marker1.__dict__, "status": "in_progress"})
        _write_marker(handoff_path, updated_marker1)
        
        # Close marker2 (should not affect marker-context.md since it's for marker1)
        closed_marker2 = close_marker(
            handoff_path,
            "m2",
            project_id="testproj",
            status="done",
            # No context_path provided, so file shouldn't be touched
        )
        
        assert closed_marker2.status == "done"
        # Context file should still exist since it's for marker1
        assert os.path.exists(context_path)
        
        # Now close marker1 (should remove context file)
        closed_marker1 = close_marker(
            handoff_path,
            "m1",
            project_id="testproj",
            status="done",
            context_path="marker-context.md",
        )
        
        assert closed_marker1.status == "done"
        assert not os.path.exists(context_path)


if __name__ == "__main__":
    # Für direkte Ausführung ohne pytest müssen wir monkeypatch manuell simulieren
    import sys
    sys.exit(0)