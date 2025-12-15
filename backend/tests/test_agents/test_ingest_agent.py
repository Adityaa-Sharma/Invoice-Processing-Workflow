"""Tests for IngestAgent (INTAKE stage)."""
import pytest
from src.agents.ingest_agent import IngestAgent


@pytest.mark.asyncio
async def test_ingest_agent_validates_payload(initial_state):
    """Test INTAKE stage validates invoice."""
    agent = IngestAgent()
    result = await agent.execute(initial_state)
    
    assert result["validated"] is True
    assert "raw_id" in result
    assert result["raw_id"].startswith("RAW-")
    assert "ingest_ts" in result
    assert result["current_stage"] == "INTAKE"


@pytest.mark.asyncio
async def test_ingest_agent_rejects_invalid():
    """Test INTAKE rejects invalid payload."""
    agent = IngestAgent()
    invalid_state = {
        "invoice_payload": {"invalid": "data"},
        "audit_log": [],
        "bigtool_selections": {},
        "error_log": [],
    }
    
    result = await agent.execute(invalid_state)
    
    assert result["validated"] is False
    assert result["status"] == "FAILED"


@pytest.mark.asyncio
async def test_ingest_agent_bigtool_selection(initial_state):
    """Test INTAKE stage selects storage tool."""
    agent = IngestAgent()
    result = await agent.execute(initial_state)
    
    assert "bigtool_selections" in result
    assert "INTAKE" in result["bigtool_selections"]
    assert result["bigtool_selections"]["INTAKE"]["capability"] == "storage"
    assert result["bigtool_selections"]["INTAKE"]["selected_tool"] == "local_fs"
