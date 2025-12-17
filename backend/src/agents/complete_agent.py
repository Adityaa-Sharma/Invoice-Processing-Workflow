"""Complete Agent - COMPLETE Stage."""
from datetime import datetime, timezone
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class CompleteAgent(BaseAgent):
    """
    COMPLETE Stage Agent.
    
    Produces final structured payload and marks workflow complete.
    Uses COMMON server for final processing and audit persistence.
    Uses BigtoolPicker to select database for audit storage.
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
        
        - Uses BigtoolPicker to select database for audit
        - Persists audit log via COMMON server
        - Assembles final payload with all processing results
        - Marks workflow as completed
        
        Returns:
            dict with final_payload, status, audit_log
        """
        self.logger.info("Starting COMPLETE stage")
        
        try:
            # Step 1: Use BigtoolPicker to select database tool
            tool_selection = await self.select_tool(
                capability="db",
                context={
                    "action": "persist_audit",
                    "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
                    "audit_entries": len(state.get("audit_log", [])),
                },
                use_llm=False  # Simple selection for DB
            )
            
            bigtool_selection = {
                "COMPLETE": {
                    "capability": "db",
                    "selected_tool": tool_selection.get("selected_tool", "postgresql"),
                    "pool": tool_selection.get("pool", ["postgresql", "mongodb", "sqlite"]),
                    "reason": tool_selection.get("reason", "BigtoolPicker selection")
                }
            }
            
            # Step 2: Persist audit log via COMMON server
            audit_result = await self.execute_with_bigtool(
                capability="db",
                params={
                    "action": "persist_audit",
                    "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
                    "raw_id": state.get("raw_id"),
                    "audit_entries": state.get("audit_log", []),
                    "bigtool_selections": state.get("bigtool_selections", {})
                },
                context={"stage": "COMPLETE"}
            )
            
            # Build final payload from all stage outputs
            final_payload = self._build_final_payload(state)
            
            # Add bigtool selections and integration info to final payload
            final_payload["bigtool_selections"] = {
                **state.get("bigtool_selections", {}),
                **bigtool_selection
            }
            final_payload["integration"] = {
                "bigtool_used": True,
                "llm_used": True,
                "mcp_servers": ["COMMON", "ATLAS"],
                "audit_persisted": audit_result.get("persisted", True)
            }
            
            self.log_execution(
                stage="COMPLETE",
                action="finalize_workflow",
                result={
                    "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
                    "status": "COMPLETED",
                    "db_tool": tool_selection.get("selected_tool")
                },
                bigtool_selection=bigtool_selection["COMPLETE"]
            )
            
            return {
                "final_payload": final_payload,
                "current_stage": "COMPLETE",
                "status": "COMPLETED",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "COMPLETE",
                    "workflow_completed",
                    {
                        "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
                        "erp_txn_id": state.get("erp_txn_id"),
                        "scheduled_payment_id": state.get("scheduled_payment_id"),
                        "total_stages": 12,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "db_tool": tool_selection.get("selected_tool", "postgresql"),
                        "bigtool_used": True
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
                "required_hitl": state.get("hitl_checkpoint_id") is not None,
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
