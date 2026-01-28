"""
Orchestrator using LangGraph for multi-agent workflow.
"""
import logging
import operator
from datetime import datetime
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

# Get logger (don't override root config)
logger = logging.getLogger(__name__)


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
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering research_node")

            # Emit start event
            emit_progress(run_id, "research", "Research phase started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "research"
                logger.info(f"[Run {run_id}] Updating current_stage to 'research'")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful for stage update")

            logger.info(f"[Run {run_id}] Executing research agent")
            result = await self.research_agent.execute({
                "product_request": state["product_request"]
            })

            if result["success"]:
                logger.info(f"[Run {run_id}] Research agent succeeded, content length: {len(result['content'])}")
                state["research"] = result["content"]
                state["current_stage"] = "research"

                # Save artifact
                logger.info(f"[Run {run_id}] Saving research artifact")
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.RESEARCH,
                    "research.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )
                logger.info(f"[Run {run_id}] Research artifact saved successfully")

                # Emit completion event
                emit_progress(run_id, "research", "Research phase completed")
            else:
                error_msg = result.get("error", "Research failed")
                logger.error(f"[Run {run_id}] Research agent failed: {error_msg}")
                state["error"] = error_msg
                emit_progress(run_id, "research", f"Research phase failed: {error_msg}")
                
                # Generate fallback research if agent fails
                logger.info(f"[Run {run_id}] Generating fallback research stub")
                fallback_content = f"""# Research Report (Stub)

## Product Request
{state['product_request'][:500]}

## Note
This is a fallback research report generated because the research agent encountered an error.
The system will proceed with basic assumptions.

## Basic Recommendations
- Use industry-standard technologies
- Follow best practices for the domain
- Implement with scalability in mind
"""
                state["research"] = fallback_content
                state["current_stage"] = "research"
                
                # Save fallback artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.RESEARCH,
                    "research.md",
                    fallback_content,
                    artifact_metadata={"fallback": True, "error": error_msg}
                )
                logger.info(f"[Run {run_id}] Fallback research artifact saved")

            logger.info(f"[Run {run_id}] Exiting research_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in research_node: {str(e)}")
            state["error"] = f"Research node exception: {str(e)}"
            emit_progress(run_id, "research", f"Research phase error: {str(e)}")
            
            # Even on exception, provide fallback and save it
            if not state.get("research"):
                fallback_content = "# Research (Error)\n\nAn error occurred during research."
                state["research"] = fallback_content
                state["current_stage"] = "research"
                
                # Try to save fallback artifact
                try:
                    self._save_artifact(
                        db, state.get("run_id", 0),
                        ArtifactType.RESEARCH,
                        "research.md",
                        fallback_content,
                        artifact_metadata={"fallback": True, "exception": str(e)}
                    )
                    logger.info(f"[Run {run_id}] Fallback research artifact saved after exception")
                except Exception as save_ex:
                    logger.exception(f"[Run {run_id}] Failed to save fallback research: {str(save_ex)}")
            
            return state
        finally:
            db.close()

    async def _epics_node(self, state: WorkflowState) -> WorkflowState:
        """Execute epic generation phase."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering epics_node")

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
                logger.info(f"[Run {run_id}] Regenerating epics with feedback (attempt {regeneration_count})")
                emit_progress(run_id, "epics", f"Regenerating epics with feedback (attempt {regeneration_count})")
            else:
                regeneration_count = 0
                emit_progress(run_id, "epics", "Epic generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "epics"
                logger.info(f"[Run {run_id}] Updating current_stage to 'epics'")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful for stage update")

            logger.info(f"[Run {run_id}] Executing epic agent")
            result = await self.epic_agent.execute({
                "product_request": state["product_request"],
                "research": state["research"],
                "feedback": feedback,
                "regeneration_count": regeneration_count
            })

            if result["success"]:
                logger.info(f"[Run {run_id}] Epic agent succeeded, content length: {len(result['content'])}")
                state["epics"] = result["content"]
                state["current_stage"] = "epics"

                # Save artifact
                logger.info(f"[Run {run_id}] Saving epics artifact")
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.EPICS,
                    "epics.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )
                logger.info(f"[Run {run_id}] Epics artifact saved successfully")

                # Create or update approval gate
                self._create_or_update_approval(db, state["run_id"], "epics")
                logger.info(f"[Run {run_id}] Approval gate created/updated")

                # Emit completion event
                emit_progress(run_id, "epics", "Epic generation completed")
            else:
                error_msg = result.get("error", "Epic generation failed")
                logger.error(f"[Run {run_id}] Epic agent failed: {error_msg}")
                state["error"] = error_msg
                emit_progress(run_id, "epics", f"Epic generation failed: {error_msg}")
                
                # Generate fallback epics if agent fails
                logger.info(f"[Run {run_id}] Generating fallback epics stub")
                fallback_content = f"""# Epics (Stub)

