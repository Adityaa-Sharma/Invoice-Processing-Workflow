"""Common response Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Current server time")
    database: str = Field(..., description="Database connection status")


class WorkflowStage(BaseModel):
    """Workflow stage information."""
    id: str = Field(..., description="Stage identifier")
    name: str = Field(..., description="Stage display name")
    mode: str = Field(..., description="deterministic or non-deterministic")
    status: Optional[str] = Field(None, description="Stage completion status")


class WorkflowStatusResponse(BaseModel):
    """Detailed workflow status response."""
    thread_id: str = Field(..., description="Workflow thread ID")
    invoice_id: Optional[str] = Field(None, description="Invoice identifier")
    status: str = Field(..., description="Current workflow status")
    current_stage: str = Field(..., description="Current processing stage")
    
    # Stage details
    stages_completed: list[str] = Field(default=[], description="Completed stages")
    stages_pending: list[str] = Field(default=[], description="Pending stages")
    
    # HITL info
    requires_human_review: bool = Field(default=False, description="Whether HITL is needed")
    checkpoint_id: Optional[str] = Field(None, description="Checkpoint ID if paused")
    review_url: Optional[str] = Field(None, description="Review URL if paused")
    
    # Processing results
    match_score: Optional[float] = Field(None, description="Match score")
    match_result: Optional[str] = Field(None, description="Match result")
    
    # Completion info
    erp_txn_id: Optional[str] = Field(None, description="ERP transaction ID")
    final_payload: Optional[dict] = Field(None, description="Final output payload")
    
    # Bigtool selections
    bigtool_selections: dict = Field(default={}, description="Tool selections per stage")
    
    # Audit
    audit_log: list[dict] = Field(default=[], description="Audit log entries")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Workflow start time")
    completed_at: Optional[datetime] = Field(None, description="Workflow completion time")


class AuditEntry(BaseModel):
    """Single audit log entry."""
    timestamp: datetime
    stage: str
    action: str
    details: dict = Field(default={})
