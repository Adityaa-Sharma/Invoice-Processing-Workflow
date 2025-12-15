"""Workflow status and management endpoints."""
from fastapi import APIRouter, HTTPException

from ...schemas.response import WorkflowStatusResponse, WorkflowStage
from ...graph.workflow import get_workflow_stages
from ...utils.logger import get_logger

router = APIRouter(prefix="/workflow", tags=["Workflow"])
logger = get_logger("api.workflow")

# Reference to invoice module's state storage
from .invoice import _workflow_states


@router.get("/stages", response_model=list[WorkflowStage])
async def get_stages() -> list[WorkflowStage]:
    """
    Get list of all workflow stages.
    
    Returns the 12 stages with their mode (deterministic/non-deterministic).
    """
    stages = get_workflow_stages()
    return [
        WorkflowStage(
            id=s["id"],
            name=s["name"],
            mode=s["mode"]
        )
        for s in stages
    ]


@router.get("/status/{thread_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(thread_id: str) -> WorkflowStatusResponse:
    """
    Get detailed workflow status for a thread.
    
    Args:
        thread_id: Workflow thread ID
    """
    logger.info(f"Getting workflow status for thread: {thread_id}")
    
    stored = _workflow_states.get(thread_id)
    if not stored:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {thread_id}")
    
    result = stored.get("result", {})
    invoice = result.get("invoice_payload", {})
    
    # Determine completed and pending stages
    all_stages = [s["id"] for s in get_workflow_stages()]
    current_stage = result.get("current_stage", "")
    
    completed = []
    pending = []
    found_current = False
    
    for stage in all_stages:
        if stage == current_stage:
            found_current = True
            if result.get("status") == "COMPLETED":
                completed.append(stage)
            else:
                pending.append(stage)
        elif found_current:
            pending.append(stage)
        else:
            completed.append(stage)
    
    # Determine if HITL is needed
    requires_hitl = (
        result.get("status") == "PAUSED" and
        result.get("hitl_checkpoint_id") is not None
    )
    
    return WorkflowStatusResponse(
        thread_id=thread_id,
        invoice_id=invoice.get("invoice_id"),
        status=result.get("status", "UNKNOWN"),
        current_stage=current_stage,
        stages_completed=completed,
        stages_pending=pending,
        requires_human_review=requires_hitl,
        checkpoint_id=result.get("hitl_checkpoint_id"),
        review_url=result.get("review_url"),
        match_score=result.get("match_score"),
        match_result=result.get("match_result"),
        erp_txn_id=result.get("erp_txn_id"),
        final_payload=result.get("final_payload"),
        bigtool_selections=result.get("bigtool_selections", {}),
        audit_log=result.get("audit_log", [])
    )


@router.get("/all")
async def list_all_workflows():
    """
    List all workflow threads.
    
    Returns summary of all tracked workflows.
    """
    workflows = []
    
    for thread_id, stored in _workflow_states.items():
        result = stored.get("result", {})
        workflows.append({
            "thread_id": thread_id,
            "invoice_id": stored.get("invoice_id"),
            "status": result.get("status", "UNKNOWN"),
            "current_stage": result.get("current_stage", ""),
            "created_at": stored.get("created_at")
        })
    
    return {
        "workflows": workflows,
        "total": len(workflows)
    }
