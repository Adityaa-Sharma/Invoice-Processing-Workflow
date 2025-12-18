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
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, List, Dict, Literal
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

class ToolResponse(BaseModel):
    """Generic tool response."""
    success: bool
    tool: str
    result: dict[str, Any]
    timestamp: str


# --- Extract OCR ---
class ExtractOCRRequest(BaseModel):
    """Request model for extract_ocr tool."""
    file_path: str = Field(..., description="Path to file to process")
    provider: Optional[Literal["google_vision", "aws_textract", "tesseract"]] = Field(
        None, description="OCR provider to use"
    )
    file_type: Optional[str] = Field("pdf", description="Type of document (pdf, image)")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/uploads/invoice_scan.pdf",
                "provider": "google_vision"
            }
        }


# --- Enrich Vendor ---
class EnrichVendorRequest(BaseModel):
    """Request model for enrich_vendor tool."""
    vendor_name: str = Field(..., description="Vendor name to enrich")
    tax_id: Optional[str] = Field(None, description="Optional tax ID for better matching")
    vendor_id: Optional[str] = Field(None, description="Optional vendor ID")
    provider: Optional[Literal["clearbit", "people_data_labs", "vendor_db"]] = Field(
        None, description="Enrichment provider"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vendor_name": "Acme Technologies Inc",
                "tax_id": "TAX-123456",
                "provider": "clearbit"
            }
        }


# --- Fetch PO Data ---
class FetchPODataRequest(BaseModel):
    """Request model for fetch_po_data tool."""
    po_number: Optional[str] = Field(None, description="PO number to fetch")
    vendor_name: Optional[str] = Field(None, description="Vendor name for filtering")
    vendor_id: Optional[str] = Field(None, description="Vendor identifier")
    invoice_id: Optional[str] = Field(None, description="Related invoice ID")
    erp_system: Optional[Literal["sap", "oracle", "netsuite"]] = Field(
        None, description="ERP system to query"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "po_number": "PO-2024-001234",
                "vendor_name": "Acme Corp",
                "erp_system": "sap"
            }
        }


# --- Fetch GRN Data ---
class FetchGRNDataRequest(BaseModel):
    """Request model for fetch_grn_data tool."""
    po_number: Optional[str] = Field(None, description="Related PO number")
    vendor_name: Optional[str] = Field(None, description="Vendor name")
    grn_number: Optional[str] = Field(None, description="GRN number to fetch")
    invoice_id: Optional[str] = Field(None, description="Related invoice ID")

    class Config:
        json_schema_extra = {
            "example": {
                "po_number": "PO-2024-001234",
                "vendor_name": "Acme Corp"
            }
        }


# --- Post to ERP ---
class PostToERPRequest(BaseModel):
    """Request model for post_to_erp tool."""
    invoice_id: str = Field(..., description="Invoice identifier")
    entries: List[Dict[str, Any]] = Field(..., description="Accounting entries to post")
    invoice_data: Optional[Dict[str, Any]] = Field(None, description="Complete invoice data")
    erp_system: Optional[Literal["sap", "oracle", "netsuite"]] = Field(
        None, description="Target ERP system"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-2024-001",
                "entries": [
                    {"type": "DEBIT", "account": "6000", "amount": 15000},
                    {"type": "CREDIT", "account": "2100", "amount": 15000}
                ],
                "erp_system": "sap"
            }
        }


# --- Schedule Payment ---
class SchedulePaymentRequest(BaseModel):
    """Request model for schedule_payment tool."""
    invoice_id: str = Field(..., description="Invoice to pay")
    amount: float = Field(..., description="Payment amount")
    due_date: Optional[str] = Field(None, description="Payment due date")
    currency: Optional[str] = Field("USD", description="Payment currency")
    vendor_id: Optional[str] = Field(None, description="Vendor identifier")
    payment_method: Optional[Literal["ach", "wire", "check"]] = Field(
        None, description="Payment method"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-2024-001",
                "amount": 15000.00,
                "due_date": "2024-02-15",
                "payment_method": "ach"
            }
        }


# --- Send Notification ---
class SendNotificationRequest(BaseModel):
    """Request model for send_notification tool."""
    recipients: List[str] = Field(..., description="List of email recipients")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")
    notification_type: Optional[str] = Field("email", description="Type of notification")
    invoice_id: Optional[str] = Field(None, description="Related invoice ID")
    provider: Optional[Literal["sendgrid", "ses", "smtp"]] = Field(
        None, description="Email provider"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "recipients": ["vendor@example.com", "finance@company.com"],
                "subject": "Invoice INV-2024-001 Processed",
                "body": "Your invoice has been approved for payment.",
                "provider": "sendgrid"
            }
        }


