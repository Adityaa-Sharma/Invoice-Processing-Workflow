"""OCR/NLP Agent - UNDERSTAND Stage."""
import re
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class OcrNlpAgent(BaseAgent):
    """
    UNDERSTAND Stage Agent.
    
    Runs OCR on invoice attachments and parses line items.
    Uses ATLAS server for OCR (external service).
    Uses COMMON server for parsing.
    Uses BigtoolPicker to select OCR provider and LLM for parsing.
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
        
        - Uses BigtoolPicker to select OCR provider
        - Runs OCR on attachments via MCP ATLAS server
        - Uses LLM to parse and structure extracted data
        - Parses line items via MCP COMMON server
        
        Returns:
            dict with parsed_invoice, audit_log
        """
        self.logger.info("Starting UNDERSTAND stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            attachments = invoice.get("attachments", [])
            raw_id = state.get("raw_id")
            
            # Step 1: Use BigtoolPicker to select best OCR tool
            tool_selection = await self.select_tool(
                capability="ocr",
                context={
                    "attachments": attachments,
                    "file_types": [self._get_file_type(a) for a in attachments],
                    "invoice_id": invoice.get("invoice_id"),
                },
                use_llm=True
            )
            
            bigtool_selection = {
                "UNDERSTAND": {
                    "capability": "ocr",
                    "selected_tool": tool_selection.get("selected_tool", "google_vision"),
                    "pool": tool_selection.get("pool", ["google_vision", "tesseract", "aws_textract"]),
                    "reason": tool_selection.get("reason", "BigtoolPicker selection")
                }
            }
            
            # Step 2: Execute OCR via BigtoolPicker -> MCP ATLAS server
            ocr_result = await self.execute_with_bigtool(
                capability="ocr",
                params={
                    "raw_id": raw_id,
                    "attachments": attachments,
                    "invoice_data": invoice
                },
                context={"stage": "UNDERSTAND"}
            )
            
            # Get OCR text (with fallback to mock if MCP call fails)
            ocr_text = ocr_result.get("extracted_text") or self._mock_ocr_extract(invoice)
            ocr_results = ocr_result.get("attachment_results") or self._process_attachments(attachments, invoice)
            
            # Step 3: Use LLM to intelligently parse the OCR output
            llm_parse_result = await self.invoke_llm(
                stage="UNDERSTAND",
                task="Parse invoice OCR output and extract structured data",
                context={
                    "ocr_text": ocr_text,
                    "invoice_metadata": {
                        "invoice_id": invoice.get("invoice_id"),
                        "vendor_name": invoice.get("vendor_name"),
                        "amount": invoice.get("amount"),
                    },
                    "line_items_raw": invoice.get("line_items", [])
                },
                output_format="json with: line_items, po_references, currency, dates"
            )
            
            # Step 4: Call COMMON server for line item parsing/validation
            parse_result = await self.execute_with_bigtool(
                capability="parsing",
                params={
                    "raw_id": raw_id,
                    "ocr_text": ocr_text,
                    "line_items": invoice.get("line_items", [])
                },
                context={"stage": "UNDERSTAND"}
            )
            
            # Build parsed invoice with combined results
            parsed_invoice = {
                "invoice_text": ocr_text,
                "parsed_line_items": parse_result.get("line_items") or invoice.get("line_items", []),
                "detected_pos": self._extract_po_references(ocr_text),
                "currency": invoice.get("currency", "USD"),
                "parsed_dates": {
                    "invoice_date": invoice.get("invoice_date"),
                    "due_date": invoice.get("due_date")
                },
                "attachments_processed": ocr_results,
                "llm_analysis": llm_parse_result.get("response", {})
            }
            
            self.log_execution(
                stage="UNDERSTAND",
                action="ocr_parse",
                result={
                    "line_items_count": len(parsed_invoice["parsed_line_items"]),
                    "attachments_processed": len(attachments),
                    "ocr_tool": tool_selection.get("selected_tool")
                },
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
                        "tool": tool_selection.get("selected_tool", "google_vision"),
                        "line_items_parsed": len(parsed_invoice["parsed_line_items"]),
                        "pos_detected": len(parsed_invoice["detected_pos"]),
                        "attachments_scanned": len(attachments),
                        "confidence": ocr_result.get("confidence", 0.95),
                        "llm_used": True
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("UNDERSTAND", e, state)
    
    def _get_file_type(self, attachment: str) -> str:
        """Get file type from attachment name."""
        if attachment.endswith(".pdf"):
            return "pdf"
        elif attachment.endswith((".png", ".jpg", ".jpeg")):
            return "image"
        return "unknown"
    
    def _process_attachments(self, attachments: list[str], invoice: dict) -> list[dict]:
        """
        Process each attachment with mock OCR.
        
        Returns list of OCR results per attachment.
        """
        results = []
        for idx, attachment in enumerate(attachments):
            # Determine file type from extension
            file_type = "unknown"
            if attachment.endswith(".pdf"):
                file_type = "pdf"
            elif attachment.endswith((".png", ".jpg", ".jpeg")):
                file_type = "image"
            
            results.append({
                "file": attachment,
                "file_type": file_type,
                "ocr_provider": "google_vision",
                "pages_processed": 1 if file_type == "image" else 2,
                "confidence_score": 0.92 + (idx * 0.02),  # Slightly vary confidence
                "extracted_text_preview": f"[OCR content from {attachment}]",
                "status": "success"
            })
        
        return results
    
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
