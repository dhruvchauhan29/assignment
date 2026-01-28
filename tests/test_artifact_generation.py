"""
Test artifact generation during run execution.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.database import Artifact, ArtifactType, Project, Run, RunStatus


@pytest.mark.asyncio
async def test_run_generates_research_artifact(client, auth_token, db, test_user):
    """Test that starting a run generates research artifact."""
    # Create a project
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create a run
    run = Run(project_id=project.id, status=RunStatus.PENDING)
    db.add(run)
    db.commit()
    db.refresh(run)

    # Mock the research agent
    mock_research_result = {
        "success": True,
        "content": "# Research Report\n\nMocked research content",
        "metadata": {
            "urls_consulted": [],
            "total_urls": 0
        }
    }

    # Mock the epic agent
    mock_epic_result = {
        "success": True,
        "content": "# Epic Plan\n\nMocked epic content",
        "metadata": {}
    }

    with patch('app.agents.research_agent.ResearchAgent.execute', new_callable=AsyncMock) as mock_research, \
         patch('app.agents.epic_agent.EpicAgent.execute', new_callable=AsyncMock) as mock_epic:
        
        mock_research.return_value = mock_research_result
        mock_epic.return_value = mock_epic_result

        # Start the run
        response = client.post(
            f"/api/runs/{run.id}/start",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

        # Give workflow time to execute (in real scenario, would poll or use SSE)
        import asyncio
        await asyncio.sleep(2)

        # Check that research artifact was created
        artifacts = db.query(Artifact).filter(
            Artifact.run_id == run.id,
            Artifact.artifact_type == ArtifactType.RESEARCH
        ).all()

        assert len(artifacts) > 0, "Research artifact should be created"
        assert artifacts[0].content == mock_research_result["content"]

        # Check that epic artifact was created
        epic_artifacts = db.query(Artifact).filter(
            Artifact.run_id == run.id,
            Artifact.artifact_type == ArtifactType.EPICS
        ).all()

        assert len(epic_artifacts) > 0, "Epic artifact should be created"


@pytest.mark.asyncio
async def test_run_status_updates_during_execution(client, auth_token, db, test_user):
    """Test that run status updates correctly during execution."""
    # Create a project
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create a run
    run = Run(project_id=project.id, status=RunStatus.PENDING)
    db.add(run)
    db.commit()
    db.refresh(run)

    # Mock the agents
    with patch('app.agents.research_agent.ResearchAgent.execute', new_callable=AsyncMock) as mock_research, \
         patch('app.agents.epic_agent.EpicAgent.execute', new_callable=AsyncMock) as mock_epic:
        
        mock_research.return_value = {
            "success": True,
            "content": "# Research Report\n\nMocked research content",
            "metadata": {}
        }
        mock_epic.return_value = {
            "success": True,
            "content": "# Epic Plan\n\nMocked epic content",
            "metadata": {}
        }

        # Start the run
        response = client.post(
            f"/api/runs/{run.id}/start",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

        # Check initial status
        db.refresh(run)
        assert run.status == RunStatus.RUNNING

        # Give workflow time to execute
        import asyncio
        await asyncio.sleep(2)

        # Check status endpoint
        response = client.get(
            f"/api/runs/{run.id}/status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] in ["running", "pending", "paused"]


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
