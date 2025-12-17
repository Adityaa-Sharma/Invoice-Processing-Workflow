"""LangGraph state schema and TypedDict definitions."""
from typing import TypedDict, Optional, Annotated, Any
from operator import add


class ParsedInvoice(TypedDict):
    """Parsed invoice data from OCR/NLP."""
    invoice_text: str
    parsed_line_items: list[dict]
    detected_pos: list[str]
    currency: str
    parsed_dates: dict


class VendorProfile(TypedDict):
    """Enriched vendor profile."""
    normalized_name: str
    tax_id: str
    enrichment_meta: dict
    risk_score: float


class MatchEvidence(TypedDict):
    """Evidence from matching process."""
    matched_fields: list[str]
    mismatched_fields: list[str]
    tolerance_analysis: dict


class InvoiceWorkflowState(TypedDict):
    """
    Complete state schema for the invoice processing workflow.
    
    All fields must be explicitly typed. Uses TypedDict for
    immutability and type safety across LangGraph nodes.
    """
    
    # ===== Input =====
    invoice_payload: dict
    
    # ===== INTAKE output =====
    raw_id: Optional[str]
    ingest_ts: Optional[str]
    validated: Optional[bool]
    
    # ===== UNDERSTAND output =====
    parsed_invoice: Optional[ParsedInvoice]
    
    # ===== PREPARE output =====
    vendor_profile: Optional[VendorProfile]
    normalized_invoice: Optional[dict]
    flags: Optional[dict]
    
    # ===== RETRIEVE output =====
    matched_pos: Optional[list]
    matched_grns: Optional[list]
    history: Optional[list]
    
    # ===== MATCH_TWO_WAY output =====
    match_score: Optional[float]
    match_result: Optional[str]  # "MATCHED" | "FAILED"
    tolerance_pct: Optional[float]
    match_evidence: Optional[MatchEvidence]
    
    # ===== CHECKPOINT_HITL output =====
    hitl_checkpoint_id: Optional[str]
    review_url: Optional[str]
    paused_reason: Optional[str]
    
    # ===== HITL_DECISION output =====
    human_decision: Optional[str]  # "ACCEPT" | "REJECT"
    reviewer_id: Optional[str]
    reviewer_notes: Optional[str]
    resume_token: Optional[str]
    
    # ===== RECONCILE output =====
    accounting_entries: Optional[list]
    reconciliation_report: Optional[dict]
    
    # ===== APPROVE output =====
    approval_status: Optional[str]
    approver_id: Optional[str]
    
    # ===== POSTING output =====
    posted: Optional[bool]
    erp_txn_id: Optional[str]
    scheduled_payment_id: Optional[str]
    
    # ===== NOTIFY output =====
    notify_status: Optional[dict]
    notified_parties: Optional[list]
    
    # ===== COMPLETE output =====
    final_payload: Optional[dict]
    
    # ===== Workflow Metadata =====
    thread_id: str  # Workflow thread ID for event emission
    current_stage: str
    status: str  # "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "REQUIRES_MANUAL_HANDLING"
    error: Optional[str]
    
    # ===== Accumulated Data (using reducers) =====
    audit_log: Annotated[list[dict], add]  # Append-only audit entries
    bigtool_selections: dict  # Track which tools were selected per stage
    error_log: Annotated[list[dict], add]  # Append-only error entries


def create_initial_state(invoice_payload: dict, thread_id: str = "") -> InvoiceWorkflowState:
    """
    Create initial workflow state from invoice payload.
    
    Args:
        invoice_payload: Raw invoice data
        thread_id: Workflow thread ID for event emission
        
    Returns:
        Initial InvoiceWorkflowState
    """
    return {
        # Input
        "invoice_payload": invoice_payload,
        
        # INTAKE
        "raw_id": None,
        "ingest_ts": None,
        "validated": None,
        
        # UNDERSTAND
        "parsed_invoice": None,
        
        # PREPARE
        "vendor_profile": None,
        "normalized_invoice": None,
        "flags": None,
        
        # RETRIEVE
        "matched_pos": None,
        "matched_grns": None,
        "history": None,
        
        # MATCH_TWO_WAY
        "match_score": None,
        "match_result": None,
        "tolerance_pct": None,
        "match_evidence": None,
        
        # CHECKPOINT_HITL
        "hitl_checkpoint_id": None,
        "review_url": None,
        "paused_reason": None,
        
        # HITL_DECISION
        "human_decision": None,
        "reviewer_id": None,
        "reviewer_notes": None,
        "resume_token": None,
        
        # RECONCILE
        "accounting_entries": None,
        "reconciliation_report": None,
        
        # APPROVE
        "approval_status": None,
        "approver_id": None,
        
        # POSTING
        "posted": None,
        "erp_txn_id": None,
        "scheduled_payment_id": None,
        
        # NOTIFY
        "notify_status": None,
        "notified_parties": None,
        
        # COMPLETE
        "final_payload": None,
        
        # Metadata
        "thread_id": thread_id,
        "current_stage": "START",
        "status": "RUNNING",
        "error": None,
        
        # Accumulated
        "audit_log": [],
        "bigtool_selections": {},
        "error_log": [],
    }
