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
    """List available tools."""
    return [
        "validate_invoice_schema",
        "persist_invoice",
        "parse_line_items",
        "normalize_vendor",
        "create_checkpoint",
        "get_checkpoint"
    ]


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


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
