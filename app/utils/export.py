"""
Export utilities for downloading artifacts.
"""
import io
import zipfile
from typing import List
from sqlalchemy.orm import Session

from app.database import Artifact, Run


def export_artifacts_as_markdown(artifacts: List[Artifact]) -> str:
    """
    Export artifacts as a single markdown document.
    
    Args:
        artifacts: List of artifacts to export
        
    Returns:
        Markdown formatted string
    """
    markdown_parts = ["# Project Artifacts\n\n"]
    
    # Group by type
    by_type = {}
    for artifact in artifacts:
        artifact_type = artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else artifact.artifact_type
        if artifact_type not in by_type:
            by_type[artifact_type] = []
        by_type[artifact_type].append(artifact)
    
    # Generate markdown for each type
    for artifact_type, type_artifacts in by_type.items():
        markdown_parts.append(f"## {artifact_type.upper()}\n\n")
        
        for artifact in type_artifacts:
            markdown_parts.append(f"### {artifact.name}\n\n")
            markdown_parts.append(artifact.content)
            markdown_parts.append("\n\n---\n\n")
    
    return "".join(markdown_parts)


def create_code_bundle_zip(artifacts: List[Artifact]) -> bytes:
    """
    Create a ZIP file containing all code artifacts.
    
    Args:
        artifacts: List of artifacts to include
        
    Returns:
        ZIP file as bytes
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for artifact in artifacts:
            filename = artifact.name
            zip_file.writestr(filename, artifact.content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def export_validation_report(run: Run, db: Session) -> str:
    """
    Export validation report for a run.
    
    Args:
        run: Run to export validation for
        db: Database session
        
    Returns:
        Formatted validation report
    """
    validation_artifacts = db.query(Artifact).filter(
        Artifact.run_id == run.id,
        Artifact.artifact_type == "validation"
    ).all()
    
    if not validation_artifacts:
        return "# Validation Report\n\nNo validation results available."
    
    report_parts = ["# Validation Report\n\n"]
    report_parts.append(f"**Run ID:** {run.id}\n")
    report_parts.append(f"**Status:** {run.status.value if hasattr(run.status, 'value') else run.status}\n")
    report_parts.append(f"**Total Tokens:** {run.total_tokens}\n\n")
    report_parts.append("---\n\n")
    
    for artifact in validation_artifacts:
        report_parts.append(artifact.content)
        report_parts.append("\n\n")
    
    return "".join(report_parts)
