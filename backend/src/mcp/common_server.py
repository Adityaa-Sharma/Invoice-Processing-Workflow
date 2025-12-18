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
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Any, Optional
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

@app.post("/tools/validate_invoice_schema")
async def validate_invoice_schema(request: ToolRequest):
    """
    Validate invoice payload against schema.
    
    Args:
        payload: The data to validate
        schema_type: Type of schema (default: invoice)
    """
    data = request.model_dump()
    payload = data.get("payload", data)
    schema_type = data.get("schema_type", "invoice")
    
    errors = []
    
    if schema_type == "invoice":
        required_fields = ["invoice_id", "vendor_name", "amount", "currency"]
        for field in required_fields:
            if field not in payload or payload.get(field) is None:
                errors.append(f"Missing required field: {field}")
        
        amount = payload.get("amount")
        if amount is not None and amount <= 0:
            errors.append("Amount must be positive")
        
        currency = payload.get("currency", "")
        if currency and len(currency) != 3:
            errors.append("Currency must be 3-letter ISO code")
    
    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "schema_type": schema_type,
        "fields_checked": len(payload)
    }
    
    return ToolResponse(
        success=True,
        tool="validate_invoice_schema",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/persist_invoice")
async def persist_invoice(request: ToolRequest):
    """
    Persist invoice data to storage.
    
    Args:
        payload: Invoice data to persist
        storage_type: Type of storage (default: database)
    """
    data = request.model_dump()
    payload = data.get("payload", data)
    storage_type = data.get("storage_type", "database")
    
    raw_id = f"RAW-{uuid4().hex[:12].upper()}"
    
    result = {
        "raw_id": raw_id,
        "storage_type": storage_type,
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "payload_size": len(str(payload)),
        "invoice_id": payload.get("invoice_id"),
        "persisted": True
    }
    
    return ToolResponse(
        success=True,
        tool="persist_invoice",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/tools/parse_line_items")
async def parse_line_items(request: ToolRequest):
    """
    Parse line items from structured data or text.
    
    Args:
        line_items: List of line item dicts
        text: Raw text to parse
    """
    data = request.model_dump()
    line_items = data.get("line_items", [])
    text = data.get("text", "")
    
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


@app.post("/tools/normalize_vendor")
async def normalize_vendor(request: ToolRequest):
    """
    Normalize vendor name and data.
    
    Args:
        vendor_name: Vendor name to normalize
        vendor_data: Optional additional vendor data
    """
    data = request.model_dump()
    vendor_name = data.get("vendor_name", "")
    vendor_data = data.get("vendor_data", {})
    
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


@app.post("/tools/create_checkpoint")
async def create_checkpoint(request: ToolRequest):
    """
    Create HITL checkpoint for workflow interruption.
    
    Args:
        workflow_id: Workflow identifier
        invoice_id: Invoice identifier
        state: Current workflow state
        reason: Reason for checkpoint
        required_fields: Fields that need review
    """
    data = request.model_dump()
    
    checkpoint_id = f"CP-{uuid4().hex[:12].upper()}"
    
    checkpoint = {
        "checkpoint_id": checkpoint_id,
        "workflow_id": data.get("workflow_id"),
        "invoice_id": data.get("invoice_id"),
        "state": data.get("state", {}),
        "reason": data.get("reason", "Manual review required"),
        "required_fields": data.get("required_fields", []),
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


@app.post("/tools/get_checkpoint")
async def get_checkpoint(request: ToolRequest):
    """
    Retrieve checkpoint by ID.
    
    Args:
        checkpoint_id: Checkpoint identifier to retrieve
    """
    data = request.model_dump()
    checkpoint_id = data.get("checkpoint_id")
    
    if not checkpoint_id:
        return ToolResponse(
            success=False,
            tool="get_checkpoint",
            result={"error": "checkpoint_id required"},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
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


@app.post("/tools/compute_match")
async def compute_match(request: ToolRequest):
    """
    Compute match score between invoice and PO.
    
    Args:
        invoice: Invoice data
        purchase_orders: List of POs
        grns: List of GRNs
        tolerance_pct: Tolerance percentage
    """
    data = request.model_dump()
    invoice = data.get("invoice", {})
    pos = data.get("purchase_orders", [])
    tolerance = data.get("tolerance_pct", 5.0)
    
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


@app.post("/tools/build_entries")
async def build_entries(request: ToolRequest):
    """
    Build accounting entries for an invoice.
    
    Args:
        invoice: Invoice data
        vendor: Vendor profile
        line_items: Line items to process
    """
    data = request.model_dump()
    invoice = data.get("invoice", {})
    vendor = data.get("vendor", {})
    
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


@app.post("/tools/persist_audit")
async def persist_audit(request: ToolRequest):
    """
    Persist audit log entries to storage.
    
    Args:
        invoice_id: Invoice identifier
        raw_id: Raw workflow ID
        audit_entries: List of audit entries
    """
    data = request.model_dump()
    invoice_id = data.get("invoice_id", "")
    raw_id = data.get("raw_id", "")
    audit_entries = data.get("audit_entries", [])
    
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
