"""LangGraph node functions for invoice processing workflow."""
from typing import Any
from langgraph.types import interrupt

from ..agents import AgentRegistry
from .state import InvoiceWorkflowState
from ..utils.logger import get_logger

logger = get_logger("nodes")


async def intake_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    INTAKE node - validates and persists invoice.
    
    Node functions receive state and return updates to merge.
    """
    logger.info("Executing INTAKE node")
    agent = AgentRegistry.get("INTAKE")
    return await agent.execute(state)


async def understand_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    UNDERSTAND node - OCR and parsing.
    
    Runs OCR on attachments and parses line items.
    """
    logger.info("Executing UNDERSTAND node")
    agent = AgentRegistry.get("UNDERSTAND")
    return await agent.execute(state)


async def prepare_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    PREPARE node - normalize and enrich.
    
    Normalizes vendor data and enriches with external info.
    """
    logger.info("Executing PREPARE node")
    agent = AgentRegistry.get("PREPARE")
    return await agent.execute(state)


async def retrieve_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    RETRIEVE node - fetch ERP data.
    
    Fetches POs, GRNs, and historical invoices from ERP.
    """
    logger.info("Executing RETRIEVE node")
    agent = AgentRegistry.get("RETRIEVE")
    return await agent.execute(state)


async def match_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    MATCH_TWO_WAY node - compute match score.
    
    Performs 2-way matching between invoice and PO.
    """
    logger.info("Executing MATCH_TWO_WAY node")
    agent = AgentRegistry.get("MATCH_TWO_WAY")
    return await agent.execute(state)


async def checkpoint_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    CHECKPOINT_HITL node - create checkpoint for human review.
    
    Creates checkpoint, persists state, and pauses workflow.
    """
    logger.info("Executing CHECKPOINT_HITL node")
    agent = AgentRegistry.get("CHECKPOINT_HITL")
    return await agent.execute(state)


async def hitl_decision_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    HITL_DECISION node - waits for human input.
    
    Uses LangGraph's interrupt() for clean pause/resume.
    This is a non-deterministic node.
    """
    logger.info("Executing HITL_DECISION node")
    
    # Check if we already have a decision (resuming after interrupt)
    if state.get("human_decision"):
        logger.info(f"Resuming with decision: {state.get('human_decision')}")
        agent = AgentRegistry.get("HITL_DECISION")
        return await agent.execute(state)
    
    # Interrupt and wait for human input
    # This will pause the workflow until resumed via API with Command(resume=...)
    logger.info("Interrupting for human review")
    human_input = interrupt({
        "type": "human_review",
        "hitl_checkpoint_id": state.get("hitl_checkpoint_id"),
        "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
        "reason": state.get("paused_reason"),
        "review_url": state.get("review_url"),
        "match_score": state.get("match_score"),
        "match_evidence": state.get("match_evidence"),
    })
    
    # After resume, process the decision
    # The human_input will contain the decision from Command(resume={...})
    return {
        "human_decision": human_input.get("decision"),
        "reviewer_id": human_input.get("reviewer_id"),
        "reviewer_notes": human_input.get("notes", ""),
        "current_stage": "HITL_DECISION",
        "status": "RUNNING" if human_input.get("decision") == "ACCEPT" else "REQUIRES_MANUAL_HANDLING",
        "audit_log": [{
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "stage": "HITL_DECISION",
            "action": f"decision_{human_input.get('decision', 'unknown').lower()}",
            "details": {
                "decision": human_input.get("decision"),
                "reviewer_id": human_input.get("reviewer_id"),
                "notes": human_input.get("notes", "")
            }
        }]
    }


async def reconcile_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    RECONCILE node - build accounting entries.
    
    Reconstructs accounting entries and builds ledger.
    """
    logger.info("Executing RECONCILE node")
    agent = AgentRegistry.get("RECONCILE")
    return await agent.execute(state)


async def approve_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    APPROVE node - apply approval policy.
    
    Auto-approves or escalates based on rules.
    """
    logger.info("Executing APPROVE node")
    agent = AgentRegistry.get("APPROVE")
    return await agent.execute(state)


async def posting_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    POSTING node - post to ERP and schedule payment.
    
    Posts entries to ERP and schedules payment.
    """
    logger.info("Executing POSTING node")
    agent = AgentRegistry.get("POSTING")
    return await agent.execute(state)


async def notify_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    NOTIFY node - send notifications.
    
    Notifies vendor and internal finance team.
    """
    logger.info("Executing NOTIFY node")
    agent = AgentRegistry.get("NOTIFY")
    return await agent.execute(state)


async def complete_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    COMPLETE node - finalize workflow.
    
    Produces final payload and marks workflow complete.
    """
    logger.info("Executing COMPLETE node")
    agent = AgentRegistry.get("COMPLETE")
    return await agent.execute(state)


async def manual_handoff_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    MANUAL_HANDOFF node - handles rejected invoices.
    
    Finalizes workflow with REQUIRES_MANUAL_HANDLING status.
    """
    logger.info("Executing MANUAL_HANDOFF node")
    
    return {
        "current_stage": "MANUAL_HANDOFF",
        "status": "REQUIRES_MANUAL_HANDLING",
        "final_payload": {
            "workflow_id": state.get("raw_id"),
            "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
            "status": "REQUIRES_MANUAL_HANDLING",
            "reason": "Invoice rejected during human review",
            "reviewer_id": state.get("reviewer_id"),
            "reviewer_notes": state.get("reviewer_notes"),
            "hitl_checkpoint_id": state.get("hitl_checkpoint_id"),
        },
        "audit_log": [{
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "stage": "MANUAL_HANDOFF",
            "action": "workflow_requires_manual_handling",
            "details": {
                "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
                "reason": "Rejected during human review"
            }
        }]
    }
