"""
Orchestrator using LangGraph for multi-agent workflow.
"""
from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
import operator

from app.agents.research_agent import ResearchAgent
from app.agents.epic_agent import EpicAgent
from app.agents.story_agent import StoryAgent
from app.agents.spec_agent import SpecAgent
from app.agents.code_agent import CodeAgent
from app.agents.validation_agent import ValidationAgent
from app.database import Run, Artifact, Approval, RunStatus, ArtifactType


class WorkflowState(TypedDict):
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
        
        # Add nodes for each stage
        workflow.add_node("research", self._research_node)
        workflow.add_node("epics", self._epics_node)
        workflow.add_node("wait_epic_approval", self._wait_epic_approval_node)
        workflow.add_node("stories", self._stories_node)
        workflow.add_node("wait_story_approval", self._wait_story_approval_node)
        workflow.add_node("specs", self._specs_node)
        workflow.add_node("wait_spec_approval", self._wait_spec_approval_node)
        workflow.add_node("code", self._code_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("complete", self._complete_node)
        
        # Define edges
        workflow.set_entry_point("research")
        workflow.add_edge("research", "epics")
        workflow.add_edge("epics", "wait_epic_approval")
        workflow.add_conditional_edges(
            "wait_epic_approval",
            self._check_approval,
            {
                "approved": "stories",
                "rejected": "epics",
                "pending": "wait_epic_approval"
            }
        )
        workflow.add_edge("stories", "wait_story_approval")
        workflow.add_conditional_edges(
            "wait_story_approval",
            self._check_approval,
            {
                "approved": "specs",
                "rejected": "stories",
                "pending": "wait_story_approval"
            }
        )
        workflow.add_edge("specs", "wait_spec_approval")
        workflow.add_conditional_edges(
            "wait_spec_approval",
            self._check_approval,
            {
                "approved": "code",
                "rejected": "specs",
                "pending": "wait_spec_approval"
            }
        )
        workflow.add_edge("code", "validation")
        workflow.add_edge("validation", "complete")
        workflow.add_edge("complete", END)
        
        return workflow.compile()
    
    async def _research_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Execute research phase."""
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
                result.get("metadata")
            )
        else:
            state["error"] = result.get("error", "Research failed")
        
        return state
    
    async def _epics_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Execute epic generation phase."""
        result = await self.epic_agent.execute({
            "product_request": state["product_request"],
            "research": state["research"]
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
                result.get("metadata")
            )
            
            # Create approval gate
            self._create_approval(db, state["run_id"], "epics")
        else:
            state["error"] = result.get("error", "Epic generation failed")
        
        return state
    
    async def _stories_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Execute story generation phase."""
        result = await self.story_agent.execute({
            "epics": state["epics"]
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
                result.get("metadata")
            )
            
            # Create approval gate
            self._create_approval(db, state["run_id"], "stories")
        else:
            state["error"] = result.get("error", "Story generation failed")
        
        return state
    
    async def _specs_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Execute spec generation phase."""
        result = await self.spec_agent.execute({
            "stories": state["stories"]
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
                result.get("metadata")
            )
            
            # Create approval gate
            self._create_approval(db, state["run_id"], "specs")
        else:
            state["error"] = result.get("error", "Spec generation failed")
        
        return state
    
    async def _code_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Execute code generation phase."""
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
                result.get("metadata")
            )
        else:
            state["error"] = result.get("error", "Code generation failed")
        
        return state
    
    async def _validation_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Execute validation phase."""
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
                result.get("metadata")
            )
        else:
            state["error"] = result.get("error", "Validation failed")
        
        return state
    
    async def _complete_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Complete the workflow."""
        state["current_stage"] = "completed"
        
        # Update run status
        run = db.query(Run).filter(Run.id == state["run_id"]).first()
        if run:
            run.status = RunStatus.COMPLETED
            run.current_stage = "completed"
            db.commit()
        
        return state
    
    async def _wait_epic_approval_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Wait for epic approval."""
        state["current_stage"] = "waiting_epic_approval"
        return state
    
    async def _wait_story_approval_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Wait for story approval."""
        state["current_stage"] = "waiting_story_approval"
        return state
    
    async def _wait_spec_approval_node(self, state: WorkflowState, db: Session) -> WorkflowState:
        """Wait for spec approval."""
        state["current_stage"] = "waiting_spec_approval"
        return state
    
    def _check_approval(self, state: WorkflowState, db: Session) -> str:
        """Check if current stage is approved."""
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
    
    def _save_artifact(
        self, 
        db: Session, 
        run_id: int, 
        artifact_type: ArtifactType,
        name: str,
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """Save an artifact to the database."""
        artifact = Artifact(
            run_id=run_id,
            artifact_type=artifact_type,
            name=name,
            content=content,
            metadata=metadata
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
    
    async def execute_run(self, run_id: int, product_request: str, db: Session):
        """
        Execute a complete run through the workflow.
        
        Args:
            run_id: ID of the run to execute
            product_request: Product request text
            db: Database session
        """
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
            "error": ""
        }
        
        # Update run status
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.status = RunStatus.RUNNING
            run.current_stage = "research"
            db.commit()
        
        try:
            # Execute workflow (simplified - in production, handle checkpointing)
            final_state = await self.workflow.ainvoke(initial_state, {"db": db})
            
            if final_state.get("error"):
                run.status = RunStatus.FAILED
                run.error_message = final_state["error"]
            else:
                run.status = RunStatus.COMPLETED
            
            db.commit()
            
            return final_state
            
        except Exception as e:
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            db.commit()
            raise