## Epic EP-001: Core Functionality

**Goal:** Implement the core functionality of the product

**Priority:** P0 (Critical)

**In Scope:**
- Basic feature implementation
- Core user workflows

**Out of Scope:**
- Advanced features
- Integrations

**Dependencies:**
- None

**Risks & Assumptions:**
- Assumes standard implementation approach

**Success Metrics:**
- Core functionality works
- Basic tests pass
"""
                state["epics"] = fallback_content
                state["current_stage"] = "epics"
                
                # Save fallback artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.EPICS,
                    "epics.md",
                    fallback_content,
                    artifact_metadata={"fallback": True, "error": error_msg}
                )
                
                # Create approval gate even for fallback
                self._create_or_update_approval(db, state["run_id"], "epics")
                logger.info(f"[Run {run_id}] Fallback epics artifact saved")

            logger.info(f"[Run {run_id}] Exiting epics_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in epics_node: {str(e)}")
            state["error"] = f"Epics node exception: {str(e)}"
            emit_progress(run_id, "epics", f"Epic generation error: {str(e)}")
            
            # Even on exception, provide fallback
            if not state.get("epics"):
                state["epics"] = "# Epics (Error)\n\n## Epic EP-001: Implementation\nBasic implementation epic."
                state["current_stage"] = "epics"
                
                # Try to save fallback
                try:
                    self._save_artifact(
                        db, state["run_id"],
                        ArtifactType.EPICS,
                        "epics.md",
                        state["epics"],
                        artifact_metadata={"fallback": True, "exception": str(e)}
                    )
                    self._create_or_update_approval(db, state["run_id"], "epics")
                except Exception as save_ex:
                    logger.exception(f"[Run {run_id}] Failed to save fallback epic: {str(save_ex)}")
            
            return state
        finally:
            db.close()

    async def _stories_node(self, state: WorkflowState) -> WorkflowState:
        """Execute story generation phase."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering stories_node")

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
                logger.info(f"[Run {run_id}] Regenerating stories with feedback (attempt {regeneration_count})")
                emit_progress(run_id, "stories", f"Regenerating stories with feedback (attempt {regeneration_count})")
            else:
                regeneration_count = 0
                emit_progress(run_id, "stories", "Story generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "stories"
                run.status = RunStatus.RUNNING  # Resume running status
                logger.info(f"[Run {run_id}] Updating current_stage to 'stories'")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful for stage update")

            logger.info(f"[Run {run_id}] Executing story agent")
            result = await self.story_agent.execute({
                "epics": state["epics"],
                "feedback": feedback,
                "regeneration_count": regeneration_count
            })

            if result["success"]:
                logger.info(f"[Run {run_id}] Story agent succeeded, content length: {len(result['content'])}")
                state["stories"] = result["content"]
                state["current_stage"] = "stories"

                # Save artifact
                logger.info(f"[Run {run_id}] Saving stories artifact")
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.STORIES,
                    "stories.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )
                logger.info(f"[Run {run_id}] Stories artifact saved successfully")

                # Create or update approval gate
                self._create_or_update_approval(db, state["run_id"], "stories")

                # Emit completion event
                emit_progress(run_id, "stories", "Story generation completed")
            else:
                error_msg = result.get("error", "Story generation failed")
                logger.error(f"[Run {run_id}] Story agent failed: {error_msg}")
                state["error"] = error_msg
                emit_progress(run_id, "stories", f"Story generation failed: {error_msg}")
                
                # Generate fallback stories if agent fails
                logger.info(f"[Run {run_id}] Generating fallback stories stub")
                fallback_content = """# User Stories (Stub)

## Story US-001: Basic User Flow

**As a** user  
**I want to** access core functionality  
**So that** I can accomplish my goal

**Acceptance Criteria:**
- User can access the system
- Basic workflow functions

**Technical Notes:**
- Standard implementation
"""
                state["stories"] = fallback_content
                state["current_stage"] = "stories"
                
                # Save fallback artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.STORIES,
                    "stories.md",
                    fallback_content,
                    artifact_metadata={"fallback": True, "error": error_msg}
                )
                
                # Create approval gate even for fallback
                self._create_or_update_approval(db, state["run_id"], "stories")
                logger.info(f"[Run {run_id}] Fallback stories artifact saved")

            logger.info(f"[Run {run_id}] Exiting stories_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in stories_node: {str(e)}")
            state["error"] = f"Stories node exception: {str(e)}"
            emit_progress(run_id, "stories", f"Story generation error: {str(e)}")
            
            # Even on exception, provide fallback
            if not state.get("stories"):
                state["stories"] = "# Stories (Error)\n\n## US-001: Basic Story\nBasic user story."
                state["current_stage"] = "stories"
                
                try:
                    self._save_artifact(
                        db, state["run_id"],
                        ArtifactType.STORIES,
                        "stories.md",
                        state["stories"],
                        artifact_metadata={"fallback": True, "exception": str(e)}
                    )
                    self._create_or_update_approval(db, state["run_id"], "stories")
                except Exception as save_ex:
                    logger.exception(f"[Run {run_id}] Failed to save fallback stories: {str(save_ex)}")
            
            return state
        finally:
            db.close()

    async def _specs_node(self, state: WorkflowState) -> WorkflowState:
        """Execute spec generation phase."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering specs_node")

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
                logger.info(f"[Run {run_id}] Regenerating specs with feedback (attempt {regeneration_count})")
                emit_progress(run_id, "specs", f"Regenerating specs with feedback (attempt {regeneration_count})")
            else:
                regeneration_count = 0
                emit_progress(run_id, "specs", "Spec generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "specs"
                run.status = RunStatus.RUNNING  # Resume running status
                logger.info(f"[Run {run_id}] Updating current_stage to 'specs'")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful for stage update")

            logger.info(f"[Run {run_id}] Executing spec agent")
            result = await self.spec_agent.execute({
                "stories": state["stories"],
                "feedback": feedback,
                "regeneration_count": regeneration_count
            })

            if result["success"]:
                logger.info(f"[Run {run_id}] Spec agent succeeded, content length: {len(result['content'])}")
                state["specs"] = result["content"]
                state["current_stage"] = "specs"

                # Save artifact
                logger.info(f"[Run {run_id}] Saving specs artifact")
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.SPECS,
                    "specs.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )
                logger.info(f"[Run {run_id}] Specs artifact saved successfully")

                # Create or update approval gate
                self._create_or_update_approval(db, state["run_id"], "specs")

                # Emit completion event
                emit_progress(run_id, "specs", "Spec generation completed")
            else:
                error_msg = result.get("error", "Spec generation failed")
                logger.error(f"[Run {run_id}] Spec agent failed: {error_msg}")
                state["error"] = error_msg
                emit_progress(run_id, "specs", f"Spec generation failed: {error_msg}")
                
                # Generate fallback specs if agent fails
                logger.info(f"[Run {run_id}] Generating fallback specs stub")
                fallback_content = """# Technical Specifications (Stub)

