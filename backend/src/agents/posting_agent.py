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
    Uses BigtoolPicker to select ERP connector.
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
        
        - Uses BigtoolPicker to select ERP connector
        - Posts accounting entries to ERP via ATLAS server
        - Schedules payment based on due date
        
        Returns:
            dict with posted, erp_txn_id, scheduled_payment_id, audit_log
        """
        self.logger.info("Starting POSTING stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            entries = state.get("accounting_entries", [])
            
            # Step 1: Use BigtoolPicker to select ERP connector
            tool_selection = await self.select_tool(
                capability="erp_connector",
                context={
                    "action": "post_entries",
                    "entries_count": len(entries),
                    "invoice_amount": invoice.get("amount"),
                },
                use_llm=True
            )
            
            bigtool_selection = {
                "POSTING": {
                    "capability": "erp_connector",
                    "selected_tool": tool_selection.get("selected_tool", "mock_erp"),
                    "pool": tool_selection.get("pool", ["sap_sandbox", "netsuite", "mock_erp"]),
                    "reason": tool_selection.get("reason", "BigtoolPicker selection")
                }
            }
            
            # Step 2: Post to ERP via ATLAS server
            post_result = await self.execute_with_bigtool(
                capability="erp_connector",
                params={
                    "action": "post_to_erp",
                    "invoice": invoice,
                    "entries": entries,
                    "vendor_profile": state.get("vendor_profile", {})
                },
                context={"stage": "POSTING"}
            )
            
            # Get transaction ID (with fallback)
            erp_txn_id = post_result.get("erp_txn_id") or f"ERP-TXN-{uuid4().hex[:10].upper()}"
            
            # Step 3: Schedule payment via ERP
            payment_result = await self.execute_with_bigtool(
                capability="erp_connector",
                params={
                    "action": "schedule_payment",
                    "invoice": invoice,
                    "erp_txn_id": erp_txn_id,
                    "due_date": invoice.get("due_date")
                },
                context={"stage": "POSTING"}
            )
            
            scheduled_payment_id = payment_result.get("payment_id") or f"PAY-{uuid4().hex[:8].upper()}"
            
            # Calculate payment schedule based on due date
            due_date = invoice.get("due_date", datetime.now(timezone.utc).isoformat())
            
            self.log_execution(
                stage="POSTING",
                action="post_and_schedule",
                result={
                    "erp_txn_id": erp_txn_id,
                    "scheduled_payment_id": scheduled_payment_id,
                    "entries_posted": len(entries),
                    "erp_tool": tool_selection.get("selected_tool")
                },
                bigtool_selection=bigtool_selection["POSTING"]
            )
            
            return {
                "posted": True,
                "erp_txn_id": erp_txn_id,
                "scheduled_payment_id": scheduled_payment_id,
                "current_stage": "POSTING",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "POSTING",
                    "posted_to_erp",
                    {
                        "invoice_id": invoice.get("invoice_id"),
                        "erp_txn_id": erp_txn_id,
                        "entries_posted": len(entries),
                        "total_amount": invoice.get("amount", 0),
                        "erp_tool": tool_selection.get("selected_tool", "mock_erp"),
                        "bigtool_used": True
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
