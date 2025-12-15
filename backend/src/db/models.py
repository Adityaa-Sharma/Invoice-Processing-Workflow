"""SQLAlchemy models for invoice processing workflow."""
from datetime import datetime
from sqlalchemy import Column, String, Float, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class WorkflowCheckpoint(Base):
    """
    Stores workflow checkpoint data for HITL resume.
    
    This supplements LangGraph's built-in checkpoint storage with
    additional metadata for the human review queue.
    """
    __tablename__ = "workflow_checkpoints"
    
    id = Column(String(50), primary_key=True)
    thread_id = Column(String(50), nullable=False, index=True)
    invoice_id = Column(String(50), nullable=False, index=True)
    checkpoint_id = Column(String(50), nullable=False, unique=True)
    
    # State snapshot
    state_blob = Column(JSON, nullable=False)
    
    # Metadata
    current_stage = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="PAUSED")
    paused_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "invoice_id": self.invoice_id,
            "checkpoint_id": self.checkpoint_id,
            "current_stage": self.current_stage,
            "status": self.status,
            "paused_reason": self.paused_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HumanReviewQueue(Base):
    """
    Human review queue for invoices requiring HITL decision.
    
    Entries are created when workflow pauses at CHECKPOINT_HITL stage.
    """
    __tablename__ = "human_review_queue"
    
    id = Column(String(50), primary_key=True)
    thread_id = Column(String(50), nullable=False, index=True)
    checkpoint_id = Column(String(50), nullable=False, unique=True, index=True)
    
    # Invoice info
    invoice_id = Column(String(50), nullable=False)
    vendor_name = Column(String(200), nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    
    # Match info
    match_score = Column(Float, nullable=True)
    match_result = Column(String(50), nullable=True)
    match_evidence = Column(JSON, nullable=True)
    
    # Review info
    reason_for_hold = Column(Text, nullable=True)
    review_url = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(50), default="PENDING")  # PENDING, REVIEWED, ACCEPTED, REJECTED
    
    # Reviewer info (populated after review)
    reviewer_id = Column(String(50), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    decision = Column(String(50), nullable=True)  # ACCEPT, REJECT
    reviewed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "checkpoint_id": self.checkpoint_id,
            "invoice_id": self.invoice_id,
            "vendor_name": self.vendor_name,
            "amount": self.amount,
            "currency": self.currency,
            "match_score": self.match_score,
            "match_result": self.match_result,
            "match_evidence": self.match_evidence,
            "reason_for_hold": self.reason_for_hold,
            "review_url": self.review_url,
            "status": self.status,
            "reviewer_id": self.reviewer_id,
            "reviewer_notes": self.reviewer_notes,
            "decision": self.decision,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InvoiceAuditLog(Base):
    """
    Audit log for invoice processing actions.
    
    Stores all actions taken during invoice processing for compliance.
    """
    __tablename__ = "invoice_audit_log"
    
    id = Column(String(50), primary_key=True)
    thread_id = Column(String(50), nullable=False, index=True)
    invoice_id = Column(String(50), nullable=False, index=True)
    
    # Action info
    stage = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "invoice_id": self.invoice_id,
            "stage": self.stage,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
