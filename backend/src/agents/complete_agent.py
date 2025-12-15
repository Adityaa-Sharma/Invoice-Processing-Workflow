"""Complete Agent - COMPLETE Stage."""
from datetime import datetime, timezone
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class CompleteAgent(BaseAgent):
    """
    COMPLETE Stage Agent.
    
    Produces final structured payload and marks workflow complete.
    Uses COMMON server for final processing.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="CompleteAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "posted"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate workflow completed successfully."""
        return state.get("posted") is True
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute COMPLETE stage.
        
        - Assembles final payload with all processing results
        - Marks workflow as completed
        
        Returns:
            dict with final_payload, status, audit_log
        """
        self.logger.info("Starting COMPLETE stage")
        
        try:
            # Build final payload from all stage outputs
            final_payload = self._build_final_payload(state)
            
            self.log_execution(
                stage="COMPLETE",
                action="finalize_workflow",
                result={
                    "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
                    "status": "COMPLETED"
                }
            )
            
            return {
                "final_payload": final_payload,
                "current_stage": "COMPLETE",
                "status": "COMPLETED",
                "audit_log": [self.create_audit_entry(
                    "COMPLETE",
                    "workflow_completed",
                    {
                        "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
                        "erp_txn_id": state.get("erp_txn_id"),
                        "scheduled_payment_id": state.get("scheduled_payment_id"),
                        "total_stages": 12,
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("COMPLETE", e, state)
    
    def _build_final_payload(self, state: InvoiceWorkflowState) -> dict:
        """Build final structured payload from workflow state."""
        invoice = state.get("invoice_payload", {})
        
        return {
            "workflow_id": state.get("raw_id"),
            "invoice": {
                "id": invoice.get("invoice_id"),
                "vendor": state.get("vendor_profile", {}).get("normalized_name"),
                "amount": invoice.get("amount"),
                "currency": invoice.get("currency"),
                "line_items_count": len(invoice.get("line_items", []))
            },
            "processing": {
                "ingested_at": state.get("ingest_ts"),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "match_score": state.get("match_score"),
                "match_result": state.get("match_result"),
                "required_hitl": state.get("checkpoint_id") is not None,
                "hitl_decision": state.get("human_decision")
            },
            "erp": {
                "transaction_id": state.get("erp_txn_id"),
                "posted": state.get("posted"),
                "entries_count": len(state.get("accounting_entries", []))
            },
            "payment": {
                "scheduled_id": state.get("scheduled_payment_id"),
                "due_date": invoice.get("due_date"),
                "amount": invoice.get("amount")
            },
            "approval": {
                "status": state.get("approval_status"),
                "approver": state.get("approver_id")
            },
            "notifications": {
                "parties_notified": state.get("notified_parties", []),
                "status": state.get("notify_status", {})
            },
            "bigtool_selections": state.get("bigtool_selections", {}),
            "audit_entries_count": len(state.get("audit_log", []))
        }
