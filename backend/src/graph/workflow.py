"""LangGraph workflow definition for invoice processing."""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from .state import InvoiceWorkflowState
from .nodes import (
    intake_node,
    understand_node,
    prepare_node,
    retrieve_node,
    match_node,
    checkpoint_node,
    hitl_decision_node,
    reconcile_node,
    approve_node,
    posting_node,
    notify_node,
    complete_node,
    manual_handoff_node,
)
from .edges import should_checkpoint, after_hitl_decision
from ..utils.logger import get_logger

logger = get_logger("workflow")


def create_invoice_workflow(
    checkpointer: BaseCheckpointSaver = None
) -> StateGraph:
    """
    Create the invoice processing workflow graph.
    
    This creates a LangGraph StateGraph with all 12 stages of invoice
    processing, including HITL checkpoint/resume capability.
    
    Graph Structure:
    ---------------
    START → INTAKE → UNDERSTAND → PREPARE → RETRIEVE → MATCH_TWO_WAY
                                                              │
                                           ┌──────────────────┴────────────────────┐
                                           │                                       │
                                      (match failed)                          (match passed)
                                           │                                       │
                                           ▼                                       │
                                   CHECKPOINT_HITL                                 │
                                           │                                       │
                                           ▼                                       │
                                    HITL_DECISION                                  │
                                           │                                       │
                               ┌───────────┴───────────┐                           │
                               │                       │                           │
                          (ACCEPT)                 (REJECT)                        │
                               │                       │                           │
                               ▼                       ▼                           │
                          RECONCILE             MANUAL_HANDOFF → END               │
                               │                                                   │
                               ◄───────────────────────────────────────────────────┘
                               │
                               ▼
                            APPROVE → POSTING → NOTIFY → COMPLETE → END
    
    Args:
        checkpointer: LangGraph checkpoint saver for state persistence
        
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating invoice processing workflow graph")
    
    # Initialize graph with typed state
    workflow = StateGraph(InvoiceWorkflowState)
    
    # ===== Add all nodes =====
    workflow.add_node("INTAKE", intake_node)
    workflow.add_node("UNDERSTAND", understand_node)
    workflow.add_node("PREPARE", prepare_node)
    workflow.add_node("RETRIEVE", retrieve_node)
    workflow.add_node("MATCH_TWO_WAY", match_node)
    workflow.add_node("CHECKPOINT_HITL", checkpoint_node)
    workflow.add_node("HITL_DECISION", hitl_decision_node)
    workflow.add_node("RECONCILE", reconcile_node)
    workflow.add_node("APPROVE", approve_node)
    workflow.add_node("POSTING", posting_node)
    workflow.add_node("NOTIFY", notify_node)
    workflow.add_node("COMPLETE", complete_node)
    workflow.add_node("MANUAL_HANDOFF", manual_handoff_node)
    
    # ===== Define edges =====
    
    # Linear flow: START → INTAKE → UNDERSTAND → PREPARE → RETRIEVE → MATCH
    workflow.add_edge(START, "INTAKE")
    workflow.add_edge("INTAKE", "UNDERSTAND")
    workflow.add_edge("UNDERSTAND", "PREPARE")
    workflow.add_edge("PREPARE", "RETRIEVE")
    workflow.add_edge("RETRIEVE", "MATCH_TWO_WAY")
    
    # Conditional edge after MATCH: route based on match result
    workflow.add_conditional_edges(
        "MATCH_TWO_WAY",
        should_checkpoint,
        {
            "checkpoint": "CHECKPOINT_HITL",  # Match failed → HITL
            "continue": "RECONCILE",          # Match passed → continue
        }
    )
    
    # HITL flow: CHECKPOINT → HITL_DECISION
    workflow.add_edge("CHECKPOINT_HITL", "HITL_DECISION")
    
    # Conditional edge after HITL_DECISION: route based on human decision
    workflow.add_conditional_edges(
        "HITL_DECISION",
        after_hitl_decision,
        {
            "accept": "RECONCILE",       # Accepted → continue processing
            "reject": "MANUAL_HANDOFF",  # Rejected → manual handling
        }
    )
    
    # Manual handoff ends the workflow
    workflow.add_edge("MANUAL_HANDOFF", END)
    
    # Continue to completion: RECONCILE → APPROVE → POSTING → NOTIFY → COMPLETE
    workflow.add_edge("RECONCILE", "APPROVE")
    workflow.add_edge("APPROVE", "POSTING")
    workflow.add_edge("POSTING", "NOTIFY")
    workflow.add_edge("NOTIFY", "COMPLETE")
    workflow.add_edge("COMPLETE", END)
    
    logger.info("Workflow graph created successfully")
    
    # Compile with checkpointer for state persistence
    return workflow.compile(checkpointer=checkpointer)


def get_workflow_stages() -> list[dict]:
    """
    Get list of all workflow stages with metadata.
    
    Returns:
        List of stage info dicts
    """
    return [
        {"id": "INTAKE", "name": "Accept Invoice", "mode": "deterministic"},
        {"id": "UNDERSTAND", "name": "OCR & Parse", "mode": "deterministic"},
        {"id": "PREPARE", "name": "Normalize & Enrich", "mode": "deterministic"},
        {"id": "RETRIEVE", "name": "Fetch ERP Data", "mode": "deterministic"},
        {"id": "MATCH_TWO_WAY", "name": "Two-Way Match", "mode": "deterministic"},
        {"id": "CHECKPOINT_HITL", "name": "Checkpoint", "mode": "deterministic"},
        {"id": "HITL_DECISION", "name": "Human Decision", "mode": "non-deterministic"},
        {"id": "RECONCILE", "name": "Build Entries", "mode": "deterministic"},
        {"id": "APPROVE", "name": "Approval", "mode": "deterministic"},
        {"id": "POSTING", "name": "Post to ERP", "mode": "deterministic"},
        {"id": "NOTIFY", "name": "Notifications", "mode": "deterministic"},
        {"id": "COMPLETE", "name": "Complete", "mode": "deterministic"},
    ]
