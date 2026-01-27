"""
Research Agent - Performs web search and gathers context.
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from app.agents.base import BaseAgent


class ResearchAgent(BaseAgent):
    """Agent responsible for researching the product domain."""
    
    def __init__(self):
        super().__init__()
        self.max_urls = 5
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute research on the product request.
        
        Args:
            input_data: Contains 'product_request' key
            
        Returns:
            Research findings with URLs and summaries
        """
        try:
            product_request = input_data.get("product_request", "")
            
            # Create research prompt
            prompt = f"""
You are a research agent tasked with understanding the product domain.

Product Request:
{product_request}

Please provide:
1. Key concepts and technologies relevant to this product
2. Similar existing products or solutions
3. Important considerations for implementation
4. Potential challenges or risks

Format your response as structured research findings.
"""
            
            # For now, simulate research (in production, integrate Tavily or similar)
            response = await self.llm.ainvoke(prompt)
            research_content = response.content
            
            # Simulate URLs (in production, these would come from actual web search)
            urls = [
                {
                    "url": f"https://example.com/research-{i}",
                    "title": f"Research Finding {i}",
                    "summary": f"Summary of research finding {i} related to: {product_request[:50]}"
                }
                for i in range(1, self.max_urls + 1)
            ]
            
            metadata = {
                "urls": urls,
                "total_urls": len(urls)
            }
            
            return self.format_output(research_content, metadata)
            
        except Exception as e:
            return self.format_error(e)
