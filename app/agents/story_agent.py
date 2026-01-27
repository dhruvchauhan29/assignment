"""
Story Agent - Generates user stories from epics.
"""
from typing import Dict, Any
from app.agents.base import BaseAgent


class StoryAgent(BaseAgent):
    """Agent responsible for generating user stories."""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate user stories from epics.
        
        Args:
            input_data: Contains 'epics' key
            
        Returns:
            Generated user stories with acceptance criteria
        """
        try:
            epics = input_data.get("epics", "")
            
            prompt = f"""
You are a Story generation agent. Based on the epics, generate detailed user stories.

Epics:
{epics}

For each epic, generate 3-5 user stories with:
- Story ID (US-XXX)
- Epic ID reference
- Title (As a [user], I want [action] so that [benefit])
- Description
- Acceptance Criteria (Given/When/Then format)
- Edge Cases
- Non-Functional Requirements (NFRs)
- Estimate (Story Points)

Format as:
## User Stories for [Epic ID]

### Story US-001: [Title]
**Epic:** EP-XXX
**As a** [user type]
**I want** [action]
**So that** [benefit]

**Description:** [Detailed description]

**Acceptance Criteria:**
- Given [context]
  When [action]
  Then [outcome]
- [More criteria]

**Edge Cases:**
- [Edge case 1]
- [Edge case 2]

**NFRs:**
- Performance: [requirement]
- Security: [requirement]

**Estimate:** X story points

[Continue for all stories]
"""
            
            response = await self.llm.ainvoke(prompt)
            stories_content = response.content
            
            metadata = {
                "story_count": stories_content.count("### Story"),
                "has_acceptance_criteria": "Acceptance Criteria:" in stories_content
            }
            
            return self.format_output(stories_content, metadata)
            
        except Exception as e:
            return self.format_error(e)