# --- Apply Policy ---
class ApplyPolicyRequest(BaseModel):
    """Request model for apply_policy tool."""
    invoice: Dict[str, Any] = Field(..., description="Invoice data")
    vendor_risk_score: Optional[float] = Field(None, description="Vendor risk score")
    vendor: Optional[Dict[str, Any]] = Field(None, description="Vendor profile")
    amount: Optional[float] = Field(None, description="Invoice amount")
    policy_type: Optional[str] = Field(None, description="Policy type to apply")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice": {"invoice_id": "INV-001", "amount": 15000, "vendor_name": "Acme Corp"},
                "vendor_risk_score": 0.25,
                "policy_type": "standard_approval"
            }
        }


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
    """
    List available tools with descriptions (True MCP Protocol).
    
    Returns tool schemas that clients can use to dynamically discover
    available capabilities and make intelligent tool selections.
    """
    return {
        "tools": [
            {
                "name": "extract_ocr",
                "description": "Extract text from invoice images/PDFs using OCR. Use this to digitize paper invoices or scanned documents. Supports multiple OCR providers (Google Vision, AWS Textract, Tesseract).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to process"},
                        "provider": {"type": "string", "enum": ["google_vision", "aws_textract", "tesseract"], "description": "OCR provider to use"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "enrich_vendor",
                "description": "Enrich vendor data with external information. Use this to get company details, risk scores, and industry information from data providers like Clearbit or People Data Labs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vendor_name": {"type": "string", "description": "Vendor name to enrich"},
                        "tax_id": {"type": "string", "description": "Optional tax ID for better matching"},
                        "provider": {"type": "string", "enum": ["clearbit", "people_data_labs", "vendor_db"], "description": "Enrichment provider"}
                    },
                    "required": ["vendor_name"]
                }
            },
            {
                "name": "fetch_po_data",
                "description": "Fetch Purchase Order data from ERP systems. Use this to retrieve PO details for invoice matching. Supports SAP, Oracle, NetSuite connectors.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "po_number": {"type": "string", "description": "PO number to fetch"},
                        "vendor_name": {"type": "string", "description": "Vendor name for filtering"},
                        "erp_system": {"type": "string", "enum": ["sap", "oracle", "netsuite"], "description": "ERP system to query"}
                    }
                }
            },
            {
                "name": "fetch_grn_data",
                "description": "Fetch Goods Receipt Notes from ERP. Use this to verify that goods were actually received before approving invoice payment.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "po_number": {"type": "string", "description": "Related PO number"},
                        "vendor_name": {"type": "string", "description": "Vendor name"}
                    }
                }
            },
            {
                "name": "post_to_erp",
                "description": "Post approved invoice to ERP system. Use this to create accounting entries and update financial records in the ERP.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "string", "description": "Invoice identifier"},
                        "entries": {"type": "array", "description": "Accounting entries to post"},
                        "erp_system": {"type": "string", "enum": ["sap", "oracle", "netsuite"], "description": "Target ERP system"}
                    },
                    "required": ["invoice_id", "entries"]
                }
            },
            {
                "name": "schedule_payment",
                "description": "Schedule payment for approved invoice. Use this to create payment instruction based on payment terms and due date.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "string", "description": "Invoice to pay"},
                        "amount": {"type": "number", "description": "Payment amount"},
                        "due_date": {"type": "string", "description": "Payment due date"},
                        "payment_method": {"type": "string", "enum": ["ach", "wire", "check"], "description": "Payment method"}
                    },
                    "required": ["invoice_id", "amount"]
                }
            },
            {
                "name": "send_notification",
                "description": "Send email notifications to stakeholders. Use this to notify vendors of payment status or internal teams of processing updates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipients": {"type": "array", "description": "List of email recipients"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"},
                        "provider": {"type": "string", "enum": ["sendgrid", "ses", "smtp"], "description": "Email provider"}
                    },
                    "required": ["recipients", "subject", "body"]
                }
            },
            {
                "name": "apply_policy",
                "description": "Apply approval policies to invoice. Use this to determine if invoice can be auto-approved or needs escalation based on amount, vendor risk, or other rules.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice": {"type": "object", "description": "Invoice data"},
                        "vendor_risk_score": {"type": "number", "description": "Vendor risk score"},
                        "policy_type": {"type": "string", "description": "Policy type to apply"}
                    },
                    "required": ["invoice"]
                }
            }
        ],
        "server": "ATLAS",
        "description": "External operations server - handles OCR, enrichment, ERP integration, payments, and notifications"
    }


# ============================================================================
# Tool Endpoints
# ============================================================================

@app.post("/tools/extract_ocr", response_model=ToolResponse)
async def extract_ocr(request: ExtractOCRRequest):
    """
    Extract text from invoice document using OCR.
    
    Digitizes paper invoices or scanned documents using various OCR providers.
    """
    file_path = request.file_path
    file_type = request.file_type or "pdf"
    provider = request.provider or "google_vision"
    
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
        "ocr_engine": provider,
        "file_type": file_type,
        "extracted_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ToolResponse(
        success=True,
        tool="extract_ocr",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/enrich_vendor", response_model=ToolResponse)
