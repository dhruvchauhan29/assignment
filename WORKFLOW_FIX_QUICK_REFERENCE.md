# Workflow Fix - Quick Reference

## The Problem
```
User starts run → Workflow executes → Gets stuck
                                    ↓
                        Status: "running" forever
                        Stage: "research" forever  
                        Artifacts: [] empty
```

## The Fix

### 1. Status Flow (Before vs After)

**BEFORE:**
```
START → RUNNING → [exits at wait node] → RUNNING (stuck!)
```

**AFTER:**
```
START → RUNNING → [research] → PAUSED (waiting_epic_approval)
                                  ↓
                           [user approves]
                                  ↓
                           RUNNING → [stories] → PAUSED (waiting_story_approval)
                                                    ↓
                                             [user approves]
                                                    ↓
                                             RUNNING → COMPLETED
```

### 2. Artifact Generation (Before vs After)

**BEFORE:**
```
Agent Fails → No artifact saved → Endpoints return []
```

**AFTER:**
```
Agent Fails → Fallback stub generated → Endpoints return data
                                          ↓
                                   {"fallback": true}
```

### 3. Wait Nodes (Before vs After)

**BEFORE:**
```python
async def _wait_epic_approval_node(self, state):
    state["current_stage"] = "waiting_epic_approval"
    return state
    # ❌ Database not updated!
```

**AFTER:**
```python
async def _wait_epic_approval_node(self, state):
    db = SessionLocal()
    try:
        run.current_stage = "waiting_epic_approval"
        run.status = RunStatus.PAUSED  # ✅ Key fix
        db.commit()  # ✅ Persisted to DB
        emit_progress(...)  # ✅ SSE event
        return state
    finally:
        db.close()
```

### 4. Error Handling (Before vs After)

**BEFORE:**
```python
result = await agent.execute(...)
if result["success"]:
    save_artifact(...)
else:
    # ❌ Nothing happens, silent failure
```

**AFTER:**
```python
try:
    result = await agent.execute(...)
    if result["success"]:
        save_artifact(...)
    else:
        # ✅ Generate fallback
        save_fallback_artifact(...)
except Exception as e:
    logger.exception(...)  # ✅ Full logging
    save_fallback_artifact(...)  # ✅ Always save something
```

## Expected API Responses

### After Run Start
```bash
POST /api/runs/1/start
# Returns immediately with:
{"status": "started", "run_id": 1}
```

### Checking Status (after research completes)
```bash
GET /api/runs/1/status
{
  "run_id": 1,
  "status": "paused",           # ✅ Not "running"
  "current_stage": "waiting_epic_approval"  # ✅ Not "research"
}
```

### Getting Artifacts
```bash
GET /api/runs/1/artifacts
[
  {
    "id": 1,
    "artifact_type": "research",
    "name": "research.md",
    "content": "# Research Report\n...",
    "metadata": {"urls_consulted": [...]}
  }
]
# ✅ Always returns at least fallback data
```

### Getting Epics
```bash
GET /api/runs/1/epics
[
  {
    "id": 2,
    "artifact_type": "epics",
    "name": "epics.md",
    "content": "# Epics\n## Epic EP-001...",
    "metadata": {"epic_count": 3}
  }
]
# ✅ Non-empty array
```

### Progress Stream
```bash
GET /api/runs/1/progress
# SSE events:
event: progress
data: {"stage": "research", "message": "Research phase started"}

event: progress
data: {"stage": "research", "message": "Research phase completed"}

event: progress
data: {"stage": "epics", "message": "Epic generation started"}

event: progress
data: {"stage": "epics", "message": "Epic generation completed"}

event: progress
data: {"stage": "waiting_epic_approval", "message": "Waiting for epic approval"}
```

## Logging Output Example

```
2026-01-28 08:54:47 INFO [Run 1] execute_run called
2026-01-28 08:54:47 INFO [Run 1] Initializing run status to RUNNING
2026-01-28 08:54:47 INFO [Run 1] DB commit successful
2026-01-28 08:54:47 INFO [Run 1] Starting workflow execution
2026-01-28 08:54:47 INFO [Run 1] Entering research_node
2026-01-28 08:54:47 INFO [Run 1] Updating current_stage to 'research'
2026-01-28 08:54:47 INFO [Run 1] DB commit successful for stage update
2026-01-28 08:54:47 INFO [Run 1] Executing research agent
2026-01-28 08:54:48 INFO [Run 1] Research agent succeeded, content length: 1523
2026-01-28 08:54:48 INFO [Run 1] Saving research artifact
2026-01-28 08:54:48 INFO [Run 1] Research artifact saved successfully
2026-01-28 08:54:48 INFO [Run 1] Exiting research_node
2026-01-28 08:54:48 INFO [Run 1] Entering epics_node
2026-01-28 08:54:48 INFO [Run 1] Updating current_stage to 'epics'
2026-01-28 08:54:48 INFO [Run 1] DB commit successful for stage update
2026-01-28 08:54:48 INFO [Run 1] Executing epic agent
2026-01-28 08:54:49 INFO [Run 1] Epic agent succeeded, content length: 2341
2026-01-28 08:54:49 INFO [Run 1] Saving epics artifact
2026-01-28 08:54:49 INFO [Run 1] Epics artifact saved successfully
2026-01-28 08:54:49 INFO [Run 1] Approval gate created/updated
2026-01-28 08:54:49 INFO [Run 1] Exiting epics_node
2026-01-28 08:54:49 INFO [Run 1] Entering wait_epic_approval_node
2026-01-28 08:54:49 INFO [Run 1] Updating stage to 'waiting_epic_approval' and status to PAUSED
2026-01-28 08:54:49 INFO [Run 1] DB commit successful
2026-01-28 08:54:49 INFO [Run 1] Exiting wait_epic_approval_node
2026-01-28 08:54:49 INFO [Run 1] Workflow paused at stage: waiting_epic_approval
2026-01-28 08:54:49 INFO [Run 1] execute_run completed successfully
```

## Summary of Changes

| Area | Lines Changed | Description |
|------|---------------|-------------|
| Logging | ~100 | Entry/exit, DB commits, exceptions |
| Error Handling | ~200 | Try-catch, fallbacks, exception handlers |
| Wait Nodes | ~150 | DB session, status=PAUSED, commit |
| Fallback Generation | ~100 | Stub artifacts for all stages |
| Total | **~550** | Comprehensive workflow improvements |

## Key Takeaways

✅ **Artifacts always exist** - Real or fallback data at every stage
✅ **Status is correct** - PAUSED when waiting, not stuck on RUNNING
✅ **Stage advances** - Goes beyond research to waiting_epic_approval
✅ **Full visibility** - Comprehensive logging shows exactly what's happening
✅ **Graceful failures** - Errors don't break the workflow, fallbacks generated
✅ **System is usable** - All endpoints return data, workflow progresses
