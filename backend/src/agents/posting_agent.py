"""Posting Agent - POSTING Stage."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class PostingAgent(BaseAgent):
    """
    POSTING Stage Agent.
    
    Posts entries to ERP and schedules payment.
    Uses ATLAS server for ERP integration.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="PostingAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "accounting_entries", "approval_status"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("accounting_entries") is not None and
            state.get("approval_status") is not None and
            "APPROVED" in state.get("approval_status", "")
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute POSTING stage.
        
        - Posts accounting entries to ERP (mock)
        - Schedules payment based on due date
        
        Returns:
            dict with posted, erp_txn_id, scheduled_payment_id, audit_log
        """
        self.logger.info("Starting POSTING stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            entries = state.get("accounting_entries", [])
            
            # Mock ERP posting
            erp_txn_id = f"ERP-TXN-{uuid4().hex[:10].upper()}"
            
            # Mock payment scheduling
            scheduled_payment_id = f"PAY-{uuid4().hex[:8].upper()}"
            
            # Calculate payment schedule based on due date
            due_date = invoice.get("due_date", datetime.now(timezone.utc).isoformat())
            
            self.log_execution(
                stage="POSTING",
                action="post_and_schedule",
                result={
                    "erp_txn_id": erp_txn_id,
                    "scheduled_payment_id": scheduled_payment_id,
                    "entries_posted": len(entries)
                }
            )
            
            return {
                "posted": True,
                "erp_txn_id": erp_txn_id,
                "scheduled_payment_id": scheduled_payment_id,
                "current_stage": "POSTING",
                "audit_log": [self.create_audit_entry(
                    "POSTING",
                    "posted_to_erp",
                    {
                        "invoice_id": invoice.get("invoice_id"),
                        "erp_txn_id": erp_txn_id,
                        "entries_posted": len(entries),
                        "total_amount": invoice.get("amount", 0)
                    }
                ),
                self.create_audit_entry(
                    "POSTING",
                    "payment_scheduled",
                    {
                        "scheduled_payment_id": scheduled_payment_id,
                        "due_date": due_date,
                        "amount": invoice.get("amount", 0)
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("POSTING", e, state)
