"""OCR/NLP Agent - UNDERSTAND Stage."""
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class OcrNlpAgent(BaseAgent):
    """
    UNDERSTAND Stage Agent.
    
    Runs OCR on invoice attachments and parses line items.
    Uses ATLAS server for OCR (external service).
    Uses COMMON server for parsing.
    Uses Bigtool to select OCR provider.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="OcrNlpAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "raw_id"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("raw_id") is not None and
            state.get("invoice_payload") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute UNDERSTAND stage.
        
        - Runs OCR on attachments (mock)
        - Parses line items, amounts, PO references
        - Normalizes dates and currency
        
        Returns:
            dict with parsed_invoice, audit_log
        """
        self.logger.info("Starting UNDERSTAND stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            
            # Mock bigtool selection for OCR
            bigtool_selection = {
                "UNDERSTAND": {
                    "capability": "ocr",
                    "selected_tool": "google_vision",
                    "pool": ["google_vision", "tesseract", "aws_textract"],
                    "reason": "google_vision highest accuracy, available"
                }
            }
            
            # Mock OCR result - in production, would call actual OCR service
            ocr_text = self._mock_ocr_extract(invoice)
            
            # Parse the invoice data
            parsed_invoice = {
                "invoice_text": ocr_text,
                "parsed_line_items": invoice.get("line_items", []),
                "detected_pos": self._extract_po_references(ocr_text),
                "currency": invoice.get("currency", "USD"),
                "parsed_dates": {
                    "invoice_date": invoice.get("invoice_date"),
                    "due_date": invoice.get("due_date")
                }
            }
            
            self.log_execution(
                stage="UNDERSTAND",
                action="ocr_parse",
                result={"line_items_count": len(parsed_invoice["parsed_line_items"])},
                bigtool_selection=bigtool_selection["UNDERSTAND"]
            )
            
            return {
                "parsed_invoice": parsed_invoice,
                "current_stage": "UNDERSTAND",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "UNDERSTAND",
                    "ocr_completed",
                    {
                        "tool": "google_vision",
                        "line_items_parsed": len(parsed_invoice["parsed_line_items"]),
                        "pos_detected": len(parsed_invoice["detected_pos"]),
                        "confidence": 0.95
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("UNDERSTAND", e, state)
    
    def _mock_ocr_extract(self, invoice: dict) -> str:
        """Mock OCR text extraction."""
        vendor = invoice.get("vendor_name", "Unknown Vendor")
        amount = invoice.get("amount", 0)
        invoice_id = invoice.get("invoice_id", "Unknown")
        
        return f"""
INVOICE #{invoice_id}
Vendor: {vendor}
Amount: ${amount:,.2f}
Date: {invoice.get('invoice_date', 'N/A')}
Due: {invoice.get('due_date', 'N/A')}

Line Items:
{self._format_line_items(invoice.get('line_items', []))}

PO Reference: PO-{invoice_id.replace('INV-', '')}
        """.strip()
    
    def _format_line_items(self, line_items: list) -> str:
        """Format line items for mock OCR output."""
        lines = []
        for item in line_items:
            lines.append(
                f"- {item.get('desc')}: {item.get('qty')} x ${item.get('unit_price')} = ${item.get('total')}"
            )
        return "\n".join(lines)
    
    def _extract_po_references(self, text: str) -> list[str]:
        """Extract PO references from OCR text."""
        # Simple mock extraction - in production would use regex/NLP
        pos = []
        if "PO-" in text:
            # Extract PO references
            import re
            matches = re.findall(r'PO-[\w\d-]+', text)
            pos.extend(matches)
        return pos
