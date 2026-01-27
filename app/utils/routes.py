"""
Export API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session

from app.database import get_db, Run, Project, User, Artifact
from app.auth.utils import get_current_user
from app.utils.export import (
    export_artifacts_as_markdown,
    create_code_bundle_zip,
    export_validation_report
)

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/{run_id}/artifacts.md")
def export_artifacts_markdown(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all artifacts for a run as a markdown document.
    """
    # Verify run exists and belongs to user
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    artifacts = db.query(Artifact).filter(Artifact.run_id == run_id).all()
    
    if not artifacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No artifacts found"
        )
    
    markdown_content = export_artifacts_as_markdown(artifacts)
    
    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=run_{run_id}_artifacts.md"
        }
    )


@router.get("/{run_id}/code.zip")
def export_code_bundle(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export code artifacts as a ZIP bundle.
    """
    # Verify run exists and belongs to user
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    # Get code artifacts
    artifacts = db.query(Artifact).filter(
        Artifact.run_id == run_id,
        Artifact.artifact_type.in_(["code", "specs"])
    ).all()
    
    if not artifacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No code artifacts found"
        )
    
    zip_content = create_code_bundle_zip(artifacts)
    
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=run_{run_id}_code.zip"
        }
    )


@router.get("/{run_id}/validation.md")
def export_validation_report_endpoint(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export validation report for a run.
    """
    # Verify run exists and belongs to user
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    report_content = export_validation_report(run, db)
    
    return Response(
        content=report_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=run_{run_id}_validation.md"
        }
    )
