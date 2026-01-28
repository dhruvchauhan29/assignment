"""
Orchestrator using LangGraph for multi-agent workflow.
"""
import operator
from typing import Annotated, Any, Dict, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.code_agent import CodeAgent
from app.agents.epic_agent import EpicAgent
from app.agents.research_agent import ResearchAgent
from app.agents.spec_agent import SpecAgent
from app.agents.story_agent import StoryAgent
from app.agents.validation_agent import ValidationAgent
from app.database import Approval, Artifact, ArtifactType, Run, RunStatus
from app.runs.progress_emitter import emit_progress


class WorkflowState(TypedDict, total=False):
    """State for the workflow graph."""
    run_id: int
    product_request: str
    research: str
    epics: str
    stories: str
    specs: str
    code: str
    validation: str
    messages: Annotated[list, operator.add]
    current_stage: str
    error: str
    epic_regeneration_count: int
    story_regeneration_count: int
    spec_regeneration_count: int


class Orchestrator:
    """Orchestrates the multi-agent workflow using LangGraph."""

    def __init__(self):
        """Initialize the orchestrator with agents."""
        self.research_agent = ResearchAgent()
        self.epic_agent = EpicAgent()
        self.story_agent = StoryAgent()
        self.spec_agent = SpecAgent()
        self.code_agent = CodeAgent()
        self.validation_agent = ValidationAgent()

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)

        # Add nodes for each stage (using different names than state attributes)
        workflow.add_node("research_phase", self._research_node)
        workflow.add_node("epics_phase", self._epics_node)
        workflow.add_node("wait_epic_approval", self._wait_epic_approval_node)
        workflow.add_node("stories_phase", self._stories_node)
        workflow.add_node("wait_story_approval", self._wait_story_approval_node)
        workflow.add_node("specs_phase", self._specs_node)
        workflow.add_node("wait_spec_approval", self._wait_spec_approval_node)
        workflow.add_node("code_phase", self._code_node)
        workflow.add_node("validation_phase", self._validation_node)
        workflow.add_node("complete", self._complete_node)

        # Define edges
        workflow.set_entry_point("research_phase")
        workflow.add_edge("research_phase", "epics_phase")
        workflow.add_edge("epics_phase", "wait_epic_approval")
        workflow.add_conditional_edges(
            "wait_epic_approval",
            self._check_approval,
            {
                "approved": "stories_phase",
                "rejected": "epics_phase",
                "pending": END  # Exit workflow when waiting for approval
            }
        )
        workflow.add_edge("stories_phase", "wait_story_approval")
        workflow.add_conditional_edges(
            "wait_story_approval",
            self._check_approval,
            {
                "approved": "specs_phase",
                "rejected": "stories_phase",
                "pending": END  # Exit workflow when waiting for approval
            }
        )
        workflow.add_edge("specs_phase", "wait_spec_approval")
        workflow.add_conditional_edges(
            "wait_spec_approval",
            self._check_approval,
            {
                "approved": "code_phase",
                "rejected": "specs_phase",
                "pending": END  # Exit workflow when waiting for approval
            }
        )
        workflow.add_edge("code_phase", "validation_phase")
        workflow.add_edge("validation_phase", "complete")
        workflow.add_edge("complete", END)

        return workflow.compile()

    async def _research_node(self, state: WorkflowState) -> WorkflowState:
        """Execute research phase."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            run_id = state["run_id"]

            # Emit start event
            emit_progress(run_id, "research", "Research phase started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "research"
                db.commit()

            result = await self.research_agent.execute({
                "product_request": state["product_request"]
            })

            if result["success"]:
                state["research"] = result["content"]
                state["current_stage"] = "research"

                # Save artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.RESEARCH,
                    "research.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )

                # Emit completion event
                emit_progress(run_id, "research", "Research phase completed")
            else:
                state["error"] = result.get("error", "Research failed")
                emit_progress(run_id, "research", f"Research phase failed: {state['error']}")

            return state
        finally:
            db.close()

    async def _epics_node(self, state: WorkflowState) -> WorkflowState:
        """Execute epic generation phase."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            run_id = state["run_id"]

            # Check if we need to incorporate feedback from rejection
            feedback = ""
            approval = db.query(Approval).filter(
                Approval.run_id == state["run_id"],
                Approval.stage == "epics"
            ).first()

            if approval and approval.action == "regenerate" and approval.feedback:
                feedback = approval.feedback
                # Increment regeneration count
                regeneration_count = state.get("epic_regeneration_count", 0) + 1
                state["epic_regeneration_count"] = regeneration_count
                emit_progress(run_id, "epics", f"Regenerating epics with feedback (attempt {regeneration_count})")
            else:
                regeneration_count = 0
                emit_progress(run_id, "epics", "Epic generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "epics"
                db.commit()

            result = await self.epic_agent.execute({
                "product_request": state["product_request"],
                "research": state["research"],
                "feedback": feedback,
                "regeneration_count": regeneration_count
            })

            if result["success"]:
                state["epics"] = result["content"]
                state["current_stage"] = "epics"

                # Save artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.EPICS,
                    "epics.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )

                # Create or update approval gate
                self._create_or_update_approval(db, state["run_id"], "epics")

                # Emit completion event
                emit_progress(run_id, "epics", "Epic generation completed")
            else:
                state["error"] = result.get("error", "Epic generation failed")
                emit_progress(run_id, "epics", f"Epic generation failed: {state['error']}")

            return state
        finally:
            db.close()

    async def _stories_node(self, state: WorkflowState) -> WorkflowState:
        """Execute story generation phase."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            run_id = state["run_id"]

            # Check if we need to incorporate feedback from rejection
            feedback = ""
            approval = db.query(Approval).filter(
                Approval.run_id == state["run_id"],
                Approval.stage == "stories"
            ).first()

            if approval and approval.action == "regenerate" and approval.feedback:
                feedback = approval.feedback
                regeneration_count = state.get("story_regeneration_count", 0) + 1
                state["story_regeneration_count"] = regeneration_count
                emit_progress(run_id, "stories", f"Regenerating stories with feedback (attempt {regeneration_count})")
            else:
                regeneration_count = 0
                emit_progress(run_id, "stories", "Story generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "stories"
                db.commit()

            result = await self.story_agent.execute({
                "epics": state["epics"],
                "feedback": feedback,
                "regeneration_count": regeneration_count
            })

            if result["success"]:
                state["stories"] = result["content"]
                state["current_stage"] = "stories"

                # Save artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.STORIES,
                    "stories.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )

                # Create or update approval gate
                self._create_or_update_approval(db, state["run_id"], "stories")

                # Emit completion event
                emit_progress(run_id, "stories", "Story generation completed")
            else:
                state["error"] = result.get("error", "Story generation failed")
                emit_progress(run_id, "stories", f"Story generation failed: {state['error']}")

            return state
        finally:
            db.close()

    async def _specs_node(self, state: WorkflowState) -> WorkflowState:
        """Execute spec generation phase."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            run_id = state["run_id"]

            # Check if we need to incorporate feedback from rejection
            feedback = ""
            approval = db.query(Approval).filter(
                Approval.run_id == state["run_id"],
                Approval.stage == "specs"
            ).first()

            if approval and approval.action == "regenerate" and approval.feedback:
                feedback = approval.feedback
                regeneration_count = state.get("spec_regeneration_count", 0) + 1
                state["spec_regeneration_count"] = regeneration_count
                emit_progress(run_id, "specs", f"Regenerating specs with feedback (attempt {regeneration_count})")
            else:
                regeneration_count = 0
                emit_progress(run_id, "specs", "Spec generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "specs"
                db.commit()

            result = await self.spec_agent.execute({
                "stories": state["stories"],
                "feedback": feedback,
                "regeneration_count": regeneration_count
            })

            if result["success"]:
                state["specs"] = result["content"]
                state["current_stage"] = "specs"

                # Save artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.SPECS,
                    "specs.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )

                # Create or update approval gate
                self._create_or_update_approval(db, state["run_id"], "specs")

                # Emit completion event
                emit_progress(run_id, "specs", "Spec generation completed")
            else:
                state["error"] = result.get("error", "Spec generation failed")
                emit_progress(run_id, "specs", f"Spec generation failed: {state['error']}")

            return state
        finally:
            db.close()

    async def _code_node(self, state: WorkflowState) -> WorkflowState:
        """Execute code generation phase."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            run_id = state["run_id"]

            emit_progress(run_id, "code", "Code generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "code"
                db.commit()

            result = await self.code_agent.execute({
                "specs": state["specs"]
            })

            if result["success"]:
                state["code"] = result["content"]
                state["current_stage"] = "code"

                # Save artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.CODE,
                    "code.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )

                # Emit completion event
                emit_progress(run_id, "code", "Code generation completed")
            else:
                state["error"] = result.get("error", "Code generation failed")
                emit_progress(run_id, "code", f"Code generation failed: {state['error']}")

            return state
        finally:
            db.close()

    async def _validation_node(self, state: WorkflowState) -> WorkflowState:
        """Execute validation phase."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            run_id = state["run_id"]

            emit_progress(run_id, "validation", "Validation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "validation"
                db.commit()

            result = await self.validation_agent.execute({
                "code": state["code"]
            })

            if result["success"]:
                state["validation"] = result["content"]
                state["current_stage"] = "validation"

                # Save artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.VALIDATION,
                    "validation_report.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )

                # Emit completion event
                emit_progress(run_id, "validation", "Validation completed")
            else:
                state["error"] = result.get("error", "Validation failed")
                emit_progress(run_id, "validation", f"Validation failed: {state['error']}")

            return state
        finally:
            db.close()

    async def _complete_node(self, state: WorkflowState) -> WorkflowState:
        """Complete the workflow."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            run_id = state["run_id"]
            state["current_stage"] = "completed"

            # Update run status
            run = db.query(Run).filter(Run.id == state["run_id"]).first()
            if run:
                run.status = RunStatus.COMPLETED
                run.current_stage = "completed"
                db.commit()

            # Emit completion event
            emit_progress(run_id, "completed", "Workflow completed successfully")

            return state
        finally:
            db.close()

    async def _wait_epic_approval_node(self, state: WorkflowState) -> WorkflowState:
        """Wait for epic approval."""
        state["current_stage"] = "waiting_epic_approval"
        return state

    async def _wait_story_approval_node(self, state: WorkflowState) -> WorkflowState:
        """Wait for story approval."""
        state["current_stage"] = "waiting_story_approval"
        return state

    async def _wait_spec_approval_node(self, state: WorkflowState) -> WorkflowState:
        """Wait for spec approval."""
        state["current_stage"] = "waiting_spec_approval"
        return state

    def _check_approval(self, state: WorkflowState) -> str:
        """Check if current stage is approved."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            stage_map = {
                "waiting_epic_approval": "epics",
                "waiting_story_approval": "stories",
                "waiting_spec_approval": "specs"
            }

            stage = stage_map.get(state["current_stage"])
            if not stage:
                return "pending"

            approval = db.query(Approval).filter(
                Approval.run_id == state["run_id"],
                Approval.stage == stage
            ).first()

            if not approval or approval.approved is None:
                return "pending"

            return "approved" if approval.approved else "rejected"
        finally:
            db.close()

    def _save_artifact(
        self,
        db: Session,
        run_id: int,
        artifact_type: ArtifactType,
        name: str,
        content: str,
        artifact_metadata: Dict[str, Any] = None
    ):
        """Save an artifact to the database."""
        artifact = Artifact(
            run_id=run_id,
            artifact_type=artifact_type,
            name=name,
            content=content,
            artifact_metadata=artifact_metadata
        )
        db.add(artifact)
        db.commit()

    def _create_approval(self, db: Session, run_id: int, stage: str):
        """Create an approval gate."""
        # Check if already exists
        existing = db.query(Approval).filter(
            Approval.run_id == run_id,
            Approval.stage == stage
        ).first()

        if not existing:
            approval = Approval(
                run_id=run_id,
                stage=stage,
                approved=None
            )
            db.add(approval)
            db.commit()

    def _create_or_update_approval(self, db: Session, run_id: int, stage: str):
        """Create or reset an approval gate for regeneration."""
        approval = db.query(Approval).filter(
            Approval.run_id == run_id,
            Approval.stage == stage
        ).first()

        if approval:
            # Reset approval status for regenerated content
            approval.approved = None
            approval.action = "proceed"
            # Keep the feedback for reference
        else:
            approval = Approval(
                run_id=run_id,
                stage=stage,
                approved=None
            )
            db.add(approval)

        db.commit()

    async def continue_run(self, run_id: int, from_stage: str):
        """
        Continue a run from a specific stage after approval.

        Args:
            run_id: ID of the run to continue
            from_stage: Stage to continue from ('epics', 'stories', 'specs')
        """
        from app.database import SessionLocal

        # Get current run state from database
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")

            # Get artifacts to reconstruct state
            artifacts = db.query(Artifact).filter(Artifact.run_id == run_id).all()

            # Build state from artifacts
            state: WorkflowState = {
                "run_id": run_id,
                "product_request": run.project.product_request,
                "research": "",
                "epics": "",
                "stories": "",
                "specs": "",
                "code": "",
                "validation": "",
                "messages": [],
                "current_stage": from_stage,
                "error": "",
                "epic_regeneration_count": 0,
                "story_regeneration_count": 0,
                "spec_regeneration_count": 0
            }

            # Populate state from artifacts
            for artifact in artifacts:
                if artifact.artifact_type == ArtifactType.RESEARCH:
                    state["research"] = artifact.content
                elif artifact.artifact_type == ArtifactType.EPICS:
                    state["epics"] = artifact.content
                elif artifact.artifact_type == ArtifactType.STORIES:
                    state["stories"] = artifact.content
                elif artifact.artifact_type == ArtifactType.SPECS:
                    state["specs"] = artifact.content
                elif artifact.artifact_type == ArtifactType.CODE:
                    state["code"] = artifact.content
                elif artifact.artifact_type == ArtifactType.VALIDATION:
                    state["validation"] = artifact.content

            # Update run status to running
            run.status = RunStatus.RUNNING
            db.commit()
        finally:
            db.close()

        try:
            # Continue execution based on stage
            if from_stage == "epics":
                # Check if we need to regenerate or continue to stories
                db = SessionLocal()
                try:
                    approval = db.query(Approval).filter(
                        Approval.run_id == run_id,
                        Approval.stage == "epics"
                    ).first()

                    if approval and approval.action == "regenerate":
                        # Re-run epics node
                        state = await self._epics_node(state)
                        # Then wait for approval again
                    elif approval and approval.approved:
                        # Continue to stories
                        state = await self._stories_node(state)
                        # Then wait for story approval
                finally:
                    db.close()

            elif from_stage == "stories":
                # Check if we need to regenerate or continue to specs
                db = SessionLocal()
                try:
                    approval = db.query(Approval).filter(
                        Approval.run_id == run_id,
                        Approval.stage == "stories"
                    ).first()

                    if approval and approval.action == "regenerate":
                        # Re-run stories node
                        state = await self._stories_node(state)
                    elif approval and approval.approved:
                        # Continue to specs
                        state = await self._specs_node(state)
                finally:
                    db.close()

            elif from_stage == "specs":
                # Check if we need to regenerate or continue to code
                db = SessionLocal()
                try:
                    approval = db.query(Approval).filter(
                        Approval.run_id == run_id,
                        Approval.stage == "specs"
                    ).first()

                    if approval and approval.action == "regenerate":
                        # Re-run specs node
                        state = await self._specs_node(state)
                    elif approval and approval.approved:
                        # Continue to code and validation
                        state = await self._code_node(state)
                        state = await self._validation_node(state)
                        state = await self._complete_node(state)
                finally:
                    db.close()

            return state

        except Exception as e:
            # Update error status
            db = SessionLocal()
            try:
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    run.status = RunStatus.FAILED
                    run.error_message = str(e)
                    db.commit()
            finally:
                db.close()
            raise

    async def execute_run(self, run_id: int, product_request: str):
        """
        Execute a complete run through the workflow.

        Args:
            run_id: ID of the run to execute
            product_request: Product request text
        """
        from app.database import SessionLocal

        initial_state: WorkflowState = {
            "run_id": run_id,
            "product_request": product_request,
            "research": "",
            "epics": "",
            "stories": "",
            "specs": "",
            "code": "",
            "validation": "",
            "messages": [],
            "current_stage": "initialized",
            "error": "",
            "epic_regeneration_count": 0,
            "story_regeneration_count": 0,
            "spec_regeneration_count": 0
        }

        # Update run status
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = RunStatus.RUNNING
                run.current_stage = "research"
                db.commit()
        finally:
            db.close()

        try:
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)

            # Update final status
            db = SessionLocal()
            try:
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    if final_state.get("error"):
                        run.status = RunStatus.FAILED
                        run.error_message = final_state["error"]
                    else:
                        run.status = RunStatus.COMPLETED
                    db.commit()
            finally:
                db.close()

            return final_state

        except Exception as e:
            # Update error status
            db = SessionLocal()
            try:
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    run.status = RunStatus.FAILED
                    run.error_message = str(e)
                    db.commit()
            finally:
                db.close()
            raise