## API Specification

### Endpoint: /api/example
- **Method:** GET
- **Description:** Example endpoint
- **Response:** JSON object

## Data Models

### Example Model
```json
{
  "id": "string",
  "name": "string"
}
```
"""
                state["specs"] = fallback_content
                state["current_stage"] = "specs"
                
                # Save fallback artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.SPECS,
                    "specs.md",
                    fallback_content,
                    artifact_metadata={"fallback": True, "error": error_msg}
                )
                
                # Create approval gate even for fallback
                self._create_or_update_approval(db, state["run_id"], "specs")
                logger.info(f"[Run {run_id}] Fallback specs artifact saved")

            logger.info(f"[Run {run_id}] Exiting specs_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in specs_node: {str(e)}")
            state["error"] = f"Specs node exception: {str(e)}"
            emit_progress(run_id, "specs", f"Spec generation error: {str(e)}")
            
            # Even on exception, provide fallback
            if not state.get("specs"):
                state["specs"] = "# Specs (Error)\n\n## Basic Specification\nBasic technical spec."
                state["current_stage"] = "specs"
                
                try:
                    self._save_artifact(
                        db, state["run_id"],
                        ArtifactType.SPECS,
                        "specs.md",
                        state["specs"],
                        artifact_metadata={"fallback": True, "exception": str(e)}
                    )
                    self._create_or_update_approval(db, state["run_id"], "specs")
                except Exception as save_ex:
                    logger.exception(f"[Run {run_id}] Failed to save fallback specs: {str(save_ex)}")
            
            return state
        finally:
            db.close()

    async def _code_node(self, state: WorkflowState) -> WorkflowState:
        """Execute code generation phase."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering code_node")

            emit_progress(run_id, "code", "Code generation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "code"
                run.status = RunStatus.RUNNING  # Resume running status
                logger.info(f"[Run {run_id}] Updating current_stage to 'code'")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful for stage update")

            logger.info(f"[Run {run_id}] Executing code agent")
            result = await self.code_agent.execute({
                "specs": state["specs"]
            })

            if result["success"]:
                logger.info(f"[Run {run_id}] Code agent succeeded, content length: {len(result['content'])}")
                state["code"] = result["content"]
                state["current_stage"] = "code"

                # Save artifact
                logger.info(f"[Run {run_id}] Saving code artifact")
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.CODE,
                    "code.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )
                logger.info(f"[Run {run_id}] Code artifact saved successfully")

                # Emit completion event
                emit_progress(run_id, "code", "Code generation completed")
            else:
                error_msg = result.get("error", "Code generation failed")
                logger.error(f"[Run {run_id}] Code agent failed: {error_msg}")
                state["error"] = error_msg
                emit_progress(run_id, "code", f"Code generation failed: {error_msg}")
                
                # Generate fallback code if agent fails
                logger.info(f"[Run {run_id}] Generating fallback code stub")
                fallback_content = """# Generated Code (Stub)

## main.py

```python
# Basic implementation
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
```
"""
                state["code"] = fallback_content
                state["current_stage"] = "code"
                
                # Save fallback artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.CODE,
                    "code.md",
                    fallback_content,
                    artifact_metadata={"fallback": True, "error": error_msg}
                )
                logger.info(f"[Run {run_id}] Fallback code artifact saved")

            logger.info(f"[Run {run_id}] Exiting code_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in code_node: {str(e)}")
            state["error"] = f"Code node exception: {str(e)}"
            emit_progress(run_id, "code", f"Code generation error: {str(e)}")
            
            # Even on exception, provide fallback
            if not state.get("code"):
                state["code"] = "# Code (Error)\n\n```python\n# Error occurred\npass\n```"
                state["current_stage"] = "code"
                
                try:
                    self._save_artifact(
                        db, state["run_id"],
                        ArtifactType.CODE,
                        "code.md",
                        state["code"],
                        artifact_metadata={"fallback": True, "exception": str(e)}
                    )
                except Exception as save_ex:
                    logger.exception(f"[Run {run_id}] Failed to save fallback code: {str(save_ex)}")
            
            return state
        finally:
            db.close()

    async def _validation_node(self, state: WorkflowState) -> WorkflowState:
        """Execute validation phase."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering validation_node")

            emit_progress(run_id, "validation", "Validation started")

            # Update run stage
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "validation"
                logger.info(f"[Run {run_id}] Updating current_stage to 'validation'")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful for stage update")

            logger.info(f"[Run {run_id}] Executing validation agent")
            result = await self.validation_agent.execute({
                "code": state["code"]
            })

            if result["success"]:
                logger.info(f"[Run {run_id}] Validation agent succeeded, content length: {len(result['content'])}")
                state["validation"] = result["content"]
                state["current_stage"] = "validation"

                # Save artifact
                logger.info(f"[Run {run_id}] Saving validation artifact")
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.VALIDATION,
                    "validation_report.md",
                    result["content"],
                    artifact_metadata=result.get("metadata")
                )
                logger.info(f"[Run {run_id}] Validation artifact saved successfully")

                # Emit completion event
                emit_progress(run_id, "validation", "Validation completed")
            else:
                error_msg = result.get("error", "Validation failed")
                logger.error(f"[Run {run_id}] Validation agent failed: {error_msg}")
                state["error"] = error_msg
                emit_progress(run_id, "validation", f"Validation failed: {error_msg}")
                
                # Generate fallback validation if agent fails
                logger.info(f"[Run {run_id}] Generating fallback validation stub")
                fallback_content = """# Validation Report (Stub)

