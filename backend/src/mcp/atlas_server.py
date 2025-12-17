"""
ATLAS MCP Server - External Operations.

Handles external/third-party operations:
- OCR extraction
- Vendor enrichment
- PO/GRN data fetching
- ERP posting
- Payment scheduling
- Notifications

Run: uvicorn src.mcp.atlas_server:app --port 8002
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import uuid4
import random

# Create FastAPI app
app = FastAPI(
    title="ATLAS MCP Server",
    description="External operations server for invoice processing",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ToolRequest(BaseModel):
    """Generic tool request."""
    class Config:
        extra = "allow"


class ToolResponse(BaseModel):
    """Generic tool response."""
    success: bool
    tool: str
    result: dict[str, Any]
    timestamp: str


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "server": "ATLAS",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/tools")
async def list_tools():
    """List available tools."""
    return [
        "extract_ocr",
        "enrich_vendor",
        "fetch_po_data",
        "fetch_grn_data",
        "post_to_erp",
        "schedule_payment",
        "send_notification",
        "apply_policy"
    ]


# ============================================================================
# Tool Endpoints
# ============================================================================

@app.post("/tools/extract_ocr")
async def extract_ocr(request: ToolRequest):
    """
    Extract text from invoice document using OCR.
    
    Args:
        file_path: Path to document
        file_base64: Base64 encoded document
        file_type: Type of document (pdf, image)
    """
    data = request.model_dump()
    file_path = data.get("file_path", "")
    file_type = data.get("file_type", "pdf")
    
    # Simulate OCR extraction
    invoice_id = f"INV-{random.randint(10000, 99999)}"
    vendor = random.choice(["Acme Corp", "TechFlow Inc", "Global Services LLC", "DataSoft Ltd"])
    amount = round(random.uniform(1000, 50000), 2)
    
    result = {
        "extracted_data": {
            "invoice_number": invoice_id,
            "vendor_name": vendor,
            "invoice_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
            "due_date": (datetime.now() + timedelta(days=random.randint(15, 45))).strftime("%Y-%m-%d"),
            "amount": amount,
            "currency": "USD",
            "line_items": [
                {"description": "Professional Services", "quantity": 1, "unit_price": amount * 0.7, "amount": amount * 0.7},
                {"description": "Support & Maintenance", "quantity": 1, "unit_price": amount * 0.3, "amount": amount * 0.3}
            ],
            "payment_terms": "NET30",
            "tax_amount": round(amount * 0.08, 2)
        },
        "confidence": round(random.uniform(0.85, 0.98), 2),
        "ocr_engine": "google_vision",
        "file_type": file_type,
        "extracted_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ToolResponse(
        success=True,
        tool="extract_ocr",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/enrich_vendor")
async def enrich_vendor(request: ToolRequest):
    """
    Enrich vendor data from external sources.
    
    Args:
        vendor_name: Name of vendor
        vendor_id: Optional vendor ID
        domain: Optional company domain
    """
    data = request.model_dump()
    vendor_name = data.get("vendor_name", "Unknown Vendor")
    
    # Simulate vendor enrichment
    vendor_id = data.get("vendor_id", f"VND-{uuid4().hex[:8].upper()}")
    
    result = {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "enriched_data": {
            "legal_name": f"{vendor_name} Corporation",
            "tax_id": f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
            "duns_number": str(random.randint(100000000, 999999999)),
            "industry": random.choice(["Technology", "Manufacturing", "Services", "Healthcare"]),
            "employee_count": random.randint(50, 5000),
            "revenue_range": random.choice(["$10M-$50M", "$50M-$100M", "$100M-$500M"]),
            "address": {
                "street": f"{random.randint(100, 9999)} Tech Boulevard",
                "city": random.choice(["San Francisco", "Austin", "Seattle", "Boston"]),
                "state": random.choice(["CA", "TX", "WA", "MA"]),
                "zip": str(random.randint(10000, 99999)),
                "country": "USA"
            },
            "payment_terms_default": "NET30",
            "risk_score": round(random.uniform(0.1, 0.5), 2)
        },
        "enrichment_source": "clearbit",
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "confidence": round(random.uniform(0.80, 0.95), 2)
    }
    
    return ToolResponse(
        success=True,
        tool="enrich_vendor",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/fetch_po_data")
async def fetch_po_data(request: ToolRequest):
    """
    Fetch Purchase Order data from ERP.
    
    Args:
        po_number: Purchase order number
        vendor_id: Vendor identifier
        invoice_id: Related invoice ID
    """
    data = request.model_dump()
    po_number = data.get("po_number", f"PO-{random.randint(10000, 99999)}")
    vendor_id = data.get("vendor_id", "")
    
    # Simulate PO fetch
    po_amount = round(random.uniform(5000, 50000), 2)
    
    result = {
        "po_number": po_number,
        "po_data": {
            "vendor_id": vendor_id,
            "po_date": (datetime.now() - timedelta(days=random.randint(30, 90))).strftime("%Y-%m-%d"),
            "po_amount": po_amount,
            "currency": "USD",
            "status": "APPROVED",
            "line_items": [
                {"description": "Professional Services", "quantity": 1, "unit_price": po_amount * 0.7},
                {"description": "Support & Maintenance", "quantity": 1, "unit_price": po_amount * 0.3}
            ],
            "approver": "John Manager",
            "cost_center": f"CC-{random.randint(100, 999)}",
            "department": random.choice(["Engineering", "Operations", "IT", "Finance"])
        },
        "source": "sap_erp",
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ToolResponse(
        success=True,
        tool="fetch_po_data",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/fetch_grn_data")
async def fetch_grn_data(request: ToolRequest):
    """
    Fetch Goods Receipt Note data from ERP.
    
    Args:
        grn_number: GRN number
        po_number: Related PO number
        invoice_id: Related invoice ID
    """
    data = request.model_dump()
    grn_number = data.get("grn_number", f"GRN-{random.randint(10000, 99999)}")
    po_number = data.get("po_number", "")
    
    # Simulate GRN fetch
    grn_amount = round(random.uniform(5000, 50000), 2)
    
    result = {
        "grn_number": grn_number,
        "grn_data": {
            "po_number": po_number,
            "receipt_date": (datetime.now() - timedelta(days=random.randint(5, 30))).strftime("%Y-%m-%d"),
            "received_amount": grn_amount,
            "currency": "USD",
            "status": "COMPLETE",
            "items_received": [
                {"description": "Professional Services", "quantity": 1, "received": True},
                {"description": "Support & Maintenance", "quantity": 1, "received": True}
            ],
            "received_by": "Jane Warehouse",
            "warehouse": "WH-001",
            "quality_check": "PASSED"
        },
        "source": "sap_erp",
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ToolResponse(
        success=True,
        tool="fetch_grn_data",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/post_to_erp")
async def post_to_erp(request: ToolRequest):
    """
    Post invoice to ERP system.
    
    Args:
        invoice_id: Invoice identifier
        invoice_data: Complete invoice data
        journal_entries: Accounting entries to post
    """
    data = request.model_dump()
    invoice_id = data.get("invoice_id", f"INV-{uuid4().hex[:8].upper()}")
    
    # Simulate ERP posting
    erp_doc_id = f"ERP-{uuid4().hex[:10].upper()}"
    
    result = {
        "erp_document_id": erp_doc_id,
        "invoice_id": invoice_id,
        "posting_status": "SUCCESS",
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "erp_system": "mock_erp",
        "fiscal_year": datetime.now().year,
        "fiscal_period": datetime.now().month,
        "document_type": "VENDOR_INVOICE",
        "posting_key": "31",
        "company_code": "1000",
        "journal_id": f"JE-{random.randint(100000, 999999)}"
    }
    
    return ToolResponse(
        success=True,
        tool="post_to_erp",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/schedule_payment")
async def schedule_payment(request: ToolRequest):
    """
    Schedule payment for approved invoice.
    
    Args:
        invoice_id: Invoice identifier
        amount: Payment amount
        currency: Payment currency
        due_date: Payment due date
        vendor_id: Vendor identifier
    """
    data = request.model_dump()
    invoice_id = data.get("invoice_id", "")
    amount = data.get("amount", 0)
    currency = data.get("currency", "USD")
    
    # Simulate payment scheduling
    payment_id = f"PAY-{uuid4().hex[:10].upper()}"
    payment_date = datetime.now() + timedelta(days=random.randint(7, 30))
    
    result = {
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "currency": currency,
        "scheduled_date": payment_date.strftime("%Y-%m-%d"),
        "payment_method": random.choice(["ACH", "WIRE", "CHECK"]),
        "status": "SCHEDULED",
        "bank_account": "****1234",
        "batch_id": f"BATCH-{datetime.now().strftime('%Y%m%d')}-{random.randint(100, 999)}",
        "scheduled_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ToolResponse(
        success=True,
        tool="schedule_payment",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/send_notification")
async def send_notification(request: ToolRequest):
    """
    Send notification via email or other channels.
    
    Args:
        recipient: Notification recipient
        notification_type: Type of notification
        subject: Notification subject
        message: Notification message
        invoice_id: Related invoice ID
    """
    data = request.model_dump()
    recipient = data.get("recipient", data.get("recipients", ["admin@company.com"]))
    notification_type = data.get("notification_type", "email")
    subject = data.get("subject", "Invoice Processing Notification")
    message = data.get("message", "Your invoice has been processed")
    invoice_id = data.get("invoice_id", "")
    
    # Simulate notification sending
    notification_id = f"NOTIF-{uuid4().hex[:10].upper()}"
    
    if isinstance(recipient, str):
        recipient = [recipient]
    
    result = {
        "notification_id": notification_id,
        "recipient": recipient,
        "notification_type": notification_type,
        "subject": subject,
        "message_preview": message[:100] + "..." if len(message) > 100 else message,
        "invoice_id": invoice_id,
        "status": "SENT",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "delivery_status": {r: "DELIVERED" for r in recipient}
    }
    
    return ToolResponse(
        success=True,
        tool="send_notification",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/apply_policy")
async def apply_policy(request: ToolRequest):
    """
    Apply approval policy to an invoice.
    
    Args:
        invoice: Invoice data
        vendor: Vendor profile
        amount: Invoice amount
    """
    data = request.model_dump()
    invoice = data.get("invoice", {})
    vendor = data.get("vendor", {})
    amount = data.get("amount", invoice.get("amount", 0))
    
    # Policy thresholds
    AUTO_APPROVE_LIMIT = 10000.0
    MANAGER_APPROVE_LIMIT = 50000.0
    
    risk_score = vendor.get("risk_score", 0) if vendor else 0
    
    # Apply policy rules
    if risk_score > 0.5:
        status = "APPROVED_WITH_REVIEW"
        approver_id = "MANAGER-REVIEW"
        policy = "high_risk_vendor"
    elif amount <= AUTO_APPROVE_LIMIT:
        status = "AUTO_APPROVED"
        approver_id = "SYSTEM"
        policy = "auto_approve_small_amount"
    elif amount <= MANAGER_APPROVE_LIMIT:
        status = "APPROVED"
        approver_id = "MGR-001"
        policy = "manager_approval"
    else:
        status = "APPROVED"
        approver_id = "EXEC-001"
        policy = "executive_approval"
    
    return ToolResponse(
        success=True,
        tool="apply_policy",
        result={
            "status": status,
            "approver_id": approver_id,
            "policy": policy,
            "amount": amount,
            "risk_score": risk_score,
            "applied_at": datetime.now(timezone.utc).isoformat()
        },
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
