"""
Epic Agent - Generates epics from product request.
"""
from typing import Dict, Any
from app.agents.base import BaseAgent


class EpicAgent(BaseAgent):
    """Agent responsible for generating epics."""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate epics from product request and research.
        
        Args:
            input_data: Contains 'product_request' and 'research' keys
            
        Returns:
            Generated epics with priorities and dependencies
        """
        try:
            product_request = input_data.get("product_request", "")
            research = input_data.get("research", "")
            
            prompt = f"""
You are an Epic planning agent. Based on the product request and research, generate 3-5 epics.

Product Request:
{product_request}

Research Context:
{research[:1000]}

For each epic, provide:
- Epic ID (EP-XXX)
- Title
- Description
- Priority (Critical/High/Medium/Low)
- Scope
- Dependencies (if any)
- Success Metrics
- Potential Risks

Also generate a Mermaid diagram showing epic dependencies.

Format as:
## Epics

### Epic EP-001: [Title]
**Priority:** [Priority]
**Description:** [Description]
**Scope:** [Scope]
**Dependencies:** [Dependencies]
**Success Metrics:** [Metrics]
**Risks:** [Risks]

[Continue for all epics]

## Dependency Diagram
```mermaid
graph TD
    EP001[Epic 1]
    EP002[Epic 2]
    EP001 --> EP002
```
"""
            
            response = await self.llm.ainvoke(prompt)
            epics_content = response.content
            
            metadata = {
                "epic_count": epics_content.count("### Epic"),
                "has_mermaid": "```mermaid" in epics_content
            }
            
            return self.format_output(epics_content, metadata)
            
        except Exception as e:
            return self.format_error(e)
