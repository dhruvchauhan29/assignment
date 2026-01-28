"""
Tests for approval gates and regeneration workflow.
"""
import pytest
from app.database import Project, Run, RunStatus


def test_approval_with_regenerate_action(client, auth_token, db, test_user):
    """Test approval with regenerate action."""
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
        status=RunStatus.RUNNING,
        current_stage="epics"
    )
    db.add(run)
    db.commit()
    
    # Submit approval with regenerate action
    response = client.post(
        f"/api/runs/{run.id}/approvals/epics",
        json={
            "approved": False,
            "feedback": "Please add more detail to Epic 2",
            "action": "regenerate"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is False
    assert data["action"] == "regenerate"
    assert "Epic 2" in data["feedback"]


def test_approval_with_proceed_action(client, auth_token, db, test_user):
    """Test approval with proceed action."""
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
        status=RunStatus.RUNNING,
        current_stage="epics"
    )
    db.add(run)
    db.commit()
    
    # Submit approval with proceed action
    response = client.post(
        f"/api/runs/{run.id}/approvals/epics",
        json={
            "approved": True,
            "feedback": "Looks good",
            "action": "proceed"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is True
    assert data["action"] == "proceed"


def test_approval_with_reject_action(client, auth_token, db, test_user):
    """Test approval with reject action (no regeneration)."""
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
        status=RunStatus.RUNNING,
        current_stage="stories"
    )
    db.add(run)
    db.commit()
    
    # Submit approval with reject action
    response = client.post(
        f"/api/runs/{run.id}/approvals/stories",
        json={
            "approved": False,
            "feedback": "Does not meet requirements",
            "action": "reject"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is False
    assert data["action"] == "reject"


def test_approval_invalid_stage(client, auth_token, db, test_user):
    """Test approval with invalid stage returns 400."""
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
        status=RunStatus.RUNNING,
        current_stage="epics"
    )
    db.add(run)
    db.commit()
    
    # Submit approval with invalid stage
    response = client.post(
        f"/api/runs/{run.id}/approvals/invalid_stage",
        json={
            "approved": True,
            "action": "proceed"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 400
    assert "Invalid stage" in response.json()["detail"]


def test_approval_update_existing(client, auth_token, db, test_user):
    """Test that submitting approval twice updates the existing one."""
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
        status=RunStatus.RUNNING,
        current_stage="specs"
    )
    db.add(run)
    db.commit()
    
    # First approval
    response1 = client.post(
        f"/api/runs/{run.id}/approvals/specs",
        json={
            "approved": False,
            "feedback": "Needs work",
            "action": "regenerate"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    approval_id = response1.json()["id"]
    
    # Second approval (should update)
    response2 = client.post(
        f"/api/runs/{run.id}/approvals/specs",
        json={
            "approved": True,
            "feedback": "Now it's good",
            "action": "proceed"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response2.status_code == 200
    data = response2.json()
    assert data["id"] == approval_id  # Same approval updated
    assert data["approved"] is True
    assert data["action"] == "proceed"
    assert "good" in data["feedback"]


def test_get_approvals_list(client, auth_token, db, test_user):
    """Test getting list of all approvals for a run."""
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
        status=RunStatus.RUNNING,
        current_stage="stories"
    )
    db.add(run)
    db.commit()
    
    # Create approvals for different stages
    client.post(
        f"/api/runs/{run.id}/approvals/epics",
        json={"approved": True, "action": "proceed"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    client.post(
        f"/api/runs/{run.id}/approvals/stories",
        json={"approved": False, "feedback": "Needs revision", "action": "regenerate"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Get all approvals
    response = client.get(
        f"/api/runs/{run.id}/approvals",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    approvals = response.json()
    assert len(approvals) == 2
    
    # Verify we have both stages
    stages = [a["stage"] for a in approvals]
    assert "epics" in stages
    assert "stories" in stages
