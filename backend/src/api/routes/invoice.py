"""Invoice submission and status endpoints."""
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from ...schemas.invoice import (
    InvoicePayload,
    InvoiceSubmitResponse,
    InvoiceStatusResponse,
)
from ...graph.workflow import create_invoice_workflow
from ...graph.state import create_initial_state
from ...graph.nodes import set_thread_id
from ...db.checkpoint_store import get_checkpointer
from ...db.models import HumanReviewQueue
from ..dependencies import get_db_session
from ...utils.logger import get_logger
from ...services.event_emitter import emit_log_message, emit_workflow_complete

router = APIRouter(prefix="/invoice", tags=["Invoice"])
logger = get_logger("api.invoice")

# In-memory storage for demo (in production, use database)
_workflow_states = {}


async def _run_workflow_async(
    thread_id: str,
    invoice_dict: dict,
    db_session_factory
) -> None:
    """
    Run the workflow asynchronously in the background.
    This allows the SSE connection to be established before workflow starts.
    """
    try:
        # Delay to ensure SSE connection is established by frontend
        await asyncio.sleep(1.0)
        
        # Set thread ID for event emission in this context (backup for ContextVar)
        set_thread_id(thread_id)
        
        # Emit starting event
        await emit_log_message(thread_id, "info", f"🚀 Workflow execution starting...")
        
        # Get checkpointer and create workflow
        checkpointer = get_checkpointer()
        workflow = create_invoice_workflow(checkpointer)
        
        # Create initial state from invoice payload WITH thread_id
        initial_state = create_initial_state(invoice_dict, thread_id=thread_id)
        
        # Config with thread_id for checkpoint tracking
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run workflow
        logger.info(f"🚀 Background workflow starting for thread: {thread_id}")
        result = await workflow.ainvoke(initial_state, config)
        
        # Store result for status queries
        _workflow_states[thread_id] = {
            "result": result,
            "invoice_id": invoice_dict.get("invoice_id"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if workflow is paused for HITL (don't emit workflow_complete yet)
        current_stage = result.get("current_stage", "")
        status = result.get("status", "")
        
        if current_stage == "CHECKPOINT_HITL" or status == "PAUSED":
            logger.info(
                f"⏸️ Workflow paused for HITL for thread: {thread_id}, "
                f"stage: {current_stage}, awaiting human decision"
            )
            # Don't emit workflow_complete - workflow will resume after HITL decision
            return
        
        # Emit workflow complete event (only if actually complete)
        final_status = result.get("status", "COMPLETED")
        await emit_workflow_complete(thread_id, final_status, {
            "current_stage": result.get("current_stage"),
            "match_result": result.get("match_result"),
        })
        
        logger.info(
            f"✅ Background workflow completed for thread: {thread_id}, "
            f"status: {result.get('status')}, stage: {result.get('current_stage')}"
        )
        
    except Exception as e:
        logger.error(f"❌ Background workflow error for thread {thread_id}: {e}")
        await emit_workflow_complete(thread_id, "FAILED", {"error": str(e)})
        _workflow_states[thread_id] = {
            "result": {"status": "FAILED", "error": str(e)},
            "invoice_id": invoice_dict.get("invoice_id"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }


@router.post("/submit", response_model=InvoiceSubmitResponse)
async def submit_invoice(
    invoice: InvoicePayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
) -> InvoiceSubmitResponse:
    """
    Submit an invoice for processing.
    
    Starts the invoice processing workflow in the background and returns 
    a thread_id immediately for SSE subscription.
    """
    logger.info(f"Submitting invoice: {invoice.invoice_id}")
    
    try:
        # Generate unique thread ID for this workflow instance
        thread_id = str(uuid4())
        
        # Initialize workflow state as PENDING
        _workflow_states[thread_id] = {
            "result": {"status": "PENDING", "current_stage": "INTAKE"},
            "invoice_id": invoice.invoice_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Emit initial log (before background task starts)
        await emit_log_message(thread_id, "info", f"📋 Invoice {invoice.invoice_id} received, preparing workflow...")
        
        # Schedule workflow to run in background using asyncio.create_task
        # This allows the response to return immediately so frontend can connect to SSE
        asyncio.create_task(_run_workflow_async(
            thread_id=thread_id,
            invoice_dict=invoice.model_dump(),
            db_session_factory=None  # We'll handle DB in background if needed
        ))
        
        logger.info(f"📤 Workflow scheduled for thread: {thread_id}, returning immediately")
        
        return InvoiceSubmitResponse(
            thread_id=thread_id,
            status="RUNNING",
            current_stage="INTAKE",
            message=f"Workflow started for invoice {invoice.invoice_id}. Connect to SSE for real-time updates."
        )
        
    except Exception as e:
        logger.error(f"Error submitting invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{thread_id}", response_model=InvoiceStatusResponse)
async def get_invoice_status(thread_id: str) -> InvoiceStatusResponse:
    """
    Get the current status of an invoice workflow.
    
    Args:
        thread_id: Workflow thread ID from submission
    """
    logger.info(f"Getting status for thread: {thread_id}")
    
    # Check in-memory storage
    stored = _workflow_states.get(thread_id)
    if not stored:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    
    result = stored.get("result", {})
    
    return InvoiceStatusResponse(
        thread_id=thread_id,
        invoice_id=stored.get("invoice_id", ""),
        status=result.get("status", "UNKNOWN"),
        current_stage=result.get("current_stage", ""),
        match_score=result.get("match_score"),
        match_result=result.get("match_result"),
        checkpoint_id=result.get("hitl_checkpoint_id"),
        review_url=result.get("review_url"),
        erp_txn_id=result.get("erp_txn_id"),
        final_payload=result.get("final_payload"),
        audit_log=result.get("audit_log", []),
        bigtool_selections=result.get("bigtool_selections", {})
    )


def _add_to_review_queue(
    db: Session,
    thread_id: str,
    invoice: InvoicePayload,
    result: dict
) -> None:
    """Add invoice to human review queue."""
    try:
        review_item = HumanReviewQueue(
            id=str(uuid4()),
            thread_id=thread_id,
            checkpoint_id=result.get("hitl_checkpoint_id", ""),
            invoice_id=invoice.invoice_id,
            vendor_name=invoice.vendor_name,
            amount=invoice.amount,
            currency=invoice.currency,
            match_score=result.get("match_score"),
            match_result=result.get("match_result"),
            match_evidence=result.get("match_evidence"),
            reason_for_hold=result.get("paused_reason", "Match failed"),
            review_url=result.get("review_url"),
            status="PENDING"
        )
        
        db.add(review_item)
        db.commit()
        logger.info(f"Added invoice {invoice.invoice_id} to review queue")
        
    except Exception as e:
        logger.error(f"Error adding to review queue: {e}")
        db.rollback()


def _get_status_message(result: dict) -> str:
    """Generate status message based on workflow result."""
    status = result.get("status", "")
    stage = result.get("current_stage", "")
    
    if status == "COMPLETED":
        return f"Invoice processing completed successfully. Transaction ID: {result.get('erp_txn_id', 'N/A')}"
    elif status == "PAUSED":
        return f"Invoice requires human review. Checkpoint: {result.get('hitl_checkpoint_id', 'N/A')}"
    elif status == "REQUIRES_MANUAL_HANDLING":
        return "Invoice rejected during review. Requires manual handling."
    elif status == "FAILED":
        return f"Invoice processing failed at {stage}: {result.get('error', 'Unknown error')}"
    else:
        return f"Invoice processing in progress. Current stage: {stage}"
