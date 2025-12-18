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
        Compute realistic 2-way match between invoice and PO.
        
        Weighted scoring based on business-critical fields:
        - Total Amount (within tolerance): 40% weight
        - Line Item Quantities: 35% weight  
        - Line Item Unit Prices: 25% weight
        
        Does NOT check vendor name (already validated in RETRIEVE stage).
        """
        if not pos:
            return {
                "score": 0.0,
                "evidence": {
                    "matched_fields": [],
                    "mismatched_fields": ["no_matching_po"],
                    "tolerance_analysis": {},
                    "line_item_details": []
                }
            }
        
        # Use first matched PO for comparison
        po = pos[0]
        
        matched_fields = []
        mismatched_fields = []
        tolerance_analysis = {}
        line_item_details = []
        
        # ===== 1. TOTAL AMOUNT CHECK (40% weight) =====
        invoice_amount = invoice.get("amount", 0)
        po_amount = po.get("total_amount", 0)
        amount_score = 0.0
        
        if po_amount > 0:
            amount_diff_pct = abs(invoice_amount - po_amount) / po_amount * 100
            tolerance_analysis["amount_diff_pct"] = round(amount_diff_pct, 2)
            tolerance_analysis["invoice_amount"] = invoice_amount
            tolerance_analysis["po_amount"] = po_amount
            
            if amount_diff_pct <= self.tolerance_pct:
                matched_fields.append("total_amount")
                amount_score = 1.0
            elif amount_diff_pct <= self.tolerance_pct * 2:
                # Partial score for close matches
                matched_fields.append("total_amount_partial")
                amount_score = 0.5
            else:
                mismatched_fields.append("total_amount")
                amount_score = 0.0
        else:
            mismatched_fields.append("total_amount")
            tolerance_analysis["error"] = "PO amount is zero or missing"
        
        # ===== 2. LINE ITEM QUANTITY CHECK (35% weight) =====
        invoice_items = invoice.get("line_items", [])
        po_items = po.get("line_items", [])
        qty_score = 0.0
        
        if invoice_items and po_items:
            qty_matches = 0
            total_items = max(len(invoice_items), len(po_items))
            
            for i, inv_item in enumerate(invoice_items):
                inv_qty = inv_item.get("qty", 0)
                
                # Find matching PO item (by index or description)
                po_item = po_items[i] if i < len(po_items) else None
                
                if po_item:
                    po_qty = po_item.get("qty", 0)
                    qty_diff_pct = abs(inv_qty - po_qty) / po_qty * 100 if po_qty > 0 else 100
                    
                    item_detail = {
                        "line": i + 1,
                        "invoice_qty": inv_qty,
                        "po_qty": po_qty,
                        "qty_diff_pct": round(qty_diff_pct, 2),
                        "qty_match": qty_diff_pct <= self.tolerance_pct
                    }
                    line_item_details.append(item_detail)
                    
                    if qty_diff_pct <= self.tolerance_pct:
                        qty_matches += 1
                else:
                    line_item_details.append({
                        "line": i + 1,
                        "invoice_qty": inv_qty,
                        "po_qty": None,
                        "error": "No matching PO line item"
                    })
            
            qty_score = qty_matches / total_items if total_items > 0 else 0.0
            tolerance_analysis["qty_match_ratio"] = f"{qty_matches}/{total_items}"
            
            if qty_score >= 0.9:
                matched_fields.append("line_quantities")
            elif qty_score >= 0.5:
                matched_fields.append("line_quantities_partial")
            else:
                mismatched_fields.append("line_quantities")
        else:
            # No line items to compare - use count check
            if len(invoice_items) == len(po_items):
                matched_fields.append("line_count")
                qty_score = 0.8
            else:
                mismatched_fields.append("line_count")
                qty_score = 0.0
        
        # ===== 3. LINE ITEM UNIT PRICE CHECK (25% weight) =====
        price_score = 0.0
        
        if invoice_items and po_items:
            price_matches = 0
            total_items = max(len(invoice_items), len(po_items))
            
            for i, inv_item in enumerate(invoice_items):
                inv_price = inv_item.get("unit_price", 0)
                po_item = po_items[i] if i < len(po_items) else None
                
                if po_item:
                    po_price = po_item.get("unit_price", 0)
                    price_diff_pct = abs(inv_price - po_price) / po_price * 100 if po_price > 0 else 100
                    
                    # Update existing line item detail
                    if i < len(line_item_details):
                        line_item_details[i]["invoice_price"] = inv_price
                        line_item_details[i]["po_price"] = po_price
                        line_item_details[i]["price_diff_pct"] = round(price_diff_pct, 2)
                        line_item_details[i]["price_match"] = price_diff_pct <= self.tolerance_pct
                    
                    if price_diff_pct <= self.tolerance_pct:
                        price_matches += 1
            
            price_score = price_matches / total_items if total_items > 0 else 0.0
            tolerance_analysis["price_match_ratio"] = f"{price_matches}/{total_items}"
            
            if price_score >= 0.9:
                matched_fields.append("unit_prices")
            elif price_score >= 0.5:
                matched_fields.append("unit_prices_partial")
            else:
                mismatched_fields.append("unit_prices")
        else:
            price_score = 0.5  # Neutral if no line items
        
        # ===== CALCULATE WEIGHTED FINAL SCORE =====
        # Weights: Amount=40%, Quantities=35%, Prices=25%
        final_score = (amount_score * 0.40) + (qty_score * 0.35) + (price_score * 0.25)
        final_score = round(final_score, 3)
        
        tolerance_analysis["component_scores"] = {
            "amount_score": round(amount_score, 2),
            "quantity_score": round(qty_score, 2),
            "price_score": round(price_score, 2),
            "weights": {"amount": 0.40, "quantity": 0.35, "price": 0.25}
        }
        
        self.logger.info(
            f"Match computed: amount={amount_score:.2f}, qty={qty_score:.2f}, "
            f"price={price_score:.2f} → final={final_score:.3f} (threshold={self.match_threshold})"
        )
        
        return {
            "score": final_score,
            "evidence": {
                "matched_fields": matched_fields,
                "mismatched_fields": mismatched_fields,
                "tolerance_analysis": tolerance_analysis,
                "line_item_details": line_item_details
            }
        }
