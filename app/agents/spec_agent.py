"""
Spec Agent - Generates formal specifications from stories.
"""
from typing import Dict, Any
from app.agents.base import BaseAgent


class SpecAgent(BaseAgent):
    """Agent responsible for generating formal specifications."""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate formal specifications from user stories.
        
        Args:
            input_data: Contains 'stories' key
            
        Returns:
            Generated specifications with API contracts and data models
        """
        try:
            stories = input_data.get("stories", "")
            
            prompt = f"""
You are a Specification agent. Based on user stories, generate formal technical specifications.

User Stories:
{stories}

For each story, provide:
- Spec ID (SPEC-XXX)
- Story ID reference
- Technical Requirements
- API Contracts (endpoints, methods, request/response schemas)
- Data Models (database schemas, types)
- Security Requirements
- Validation Rules
- Test Cases
- Implementation Notes

Format as:
## Specification SPEC-001
**Story:** US-XXX

### Technical Requirements
1. [Requirement 1]
2. [Requirement 2]

### API Contracts
```
POST /api/endpoint
Request: {{ "field": "type" }}
Response: {{ "field": "type" }}
```

### Data Models
```python
class Model:
    field: type
```

### Security
- Authentication: [method]
- Authorization: [rules]
- Data Protection: [approach]

### Validation Rules
- [Rule 1]
- [Rule 2]

### Test Cases
1. Test: [description]
   - Given: [context]
   - When: [action]
   - Then: [expected]

### Implementation Notes
- [Note 1]
- [Note 2]

[Continue for all specs]
"""
            
            response = await self.llm.ainvoke(prompt)
            spec_content = response.content
            
            metadata = {
                "spec_count": spec_content.count("## Specification"),
                "has_api_contracts": "API Contracts" in spec_content,
                "has_data_models": "Data Models" in spec_content,
                "has_test_cases": "Test Cases" in spec_content
            }
            
            return self.format_output(spec_content, metadata)
            
        except Exception as e:
            return self.format_error(e)
