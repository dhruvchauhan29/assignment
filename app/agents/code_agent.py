"""
Code Agent - Generates code from specifications.
"""
from typing import Dict, Any
from app.agents.base import BaseAgent


class CodeAgent(BaseAgent):
    """Agent responsible for generating code."""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code from specifications.
        
        Args:
            input_data: Contains 'specs' key
            
        Returns:
            Generated code files and tests
        """
        try:
            specs = input_data.get("specs", "")
            
            prompt = f"""
You are a Code generation agent. Based on specifications, generate production-ready code.

Specifications:
{specs}

Generate:
1. Implementation files (Python/FastAPI preferred)
2. Test files (pytest)
3. Configuration files if needed
4. README with setup instructions

For each file, format as:
## File: path/to/file.py
```python
# Code here
```

## File: tests/test_file.py
```python
# Test code here
```

Include:
- Type hints
- Docstrings
- Error handling
- Input validation
- Comprehensive tests
- Clear structure

Generate modular, maintainable code following best practices.
"""
            
            response = await self.llm.ainvoke(prompt)
            code_content = response.content
            
            # Count generated files
            file_count = code_content.count("## File:")
            
            metadata = {
                "file_count": file_count,
                "has_tests": "test_" in code_content or "tests/" in code_content,
                "language": "python"
            }
            
            return self.format_output(code_content, metadata)
            
        except Exception as e:
            return self.format_error(e)
