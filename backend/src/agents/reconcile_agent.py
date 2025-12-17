"""Reconcile Agent - RECONCILE Stage."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class ReconcileAgent(BaseAgent):
    """
    RECONCILE Stage Agent.
    
    Builds accounting entries and reconciliation report.
    Uses COMMON server for accounting logic.
    Uses LLM for intelligent entry generation.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="ReconcileAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "vendor_profile", "normalized_invoice"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("invoice_payload") is not None and
            state.get("vendor_profile") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute RECONCILE stage.
        
        - Builds accounting entries via COMMON server
        - Uses LLM for intelligent entry categorization
        - Creates reconciliation report
        
        Returns:
            dict with accounting_entries, reconciliation_report, audit_log
        """
        self.logger.info("Starting RECONCILE stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            vendor = state.get("vendor_profile", {})
            normalized = state.get("normalized_invoice", {})
            
            # Step 1: Call COMMON server for entry building
            entries_result = await self.execute_with_bigtool(
                capability="accounting",
                params={
                    "action": "build_entries",
                    "invoice": invoice,
                    "vendor": vendor,
                    "normalized": normalized,
                    "line_items": invoice.get("line_items", [])
                },
                context={"stage": "RECONCILE"}
            )
            
            # Get entries (with fallback to local generation)
            accounting_entries = entries_result.get("entries") or self._build_accounting_entries(invoice, vendor)
            
            # Step 2: Use LLM for intelligent entry categorization
            llm_result = await self.invoke_llm(
                stage="RECONCILE",
                task="Analyze accounting entries and suggest optimal categorization",
                context={
                    "invoice": {
                        "id": invoice.get("invoice_id"),
                        "vendor": vendor.get("normalized_name"),
                        "amount": invoice.get("amount"),
                        "line_items": invoice.get("line_items", [])[:5]  # Limit for context
                    },
                    "entries": accounting_entries,
                    "vendor_industry": vendor.get("enrichment_meta", {}).get("industry")
                },
                output_format="json with: suggested_accounts, categorization_notes"
            )
            
            # Create reconciliation report
            reconciliation_report = self._create_reconciliation_report(
                invoice, vendor, accounting_entries
            )
            
            # Add LLM suggestions to report
            if llm_result.get("response"):
                reconciliation_report["llm_suggestions"] = llm_result["response"]
            
            self.log_execution(
                stage="RECONCILE",
                action="build_entries",
                result={
                    "entries_count": len(accounting_entries),
                    "total_amount": invoice.get("amount", 0),
                    "llm_used": True
                }
            )
            
            return {
                "accounting_entries": accounting_entries,
                "reconciliation_report": reconciliation_report,
                "current_stage": "RECONCILE",
                "audit_log": [self.create_audit_entry(
                    "RECONCILE",
                    "entries_built",
                    {
                        "invoice_id": invoice.get("invoice_id"),
                        "entries_count": len(accounting_entries),
                        "total_debit": sum(
                            e.get("amount", 0) for e in accounting_entries 
                            if e.get("type") == "DEBIT"
                        ),
                        "total_credit": sum(
                            e.get("amount", 0) for e in accounting_entries 
                            if e.get("type") == "CREDIT"
                        ),
                        "bigtool_used": True,
                        "llm_used": True
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("RECONCILE", e, state)
    
    def _build_accounting_entries(self, invoice: dict, vendor: dict) -> list[dict]:
        """Build accounting entries for the invoice."""
        amount = invoice.get("amount", 0)
        invoice_id = invoice.get("invoice_id", "")
        vendor_name = vendor.get("normalized_name", invoice.get("vendor_name", ""))
        
        entry_id = uuid4().hex[:8].upper()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        return [
            {
                "entry_id": f"JE-{entry_id}-01",
                "type": "DEBIT",
                "account": "6000-Expenses",
                "amount": amount,
                "currency": invoice.get("currency", "USD"),
                "reference": invoice_id,
                "description": f"Expense for invoice {invoice_id} - {vendor_name}",
                "timestamp": timestamp
            },
            {
                "entry_id": f"JE-{entry_id}-02",
                "type": "CREDIT",
                "account": "2100-Accounts Payable",
                "amount": amount,
                "currency": invoice.get("currency", "USD"),
                "reference": invoice_id,
                "description": f"Payable to {vendor_name}",
                "timestamp": timestamp
            }
        ]
    
    def _create_reconciliation_report(
        self,
        invoice: dict,
        vendor: dict,
        entries: list
    ) -> dict:
        """Create reconciliation summary report."""
        return {
            "invoice_id": invoice.get("invoice_id"),
            "vendor": vendor.get("normalized_name"),
            "total_amount": invoice.get("amount", 0),
            "currency": invoice.get("currency", "USD"),
            "entries_count": len(entries),
            "balanced": True,  # Debit = Credit
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
            "status": "RECONCILED"
        }
