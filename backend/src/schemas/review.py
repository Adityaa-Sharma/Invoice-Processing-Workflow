"""Human review related Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReviewDecision(BaseModel):
    """Human review decision payload."""
    thread_id: str = Field(..., description="Workflow thread ID")
    checkpoint_id: str = Field(..., description="Checkpoint ID to resume")
    decision: str = Field(..., pattern="^(ACCEPT|REJECT)$", description="Review decision")
    notes: Optional[str] = Field(None, description="Reviewer notes")
    reviewer_id: str = Field(..., description="Reviewer identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "abc123-def456",
                "checkpoint_id": "CHKPT-ABC123",
                "decision": "ACCEPT",
                "notes": "Verified with vendor. Amount matches after discount.",
                "reviewer_id": "reviewer-001"
            }
        }


class PendingReviewItem(BaseModel):
    """Single item in the human review queue."""
    checkpoint_id: str = Field(..., description="Checkpoint ID")
    thread_id: str = Field(..., description="Workflow thread ID")
    invoice_id: str = Field(..., description="Invoice identifier")
    vendor_name: str = Field(..., description="Vendor name")
    amount: float = Field(..., description="Invoice amount")
    currency: str = Field(default="USD", description="Currency")
    match_score: Optional[float] = Field(None, description="Match score (0-1)")
    match_result: Optional[str] = Field(None, description="Match result")
    match_evidence: Optional[dict] = Field(None, description="Match evidence details")
    reason_for_hold: str = Field(..., description="Reason invoice is held for review")
    review_url: str = Field(..., description="URL for review page")
    created_at: datetime = Field(..., description="When review was created")
    
    class Config:
        json_schema_extra = {
            "example": {
                "checkpoint_id": "CHKPT-ABC123",
                "thread_id": "abc123-def456",
                "invoice_id": "INV-2024-001",
                "vendor_name": "Acme Corp",
                "amount": 15000.0,
                "currency": "USD",
                "match_score": 0.75,
                "match_result": "FAILED",
                "match_evidence": {
                    "matched_fields": ["vendor", "currency"],
                    "mismatched_fields": ["amount", "line_items_count"]
                },
                "reason_for_hold": "Match score 0.75 below threshold 0.90",
                "review_url": "/human-review/CHKPT-ABC123",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class PendingReviewsResponse(BaseModel):
    """Response containing list of pending reviews."""
    items: list[PendingReviewItem] = Field(..., description="List of pending reviews")
    total: int = Field(..., description="Total count of pending reviews")


class ReviewDecisionResponse(BaseModel):
    """Response after submitting review decision."""
    success: bool = Field(..., description="Whether decision was processed")
    thread_id: str = Field(..., description="Workflow thread ID")
    checkpoint_id: str = Field(..., description="Checkpoint ID")
    decision: str = Field(..., description="Decision made")
    next_stage: Optional[str] = Field(None, description="Next workflow stage")
    status: str = Field(..., description="New workflow status")
    message: str = Field(..., description="Status message")
