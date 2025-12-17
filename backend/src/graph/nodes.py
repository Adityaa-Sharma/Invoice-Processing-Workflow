"""LangGraph node functions for invoice processing workflow."""
import asyncio
from typing import Any
from langgraph.types import interrupt
from contextvars import ContextVar

from ..agents import AgentRegistry
from .state import InvoiceWorkflowState
from ..utils.logger import get_logger
from ..services.event_emitter import (
    emit_stage_started,
    emit_stage_completed,
    emit_stage_failed,
    emit_workflow_complete,
    emit_log_message,
)

logger = get_logger("nodes")

# Small delay between stages to ensure SSE events stream properly
STAGE_EMIT_DELAY = 0.1  # 100ms delay for event propagation

# Context variable to store current thread_id for event emission
_current_thread_id: ContextVar[str] = ContextVar("thread_id", default="")


def set_thread_id(thread_id: str) -> None:
    """Set the current thread ID for event emission."""
    _current_thread_id.set(thread_id)


def get_thread_id() -> str:
    """Get the current thread ID."""
    return _current_thread_id.get()


def _get_thread_id_from_state(state: InvoiceWorkflowState) -> str:
    """
    Get thread_id from state, fallback to ContextVar.
    
    Prefers state-based thread_id as it's more reliable across async boundaries.
    """
    thread_id = state.get("thread_id", "")
    if not thread_id:
        thread_id = _current_thread_id.get()
    return thread_id or "unknown"


async def intake_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    INTAKE node - validates and persists invoice.
    
    Node functions receive state and return updates to merge.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("🚀 Executing INTAKE node")
    await emit_stage_started(thread_id, "INTAKE", {"invoice_id": state.get("invoice_payload", {}).get("invoice_id")})
    
    try:
        agent = AgentRegistry.get("INTAKE")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "INTAKE", {
            "raw_id": result.get("raw_id"),
            "validated": result.get("validated"),
            "bigtool": result.get("bigtool_selections", {}).get("INTAKE")
        })
        await emit_log_message(thread_id, "info", f"✅ INTAKE completed - Raw ID: {result.get('raw_id')}")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "INTAKE", str(e))
        raise


async def understand_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    UNDERSTAND node - OCR and parsing.
    
    Runs OCR on attachments and parses line items.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("🔍 Executing UNDERSTAND node")
    await emit_stage_started(thread_id, "UNDERSTAND", {"raw_id": state.get("raw_id")})
    
    try:
        agent = AgentRegistry.get("UNDERSTAND")
        result = await agent.execute(state)
        
        parsed = result.get("parsed_invoice", {})
        await emit_stage_completed(thread_id, "UNDERSTAND", {
            "line_items": len(parsed.get("parsed_line_items", [])),
            "pos_detected": len(parsed.get("detected_pos", [])),
            "bigtool": result.get("bigtool_selections", {}).get("UNDERSTAND")
        })
        await emit_log_message(thread_id, "info", f"✅ UNDERSTAND completed - {len(parsed.get('parsed_line_items', []))} line items parsed")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "UNDERSTAND", str(e))
        raise


async def prepare_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    PREPARE node - normalize and enrich.
    
    Normalizes vendor data and enriches with external info.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("📋 Executing PREPARE node")
    await emit_stage_started(thread_id, "PREPARE", {})
    
    try:
        agent = AgentRegistry.get("PREPARE")
        result = await agent.execute(state)
        
        vendor = result.get("vendor_profile", {})
        await emit_stage_completed(thread_id, "PREPARE", {
            "vendor": vendor.get("normalized_name"),
            "risk_score": vendor.get("risk_score"),
            "bigtool": result.get("bigtool_selections", {}).get("PREPARE")
        })
        await emit_log_message(thread_id, "info", f"✅ PREPARE completed - Vendor: {vendor.get('normalized_name')}")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "PREPARE", str(e))
        raise


async def retrieve_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    RETRIEVE node - fetch ERP data.
    
    Fetches POs, GRNs, and historical invoices from ERP.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("📦 Executing RETRIEVE node")
    await emit_stage_started(thread_id, "RETRIEVE", {})
    
    try:
        agent = AgentRegistry.get("RETRIEVE")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "RETRIEVE", {
            "pos_found": len(result.get("matched_pos", [])),
            "grns_found": len(result.get("matched_grns", [])),
            "bigtool": result.get("bigtool_selections", {}).get("RETRIEVE")
        })
        await emit_log_message(thread_id, "info", f"✅ RETRIEVE completed - {len(result.get('matched_pos', []))} POs found")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "RETRIEVE", str(e))
        raise


async def match_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    MATCH_TWO_WAY node - compute match score.
    
    Performs 2-way matching between invoice and PO.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("🎯 Executing MATCH_TWO_WAY node")
    await emit_stage_started(thread_id, "MATCH_TWO_WAY", {})
    
    try:
        agent = AgentRegistry.get("MATCH_TWO_WAY")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "MATCH_TWO_WAY", {
            "match_score": result.get("match_score"),
            "match_result": result.get("match_result"),
            "matched_fields": result.get("match_evidence", {}).get("matched_fields", [])
        })
        await emit_log_message(thread_id, "info", f"✅ MATCH completed - Score: {result.get('match_score'):.2f} ({result.get('match_result')})")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "MATCH_TWO_WAY", str(e))
        raise


