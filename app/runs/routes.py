"""
Run API routes with SSE support.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime

from app.database import get_db, Run, Project, User, Artifact, Approval, RunStatus
from app.runs.schemas import (
    RunCreate, RunResponse, ArtifactResponse, 
    ApprovalCreate, ApprovalResponse
)
from app.auth.utils import get_current_user

router = APIRouter(prefix="/api/runs", tags=["Runs"])

# In-memory store for SSE connections (in production, use Redis/message queue)
run_updates = {}


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    run_data: RunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new run for a project.
    
    - **project_id**: ID of the project to run
    """
    # Verify project exists and belongs to user
    project = db.query(Project).filter(
        Project.id == run_data.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Create run
    db_run = Run(
        project_id=run_data.project_id,
        status=RunStatus.PENDING,
        current_stage="initialized"
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    
    return db_run


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific run by ID.
    """
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    return run


@router.get("/{run_id}/artifacts", response_model=List[ArtifactResponse])
def get_run_artifacts(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all artifacts for a run.
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
    return artifacts


@router.post("/{run_id}/start")
def start_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start execution of a run.
    """
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    if run.status not in [RunStatus.PENDING, RunStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start run with status {run.status}"
        )
    
    run.status = RunStatus.RUNNING
    run.started_at = datetime.utcnow()
    run.current_stage = "research"
    db.commit()
    
    # Emit SSE update
    if run_id not in run_updates:
        run_updates[run_id] = []
    run_updates[run_id].append({
        "stage": "research",
        "message": "Research phase started",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # TODO: Trigger async orchestrator workflow
    
    return {"status": "started", "run_id": run_id}


@router.post("/{run_id}/pause")
def pause_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pause a running execution.
    """
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pause run with status {run.status}"
        )
    
    run.status = RunStatus.PAUSED
    db.commit()
    
    return {"status": "paused", "run_id": run_id}


@router.get("/{run_id}/approvals", response_model=List[ApprovalResponse])
def get_approvals(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all approval gates for a run.
    """
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    approvals = db.query(Approval).filter(Approval.run_id == run_id).all()
    return approvals


@router.post("/{run_id}/approvals/{stage}", response_model=ApprovalResponse)
def submit_approval(
    run_id: int,
    stage: str,
    approval_data: ApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit approval for a stage (epics, stories, specs).
    
    - **stage**: One of 'epics', 'stories', 'specs'
    - **approved**: True to approve, False to reject
    - **feedback**: Optional feedback message
    """
    run = db.query(Run).join(Project).filter(
        Run.id == run_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    # Check if approval already exists
    approval = db.query(Approval).filter(
        Approval.run_id == run_id,
        Approval.stage == stage
    ).first()
    
    if approval:
        # Update existing approval
        approval.approved = approval_data.approved
        approval.feedback = approval_data.feedback
    else:
        # Create new approval
        approval = Approval(
            run_id=run_id,
            stage=stage,
            approved=approval_data.approved,
            feedback=approval_data.feedback
        )
        db.add(approval)
    
    db.commit()
    db.refresh(approval)
    
    # Emit SSE update
    if run_id not in run_updates:
        run_updates[run_id] = []
    run_updates[run_id].append({
        "stage": stage,
        "message": f"Stage '{stage}' {'approved' if approval_data.approved else 'rejected'}",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return approval


@router.get("/{run_id}/progress")
async def get_progress_stream(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real-time progress updates via Server-Sent Events (SSE).
    
    This endpoint streams progress updates for a run in real-time.
    Connect to this endpoint to receive live updates as the run progresses.
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
    
    async def event_generator():
        """Generate SSE events for run progress."""
        last_index = 0
        
        # Send initial connection message
        yield {
            "event": "connected",
            "data": json.dumps({
                "run_id": run_id,
                "status": run.status.value if hasattr(run.status, 'value') else run.status,
                "current_stage": run.current_stage
            })
        }
        
        while True:
            # Check if run is complete
            db.refresh(run)
            if run.status in [RunStatus.COMPLETED, RunStatus.FAILED]:
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "run_id": run_id,
                        "status": run.status.value if hasattr(run.status, 'value') else run.status,
                        "message": "Run completed"
                    })
                }
                break
            
            # Get new updates
            if run_id in run_updates and len(run_updates[run_id]) > last_index:
                for update in run_updates[run_id][last_index:]:
                    yield {
                        "event": "progress",
                        "data": json.dumps(update)
                    }
                last_index = len(run_updates[run_id])
            
            await asyncio.sleep(1)  # Poll every second
    
    return EventSourceResponse(event_generator())
