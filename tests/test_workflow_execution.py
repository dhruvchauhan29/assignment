"""
Test workflow execution with mocked agents.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.database import Project, Run, RunStatus, Artifact, ArtifactType, Approval
from app.orchestrator.workflow import Orchestrator


@pytest.mark.asyncio
async def test_workflow_creates_research_artifact(db, test_user):
    """Test that workflow creates research artifact and advances."""
    # Create project
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create run
    run = Run(
        project_id=project.id,
        status=RunStatus.PENDING
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Mock the research agent to return success
    with patch('app.orchestrator.workflow.ResearchAgent') as MockResearchAgent:
        mock_research_instance = AsyncMock()
        mock_research_instance.execute = AsyncMock(return_value={
            "success": True,
            "content": "# Research Report\n\nSample research content",
            "metadata": {"urls_consulted": []}
        })
        MockResearchAgent.return_value = mock_research_instance
        
        # Mock the epic agent
        with patch('app.orchestrator.workflow.EpicAgent') as MockEpicAgent:
            mock_epic_instance = AsyncMock()
            mock_epic_instance.execute = AsyncMock(return_value={
                "success": True,
                "content": "# Epics\n\n## Epic EP-001: Core Features",
                "metadata": {"epic_count": 1}
            })
            MockEpicAgent.return_value = mock_epic_instance
            
            # Create orchestrator and execute
            orchestrator = Orchestrator()
            await orchestrator.execute_run(run.id, project.product_request)
    
    # Refresh run from DB
    db.refresh(run)
    
    # Verify artifacts were created
    research_artifacts = db.query(Artifact).filter(
        Artifact.run_id == run.id,
        Artifact.artifact_type == ArtifactType.RESEARCH
    ).all()
    assert len(research_artifacts) > 0, "Research artifact should be created"
    
    epic_artifacts = db.query(Artifact).filter(
        Artifact.run_id == run.id,
        Artifact.artifact_type == ArtifactType.EPICS
    ).all()
    assert len(epic_artifacts) > 0, "Epic artifact should be created"
    
    # Verify run status and stage
    assert run.current_stage in ["waiting_epic_approval", "epics"], \
        f"Run should be at epic approval stage, but is at {run.current_stage}"
    assert run.status == RunStatus.PAUSED, \
        f"Run should be PAUSED waiting for approval, but status is {run.status}"
    
    # Verify approval was created
    approvals = db.query(Approval).filter(
        Approval.run_id == run.id,
        Approval.stage == "epics"
    ).all()
    assert len(approvals) > 0, "Epic approval gate should be created"


@pytest.mark.asyncio
async def test_workflow_handles_agent_failure_with_fallback(db, test_user):
    """Test that workflow creates fallback artifacts when agent fails."""
    # Create project
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create run
    run = Run(
        project_id=project.id,
        status=RunStatus.PENDING
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Mock the research agent to return failure
    with patch('app.orchestrator.workflow.ResearchAgent') as MockResearchAgent:
        mock_research_instance = AsyncMock()
        mock_research_instance.execute = AsyncMock(return_value={
            "success": False,
            "error": "API rate limit exceeded"
        })
        MockResearchAgent.return_value = mock_research_instance
        
        # Mock the epic agent to also fail
        with patch('app.orchestrator.workflow.EpicAgent') as MockEpicAgent:
            mock_epic_instance = AsyncMock()
            mock_epic_instance.execute = AsyncMock(return_value={
                "success": False,
                "error": "API rate limit exceeded"
            })
            MockEpicAgent.return_value = mock_epic_instance
            
            # Create orchestrator and execute
            orchestrator = Orchestrator()
            await orchestrator.execute_run(run.id, project.product_request)
    
    # Refresh run from DB
    db.refresh(run)
    
    # Verify fallback artifacts were created
    research_artifacts = db.query(Artifact).filter(
        Artifact.run_id == run.id,
        Artifact.artifact_type == ArtifactType.RESEARCH
    ).all()
    assert len(research_artifacts) > 0, "Fallback research artifact should be created"
    
    # Check that the artifact has fallback metadata
    research_artifact = research_artifacts[0]
    assert research_artifact.artifact_metadata is not None
    assert research_artifact.artifact_metadata.get("fallback") == True
    
    epic_artifacts = db.query(Artifact).filter(
        Artifact.run_id == run.id,
        Artifact.artifact_type == ArtifactType.EPICS
    ).all()
    assert len(epic_artifacts) > 0, "Fallback epic artifact should be created"
    
    # Verify run didn't fail completely
    assert run.status in [RunStatus.PAUSED, RunStatus.RUNNING], \
        f"Run should still be active, but status is {run.status}"


@pytest.mark.asyncio
async def test_workflow_transitions_through_stages(db, test_user):
    """Test that workflow properly transitions through stages after approvals."""
    # Create project
    project = Project(
        name="Test Project",
        product_request="Build a simple todo app",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create run
    run = Run(
        project_id=project.id,
        status=RunStatus.PENDING
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Mock all agents to succeed
    with patch('app.orchestrator.workflow.ResearchAgent') as MockResearchAgent, \
         patch('app.orchestrator.workflow.EpicAgent') as MockEpicAgent, \
         patch('app.orchestrator.workflow.StoryAgent') as MockStoryAgent:
        
        mock_research = AsyncMock()
        mock_research.execute = AsyncMock(return_value={
            "success": True,
            "content": "# Research",
            "metadata": {}
        })
        MockResearchAgent.return_value = mock_research
        
        mock_epic = AsyncMock()
        mock_epic.execute = AsyncMock(return_value={
            "success": True,
            "content": "# Epics",
            "metadata": {}
        })
        MockEpicAgent.return_value = mock_epic
        
        mock_story = AsyncMock()
        mock_story.execute = AsyncMock(return_value={
            "success": True,
            "content": "# Stories",
            "metadata": {}
        })
        MockStoryAgent.return_value = mock_story
        
        # Execute initial workflow
        orchestrator = Orchestrator()
        await orchestrator.execute_run(run.id, project.product_request)
        
        db.refresh(run)
        assert run.current_stage == "waiting_epic_approval"
        
        # Approve epics and continue
        approval = Approval(
            run_id=run.id,
            stage="epics",
            approved=True,
            action="proceed"
        )
        db.add(approval)
        db.commit()
        
        # Continue workflow
        await orchestrator.continue_run(run.id, "epics")
        
        db.refresh(run)
        # Should now be at waiting_story_approval
        assert run.current_stage == "waiting_story_approval"
        
        # Verify stories artifact was created
        story_artifacts = db.query(Artifact).filter(
            Artifact.run_id == run.id,
            Artifact.artifact_type == ArtifactType.STORIES
        ).all()
        assert len(story_artifacts) > 0, "Stories artifact should be created after epic approval"
