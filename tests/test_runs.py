"""
Tests for run endpoints.
"""
import pytest
from app.database import Project, Run, Artifact, ArtifactType


def test_create_run(client, auth_token, db, test_user):
    """Test creating a run."""
    # Create a project first
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.post(
        "/api/runs",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"project_id": project.id}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project.id
    assert data["status"] == "pending"


def test_create_run_invalid_project(client, auth_token):
    """Test creating a run with invalid project."""
    response = client.post(
        "/api/runs",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"project_id": 9999}
    )
    assert response.status_code == 404


def test_get_run(client, auth_token, db, test_user):
    """Test getting a run."""
    # Create project and run
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    
    run = Run(project_id=project.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    
    response = client.get(
        f"/api/runs/{run.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run.id
    assert data["project_id"] == project.id


def test_start_run(client, auth_token, db, test_user):
    """Test starting a run."""
    # Create project and run
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    
    run = Run(project_id=project.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    
    response = client.post(
        f"/api/runs/{run.id}/start",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    
    # Verify run status updated
    db.refresh(run)
    assert run.status.value == "running"


def test_pause_run(client, auth_token, db, test_user):
    """Test pausing a run."""
    # Create project and run
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    
    run = Run(project_id=project.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    
    response = client.post(
        f"/api/runs/{run.id}/pause",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"


def test_submit_approval(client, auth_token, db, test_user):
    """Test submitting an approval."""
    # Create project and run
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    
    run = Run(project_id=project.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    
    response = client.post(
        f"/api/runs/{run.id}/approvals/epics",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "approved": True,
            "feedback": "Looks good"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "epics"
    assert data["approved"] is True
    assert data["feedback"] == "Looks good"


def test_get_run_status(client, auth_token, db, test_user):
    """Test getting run status."""
    # Create project and run
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    
    run = Run(
        project_id=project.id,
        status="running",
        current_stage="epics"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    response = client.get(
        f"/api/runs/{run.id}/status",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run.id
    assert data["status"] == "running"
    assert data["current_stage"] == "epics"


def test_get_run_epics(client, auth_token, db, test_user):
    """Test getting epic artifacts for a run."""
    # Create project and run
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    
    run = Run(project_id=project.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Create epic artifacts
    epic1 = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.EPICS,
        name="epics.md",
        content="# Epic 1\n\nDescription"
    )
    epic2 = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.EPICS,
        name="epics_v2.md",
        content="# Epic 2\n\nDescription"
    )
    db.add_all([epic1, epic2])
    db.commit()
    
    response = client.get(
        f"/api/runs/{run.id}/epics",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(artifact["artifact_type"] == "epics" for artifact in data)
    assert data[0]["run_id"] == run.id


def test_get_run_stories(client, auth_token, db, test_user):
    """Test getting story artifacts for a run."""
    # Create project and run
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    
    run = Run(project_id=project.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Create story artifacts
    story1 = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.STORIES,
        name="stories.md",
        content="# Story 1\n\nAs a user..."
    )
    story2 = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.STORIES,
        name="stories_v2.md",
        content="# Story 2\n\nAs a user..."
    )
    # Add a different artifact type to ensure filtering works
    research = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.RESEARCH,
        name="research.md",
        content="Research content"
    )
    db.add_all([story1, story2, research])
    db.commit()
    
    response = client.get(
        f"/api/runs/{run.id}/stories",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(artifact["artifact_type"] == "stories" for artifact in data)
    assert data[0]["run_id"] == run.id


def test_get_run_status_not_found(client, auth_token):
    """Test getting status for non-existent run."""
    response = client.get(
        "/api/runs/9999/status",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404


def test_get_run_epics_not_found(client, auth_token):
    """Test getting epics for non-existent run."""
    response = client.get(
        "/api/runs/9999/epics",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404


def test_get_run_stories_not_found(client, auth_token):
    """Test getting stories for non-existent run."""
    response = client.get(
        "/api/runs/9999/stories",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404
