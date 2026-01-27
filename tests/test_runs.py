"""
Tests for run endpoints.
"""
import pytest
from app.database import Project, Run


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
