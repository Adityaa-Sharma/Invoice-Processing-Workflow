"""ERP Fetch Agent - RETRIEVE Stage."""
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class ErpFetchAgent(BaseAgent):
    """
    RETRIEVE Stage Agent.
    
    Fetches POs, GRNs, and historical invoices from ERP systems.
    Uses ATLAS server for ERP connections.
    Uses BigtoolPicker to select ERP connector.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="ErpFetchAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["parsed_invoice", "vendor_profile"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("parsed_invoice") is not None and
            state.get("vendor_profile") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute RETRIEVE stage.
        
        - Uses BigtoolPicker to select ERP connector
        - Fetches Purchase Orders via ATLAS MCP server
        - Fetches Goods Received Notes via ATLAS MCP server
        - Fetches historical invoices for vendor
        
        Returns:
            dict with matched_pos, matched_grns, history, audit_log
        """
        self.logger.info("Starting RETRIEVE stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            parsed = state.get("parsed_invoice", {})
            vendor = state.get("vendor_profile", {})
            
            # Step 1: Use BigtoolPicker to select ERP connector
            tool_selection = await self.select_tool(
                capability="erp_connector",
                context={
                    "vendor_name": vendor.get("normalized_name"),
                    "po_references": parsed.get("detected_pos", []),
                    "invoice_amount": invoice.get("amount"),
                },
                use_llm=True
            )
            
            bigtool_selection = {
                "RETRIEVE": {
                    "capability": "erp_connector",
                    "selected_tool": tool_selection.get("selected_tool", "mock_erp"),
                    "pool": tool_selection.get("pool", ["sap_sandbox", "netsuite", "mock_erp"]),
                    "reason": tool_selection.get("reason", "BigtoolPicker selection")
                }
            }
            
            # Get PO references from parsed invoice
            po_refs = parsed.get("detected_pos", [])
            
            # Step 2: Fetch POs via ATLAS server
            po_result = await self.execute_with_bigtool(
                capability="erp_connector",
                params={
                    "action": "fetch_po_data",
                    "po_references": po_refs,
                    "vendor_name": vendor.get("normalized_name"),
                    "invoice_data": invoice
                },
                context={"stage": "RETRIEVE"}
            )
            
            # Step 3: Fetch GRNs via ATLAS server
            grn_result = await self.execute_with_bigtool(
                capability="erp_connector",
                params={
                    "action": "fetch_grn_data",
                    "po_references": po_refs,
                    "vendor_name": vendor.get("normalized_name")
                },
                context={"stage": "RETRIEVE"}
            )
            
            # Get results with fallback to mock data
            matched_pos = po_result.get("purchase_orders") or self._fetch_purchase_orders(po_refs, invoice)
            matched_grns = grn_result.get("grns") or self._fetch_grns(matched_pos)
            
            # Step 4: Fetch invoice history
            history_result = await self.execute_with_bigtool(
                capability="erp_connector",
                params={
                    "action": "fetch_invoice_history",
                    "vendor_name": vendor.get("normalized_name")
                },
                context={"stage": "RETRIEVE"}
            )
            
            history = history_result.get("history") or self._fetch_invoice_history(vendor.get("normalized_name", ""))
            
            self.log_execution(
                stage="RETRIEVE",
                action="erp_fetch",
                result={
                    "pos_found": len(matched_pos),
                    "grns_found": len(matched_grns),
                    "history_count": len(history),
                    "erp_tool": tool_selection.get("selected_tool")
                },
                bigtool_selection=bigtool_selection["RETRIEVE"]
            )
            
            return {
                "matched_pos": matched_pos,
                "matched_grns": matched_grns,
                "history": history,
                "current_stage": "RETRIEVE",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "RETRIEVE",
                    "erp_data_fetched",
                    {
                        "erp_tool": tool_selection.get("selected_tool", "mock_erp"),
                        "pos_found": len(matched_pos),
                        "grns_found": len(matched_grns),
                        "history_records": len(history),
                        "bigtool_used": True
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("RETRIEVE", e, state)
    
    def _fetch_purchase_orders(self, po_refs: list, invoice: dict) -> list[dict]:
        """
        Mock fetch purchase orders from ERP.
        
        Returns realistic mock PO data based on invoice amount ranges:
        - Small invoices (<$5000): Exact match → PASS
        - Medium invoices ($5000-$20000): Slight variance (within tolerance) → PASS  
        - Large invoices (>$20000): Quantity/price discrepancies → HITL
        
        This simulates real-world scenarios where large invoices need more scrutiny.
        """
        pos = []
        invoice_amount = invoice.get("amount", 0)
        invoice_items = invoice.get("line_items", [])
        invoice_id = invoice.get("invoice_id", "INV-001")
        
        # Determine match scenario based on invoice amount (realistic business logic)
        if invoice_amount < 5000:
            # Small invoices: Auto-approve (exact match)
            match_scenario = "exact"
        elif invoice_amount <= 20000:
            # Medium invoices: Minor variance within tolerance
            match_scenario = "within_tolerance"
        else:
            # Large invoices: Discrepancies requiring human review
            match_scenario = "discrepancy"
        
        self.logger.info(f"ERP Fetch: amount=${invoice_amount}, scenario='{match_scenario}'")
        
        po_number = po_refs[0] if po_refs else f"PO-{invoice_id.replace('INV-', '')}"
        
        if match_scenario == "exact":
            # Perfect match - same amounts, quantities, prices
            pos.append({
                "po_number": po_number,
                "vendor_name": invoice.get("vendor_name", ""),
                "total_amount": invoice_amount,
                "currency": invoice.get("currency", "USD"),
                "status": "APPROVED",
                "line_items": [
                    {
                        "desc": item.get("desc", "Item"),
                        "qty": item.get("qty", 1),
                        "unit_price": item.get("unit_price", 0),
                        "total": item.get("total", 0)
                    } for item in invoice_items
                ],
                "created_date": "2024-01-15"
            })
            
        elif match_scenario == "within_tolerance":
            # Minor variance (2-3%) - should still pass with tolerance of 5%
            variance_factor = 0.97  # 3% less than invoice
            pos.append({
                "po_number": po_number,
                "vendor_name": invoice.get("vendor_name", ""),
                "total_amount": round(invoice_amount * variance_factor, 2),
                "currency": invoice.get("currency", "USD"),
                "status": "APPROVED",
                "line_items": [
                    {
                        "desc": item.get("desc", "Item"),
                        "qty": item.get("qty", 1),  # Same quantities
                        "unit_price": round(item.get("unit_price", 0) * variance_factor, 2),
                        "total": round(item.get("total", 0) * variance_factor, 2)
                    } for item in invoice_items
                ],
                "created_date": "2024-01-15"
            })
            
        else:  # discrepancy
            # Significant differences - triggers HITL
            # Scenario: PO was for fewer items or lower prices
            pos.append({
                "po_number": po_number,
                "vendor_name": invoice.get("vendor_name", ""),
                "total_amount": round(invoice_amount * 0.75, 2),  # 25% less (exceeds 5% tolerance)
                "currency": invoice.get("currency", "USD"),
                "status": "APPROVED",
                "line_items": [
                    {
                        "desc": item.get("desc", "Item"),
                        "qty": max(1, item.get("qty", 1) - 2),  # Fewer items ordered
                        "unit_price": round(item.get("unit_price", 0) * 0.85, 2),  # Lower agreed price
                        "total": round(item.get("total", 0) * 0.75, 2)
                    } for item in invoice_items
                ],
                "created_date": "2024-01-15",
                "notes": "Original PO was for smaller quantity at negotiated discount"
            })
        
        return pos
    
    def _fetch_grns(self, pos: list) -> list[dict]:
        """Mock fetch Goods Received Notes."""
        grns = []
        
        for po in pos:
            grns.append({
                "grn_number": f"GRN-{po['po_number'].replace('PO-', '')}",
                "po_reference": po["po_number"],
                "received_date": "2024-02-01",
                "received_qty": sum(
                    item.get("qty", 0) for item in po.get("line_items", [])
                ),
                "status": "COMPLETE"
            })
        
        return grns
    
    def _fetch_invoice_history(self, vendor_name: str) -> list[dict]:
        """Mock fetch historical invoices for vendor."""
        return [
            {
                "invoice_id": "INV-HIST-001",
                "vendor_name": vendor_name,
                "amount": 12500.00,
                "status": "PAID",
                "payment_date": "2024-01-20"
            },
            {
                "invoice_id": "INV-HIST-002",
                "vendor_name": vendor_name,
                "amount": 8750.00,
                "status": "PAID",
                "payment_date": "2023-12-15"
            }
        ]
