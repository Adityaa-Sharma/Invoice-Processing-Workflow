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
    Uses Bigtool to select enrichment provider.
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
        
        - Normalizes vendor name
        - Enriches vendor data (tax ID, credit score, risk)
        - Computes validation flags
        
        Returns:
            dict with vendor_profile, normalized_invoice, flags, audit_log
        """
        self.logger.info("Starting PREPARE stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            parsed = state.get("parsed_invoice", {})
            
            # Mock bigtool selection for enrichment
            bigtool_selection = {
                "PREPARE": {
                    "capability": "enrichment",
                    "selected_tool": "clearbit",
                    "pool": ["clearbit", "people_data_labs", "vendor_db"],
                    "reason": "clearbit provides comprehensive vendor data"
                }
            }
            
            # Normalize vendor name
            normalized_name = self._normalize_vendor_name(invoice.get("vendor_name", ""))
            
            # Mock vendor enrichment
            vendor_profile = {
                "normalized_name": normalized_name,
                "tax_id": invoice.get("vendor_tax_id", self._generate_mock_tax_id()),
                "enrichment_meta": {
                    "source": "clearbit",
                    "company_size": "medium",
                    "industry": "Technology Services",
                    "founded_year": 2015,
                    "credit_score": 750
                },
                "risk_score": 0.15  # Low risk (0-1 scale)
            }
            
            # Create normalized invoice
            normalized_invoice = {
                "amount": invoice.get("amount", 0),
                "currency": parsed.get("currency", "USD"),
                "line_items": parsed.get("parsed_line_items", [])
            }
            
            # Compute validation flags
            flags = self._compute_flags(invoice, vendor_profile)
            
            self.log_execution(
                stage="PREPARE",
                action="normalize_enrich",
                result={
                    "vendor": normalized_name,
                    "risk_score": vendor_profile["risk_score"]
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
                        "enrichment_tool": "clearbit",
                        "risk_score": vendor_profile["risk_score"],
                        "flags_count": len(flags.get("missing_info", []))
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
