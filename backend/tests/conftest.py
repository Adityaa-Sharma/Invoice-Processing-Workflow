"""Pytest configuration and fixtures."""
import pytest
import asyncio
from typing import AsyncGenerator

from src.graph.state import InvoiceWorkflowState, create_initial_state
from src.graph.workflow import create_invoice_workflow
from src.tools.bigtool_picker import BigtoolPicker
from src.tools.mcp_router import MCPRouter
from src.db.checkpoint_store import get_memory_checkpointer


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_invoice() -> dict:
    """Sample invoice payload for testing."""
    return {
        "invoice_id": "INV-TEST-001",
        "vendor_name": "Test Vendor Inc.",
        "vendor_tax_id": "TAX-123456",
        "invoice_date": "2024-01-15",
        "due_date": "2024-02-15",
        "amount": 15000.00,
        "currency": "USD",
        "line_items": [
            {"desc": "Software License", "qty": 5, "unit_price": 1000.0, "total": 5000.0},
            {"desc": "Support Package", "qty": 1, "unit_price": 10000.0, "total": 10000.0}
        ],
        "attachments": ["invoice.pdf"]
    }


@pytest.fixture
def sample_invoice_low_amount() -> dict:
    """Sample invoice with low amount (auto-approve)."""
    return {
        "invoice_id": "INV-TEST-002",
        "vendor_name": "Small Vendor LLC",
        "vendor_tax_id": "TAX-654321",
        "invoice_date": "2024-01-15",
        "due_date": "2024-02-15",
        "amount": 500.00,
        "currency": "USD",
        "line_items": [
            {"desc": "Office Supplies", "qty": 10, "unit_price": 50.0, "total": 500.0}
        ],
        "attachments": []
    }


@pytest.fixture
def initial_state(sample_invoice) -> InvoiceWorkflowState:
    """Initial workflow state for testing."""
    return create_initial_state(sample_invoice)


@pytest.fixture
def workflow():
    """Workflow with in-memory checkpointer for testing."""
    checkpointer = get_memory_checkpointer()
    return create_invoice_workflow(checkpointer=checkpointer)


@pytest.fixture
def bigtool() -> BigtoolPicker:
    """BigtoolPicker instance for testing."""
    return BigtoolPicker()


@pytest.fixture
def mcp_router() -> MCPRouter:
    """MCPRouter instance for testing."""
    return MCPRouter()
