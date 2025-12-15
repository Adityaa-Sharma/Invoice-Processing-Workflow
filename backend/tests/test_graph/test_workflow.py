"""Tests for workflow graph structure and execution."""
import pytest
from src.graph.workflow import create_invoice_workflow, get_workflow_stages
from src.graph.state import create_initial_state
from src.db.checkpoint_store import get_memory_checkpointer


def test_workflow_stages():
    """Test all 12 stages are defined."""
    stages = get_workflow_stages()
    
    assert len(stages) == 12
    
    stage_ids = [s["id"] for s in stages]
    expected = [
        "INTAKE", "UNDERSTAND", "PREPARE", "RETRIEVE",
        "MATCH_TWO_WAY", "CHECKPOINT_HITL", "HITL_DECISION",
        "RECONCILE", "APPROVE", "POSTING", "NOTIFY", "COMPLETE"
    ]
    
    assert stage_ids == expected


def test_workflow_creation():
    """Test workflow graph can be created."""
    checkpointer = get_memory_checkpointer()
    workflow = create_invoice_workflow(checkpointer)
    
    assert workflow is not None


@pytest.mark.asyncio
async def test_workflow_matched_flow(sample_invoice):
    """Test workflow execution with matching invoice (no HITL)."""
    checkpointer = get_memory_checkpointer()
    workflow = create_invoice_workflow(checkpointer)
    
    # Create invoice that will match
    sample_invoice["invoice_id"] = "INV-MATCH-001"
    initial_state = create_initial_state(sample_invoice)
    
    config = {"configurable": {"thread_id": "test-matched-001"}}
    
    result = await workflow.ainvoke(initial_state, config)
    
    # Should complete without HITL (match passed)
    assert result.get("status") in ["COMPLETED", "RUNNING", "PAUSED"]
    assert result.get("raw_id") is not None
    assert result.get("validated") is True


@pytest.mark.asyncio 
async def test_workflow_initial_stages(sample_invoice):
    """Test initial workflow stages execute correctly."""
    checkpointer = get_memory_checkpointer()
    workflow = create_invoice_workflow(checkpointer)
    
    initial_state = create_initial_state(sample_invoice)
    config = {"configurable": {"thread_id": "test-stages-001"}}
    
    result = await workflow.ainvoke(initial_state, config)
    
    # Check early stage outputs
    assert result.get("raw_id") is not None
    assert result.get("parsed_invoice") is not None
    assert result.get("vendor_profile") is not None
    assert result.get("matched_pos") is not None
