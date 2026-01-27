"""
Observability integration with Langfuse.
"""
from typing import Optional
from langfuse import Langfuse
from app.config import get_settings

settings = get_settings()


class ObservabilityService:
    """Service for observability and tracing."""
    
    def __init__(self):
        """Initialize Langfuse client if configured."""
        self.enabled = bool(settings.langfuse_public_key and settings.langfuse_secret_key)
        
        if self.enabled:
            self.langfuse = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host
            )
        else:
            self.langfuse = None
    
    def trace_llm_call(
        self,
        name: str,
        run_id: int,
        input_text: str,
        output_text: str,
        metadata: Optional[dict] = None
    ):
        """
        Trace an LLM call.
        
        Args:
            name: Name of the operation
            run_id: Run ID
            input_text: Input prompt
            output_text: LLM output
            metadata: Additional metadata
        """
        if not self.enabled:
            return
        
        try:
            self.langfuse.trace(
                name=name,
                user_id=str(run_id),
                metadata=metadata or {}
            )
        except Exception as e:
            # Don't fail if observability fails
            print(f"Observability error: {e}")
    
    def flush(self):
        """Flush pending traces."""
        if self.enabled and self.langfuse:
            self.langfuse.flush()


# Global observability service instance
observability = ObservabilityService()
