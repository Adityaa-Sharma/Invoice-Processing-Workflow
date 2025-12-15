"""Invoice-related Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LineItem(BaseModel):
    """Single line item in an invoice."""
    desc: str = Field(..., description="Item description")
    qty: float = Field(..., gt=0, description="Quantity")
    unit_price: float = Field(..., ge=0, description="Unit price")
    total: float = Field(..., ge=0, description="Line item total")
    
    class Config:
        json_schema_extra = {
            "example": {
                "desc": "Software License",
                "qty": 5,
                "unit_price": 1000.0,
                "total": 5000.0
            }
        }


class InvoicePayload(BaseModel):
    """Invoice payload structure."""
    invoice_id: str = Field(..., description="Unique invoice identifier")
    vendor_name: str = Field(..., description="Vendor/supplier name")
    vendor_tax_id: Optional[str] = Field(None, description="Vendor tax ID")
    invoice_date: str = Field(..., description="Invoice date (ISO format)")
    due_date: str = Field(..., description="Payment due date (ISO format)")
    amount: float = Field(..., gt=0, description="Total invoice amount")
    currency: str = Field(default="USD", description="Currency code")
    line_items: list[LineItem] = Field(..., min_length=1, description="Invoice line items")
    attachments: list[str] = Field(default=[], description="Attachment file paths/URLs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-2024-001",
                "vendor_name": "Acme Corp",
                "vendor_tax_id": "TAX-123456",
                "invoice_date": "2024-01-15",
                "due_date": "2024-02-15",
                "amount": 15000.0,
                "currency": "USD",
                "line_items": [
                    {"desc": "Software License", "qty": 5, "unit_price": 1000.0, "total": 5000.0},
                    {"desc": "Support Package", "qty": 1, "unit_price": 10000.0, "total": 10000.0}
                ],
                "attachments": ["invoice.pdf"]
            }
        }


class InvoiceSubmitRequest(BaseModel):
    """Request body for invoice submission."""
    invoice: InvoicePayload


class InvoiceSubmitResponse(BaseModel):
    """Response after invoice submission."""
    thread_id: str = Field(..., description="Workflow thread ID for tracking")
    status: str = Field(..., description="Current workflow status")
    current_stage: str = Field(..., description="Current processing stage")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "abc123-def456",
                "status": "RUNNING",
                "current_stage": "INTAKE",
                "message": "Invoice submitted successfully. Processing started."
            }
        }


class InvoiceStatusResponse(BaseModel):
    """Response for invoice status query."""
    thread_id: str
    invoice_id: str
    status: str
    current_stage: str
    match_score: Optional[float] = None
    match_result: Optional[str] = None
    checkpoint_id: Optional[str] = None
    review_url: Optional[str] = None
    erp_txn_id: Optional[str] = None
    final_payload: Optional[dict] = None
    audit_log: list[dict] = []
    bigtool_selections: dict = {}
