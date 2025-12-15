"""Validation utilities."""
from typing import Any


def validate_invoice_payload(invoice: dict[str, Any]) -> bool:
    """
    Validate invoice payload has required fields.
    
    Args:
        invoice: Invoice payload dict
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "invoice_id",
        "vendor_name",
        "invoice_date",
        "due_date",
        "amount",
        "currency",
        "line_items"
    ]
    
    for field in required_fields:
        if field not in invoice:
            return False
    
    # Validate line_items structure
    if not isinstance(invoice.get("line_items"), list):
        return False
    
    for item in invoice["line_items"]:
        if not all(k in item for k in ["desc", "qty", "unit_price", "total"]):
            return False
    
    # Validate amount is numeric
    if not isinstance(invoice.get("amount"), (int, float)):
        return False
    
    return True


def validate_line_item(item: dict[str, Any]) -> bool:
    """
    Validate a single line item.
    
    Args:
        item: Line item dict
        
    Returns:
        True if valid, False otherwise
    """
    required = ["desc", "qty", "unit_price", "total"]
    return all(k in item for k in required)
