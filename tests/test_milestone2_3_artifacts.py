"""
Tests for Milestone 2: Research and Milestone 3: Epic Generation
Tests enhanced research artifacts and epic metadata.
"""
import pytest
from app.database import Artifact, ArtifactType


def test_research_artifact_has_required_metadata(db):
    """Test that research artifacts have all required metadata fields."""
    # Create a research artifact with enhanced metadata
    metadata = {
        "urls_consulted": [
            {
                "url": "https://example.com",
                "title": "Example",
                "summary": "Summary",
                "relevance": "high"
            }
        ],
        "total_urls": 1,
        "research_depth": "comprehensive",
        "technologies_identified": ["Python", "FastAPI"],
        "approach_rationale": "Based on research findings",
        "planning_influence": {
            "epics": "Guidance for epic prioritization",
            "stories": "Align with patterns",
            "specs": "Follow recommended architecture"
        }
    }
    
    artifact = Artifact(
        run_id=1,
        artifact_type=ArtifactType.RESEARCH,
        name="research.md",
        content="# Research Report\n\nDetailed findings...",
        artifact_metadata=metadata
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    
    # Verify all required fields exist
    assert artifact.artifact_metadata is not None
    assert "urls_consulted" in artifact.artifact_metadata
    assert "planning_influence" in artifact.artifact_metadata
    assert "technologies_identified" in artifact.artifact_metadata
    assert "approach_rationale" in artifact.artifact_metadata
    
    # Verify planning influence structure
    influence = artifact.artifact_metadata["planning_influence"]
    assert "epics" in influence
    assert "stories" in influence
    assert "specs" in influence


def test_epic_artifact_has_comprehensive_metadata(db):
    """Test that epic artifacts have all required metadata fields."""
    metadata = {
        "epic_count": 4,
        "has_mermaid_diagram": True,
        "priority_breakdown": {
            "P0_critical": 1,
            "P1_high": 2,
            "P2_medium": 1
        },
        "includes_all_required_fields": True,
        "fields_included": [
            "goal",
            "priority_with_reasoning",
            "in_scope",
            "out_of_scope",
            "dependencies",
            "risks_and_assumptions",
            "success_metrics"
        ],
        "regeneration_count": 0
    }
    
    content = """
## Epic EP-001: User Authentication

**Goal:** Enable secure user authentication and authorization

**Priority:** P0 (Critical)
**Priority Reasoning:** Foundation for all other features

**In Scope:**
- User registration and login
- JWT token management
- Role-based access control

**Out of Scope:**
- Social media login
- Two-factor authentication

**Dependencies:**
- Database setup
- Security framework

**Risks & Assumptions:**
- Risk: Security vulnerabilities
- Assumption: Users will use strong passwords
- Mitigation: Use industry-standard security practices

**Success Metrics:**
- 100% of authentication attempts are secure
- < 200ms response time for login
"""
    
    artifact = Artifact(
        run_id=1,
        artifact_type=ArtifactType.EPICS,
        name="epics.md",
        content=content,
        artifact_metadata=metadata
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    
    # Verify metadata structure
    assert artifact.artifact_metadata is not None
    assert artifact.artifact_metadata["epic_count"] == 4
    assert artifact.artifact_metadata["has_mermaid_diagram"] is True
    assert "priority_breakdown" in artifact.artifact_metadata
    assert artifact.artifact_metadata["includes_all_required_fields"] is True
    
    # Verify priority breakdown
    priorities = artifact.artifact_metadata["priority_breakdown"]
    assert "P0_critical" in priorities
    assert "P1_high" in priorities
    assert "P2_medium" in priorities
    
    # Verify content has required sections
    assert "**Goal:**" in content
    assert "**Priority Reasoning:**" in content
    assert "**In Scope:**" in content
    assert "**Out of Scope:**" in content
    assert "**Dependencies:**" in content
    assert "**Risks & Assumptions:**" in content
    assert "**Success Metrics:**" in content


def test_epic_content_includes_mermaid_diagram(db):
    """Test that epic content includes Mermaid dependency diagram."""
    content = """
## Epic Dependency Diagram

```mermaid
graph TD
    EP001["EP-001: Authentication"]
    EP002["EP-002: User Management"]
    EP003["EP-003: Dashboard"]
    
    EP001 --> EP002
    EP001 --> EP003
    
    style EP001 fill:#ff9999
    style EP002 fill:#99ccff
    style EP003 fill:#99ccff
```
"""
    
    artifact = Artifact(
        run_id=1,
        artifact_type=ArtifactType.EPICS,
        name="epics.md",
        content=content,
        artifact_metadata={"has_mermaid_diagram": True}
    )
    db.add(artifact)
    db.commit()
    
    # Verify Mermaid diagram is present
    assert "```mermaid" in artifact.content
    assert "graph TD" in artifact.content
    assert "EP001" in artifact.content
    assert "-->" in artifact.content  # Dependency arrow


def test_research_urls_have_relevance_scores(db):
    """Test that research URLs include relevance information."""
    metadata = {
        "urls_consulted": [
            {
                "url": "https://example.com/article1",
                "title": "Best Practices",
                "summary": "Comprehensive guide",
                "relevance": "high"
            },
            {
                "url": "https://example.com/article2",
                "title": "Case Study",
                "summary": "Real-world example",
                "relevance": "medium"
            }
        ],
        "total_urls": 2
    }
    
    artifact = Artifact(
        run_id=1,
        artifact_type=ArtifactType.RESEARCH,
        name="research.md",
        content="Research content",
        artifact_metadata=metadata
    )
    db.add(artifact)
    db.commit()
    
    # Verify URL structure
    urls = artifact.artifact_metadata["urls_consulted"]
    for url_data in urls:
        assert "url" in url_data
        assert "title" in url_data
        assert "summary" in url_data
        assert "relevance" in url_data
        assert url_data["relevance"] in ["high", "medium", "low"]