async def enrich_vendor(request: EnrichVendorRequest):
    """
    Enrich vendor data from external sources.
    
    Gets company details, risk scores, and industry information from data providers.
    """
    vendor_name = request.vendor_name
    vendor_id = request.vendor_id or f"VND-{uuid4().hex[:8].upper()}"
    provider = request.provider or "clearbit"
    
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
        "enrichment_source": provider,
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "confidence": round(random.uniform(0.80, 0.95), 2)
    }
    
    return ToolResponse(
        success=True,
        tool="enrich_vendor",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/fetch_po_data", response_model=ToolResponse)
async def fetch_po_data(request: FetchPODataRequest):
    """
    Fetch Purchase Order data from ERP.
    
    Retrieves PO details for invoice matching from various ERP systems.
    """
    po_number = request.po_number or f"PO-{random.randint(10000, 99999)}"
    vendor_id = request.vendor_id or ""
    erp_system = request.erp_system or "sap"
    
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
        "source": f"{erp_system}_erp",
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ToolResponse(
        success=True,
        tool="fetch_po_data",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/fetch_grn_data", response_model=ToolResponse)
async def fetch_grn_data(request: FetchGRNDataRequest):
    """
    Fetch Goods Receipt Note data from ERP.
    
    Verifies that goods were actually received before approving invoice payment.
    """
    grn_number = request.grn_number or f"GRN-{random.randint(10000, 99999)}"
    po_number = request.po_number or ""
    
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


@app.post("/tools/post_to_erp", response_model=ToolResponse)
async def post_to_erp(request: PostToERPRequest):
    """
    Post invoice to ERP system.
    
    Creates accounting entries and updates financial records in the ERP.
    """
    invoice_id = request.invoice_id
    erp_system = request.erp_system or "mock_erp"
    
    # Simulate ERP posting
    erp_doc_id = f"ERP-{uuid4().hex[:10].upper()}"
    
    result = {
        "erp_document_id": erp_doc_id,
        "invoice_id": invoice_id,
        "posting_status": "SUCCESS",
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "erp_system": erp_system,
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


@app.post("/tools/schedule_payment", response_model=ToolResponse)
async def schedule_payment(request: SchedulePaymentRequest):
    """
    Schedule payment for approved invoice.
    
    Creates payment instruction based on payment terms and due date.
    """
    invoice_id = request.invoice_id
    amount = request.amount
    currency = request.currency or "USD"
    payment_method = request.payment_method or random.choice(["ach", "wire", "check"])
    
    # Simulate payment scheduling
    payment_id = f"PAY-{uuid4().hex[:10].upper()}"
    payment_date = datetime.now() + timedelta(days=random.randint(7, 30))
    
    result = {
        "payment_id": payment_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "currency": currency,
        "scheduled_date": payment_date.strftime("%Y-%m-%d"),
        "payment_method": payment_method.upper(),
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


@app.post("/tools/send_notification", response_model=ToolResponse)
async def send_notification(request: SendNotificationRequest):
    """
    Send notification via email or other channels.
    
    Notifies vendors of payment status or internal teams of processing updates.
    """
    recipients = request.recipients
    notification_type = request.notification_type or "email"
    subject = request.subject
    message = request.body
    invoice_id = request.invoice_id or ""
    provider = request.provider or "sendgrid"
    
    # Simulate notification sending
    notification_id = f"NOTIF-{uuid4().hex[:10].upper()}"
    
    result = {
        "notification_id": notification_id,
        "recipients": recipients,
        "notification_type": notification_type,
        "subject": subject,
        "message_preview": message[:100] + "..." if len(message) > 100 else message,
        "invoice_id": invoice_id,
        "status": "SENT",
        "provider": provider,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "delivery_status": {r: "DELIVERED" for r in recipients}
    }
    
    return ToolResponse(
        success=True,
        tool="send_notification",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/apply_policy", response_model=ToolResponse)
async def apply_policy(request: ApplyPolicyRequest):
    """
    Apply approval policy to an invoice.
    
    Determines if invoice can be auto-approved or needs escalation based on rules.
    """
    invoice = request.invoice
    vendor = request.vendor or {}
    amount = request.amount or invoice.get("amount", 0)
    risk_score = request.vendor_risk_score
    
    # Get risk score from vendor if not provided directly
    if risk_score is None:
        risk_score = vendor.get("risk_score", 0) if vendor else 0
    
    # Policy thresholds
    AUTO_APPROVE_LIMIT = 10000.0
    MANAGER_APPROVE_LIMIT = 50000.0
    
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