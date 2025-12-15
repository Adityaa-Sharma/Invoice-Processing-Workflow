"""Test MCP servers."""
import asyncio
import sys
sys.path.insert(0, ".")

from src.mcp.client import MCPClient


async def main():
    """Test MCP client."""
    print("=" * 60)
    print("Testing MCP Client")
    print("=" * 60)
    
    client = MCPClient()
    
    # Health check
    print("\n[1] Health Check...")
    health = await client.health_check()
    print(f"  COMMON: {'✓' if health['servers']['common'] else '✗'}")
    print(f"  ATLAS:  {'✓' if health['servers']['atlas'] else '✗'}")
    
    if not health['all_healthy']:
        print("\n⚠ Not all servers are healthy. Make sure to start:")
        print("  1. python run_common.py  (port 8001)")
        print("  2. python run_atlas.py   (port 8002)")
        return
    
    # Test COMMON tools
    print("\n[2] Testing COMMON Tools...")
    
    # Validate schema
    result = await client.call_tool("validate_invoice_schema", {
        "payload": {
            "invoice_id": "INV-001",
            "vendor_name": "Test Vendor",
            "amount": 1000.00,
            "currency": "USD"
        }
    })
    print(f"  validate_invoice_schema: {'✓' if result['success'] else '✗'}")
    if result['success']:
        print(f"    Valid: {result['result']['result']['valid']}")
    
    # Parse line items
    result = await client.call_tool("parse_line_items", {
        "line_items": [
            {"description": "Software License", "quantity": 1, "unit_price": 500},
            {"description": "Hardware Equipment", "quantity": 2, "unit_price": 250}
        ]
    })
    print(f"  parse_line_items: {'✓' if result['success'] else '✗'}")
    if result['success']:
        print(f"    Total items: {result['result']['result']['total_items']}")
    
    # Test ATLAS tools
    print("\n[3] Testing ATLAS Tools...")
    
    # Extract OCR
    result = await client.call_tool("extract_ocr", {
        "file_path": "/path/to/invoice.pdf",
        "file_type": "pdf"
    })
    print(f"  extract_ocr: {'✓' if result['success'] else '✗'}")
    if result['success']:
        data = result['result']['result']
        print(f"    Invoice: {data['extracted_data']['invoice_number']}")
        print(f"    Confidence: {data['confidence']}")
    
    # Enrich vendor
    result = await client.call_tool("enrich_vendor", {
        "vendor_name": "Acme Corporation"
    })
    print(f"  enrich_vendor: {'✓' if result['success'] else '✗'}")
    if result['success']:
        data = result['result']['result']
        print(f"    Industry: {data['enriched_data']['industry']}")
    
    # Post to ERP
    result = await client.call_tool("post_to_erp", {
        "invoice_id": "INV-001",
        "invoice_data": {"amount": 1000}
    })
    print(f"  post_to_erp: {'✓' if result['success'] else '✗'}")
    if result['success']:
        data = result['result']['result']
        print(f"    ERP Doc ID: {data['erp_document_id']}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
