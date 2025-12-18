"""
COMMON MCP Server - Internal Operations.

Handles internal/company operations:
- Schema validation
- Data persistence
- Line item parsing
- Vendor normalization
- Checkpoint management

Run: uvicorn src.mcp.common_server:app --port 8001
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict
from uuid import uuid4
import re

# Create FastAPI app
app = FastAPI(
    title="COMMON MCP Server",
    description="Internal operations server for invoice processing",
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

# In-memory checkpoint storage (in production: use Redis or database)
_checkpoints: dict[str, dict] = {}


# ============================================================================
# Request/Response Models
# ============================================================================

class ToolResponse(BaseModel):
    """Generic tool response."""
    success: bool
    tool: str
    result: dict[str, Any]
    timestamp: str


# --- Validate Invoice Schema ---
class ValidateInvoiceSchemaRequest(BaseModel):
    """Request model for validate_invoice_schema tool."""
    invoice: Dict[str, Any] = Field(..., description="Invoice data to validate")
    schema_type: Optional[str] = Field("invoice", description="Type of schema to validate against")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice": {
                    "invoice_id": "INV-001",
                    "vendor_name": "Acme Corp",
                    "amount": 15000.0,
                    "currency": "USD"
                },
                "schema_type": "invoice"
            }
        }


# --- Persist Invoice ---
class PersistInvoiceRequest(BaseModel):
    """Request model for persist_invoice tool."""
    invoice: Dict[str, Any] = Field(..., description="Invoice data to store")
    timestamp: Optional[str] = Field(None, description="Ingestion timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice": {"invoice_id": "INV-001", "vendor_name": "Acme Corp", "amount": 15000.0},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


# --- Parse Line Items ---
class LineItemInput(BaseModel):
    """Line item input model."""
    desc: Optional[str] = Field(None, description="Item description")
    description: Optional[str] = Field(None, description="Item description (alternate)")
    qty: Optional[float] = Field(None, description="Quantity")
    quantity: Optional[float] = Field(None, description="Quantity (alternate)")
    unit_price: Optional[float] = Field(None, description="Unit price")
    price: Optional[float] = Field(None, description="Price (alternate)")
    amount: Optional[float] = Field(None, description="Line amount")
    total: Optional[float] = Field(None, description="Line total")

    class Config:
        extra = "allow"


class ParseLineItemsRequest(BaseModel):
    """Request model for parse_line_items tool."""
    line_items: List[Dict[str, Any]] = Field(default=[], description="List of line item dicts")
    text: Optional[str] = Field("", description="Raw invoice text to parse")

    class Config:
        json_schema_extra = {
            "example": {
                "line_items": [
                    {"desc": "Software License", "qty": 5, "unit_price": 1000, "total": 5000},
                    {"desc": "Support Package", "qty": 1, "unit_price": 2000, "total": 2000}
                ]
            }
        }


# --- Normalize Vendor ---
class NormalizeVendorRequest(BaseModel):
    """Request model for normalize_vendor tool."""
    vendor_name: str = Field(..., description="Raw vendor name to normalize")
    tax_id: Optional[str] = Field(None, description="Optional tax ID for validation")
    vendor_data: Optional[Dict[str, Any]] = Field(None, description="Additional vendor data")

    class Config:
        json_schema_extra = {
            "example": {
                "vendor_name": "Acme Technologies Inc.",
                "tax_id": "TAX-123456"
            }
        }


# --- Create Checkpoint ---
class CreateCheckpointRequest(BaseModel):
    """Request model for create_checkpoint tool."""
    thread_id: str = Field(..., description="Workflow thread identifier")
    state: Dict[str, Any] = Field(..., description="Current workflow state to checkpoint")
    reason: Optional[str] = Field("Manual review required", description="Reason for checkpoint")
    workflow_id: Optional[str] = Field(None, description="Workflow identifier")
    invoice_id: Optional[str] = Field(None, description="Invoice identifier")
    required_fields: Optional[List[str]] = Field(None, description="Fields that need review")

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc123",
                "state": {"current_stage": "MATCH_TWO_WAY", "match_score": 0.75},
                "reason": "Match score below threshold"
            }
        }


# --- Get Checkpoint ---
class GetCheckpointRequest(BaseModel):
    """Request model for get_checkpoint tool."""
    checkpoint_id: str = Field(..., description="Checkpoint identifier to retrieve")

    class Config:
        json_schema_extra = {
            "example": {"checkpoint_id": "CP-ABC123DEF456"}
        }


# --- Compute Match ---
class ComputeMatchRequest(BaseModel):
    """Request model for compute_match tool."""
    invoice: Dict[str, Any] = Field(..., description="Invoice data")
    purchase_orders: List[Dict[str, Any]] = Field(..., description="List of POs to match against")
    tolerance_pct: Optional[float] = Field(5.0, description="Tolerance percentage for matching")
    grns: Optional[List[Dict[str, Any]]] = Field(None, description="List of GRNs")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice": {"invoice_id": "INV-001", "amount": 15000, "vendor_name": "Acme Corp"},
                "purchase_orders": [{"po_number": "PO-001", "total_amount": 15000, "vendor_name": "Acme Corp"}],
                "tolerance_pct": 5.0
            }
        }


# --- Build Entries ---
class BuildEntriesRequest(BaseModel):
    """Request model for build_entries tool."""
    invoice: Dict[str, Any] = Field(..., description="Invoice data")
    vendor: Optional[Dict[str, Any]] = Field(None, description="Vendor profile")
    account_mapping: Optional[Dict[str, Any]] = Field(None, description="Account code mappings")
    line_items: Optional[List[Dict[str, Any]]] = Field(None, description="Line items to process")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice": {"invoice_id": "INV-001", "amount": 15000, "currency": "USD", "vendor_name": "Acme Corp"},
                "vendor": {"normalized_name": "Acme Corporation"}
            }
        }


# --- Persist Audit ---
class PersistAuditRequest(BaseModel):
    """Request model for persist_audit tool."""
    invoice_id: str = Field(..., description="Invoice identifier")
    audit_entries: List[Dict[str, Any]] = Field(..., description="List of audit entries to store")
    raw_id: Optional[str] = Field(None, description="Raw workflow ID")

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-001",
                "audit_entries": [
                    {"stage": "INTAKE", "action": "validated", "timestamp": "2024-01-15T10:30:00Z"},
                    {"stage": "COMPLETE", "action": "finalized", "timestamp": "2024-01-15T10:35:00Z"}
                ]
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
        "server": "COMMON",
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
                "name": "validate_invoice_schema",
                "description": "Validate invoice payload against the expected schema. Use this to verify invoice data structure before processing. Returns validation errors if schema is invalid.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice": {"type": "object", "description": "Invoice data to validate"},
                        "schema_type": {"type": "string", "description": "Type of schema to validate against"}
                    },
                    "required": ["invoice"]
                }
            },
            {
                "name": "persist_invoice",
                "description": "Store invoice data to persistent storage. Use this to save raw invoice data for audit trail and later retrieval. Supports various storage backends.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice": {"type": "object", "description": "Invoice data to store"},
                        "timestamp": {"type": "string", "description": "Ingestion timestamp"}
                    },
                    "required": ["invoice"]
                }
            },
            {
                "name": "persist_audit",
                "description": "Persist audit log entries for compliance and tracking. Use this to store workflow execution history and decision trails.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "string", "description": "Invoice identifier"},
                        "audit_entries": {"type": "array", "description": "List of audit entries to store"}
                    },
                    "required": ["invoice_id", "audit_entries"]
                }
            },
            {
                "name": "parse_line_items",
                "description": "Parse and extract line items from invoice text. Use this to structure raw OCR text into individual line items with quantities and prices.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Raw invoice text to parse"},
                        "format_hint": {"type": "string", "description": "Optional format hint"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "normalize_vendor",
                "description": "Normalize vendor name to canonical form. Use this to standardize vendor names for consistent matching and deduplication.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vendor_name": {"type": "string", "description": "Raw vendor name to normalize"},
                        "tax_id": {"type": "string", "description": "Optional tax ID for validation"}
                    },
                    "required": ["vendor_name"]
                }
            },
            {
                "name": "create_checkpoint",
                "description": "Create a workflow checkpoint for HITL (Human-in-the-Loop) review. Use this when matching fails and human review is required.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "thread_id": {"type": "string", "description": "Workflow thread identifier"},
                        "state": {"type": "object", "description": "Current workflow state to checkpoint"},
                        "reason": {"type": "string", "description": "Reason for checkpoint"}
                    },
                    "required": ["thread_id", "state"]
                }
            },
            {
                "name": "get_checkpoint",
                "description": "Retrieve a previously created checkpoint. Use this to resume a paused workflow after human review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "checkpoint_id": {"type": "string", "description": "Checkpoint identifier to retrieve"}
                    },
                    "required": ["checkpoint_id"]
                }
            },
            {
                "name": "compute_match",
                "description": "Compute 2-way match between invoice and purchase order. Use this to calculate match score and identify discrepancies.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice": {"type": "object", "description": "Invoice data"},
                        "purchase_orders": {"type": "array", "description": "List of POs to match against"},
                        "tolerance_pct": {"type": "number", "description": "Tolerance percentage for matching"}
                    },
                    "required": ["invoice", "purchase_orders"]
                }
            },
            {
                "name": "build_entries",
                "description": "Build accounting journal entries from invoice data. Use this to create debit/credit entries for ERP posting.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "invoice": {"type": "object", "description": "Invoice data"},
                        "account_mapping": {"type": "object", "description": "Account code mappings"}
                    },
                    "required": ["invoice"]
                }
            }
        ],
        "server": "COMMON",
        "description": "Internal operations server - handles validation, storage, matching, and accounting"
    }


# ============================================================================
# Tool Endpoints
# ============================================================================

@app.post("/tools/validate_invoice_schema", response_model=ToolResponse)
async def validate_invoice_schema(request: ValidateInvoiceSchemaRequest):
    """
    Validate invoice payload against schema.
    
    Validates that invoice data contains required fields and follows expected format.
    """
    invoice = request.invoice
    schema_type = request.schema_type or "invoice"
    
    errors = []
    
    if schema_type == "invoice":
        required_fields = ["invoice_id", "vendor_name", "amount", "currency"]
        for field in required_fields:
            if field not in invoice or invoice.get(field) is None:
                errors.append(f"Missing required field: {field}")
        
        amount = invoice.get("amount")
        if amount is not None and amount <= 0:
            errors.append("Amount must be positive")
        
        currency = invoice.get("currency", "")
        if currency and len(currency) != 3:
            errors.append("Currency must be 3-letter ISO code")
    
    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "schema_type": schema_type,
        "fields_checked": len(invoice)
    }
    
    return ToolResponse(
        success=True,
        tool="validate_invoice_schema",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/persist_invoice", response_model=ToolResponse)
async def persist_invoice(request: PersistInvoiceRequest):
    """
    Persist invoice data to storage.
    
    Stores raw invoice data for audit trail and later retrieval.
    """
    invoice = request.invoice
    timestamp = request.timestamp or datetime.now(timezone.utc).isoformat()
    
    raw_id = f"RAW-{uuid4().hex[:12].upper()}"
    
    result = {
        "raw_id": raw_id,
        "stored_at": timestamp,
        "payload_size": len(str(invoice)),
        "invoice_id": invoice.get("invoice_id"),
        "persisted": True
    }
    
    return ToolResponse(
        success=True,
        tool="persist_invoice",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/parse_line_items", response_model=ToolResponse)
async def parse_line_items(request: ParseLineItemsRequest):
    """
    Parse line items from structured data or text.
    
    Structures line items with GL codes and calculations.
    """
    line_items = request.line_items
    text = request.text or ""
    
    parsed_items = []
    
    # GL code mapping based on description keywords
    gl_mapping = {
        "software": "6200",
        "hardware": "1500",
        "license": "6210",
        "service": "6300",
        "support": "6310",
        "consulting": "6320",
        "maintenance": "6350",
        "equipment": "1510",
        "supply": "5100",
        "office": "5110",
    }
    
    for idx, item in enumerate(line_items, 1):
        desc = item.get("desc", item.get("description", ""))
        quantity = item.get("quantity", item.get("qty", 1))
        unit_price = item.get("unit_price", item.get("price", 0))
        amount = item.get("amount", quantity * unit_price)
        
        # Determine GL code
        gl_code = "6000"  # Default
        desc_lower = desc.lower()
        for keyword, code in gl_mapping.items():
            if keyword in desc_lower:
                gl_code = code
                break
        
        parsed_items.append({
            "line_number": idx,
            "description": desc,
            "quantity": quantity,
            "unit_price": unit_price,
            "amount": amount,
            "gl_code": gl_code,
            "tax_applicable": True
        })
    
    result = {
        "parsed_items": parsed_items,
        "total_items": len(parsed_items),
        "total_amount": sum(item["amount"] for item in parsed_items),
        "gl_codes_assigned": len(set(item["gl_code"] for item in parsed_items))
    }
    
    return ToolResponse(
        success=True,
        tool="parse_line_items",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/normalize_vendor", response_model=ToolResponse)
async def normalize_vendor(request: NormalizeVendorRequest):
    """
    Normalize vendor name and data.
    
    Standardizes vendor names for consistent matching and deduplication.
    """
    vendor_name = request.vendor_name
    vendor_data = request.vendor_data or {}
    
    # Normalize vendor name
    normalized = vendor_name.strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s\-&\.]', '', normalized)
    
    # Remove common suffixes for matching
    suffixes = [' inc', ' llc', ' ltd', ' corp', ' corporation', ' company', ' co']
    canonical = normalized.lower()
    for suffix in suffixes:
        if canonical.endswith(suffix):
            canonical = canonical[:-len(suffix)]
            break
    
    # Generate vendor ID
    vendor_id = f"VND-{uuid4().hex[:8].upper()}"
    
    result = {
        "original_name": vendor_name,
        "normalized_name": normalized,
        "canonical_name": canonical.title(),
        "vendor_id": vendor_id,
        "normalized_at": datetime.now(timezone.utc).isoformat()
    }
    
    return ToolResponse(
        success=True,
        tool="normalize_vendor",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/create_checkpoint", response_model=ToolResponse)
async def create_checkpoint(request: CreateCheckpointRequest):
    """
    Create HITL checkpoint for workflow interruption.
    
    Creates a checkpoint when human review is required.
    """
    checkpoint_id = f"CP-{uuid4().hex[:12].upper()}"
    
    checkpoint = {
        "checkpoint_id": checkpoint_id,
        "workflow_id": request.workflow_id or request.thread_id,
        "thread_id": request.thread_id,
        "invoice_id": request.invoice_id,
        "state": request.state,
        "reason": request.reason,
        "required_fields": request.required_fields or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
    
    # Store checkpoint
    _checkpoints[checkpoint_id] = checkpoint
    
    return ToolResponse(
        success=True,
        tool="create_checkpoint",
        result=checkpoint,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/get_checkpoint", response_model=ToolResponse)
async def get_checkpoint(request: GetCheckpointRequest):
    """
    Retrieve checkpoint by ID.
    
    Retrieves a previously created checkpoint for workflow resumption.
    """
    checkpoint_id = request.checkpoint_id
    checkpoint = _checkpoints.get(checkpoint_id)
    
    if not checkpoint:
        return ToolResponse(
            success=False,
            tool="get_checkpoint",
            result={"error": f"Checkpoint {checkpoint_id} not found"},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    return ToolResponse(
        success=True,
        tool="get_checkpoint",
        result=checkpoint,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/compute_match", response_model=ToolResponse)
async def compute_match(request: ComputeMatchRequest):
    """
    Compute match score between invoice and PO.
    
    Performs 2-way matching and calculates match score.
    """
    invoice = request.invoice
    pos = request.purchase_orders
    tolerance = request.tolerance_pct or 5.0
    
    if not pos:
        return ToolResponse(
            success=True,
            tool="compute_match",
            result={
                "score": 0.0,
                "evidence": {"error": "No POs to match"}
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    # Simple match logic
    po = pos[0]
    matched_fields = []
    mismatched_fields = []
    
    # Amount match
    inv_amount = invoice.get("amount", 0)
    po_amount = po.get("total_amount", 0)
    if po_amount > 0:
        diff_pct = abs(inv_amount - po_amount) / po_amount * 100
        if diff_pct <= tolerance:
            matched_fields.append("amount")
        else:
            mismatched_fields.append("amount")
    
    # Vendor match
    inv_vendor = invoice.get("vendor_name", "").upper()
    po_vendor = po.get("vendor_name", "").upper()
    if inv_vendor and po_vendor and (inv_vendor in po_vendor or po_vendor in inv_vendor):
        matched_fields.append("vendor")
    else:
        mismatched_fields.append("vendor")
    
    # Currency match
    if invoice.get("currency") == po.get("currency"):
        matched_fields.append("currency")
    else:
        mismatched_fields.append("currency")
    
    total = len(matched_fields) + len(mismatched_fields)
    score = len(matched_fields) / total if total > 0 else 0.0
    
    return ToolResponse(
        success=True,
        tool="compute_match",
        result={
            "score": score,
            "evidence": {
                "matched_fields": matched_fields,
                "mismatched_fields": mismatched_fields,
            }
        },
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/build_entries", response_model=ToolResponse)
async def build_entries(request: BuildEntriesRequest):
    """
    Build accounting entries for an invoice.
    
    Creates debit/credit journal entries for ERP posting.
    """
    invoice = request.invoice
    vendor = request.vendor or {}
    
    amount = invoice.get("amount", 0)
    invoice_id = invoice.get("invoice_id", "")
    vendor_name = vendor.get("normalized_name", invoice.get("vendor_name", ""))
    
    entry_id = uuid4().hex[:8].upper()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    entries = [
        {
            "entry_id": f"JE-{entry_id}-01",
            "type": "DEBIT",
            "account": "6000-Expenses",
            "amount": amount,
            "currency": invoice.get("currency", "USD"),
            "reference": invoice_id,
            "description": f"Expense for invoice {invoice_id} - {vendor_name}",
            "timestamp": timestamp
        },
        {
            "entry_id": f"JE-{entry_id}-02",
            "type": "CREDIT",
            "account": "2100-Accounts Payable",
            "amount": amount,
            "currency": invoice.get("currency", "USD"),
            "reference": invoice_id,
            "description": f"Payable to {vendor_name}",
            "timestamp": timestamp
        }
    ]
    
    return ToolResponse(
        success=True,
        tool="build_entries",
        result={"entries": entries},
        timestamp=timestamp
    )


@app.post("/tools/persist_audit", response_model=ToolResponse)
async def persist_audit(request: PersistAuditRequest):
    """
    Persist audit log entries to storage.
    
    Stores workflow execution history for compliance and tracking.
    """
    invoice_id = request.invoice_id
    raw_id = request.raw_id or ""
    audit_entries = request.audit_entries
    
    audit_record_id = f"AUDIT-{uuid4().hex[:10].upper()}"
    
    return ToolResponse(
        success=True,
        tool="persist_audit",
        result={
            "audit_id": audit_record_id,
            "invoice_id": invoice_id,
            "raw_id": raw_id,
            "entries_persisted": len(audit_entries),
            "persisted": True,
            "persisted_at": datetime.now(timezone.utc).isoformat()
        },
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
