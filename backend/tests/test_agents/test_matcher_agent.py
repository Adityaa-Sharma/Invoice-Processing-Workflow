"""Tests for MatcherAgent (MATCH_TWO_WAY stage)."""
import pytest
from src.agents.matcher_agent import MatcherAgent


@pytest.mark.asyncio
async def test_matcher_agent_matched():
    """Test MATCH_TWO_WAY with matching invoice and PO."""
    agent = MatcherAgent()
    
    state = {
        "invoice_payload": {
            "invoice_id": "INV-001",
            "vendor_name": "Test Vendor",
            "amount": 10000.0,
            "currency": "USD",
            "line_items": [
                {"desc": "Item 1", "qty": 1, "unit_price": 10000.0, "total": 10000.0}
            ]
        },
        "matched_pos": [{
            "po_number": "PO-001",
            "vendor_name": "Test Vendor",
            "total_amount": 10000.0,
            "currency": "USD",
            "line_items": [
                {"desc": "Item 1", "qty": 1, "unit_price": 10000.0, "total": 10000.0}
            ]
        }],
        "matched_grns": [],
        "audit_log": [],
        "bigtool_selections": {},
        "error_log": [],
    }
    
    result = await agent.execute(state)
    
    assert result["match_result"] == "MATCHED"
    assert result["match_score"] >= 0.9


@pytest.mark.asyncio
async def test_matcher_agent_failed():
    """Test MATCH_TWO_WAY with mismatched amounts."""
    agent = MatcherAgent()
    
    state = {
        "invoice_payload": {
            "invoice_id": "INV-001",
            "vendor_name": "Test Vendor",
            "amount": 15000.0,  # Different amount
            "currency": "USD",
            "line_items": [{"desc": "Item", "qty": 1, "unit_price": 15000.0, "total": 15000.0}]
        },
        "matched_pos": [{
            "po_number": "PO-001",
            "vendor_name": "Test Vendor",
            "total_amount": 10000.0,  # Different amount
            "currency": "USD",
            "line_items": [{"desc": "Item", "qty": 1, "unit_price": 10000.0, "total": 10000.0}]
        }],
        "matched_grns": [],
        "audit_log": [],
        "bigtool_selections": {},
        "error_log": [],
    }
    
    result = await agent.execute(state)
    
    assert result["match_result"] == "FAILED"
    assert result["match_score"] < 0.9


@pytest.mark.asyncio
async def test_matcher_agent_no_po():
    """Test MATCH_TWO_WAY with no matching PO."""
    agent = MatcherAgent()
    
    state = {
        "invoice_payload": {
            "invoice_id": "INV-001",
            "vendor_name": "Test Vendor",
            "amount": 10000.0,
            "currency": "USD",
            "line_items": []
        },
        "matched_pos": [],
        "matched_grns": [],
        "audit_log": [],
        "bigtool_selections": {},
        "error_log": [],
    }
    
    result = await agent.execute(state)
    
    assert result["match_result"] == "FAILED"
    assert result["match_score"] == 0.0
