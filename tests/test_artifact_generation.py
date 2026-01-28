"""
Test artifact generation during run execution.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.database import Artifact, ArtifactType, Project, Run, RunStatus


def test_get_epics_endpoint(client, auth_token, db, test_user):
    """Test that epics endpoint returns artifacts."""
    # Create a project and run with artifacts
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()

    run = Run(project_id=project.id)
    db.add(run)
    db.commit()

    # Create an epic artifact
    artifact = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.EPICS,
        name="epics.md",
        content="# Epic 1\n\nTest epic content"
    )
    db.add(artifact)
    db.commit()

    # Get epics
    response = client.get(
        f"/api/runs/{run.id}/epics",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    epics = response.json()
    assert len(epics) == 1
    assert epics[0]["artifact_type"] == "epics"


def test_get_stories_endpoint(client, auth_token, db, test_user):
    """Test that stories endpoint returns artifacts."""
    # Create a project and run with artifacts
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()

    run = Run(project_id=project.id)
    db.add(run)
    db.commit()

    # Create a story artifact
    artifact = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.STORIES,
        name="stories.md",
        content="# Story 1\n\nTest story content"
    )
    db.add(artifact)
    db.commit()

    # Get stories
    response = client.get(
        f"/api/runs/{run.id}/stories",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    stories = response.json()
    assert len(stories) == 1
    assert stories[0]["artifact_type"] == "stories"


def test_get_artifacts_endpoint(client, auth_token, db, test_user):
    """Test that artifacts endpoint returns all artifacts."""
    # Create a project and run with multiple artifacts
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()

    run = Run(project_id=project.id)
    db.add(run)
    db.commit()

    # Create multiple artifacts
    artifacts_data = [
        (ArtifactType.RESEARCH, "research.md", "Research content"),
        (ArtifactType.EPICS, "epics.md", "Epic content"),
        (ArtifactType.STORIES, "stories.md", "Story content"),
    ]

    for artifact_type, name, content in artifacts_data:
        artifact = Artifact(
            run_id=run.id,
            artifact_type=artifact_type,
            name=name,
            content=content
        )
        db.add(artifact)
    db.commit()

    # Get all artifacts
    response = client.get(
        f"/api/runs/{run.id}/artifacts",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    artifacts = response.json()
    assert len(artifacts) == 3


def test_epics_empty_when_no_artifacts(client, auth_token, db, test_user):
    """Test that epics endpoint returns empty list when no artifacts exist."""
    # Create a project and run without artifacts
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()

    run = Run(project_id=project.id)
    db.add(run)
    db.commit()

    # Get epics (should be empty)
    response = client.get(
        f"/api/runs/{run.id}/epics",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    epics = response.json()
    assert len(epics) == 0


def test_stories_empty_when_no_artifacts(client, auth_token, db, test_user):
    """Test that stories endpoint returns empty list when no artifacts exist."""
    # Create a project and run without artifacts
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()

    run = Run(project_id=project.id)
    db.add(run)
    db.commit()

    # Get stories (should be empty)
    response = client.get(
        f"/api/runs/{run.id}/stories",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    stories = response.json()
    assert len(stories) == 0
