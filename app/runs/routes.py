"""
Run API routes with SSE support.
"""
import asyncio
import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth.utils import get_current_user
from app.database import (
    Approval,
    Artifact,
    ArtifactType,
    Project,
    Run,
    RunStatus,
    User,
    get_db,
)
from app.orchestrator.workflow import Orchestrator
from app.runs.progress_emitter import emit_progress, get_updates
from app.runs.schemas import (
    ApprovalCreate,
    ApprovalResponse,
    ArtifactResponse,
    RunCreate,
    RunResponse,
    RunStatusResponse,
)

router = APIRouter(prefix="/api/runs", tags=["Runs"])

# Create a single orchestrator instance to be reused
orchestrator = Orchestrator()


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
        current_stage=""
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


@router.get("/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current status and stage of a run.

    Returns:
    - **run_id**: ID of the run
    - **status**: Current execution status (pending, running, paused, completed, failed)
    - **current_stage**: Current workflow stage (research, epics, stories, specs, code, validation)
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

    return RunStatusResponse(
        run_id=run.id,
        status=run.status.value if hasattr(run.status, 'value') else run.status,
        current_stage=run.current_stage
    )


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


@router.get("/{run_id}/epics", response_model=List[ArtifactResponse])
def get_run_epics(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get epic artifacts for a run.

    Returns all epic artifacts generated during the run's execution.
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

    epics = db.query(Artifact).filter(
        Artifact.run_id == run_id,
        Artifact.artifact_type == ArtifactType.EPICS
    ).all()
    return epics


@router.get("/{run_id}/stories", response_model=List[ArtifactResponse])
def get_run_stories(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get story artifacts for a run.

    Returns all story artifacts generated during the run's execution.
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

    stories = db.query(Artifact).filter(
        Artifact.run_id == run_id,
        Artifact.artifact_type == ArtifactType.STORIES
    ).all()
    return stories


@router.post("/{run_id}/start")
async def start_run(
    run_id: int,
    background_tasks: BackgroundTasks,
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
    emit_progress(
        run_id=run_id,
        stage="research",
        message="Research phase started"
    )

    # Get the product request from the project
    product_request = run.project.product_request

    # Trigger async orchestrator workflow in background
    background_tasks.add_task(execute_workflow_task, run_id, product_request)

    return {"status": "started", "run_id": run_id}


async def execute_workflow_task(run_id: int, product_request: str):
    """
    Background task to execute the orchestrator workflow.
    
    Args:
        run_id: ID of the run to execute
        product_request: Product request text
    """
    try:
        await orchestrator.execute_run(run_id, product_request)
    except Exception as e:
        # Log the error (in production, use proper logging)
        print(f"Error executing workflow for run {run_id}: {str(e)}")
        # Error is already handled in execute_run, so we just log here


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
    - **action**: 'proceed' (default), 'regenerate', or 'reject'

    **Actions:**
    - `proceed` with `approved=True`: Approves and continues to next stage
    - `regenerate` with `approved=False`: Rejects and triggers regeneration with feedback
    - `reject` with `approved=False`: Rejects without regeneration
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

    # Validate stage
    valid_stages = ["epics", "stories", "specs"]
    if stage not in valid_stages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage. Must be one of: {', '.join(valid_stages)}"
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
        approval.action = approval_data.action or "proceed"
    else:
        # Create new approval
        approval = Approval(
            run_id=run_id,
            stage=stage,
            approved=approval_data.approved,
            feedback=approval_data.feedback,
            action=approval_data.action or "proceed"
        )
        db.add(approval)

    db.commit()
    db.refresh(approval)

    # Emit SSE update
    action_msg = ""
    if approval_data.action == "regenerate":
        action_msg = " - will regenerate with feedback"
    elif approval_data.action == "reject":
        action_msg = " - rejected"

    emit_progress(
        run_id=run_id,
        stage=stage,
        message=f"Stage '{stage}' {'approved' if approval_data.approved else 'rejected'}{action_msg}"
    )

    # TODO: If action is "regenerate", trigger regeneration workflow

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
            updates = get_updates(run_id, from_index=last_index)
            if updates:
                for update in updates:
                    yield {
                        "event": "progress",
                        "data": json.dumps(update)
                    }
                last_index = last_index + len(updates)

            await asyncio.sleep(1)  # Poll every second

    return EventSourceResponse(event_generator())
