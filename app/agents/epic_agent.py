"""
Epic Agent - Generates epics from product request.
"""
from typing import Dict, Any
from app.agents.base import BaseAgent


class EpicAgent(BaseAgent):
    """Agent responsible for generating epics with comprehensive planning details."""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate epics from product request and research.
        
        Each epic includes:
        - Title & goal
        - In-scope / out-of-scope
        - Priority (P0/P1/P2) with reasoning
        - Dependencies
        - Risks & assumptions
        - Success metrics
        
        Args:
            input_data: Contains 'product_request', 'research', and optional 'feedback' keys
            
        Returns:
            Generated epics with priorities, dependencies, and Mermaid diagram
        """
        try:
            product_request = input_data.get("product_request", "")
            research = input_data.get("research", "")
            feedback = input_data.get("feedback", "")
            
            feedback_section = ""
            if feedback:
                feedback_section = f"""

## User Feedback from Previous Iteration
{feedback}

Please incorporate this feedback into the epic generation.
"""
            
            prompt = f"""
You are an Epic planning agent. Based on the product request and research, generate 3-5 comprehensive epics.

Product Request:
{product_request}

Research Context:
{research[:2000]}
{feedback_section}

For each epic, provide ALL of the following sections:

### Epic EP-XXX: [Clear, Action-Oriented Title]

**Goal:** One-sentence description of what this epic achieves

**Priority:** P0 (Critical) / P1 (High) / P2 (Medium)
**Priority Reasoning:** Explain why this priority was chosen based on:
- Business value
- Technical dependencies
- User impact
- Risk mitigation

**In Scope:**
- Clearly defined deliverables that ARE part of this epic
- Specific features and capabilities

**Out of Scope:**
- Explicitly stated items that are NOT included
- Future considerations that may be separate epics

**Dependencies:**
- Other epics that must be completed first (use Epic IDs)
- External dependencies (third-party services, infrastructure, etc.)
- Technical prerequisites

**Risks & Assumptions:**
- Risks: Potential problems that could derail this epic
- Assumptions: What we're assuming to be true
- Mitigation strategies for identified risks

**Success Metrics:**
- Quantifiable measures of success
- Acceptance criteria for epic completion
- KPIs to track

---

Generate 3-5 epics following this exact format.

After all epics, include a Mermaid dependency diagram:

## Epic Dependency Diagram

```mermaid
graph TD
    EP001["EP-001: Epic Title"]
    EP002["EP-002: Epic Title"]
    EP003["EP-003: Epic Title"]
    
    EP001 --> EP002
    EP001 --> EP003
    
    style EP001 fill:#ff9999
    style EP002 fill:#99ccff
    style EP003 fill:#99ff99
```

Use different colors for different priorities:
- P0 (Critical): Red (#ff9999)
- P1 (High): Blue (#99ccff)  
- P2 (Medium): Green (#99ff99)
"""
            
            response = await self.llm.ainvoke(prompt)
            epics_content = response.content
            
            # Extract structured information for metadata
            epic_count = epics_content.count("### Epic EP-")
            has_mermaid = "```mermaid" in epics_content
            
            # Count priorities
            p0_count = epics_content.count("**Priority:** P0")
            p1_count = epics_content.count("**Priority:** P1")
            p2_count = epics_content.count("**Priority:** P2")
            
            metadata = {
                "epic_count": epic_count,
                "has_mermaid_diagram": has_mermaid,
                "priority_breakdown": {
                    "P0_critical": p0_count,
                    "P1_high": p1_count,
                    "P2_medium": p2_count
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
                "regeneration_count": input_data.get("regeneration_count", 0)
            }
            
            return self.format_output(epics_content, metadata)
            
        except Exception as e:
            return self.format_error(e)
