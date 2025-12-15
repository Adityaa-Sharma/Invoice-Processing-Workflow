"""Invoice submission and status endpoints."""
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ...schemas.invoice import (
    InvoicePayload,
    InvoiceSubmitResponse,
    InvoiceStatusResponse,
)
from ...graph.workflow import create_invoice_workflow
from ...graph.state import create_initial_state
from ...db.checkpoint_store import get_checkpointer
from ...db.models import HumanReviewQueue
from ..dependencies import get_db_session
from ...utils.logger import get_logger

router = APIRouter(prefix="/invoice", tags=["Invoice"])
logger = get_logger("api.invoice")

# In-memory storage for demo (in production, use database)
_workflow_states = {}


@router.post("/submit", response_model=InvoiceSubmitResponse)
async def submit_invoice(
    invoice: InvoicePayload,
    db: Session = Depends(get_db_session)
) -> InvoiceSubmitResponse:
    """
    Submit an invoice for processing.
    
    Starts the invoice processing workflow and returns a thread_id
    for tracking the workflow status.
    """
    logger.info(f"Submitting invoice: {invoice.invoice_id}")
    
    try:
        # Generate unique thread ID for this workflow instance
        thread_id = str(uuid4())
        
        # Create workflow with checkpointer
        checkpointer = get_checkpointer()
        workflow = create_invoice_workflow(checkpointer)
        
        # Create initial state from invoice payload
        initial_state = create_initial_state(invoice.model_dump())
        
        # Config with thread_id for checkpoint tracking
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run workflow (will pause at HITL if needed)
        logger.info(f"Starting workflow for thread: {thread_id}")
        result = await workflow.ainvoke(initial_state, config)
        
        # Store result for status queries
        _workflow_states[thread_id] = {
            "result": result,
            "invoice_id": invoice.invoice_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # If workflow paused for HITL, add to review queue
        if result.get("status") == "PAUSED" and result.get("hitl_checkpoint_id"):
            _add_to_review_queue(db, thread_id, invoice, result)
        
        logger.info(
            f"Workflow completed/paused for thread: {thread_id}, "
            f"status: {result.get('status')}, stage: {result.get('current_stage')}"
        )
        
        return InvoiceSubmitResponse(
            thread_id=thread_id,
            status=result.get("status", "RUNNING"),
            current_stage=result.get("current_stage", "INTAKE"),
            message=_get_status_message(result)
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
