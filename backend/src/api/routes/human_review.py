"""Human review endpoints for HITL workflow."""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from langgraph.types import Command

from ...schemas.review import (
    ReviewDecision,
    PendingReviewItem,
    PendingReviewsResponse,
    ReviewDecisionResponse,
)
from ...graph.workflow import create_invoice_workflow
from ...db.checkpoint_store import get_checkpointer
from ...db.models import HumanReviewQueue
from ..dependencies import get_db_session
from ...utils.logger import get_logger
from ...graph.nodes import set_thread_id

router = APIRouter(prefix="/human-review", tags=["Human Review"])
logger = get_logger("api.human_review")

# Reference to invoice module's state storage
from .invoice import _workflow_states


@router.get("/pending", response_model=PendingReviewsResponse)
async def get_pending_reviews(
    db: Session = Depends(get_db_session)
) -> PendingReviewsResponse:
    """
    Get all pending human reviews.
    
    Returns list of invoices waiting for human decision.
    """
    logger.info("Fetching pending reviews")
    
    try:
        # Query pending reviews from database
        pending = db.query(HumanReviewQueue).filter(
            HumanReviewQueue.status == "PENDING"
        ).all()
        
        items = []
        for review in pending:
            items.append(PendingReviewItem(
                checkpoint_id=review.checkpoint_id,
                thread_id=review.thread_id,
                invoice_id=review.invoice_id,
                vendor_name=review.vendor_name or "",
                amount=review.amount or 0,
                currency=review.currency or "USD",
                match_score=review.match_score,
                match_result=review.match_result,
                match_evidence=review.match_evidence,
                reason_for_hold=review.reason_for_hold or "",
                review_url=review.review_url or f"/human-review/{review.checkpoint_id}",
                created_at=review.created_at or datetime.now(timezone.utc)
            ))
        
        logger.info(f"Found {len(items)} pending reviews")
        
        return PendingReviewsResponse(
            items=items,
            total=len(items)
        )
        
    except Exception as e:
        logger.error(f"Error fetching pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{checkpoint_id}")
async def get_review_detail(
    checkpoint_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Get details of a specific review item.
    
    Args:
        checkpoint_id: Checkpoint ID to retrieve
    """
    logger.info(f"Fetching review detail for checkpoint: {checkpoint_id}")
    
    review = db.query(HumanReviewQueue).filter(
        HumanReviewQueue.checkpoint_id == checkpoint_id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail=f"Checkpoint not found: {checkpoint_id}")
    
    # Get additional state info
    stored = _workflow_states.get(review.thread_id, {})
    result = stored.get("result", {})
    
    return {
        "checkpoint_id": review.checkpoint_id,
        "thread_id": review.thread_id,
        "invoice_id": review.invoice_id,
        "vendor_name": review.vendor_name,
        "amount": review.amount,
        "currency": review.currency,
        "match_score": review.match_score,
        "match_result": review.match_result,
        "match_evidence": review.match_evidence,
        "reason_for_hold": review.reason_for_hold,
        "status": review.status,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        # Additional context from workflow state
        "vendor_profile": result.get("vendor_profile"),
        "matched_pos": result.get("matched_pos"),
        "matched_grns": result.get("matched_grns"),
        "parsed_invoice": result.get("parsed_invoice"),
    }


@router.post("/decision", response_model=ReviewDecisionResponse)
async def submit_decision(
    decision: ReviewDecision,
    db: Session = Depends(get_db_session)
) -> ReviewDecisionResponse:
    """
    Submit human review decision and resume workflow.
    
    Args:
        decision: Review decision payload with ACCEPT or REJECT
    """
    logger.info(
        f"Processing decision for checkpoint: {decision.checkpoint_id}, "
        f"decision: {decision.decision}"
    )
    
    try:
        # Update review queue record
        review = db.query(HumanReviewQueue).filter(
            HumanReviewQueue.checkpoint_id == decision.checkpoint_id
        ).first()
        
        if review:
            review.status = "REVIEWED"
            review.decision = decision.decision
            review.reviewer_id = decision.reviewer_id
            review.reviewer_notes = decision.notes
            review.reviewed_at = datetime.now(timezone.utc)
            db.commit()
        
        # Get stored workflow state
        stored = _workflow_states.get(decision.thread_id)
        if not stored:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow not found: {decision.thread_id}"
            )
        
        # Resume workflow with human decision in background task
        checkpointer = get_checkpointer()
        workflow = create_invoice_workflow(checkpointer)
        
        # Config with thread_id
        config = {"configurable": {"thread_id": decision.thread_id}}
        
        # Resume with Command containing the human decision
        logger.info(f"Resuming workflow with decision: {decision.decision}")
        
        resume_input = Command(resume={
            "decision": decision.decision,
            "reviewer_id": decision.reviewer_id,
            "notes": decision.notes or "",
        })
        
        # Run workflow resume in background task to not block SSE reconnection
        async def _resume_workflow_background():
            """Run resumed workflow in background so SSE can reconnect first."""
            await asyncio.sleep(0.5)  # Wait for SSE to reconnect
            set_thread_id(decision.thread_id)  # Set thread_id for event emission
            logger.info(f"[Background] Starting resumed workflow for thread: {decision.thread_id}")
            result = await workflow.ainvoke(resume_input, config)
            # Update stored state
            _workflow_states[decision.thread_id]["result"] = result
            logger.info(f"[Background] Resumed workflow completed for thread: {decision.thread_id}")
        
        # Start background task
        asyncio.create_task(_resume_workflow_background())
        
        # Determine next stage based on decision - return immediately
        if decision.decision == "ACCEPT":
            next_stage = "RECONCILE"
            status = "RUNNING"
            message = "Invoice accepted. Workflow resuming..."
        else:
            next_stage = "MANUAL_HANDOFF"
            status = "REQUIRES_MANUAL_HANDLING"
            message = "Invoice rejected. Requires manual handling."
        
        logger.info(
            f"Decision accepted for thread: {decision.thread_id}, "
            f"decision: {decision.decision}, workflow resuming in background"
        )
        
        return ReviewDecisionResponse(
            success=True,
            thread_id=decision.thread_id,
            checkpoint_id=decision.checkpoint_id,
            decision=decision.decision,
            next_stage=next_stage,
            status=status,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))