async def checkpoint_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    CHECKPOINT_HITL node - create checkpoint for human review.
    
    Creates checkpoint, persists state, and pauses workflow.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("⏸️ Executing CHECKPOINT_HITL node")
    await emit_stage_started(thread_id, "CHECKPOINT_HITL", {})
    
    try:
        agent = AgentRegistry.get("CHECKPOINT_HITL")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "CHECKPOINT_HITL", {
            "checkpoint_id": result.get("hitl_checkpoint_id"),
            "paused": True
        })
        await emit_log_message(thread_id, "warning", f"⏸️ Workflow paused for human review - Checkpoint: {result.get('hitl_checkpoint_id')}")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "CHECKPOINT_HITL", str(e))
        raise


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
    thread_id = _get_thread_id_from_state(state)
    logger.info("📊 Executing RECONCILE node")
    await emit_stage_started(thread_id, "RECONCILE", {})
    
    try:
        agent = AgentRegistry.get("RECONCILE")
        result = await agent.execute(state)
        
        entries = result.get("accounting_entries", [])
        await emit_stage_completed(thread_id, "RECONCILE", {
            "entries_count": len(entries),
            "total_debit": sum(e.get("amount", 0) for e in entries if e.get("type") == "DEBIT"),
            "total_credit": sum(e.get("amount", 0) for e in entries if e.get("type") == "CREDIT")
        })
        await emit_log_message(thread_id, "info", f"✅ RECONCILE completed - {len(entries)} entries created")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "RECONCILE", str(e))
        raise


async def approve_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    APPROVE node - apply approval policy.
    
    Auto-approves or escalates based on rules.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("✅ Executing APPROVE node")
    await emit_stage_started(thread_id, "APPROVE", {})
    
    try:
        agent = AgentRegistry.get("APPROVE")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "APPROVE", {
            "approval_status": result.get("approval_status"),
            "approver_id": result.get("approver_id")
        })
        await emit_log_message(thread_id, "info", f"✅ APPROVE completed - {result.get('approval_status')} by {result.get('approver_id')}")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "APPROVE", str(e))
        raise


async def posting_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    POSTING node - post to ERP and schedule payment.
    
    Posts entries to ERP and schedules payment.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("📤 Executing POSTING node")
    await emit_stage_started(thread_id, "POSTING", {})
    
    try:
        agent = AgentRegistry.get("POSTING")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "POSTING", {
            "erp_txn_id": result.get("erp_txn_id"),
            "scheduled_payment_id": result.get("scheduled_payment_id"),
            "bigtool": result.get("bigtool_selections", {}).get("POSTING")
        })
        await emit_log_message(thread_id, "info", f"✅ POSTING completed - ERP TXN: {result.get('erp_txn_id')}")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "POSTING", str(e))
        raise


async def notify_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    NOTIFY node - send notifications.
    
    Notifies vendor and internal finance team.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("📧 Executing NOTIFY node")
    await emit_stage_started(thread_id, "NOTIFY", {})
    
    try:
        agent = AgentRegistry.get("NOTIFY")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "NOTIFY", {
            "parties_notified": len(result.get("notified_parties", [])),
            "bigtool": result.get("bigtool_selections", {}).get("NOTIFY")
        })
        await emit_log_message(thread_id, "info", f"✅ NOTIFY completed - {len(result.get('notified_parties', []))} parties notified")
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "NOTIFY", str(e))
        raise


async def complete_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    COMPLETE node - finalize workflow.
    
    Produces final payload and marks workflow complete.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("🎉 Executing COMPLETE node")
    await emit_stage_started(thread_id, "COMPLETE", {})
    
    try:
        agent = AgentRegistry.get("COMPLETE")
        result = await agent.execute(state)
        
        await emit_stage_completed(thread_id, "COMPLETE", {
            "status": result.get("status"),
            "bigtool": result.get("bigtool_selections", {}).get("COMPLETE")
        })
        await emit_log_message(thread_id, "info", "🎉 Workflow COMPLETED successfully!")
        
        # Emit workflow complete event
        await emit_workflow_complete(thread_id, "COMPLETED", {
            "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
            "erp_txn_id": state.get("erp_txn_id"),
            "final_payload": result.get("final_payload")
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "COMPLETE", str(e))
        raise


async def manual_handoff_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    MANUAL_HANDOFF node - handles rejected invoices.
    
    Finalizes workflow with REQUIRES_MANUAL_HANDLING status.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("⚠️ Executing MANUAL_HANDOFF node")
    await emit_stage_started(thread_id, "MANUAL_HANDOFF", {})
    
    result = {
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
    
    await emit_stage_completed(thread_id, "MANUAL_HANDOFF", {"status": "REQUIRES_MANUAL_HANDLING"})
    await emit_log_message(thread_id, "warning", "⚠️ Workflow ended - Manual handling required")
    await emit_workflow_complete(thread_id, "REQUIRES_MANUAL_HANDLING", result.get("final_payload"))
    
    return result

