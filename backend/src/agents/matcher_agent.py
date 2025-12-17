"""Matcher Agent - MATCH_TWO_WAY Stage."""
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState
from ..config.settings import settings


class MatcherAgent(BaseAgent):
    """
    MATCH_TWO_WAY Stage Agent.
    
    Performs 2-way matching between invoice and PO.
    Computes match score and determines if HITL checkpoint is needed.
    Uses COMMON server for match computation.
    Uses LLM for intelligent match analysis.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="MatcherAgent", config=config)
        self.match_threshold = config.get("match_threshold", settings.MATCH_THRESHOLD) if config else settings.MATCH_THRESHOLD
        self.tolerance_pct = config.get("tolerance_pct", settings.TWO_WAY_TOLERANCE_PCT) if config else settings.TWO_WAY_TOLERANCE_PCT
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "matched_pos", "matched_grns"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("invoice_payload") is not None and
            state.get("matched_pos") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute MATCH_TWO_WAY stage.
        
        - Compares invoice against matched POs via COMMON server
        - Uses LLM for intelligent match analysis
        - Calculates match score (0-1)
        - Determines match result (MATCHED/FAILED)
        
        Returns:
            dict with match_score, match_result, match_evidence, audit_log
        """
        self.logger.info("Starting MATCH_TWO_WAY stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            matched_pos = state.get("matched_pos", [])
            matched_grns = state.get("matched_grns", [])
            
            # Step 1: Compute match via COMMON server
            match_compute_result = await self.execute_with_bigtool(
                capability="matching",
                params={
                    "invoice": invoice,
                    "purchase_orders": matched_pos,
                    "grns": matched_grns,
                    "tolerance_pct": self.tolerance_pct
                },
                context={"stage": "MATCH_TWO_WAY"}
            )
            
            # Get match result (with fallback to local computation)
            if match_compute_result.get("score") is not None:
                match_result = {
                    "score": match_compute_result["score"],
                    "evidence": match_compute_result.get("evidence", {})
                }
            else:
                match_result = self._compute_match(invoice, matched_pos, matched_grns)
            
            # Determine if match passed threshold
            match_status = "MATCHED" if match_result["score"] >= self.match_threshold else "FAILED"
            
            # Step 2: Use LLM for intelligent match analysis
            llm_analysis = await self.invoke_llm(
                stage="MATCH_TWO_WAY",
                task="Analyze invoice-PO match result and provide insights",
                context={
                    "invoice": {
                        "id": invoice.get("invoice_id"),
                        "vendor": invoice.get("vendor_name"),
                        "amount": invoice.get("amount"),
                        "line_items_count": len(invoice.get("line_items", []))
                    },
                    "matched_pos": [
                        {
                            "po_number": po.get("po_number"),
                            "amount": po.get("total_amount"),
                            "status": po.get("status")
                        } for po in matched_pos[:3]  # Limit for LLM context
                    ],
                    "match_score": match_result["score"],
                    "match_status": match_status,
                    "matched_fields": match_result["evidence"].get("matched_fields", []),
                    "mismatched_fields": match_result["evidence"].get("mismatched_fields", [])
                },
                output_format="json with: recommendation, confidence, risk_factors"
            )
            
            # Add LLM analysis to evidence
            match_evidence = match_result["evidence"]
            match_evidence["llm_analysis"] = llm_analysis.get("response", {})
            
            self.log_execution(
                stage="MATCH_TWO_WAY",
                action="compute_match",
                result={
                    "match_score": match_result["score"],
                    "match_status": match_status,
                    "threshold": self.match_threshold,
                    "llm_used": True
                }
            )
            
            return {
                "match_score": match_result["score"],
                "match_result": match_status,
                "tolerance_pct": self.tolerance_pct,
                "match_evidence": match_evidence,
                "current_stage": "MATCH_TWO_WAY",
                "audit_log": [self.create_audit_entry(
                    "MATCH_TWO_WAY",
                    "match_computed",
                    {
                        "match_score": match_result["score"],
                        "match_result": match_status,
                        "threshold": self.match_threshold,
                        "matched_fields": match_result["evidence"].get("matched_fields", []),
                        "mismatched_fields": match_result["evidence"].get("mismatched_fields", []),
                        "bigtool_used": True,
                        "llm_used": True
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("MATCH_TWO_WAY", e, state)
    
    def _compute_match(self, invoice: dict, pos: list, grns: list) -> dict:
        """
        Compute 2-way match between invoice and PO.
        
        Checks:
        - Amount match (within tolerance)
        - Line items match
        - Vendor match
        - Currency match
        """
        if not pos:
            return {
                "score": 0.0,
                "evidence": {
                    "matched_fields": [],
                    "mismatched_fields": ["no_matching_po"],
                    "tolerance_analysis": {}
                }
            }
        
        # Use first matched PO for comparison
        po = pos[0]
        
        matched_fields = []
        mismatched_fields = []
        tolerance_analysis = {}
        
        # Check amount match
        invoice_amount = invoice.get("amount", 0)
        po_amount = po.get("total_amount", 0)
        
        if po_amount > 0:
            amount_diff_pct = abs(invoice_amount - po_amount) / po_amount * 100
            tolerance_analysis["amount_diff_pct"] = amount_diff_pct
            
            if amount_diff_pct <= self.tolerance_pct:
                matched_fields.append("amount")
            else:
                mismatched_fields.append("amount")
        else:
            mismatched_fields.append("amount")
        
        # Check vendor match
        invoice_vendor = invoice.get("vendor_name", "").upper()
        po_vendor = po.get("vendor_name", "").upper()
        
        if invoice_vendor and po_vendor and invoice_vendor in po_vendor or po_vendor in invoice_vendor:
            matched_fields.append("vendor")
        else:
            mismatched_fields.append("vendor")
        
        # Check currency match
        if invoice.get("currency") == po.get("currency"):
            matched_fields.append("currency")
        else:
            mismatched_fields.append("currency")
        
        # Check line items count match
        invoice_items = len(invoice.get("line_items", []))
        po_items = len(po.get("line_items", []))
        
        if invoice_items == po_items:
            matched_fields.append("line_items_count")
        else:
            mismatched_fields.append("line_items_count")
        
        # Calculate score
        total_checks = len(matched_fields) + len(mismatched_fields)
        score = len(matched_fields) / total_checks if total_checks > 0 else 0.0
        
        return {
            "score": score,
            "evidence": {
                "matched_fields": matched_fields,
                "mismatched_fields": mismatched_fields,
                "tolerance_analysis": tolerance_analysis
            }
        }
