"""
Tests for artifact metadata field (SQLAlchemy reserved name fix).
"""
import pytest
from app.database import Project, Run, Artifact, ArtifactType


def test_artifact_creation_with_metadata(db, test_user):
    """Test that artifacts can be created with metadata without SQLAlchemy errors."""
    # Create a project
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create a run
    run = Run(project_id=project.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Create an artifact with metadata
    test_metadata = {
        "tokens": 1000,
        "model": "gpt-4",
        "version": "1.0"
    }
    
    artifact = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.RESEARCH,
        name="test_artifact.md",
        content="Test content",
        artifact_metadata=test_metadata
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    
    # Verify artifact was created successfully
    assert artifact.id is not None
    assert artifact.run_id == run.id
    assert artifact.artifact_type == ArtifactType.RESEARCH
    assert artifact.name == "test_artifact.md"
    assert artifact.content == "Test content"
    assert artifact.artifact_metadata == test_metadata
    assert artifact.created_at is not None


def test_artifact_creation_without_metadata(db, test_user):
    """Test that artifacts can be created without metadata."""
    # Create a project
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create a run
    run = Run(project_id=project.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Create an artifact without metadata
    artifact = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.CODE,
        name="code.py",
        content="print('hello')",
        artifact_metadata=None
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    
    # Verify artifact was created successfully
    assert artifact.id is not None
    assert artifact.artifact_metadata is None


def test_artifact_query_and_update(db, test_user):
    """Test querying and updating artifact metadata."""
    # Create a project and run
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
    
    # Create an artifact
    artifact = Artifact(
        run_id=run.id,
        artifact_type=ArtifactType.EPICS,
        name="epics.md",
        content="Epic content",
        artifact_metadata={"version": "1.0"}
    )
    db.add(artifact)
    db.commit()
    artifact_id = artifact.id
    
    # Query the artifact
    queried_artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    assert queried_artifact is not None
    assert queried_artifact.artifact_metadata == {"version": "1.0"}
    
    # Update the metadata
    queried_artifact.artifact_metadata = {"version": "2.0", "updated": True}
    db.commit()
    
    # Verify the update
    db.refresh(queried_artifact)
    assert queried_artifact.artifact_metadata == {"version": "2.0", "updated": True}


def test_multiple_artifacts_with_different_metadata(db, test_user):
    """Test creating multiple artifacts with different metadata."""
    # Create a project and run
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
    
    # Create multiple artifacts with different metadata
    artifacts_data = [
        {
            "type": ArtifactType.RESEARCH,
            "name": "research.md",
            "metadata": {"stage": "research", "tokens": 500}
        },
        {
            "type": ArtifactType.EPICS,
            "name": "epics.md",
            "metadata": {"stage": "epics", "count": 5}
        },
        {
            "type": ArtifactType.STORIES,
            "name": "stories.md",
            "metadata": {"stage": "stories", "count": 15}
        }
    ]
    
    for data in artifacts_data:
        artifact = Artifact(
            run_id=run.id,
            artifact_type=data["type"],
            name=data["name"],
            content=f"Content for {data['name']}",
            artifact_metadata=data["metadata"]
        )
        db.add(artifact)
    
    db.commit()
    
    # Query all artifacts
    all_artifacts = db.query(Artifact).filter(Artifact.run_id == run.id).all()
    assert len(all_artifacts) == 3
    
    # Verify each artifact has the correct metadata
    for artifact in all_artifacts:
        assert artifact.artifact_metadata is not None
        assert "stage" in artifact.artifact_metadata
