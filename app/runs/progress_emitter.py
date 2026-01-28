"""
Progress emitter for SSE events.
"""
from datetime import datetime
from typing import Dict, Any, Optional

# In-memory store for SSE connections (in production, use Redis/message queue)
run_updates: Dict[int, list] = {}


def emit_progress(run_id: int, stage: str, message: str, data: Optional[Dict[str, Any]] = None):
    """
    Emit a progress update for SSE streaming.
    
    Args:
        run_id: ID of the run
        stage: Current stage (research, epics, stories, specs, code, validation)
        message: Progress message
        data: Optional additional data
    """
    if run_id not in run_updates:
        run_updates[run_id] = []
    
    update = {
        "stage": stage,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data:
        update["data"] = data
    
    run_updates[run_id].append(update)


def get_updates(run_id: int, from_index: int = 0) -> list:
    """
    Get progress updates for a run.
    
    Args:
        run_id: ID of the run
        from_index: Index to start from
        
    Returns:
        List of updates from the specified index
    """
    if run_id not in run_updates:
        return []
    
    return run_updates[run_id][from_index:]


def clear_updates(run_id: int):
    """
    Clear progress updates for a run.
    
    Args:
        run_id: ID of the run
    """
    if run_id in run_updates:
        del run_updates[run_id]
