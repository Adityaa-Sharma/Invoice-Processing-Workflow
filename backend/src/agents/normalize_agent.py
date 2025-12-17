"""Normalize/Enrich Agent - PREPARE Stage."""
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class NormalizeAgent(BaseAgent):
    """
    PREPARE Stage Agent.
    
    Normalizes vendor name, enriches vendor data, and computes flags.
    Uses COMMON server for normalization and flag computation.
    Uses ATLAS server for vendor enrichment.
    Uses BigtoolPicker to select enrichment provider and LLM for analysis.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="NormalizeAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "parsed_invoice"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("parsed_invoice") is not None and
            state.get("invoice_payload") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute PREPARE stage.
        
        - Uses BigtoolPicker to select enrichment provider
        - Normalizes vendor name via COMMON server
        - Enriches vendor data via ATLAS server
        - Uses LLM for flag computation and risk analysis
        
        Returns:
            dict with vendor_profile, normalized_invoice, flags, audit_log
        """
        self.logger.info("Starting PREPARE stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            parsed = state.get("parsed_invoice", {})
            
            # Step 1: Use BigtoolPicker to select enrichment tool
            tool_selection = await self.select_tool(
                capability="enrichment",
                context={
                    "vendor_name": invoice.get("vendor_name"),
                    "vendor_tax_id": invoice.get("vendor_tax_id"),
                    "invoice_amount": invoice.get("amount"),
                },
                use_llm=True
            )
            
            bigtool_selection = {
                "PREPARE": {
                    "capability": "enrichment",
                    "selected_tool": tool_selection.get("selected_tool", "clearbit"),
                    "pool": tool_selection.get("pool", ["clearbit", "people_data_labs", "vendor_db"]),
                    "reason": tool_selection.get("reason", "BigtoolPicker selection")
                }
            }
            
            # Step 2: Normalize vendor name via COMMON server
            normalize_result = await self.execute_with_bigtool(
                capability="normalize",
                params={
                    "vendor_name": invoice.get("vendor_name", ""),
                    "invoice_data": invoice
                },
                context={"stage": "PREPARE"}
            )
            
            normalized_name = normalize_result.get("normalized_name") or self._normalize_vendor_name(invoice.get("vendor_name", ""))
            
            # Step 3: Enrich vendor data via ATLAS server
            enrichment_result = await self.execute_with_bigtool(
                capability="enrichment",
                params={
                    "vendor_name": normalized_name,
                    "tax_id": invoice.get("vendor_tax_id"),
                    "invoice_amount": invoice.get("amount")
                },
                context={"stage": "PREPARE"}
            )
            
            # Build vendor profile (with fallback to mock data)
            vendor_profile = {
                "normalized_name": normalized_name,
                "tax_id": enrichment_result.get("tax_id") or invoice.get("vendor_tax_id") or self._generate_mock_tax_id(),
                "enrichment_meta": enrichment_result.get("meta") or {
                    "source": tool_selection.get("selected_tool", "clearbit"),
                    "company_size": "medium",
                    "industry": "Technology Services",
                    "founded_year": 2015,
                    "credit_score": 750
                },
                "risk_score": enrichment_result.get("risk_score", 0.15)
            }
            
            # Create normalized invoice
            normalized_invoice = {
                "amount": invoice.get("amount", 0),
                "currency": parsed.get("currency", "USD"),
                "line_items": parsed.get("parsed_line_items", [])
            }
            
            # Step 4: Use LLM for intelligent flag computation
            llm_flags_result = await self.invoke_llm(
                stage="PREPARE",
                task="Analyze invoice and vendor data to compute validation flags",
                context={
                    "invoice": invoice,
                    "vendor_profile": vendor_profile,
                    "normalized_invoice": normalized_invoice
                },
                output_format="json with: missing_info, risk_flags, recommendations"
            )
            
            # Compute validation flags (with LLM enhancement)
            flags = self._compute_flags(invoice, vendor_profile)
            if llm_flags_result.get("response"):
                flags["llm_analysis"] = llm_flags_result["response"]
            
            self.log_execution(
                stage="PREPARE",
                action="normalize_enrich",
                result={
                    "vendor": normalized_name,
                    "risk_score": vendor_profile["risk_score"],
                    "enrichment_tool": tool_selection.get("selected_tool")
                },
                bigtool_selection=bigtool_selection["PREPARE"]
            )
            
            return {
                "vendor_profile": vendor_profile,
                "normalized_invoice": normalized_invoice,
                "flags": flags,
                "current_stage": "PREPARE",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "PREPARE",
                    "vendor_normalized_enriched",
                    {
                        "original_name": invoice.get("vendor_name"),
                        "normalized_name": normalized_name,
                        "enrichment_tool": tool_selection.get("selected_tool", "clearbit"),
                        "risk_score": vendor_profile["risk_score"],
                        "flags_count": len(flags.get("missing_info", [])),
                        "bigtool_used": True,
                        "llm_used": True
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("PREPARE", e, state)
    
    def _normalize_vendor_name(self, name: str) -> str:
        """Normalize vendor name to standard format."""
        # Remove common suffixes and normalize
        name = name.strip()
        for suffix in [" Inc.", " Inc", " LLC", " Ltd.", " Ltd", " Corp.", " Corp"]:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name.upper().strip()
    
    def _generate_mock_tax_id(self) -> str:
        """Generate mock tax ID for demo."""
        import random
        return f"TAX-{random.randint(100000, 999999)}"
    
    def _compute_flags(self, invoice: dict, vendor_profile: dict) -> dict:
        """Compute validation flags."""
        missing_info = []
        
        # Check for missing fields
        if not invoice.get("vendor_tax_id"):
            missing_info.append("vendor_tax_id")
        if not invoice.get("line_items"):
            missing_info.append("line_items")
        
        return {
            "missing_info": missing_info,
            "risk_score": vendor_profile.get("risk_score", 0),
            "high_value": invoice.get("amount", 0) > 10000,
            "new_vendor": False  # Mock - would check vendor history
        }