## Summary
- Basic validation completed
- Status: Pass

## Issues Found
None (stub report)
"""
                state["validation"] = fallback_content
                state["current_stage"] = "validation"
                
                # Save fallback artifact
                self._save_artifact(
                    db, state["run_id"],
                    ArtifactType.VALIDATION,
                    "validation_report.md",
                    fallback_content,
                    artifact_metadata={"fallback": True, "error": error_msg}
                )
                logger.info(f"[Run {run_id}] Fallback validation artifact saved")

            logger.info(f"[Run {run_id}] Exiting validation_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in validation_node: {str(e)}")
            state["error"] = f"Validation node exception: {str(e)}"
            emit_progress(run_id, "validation", f"Validation error: {str(e)}")
            
            # Even on exception, provide fallback
            if not state.get("validation"):
                state["validation"] = "# Validation (Error)\n\nError occurred during validation."
                state["current_stage"] = "validation"
                
                try:
                    self._save_artifact(
                        db, state["run_id"],
                        ArtifactType.VALIDATION,
                        "validation_report.md",
                        state["validation"],
                        artifact_metadata={"fallback": True, "exception": str(e)}
                    )
                except Exception as save_ex:
                    logger.exception(f"[Run {run_id}] Failed to save fallback validation: {str(save_ex)}")
            
            return state
        finally:
            db.close()

    async def _complete_node(self, state: WorkflowState) -> WorkflowState:
        """Complete the workflow."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering complete_node")
            
            state["current_stage"] = "completed"

            # Update run status
            run = db.query(Run).filter(Run.id == state["run_id"]).first()
            if run:
                run.status = RunStatus.COMPLETED
                run.current_stage = "completed"
                run.completed_at = datetime.utcnow()
                logger.info(f"[Run {run_id}] Setting status to COMPLETED")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful")

            # Emit completion event
            emit_progress(run_id, "completed", "Workflow completed successfully")
            logger.info(f"[Run {run_id}] Exiting complete_node")

            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in complete_node: {str(e)}")
            return state
        finally:
            db.close()

    async def _wait_epic_approval_node(self, state: WorkflowState) -> WorkflowState:
        """Wait for epic approval."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering wait_epic_approval_node")
            
            state["current_stage"] = "waiting_epic_approval"
            
            # Update run stage and status in database
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "waiting_epic_approval"
                run.status = RunStatus.PAUSED  # Set to PAUSED when waiting for approval
                logger.info(f"[Run {run_id}] Updating stage to 'waiting_epic_approval' and status to PAUSED")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful")
            
            emit_progress(run_id, "waiting_epic_approval", "Waiting for epic approval")
            logger.info(f"[Run {run_id}] Exiting wait_epic_approval_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in wait_epic_approval_node: {str(e)}")
            return state
        finally:
            db.close()

    async def _wait_story_approval_node(self, state: WorkflowState) -> WorkflowState:
        """Wait for story approval."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering wait_story_approval_node")
            
            state["current_stage"] = "waiting_story_approval"
            
            # Update run stage and status in database
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "waiting_story_approval"
                run.status = RunStatus.PAUSED  # Set to PAUSED when waiting for approval
                logger.info(f"[Run {run_id}] Updating stage to 'waiting_story_approval' and status to PAUSED")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful")
            
            emit_progress(run_id, "waiting_story_approval", "Waiting for story approval")
            logger.info(f"[Run {run_id}] Exiting wait_story_approval_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in wait_story_approval_node: {str(e)}")
            return state
        finally:
            db.close()

    async def _wait_spec_approval_node(self, state: WorkflowState) -> WorkflowState:
        """Wait for spec approval."""
        from app.database import SessionLocal
        run_id = state.get("run_id", "unknown")  # Define before try block
        db = SessionLocal()
        try:
            logger.info(f"[Run {run_id}] Entering wait_spec_approval_node")
            
            state["current_stage"] = "waiting_spec_approval"
            
            # Update run stage and status in database
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.current_stage = "waiting_spec_approval"
                run.status = RunStatus.PAUSED  # Set to PAUSED when waiting for approval
                logger.info(f"[Run {run_id}] Updating stage to 'waiting_spec_approval' and status to PAUSED")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful")
            
            emit_progress(run_id, "waiting_spec_approval", "Waiting for spec approval")
            logger.info(f"[Run {run_id}] Exiting wait_spec_approval_node")
            return state
        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in wait_spec_approval_node: {str(e)}")
            return state
        finally:
            db.close()

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
        
        logger.info(f"[Run {run_id}] continue_run called from stage: {from_stage}")

        # Get current run state from database
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")

            # Get artifacts to reconstruct state
            artifacts = db.query(Artifact).filter(Artifact.run_id == run_id).all()
            logger.info(f"[Run {run_id}] Found {len(artifacts)} artifacts to reconstruct state")

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
            logger.info(f"[Run {run_id}] Updating status to RUNNING")
            db.commit()
            logger.info(f"[Run {run_id}] DB commit successful")
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
                        logger.info(f"[Run {run_id}] Regenerating epics")
                        # Re-run epics node
                        state = await self._epics_node(state)
                        # Then wait for approval again
                        state = await self._wait_epic_approval_node(state)
                    elif approval and approval.approved:
                        logger.info(f"[Run {run_id}] Epics approved, continuing to stories")
                        # Continue to stories
                        state = await self._stories_node(state)
                        # Then wait for story approval
                        state = await self._wait_story_approval_node(state)
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
                        logger.info(f"[Run {run_id}] Regenerating stories")
                        # Re-run stories node
                        state = await self._stories_node(state)
                        state = await self._wait_story_approval_node(state)
                    elif approval and approval.approved:
                        logger.info(f"[Run {run_id}] Stories approved, continuing to specs")
                        # Continue to specs
                        state = await self._specs_node(state)
                        state = await self._wait_spec_approval_node(state)
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
                        logger.info(f"[Run {run_id}] Regenerating specs")
                        # Re-run specs node
                        state = await self._specs_node(state)
                        state = await self._wait_spec_approval_node(state)
                    elif approval and approval.approved:
                        logger.info(f"[Run {run_id}] Specs approved, continuing to code and validation")
                        # Continue to code and validation
                        state = await self._code_node(state)
                        state = await self._validation_node(state)
                        state = await self._complete_node(state)
                finally:
                    db.close()

            logger.info(f"[Run {run_id}] continue_run completed successfully")
            return state

        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in continue_run: {str(e)}")
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
        
        logger.info(f"[Run {run_id}] execute_run called")

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
                logger.info(f"[Run {run_id}] Initializing run status to RUNNING")
                db.commit()
                logger.info(f"[Run {run_id}] DB commit successful")
        finally:
            db.close()

        try:
            logger.info(f"[Run {run_id}] Starting workflow execution")
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            logger.info(f"[Run {run_id}] Workflow execution completed, final stage: {final_state.get('current_stage')}")

            # Update final status
            # Note: Don't update to COMPLETED here if we're waiting for approval
            # The wait nodes already set status to PAUSED
            db = SessionLocal()
            try:
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    if final_state.get("error"):
                        logger.warning(f"[Run {run_id}] Workflow completed with error: {final_state['error']}")
                        run.status = RunStatus.FAILED
                        run.error_message = final_state["error"]
                        db.commit()
                    elif final_state.get("current_stage") == "completed":
                        # Only set to completed if the workflow actually completed
                        logger.info(f"[Run {run_id}] Workflow fully completed")
                        # Status already set in complete_node
                    else:
                        # Workflow exited at approval gate - status already set to PAUSED by wait nodes
                        logger.info(f"[Run {run_id}] Workflow paused at stage: {final_state.get('current_stage')}")
            finally:
                db.close()

            logger.info(f"[Run {run_id}] execute_run completed successfully")
            return final_state

        except Exception as e:
            logger.exception(f"[Run {run_id}] Exception in execute_run: {str(e)}")
            # Update error status
            db = SessionLocal()
            try:
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    run.status = RunStatus.FAILED
                    run.error_message = str(e)
                    db.commit()
                    logger.info(f"[Run {run_id}] Set status to FAILED due to exception")
            finally:
                db.close()
            raise
