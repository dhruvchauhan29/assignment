"""
Validation Agent - Validates generated code.
"""
from typing import Dict, Any
from app.agents.base import BaseAgent


class ValidationAgent(BaseAgent):
    """Agent responsible for validating generated code."""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate generated code.
        
        Args:
            input_data: Contains 'code' key
            
        Returns:
            Validation report with issues and suggestions
        """
        try:
            code = input_data.get("code", "")
            
            prompt = f"""
You are a Validation agent. Analyze the generated code and provide a validation report.

Code to Validate:
{code[:2000]}

Check for:
1. Syntax errors
2. Type inconsistencies
3. Missing error handling
4. Security vulnerabilities
5. Code style issues
6. Missing tests
7. Documentation gaps
8. Performance concerns

Format report as:
## Validation Report

### Summary
- Total Issues: X
- Critical: X
- High: X
- Medium: X
- Low: X

### Issues

#### Critical Issues
1. [Issue description]
   - Location: [file:line]
   - Fix: [suggested fix]

#### High Priority Issues
1. [Issue description]

#### Medium Priority Issues
1. [Issue description]

#### Low Priority Issues
1. [Issue description]

### Recommendations
- [Recommendation 1]
- [Recommendation 2]

### Test Coverage
- [Coverage analysis]

### Overall Score: X/10
"""
            
            response = await self.llm.ainvoke(prompt)
            validation_content = response.content
            
            # Extract score if present
            score = 0
            if "Overall Score:" in validation_content:
                try:
                    score_line = [line for line in validation_content.split('\n') if 'Overall Score:' in line][0]
                    score = int(score_line.split(':')[1].split('/')[0].strip())
                except:
                    score = 0
            
            metadata = {
                "has_critical_issues": "Critical Issues" in validation_content and validation_content.count("1.") > 0,
                "overall_score": score
            }
            
            return self.format_output(validation_content, metadata)
            
        except Exception as e:
            return self.format_error(e)
