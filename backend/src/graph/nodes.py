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
    emit_tool_call,
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
    INTAKE 📥 node - accepts and validates invoice payload.
    
    Server: COMMON
    Operations: accept_invoice_payload, validate_schema, persist_raw
    """
    thread_id = _get_thread_id_from_state(state)
    invoice_id = state.get("invoice_payload", {}).get("invoice_id", "unknown")
    vendor = state.get("invoice_payload", {}).get("vendor_name", "unknown")
    
    logger.info(f"📥 INTAKE: Processing invoice {invoice_id} from {vendor}")
    await emit_stage_started(thread_id, "INTAKE", {"invoice_id": invoice_id, "vendor": vendor})
    
    try:
        agent = AgentRegistry.get("INTAKE")
        
        # Emit tool call started (BigtoolPicker selection)
        await emit_tool_call(thread_id, "INTAKE", "validate_schema", "COMMON", status="started")
        
        result = await agent.execute(state)
        
        bigtool = result.get("bigtool_selections", {}).get("INTAKE", {})
        tool_name = bigtool.get('tool_name', 'validate_schema')
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "INTAKE", tool_name, "COMMON",
            params={"invoice_id": invoice_id},
            result={"validated": result.get('validated'), "raw_id": result.get('raw_id')},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"📋 Schema validated: {result.get('validated', False)}", stage="INTAKE", log_type="result")
        await emit_log_message(thread_id, "info", f"💾 Persisted with Raw ID: {result.get('raw_id')}", stage="INTAKE", log_type="result")
        
        await emit_stage_completed(thread_id, "INTAKE", {
            "raw_id": result.get("raw_id"),
            "validated": result.get("validated"),
            "bigtool": bigtool
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "INTAKE", str(e))
        await emit_log_message(thread_id, "error", f"❌ INTAKE failed: {str(e)}", stage="INTAKE", log_type="error")
        raise


async def understand_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    UNDERSTAND 🧠 node - OCR extraction and line item parsing.
    
    Servers: ATLAS (OCR), COMMON (parsing)
    Operations: ocr_extract, parse_line_items
    BigtoolPicker: Selects OCR provider (Google Vision / Tesseract / AWS Textract)
    """
    thread_id = _get_thread_id_from_state(state)
    raw_id = state.get("raw_id", "unknown")
    
    logger.info(f"🧠 UNDERSTAND: Running OCR on invoice {raw_id}")
    await emit_stage_started(thread_id, "UNDERSTAND", {"raw_id": raw_id})
    
    try:
        agent = AgentRegistry.get("UNDERSTAND")
        
        # Emit tool call started (BigtoolPicker selects OCR provider)
        await emit_tool_call(thread_id, "UNDERSTAND", "extract_ocr", "ATLAS", status="started")
        
        result = await agent.execute(state)
        
        bigtool = result.get("bigtool_selections", {}).get("UNDERSTAND", {})
        tool_name = bigtool.get('tool_name', 'extract_ocr')
        
        parsed = result.get("parsed_invoice", {})
        line_items = parsed.get("parsed_line_items", [])
        detected_pos = parsed.get("detected_pos", [])
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "UNDERSTAND", tool_name, "ATLAS",
            params={"raw_id": raw_id},
            result={"line_items_count": len(line_items), "pos_count": len(detected_pos)},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"📝 Parsed {len(line_items)} line items", stage="UNDERSTAND", log_type="result")
        await emit_log_message(thread_id, "info", f"🔗 Detected {len(detected_pos)} PO references: {detected_pos[:3]}..." if len(detected_pos) > 3 else f"🔗 Detected PO refs: {detected_pos}", stage="UNDERSTAND", log_type="result")
        
        await emit_stage_completed(thread_id, "UNDERSTAND", {
            "line_items": len(line_items),
            "pos_detected": len(detected_pos),
            "bigtool": bigtool
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "UNDERSTAND", str(e))
        await emit_log_message(thread_id, "error", f"❌ UNDERSTAND failed: {str(e)}", stage="UNDERSTAND", log_type="error")
        raise


async def prepare_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    PREPARE 🛠️ node - normalize vendor and compute flags.
    
    Servers: COMMON (normalize, flags), ATLAS (enrichment)
    Operations: normalize_vendor, enrich_vendor, compute_flags
    BigtoolPicker: Selects enrichment tool (Clearbit / PDL / Vendor DB)
    """
    thread_id = _get_thread_id_from_state(state)
    
    logger.info("🛠️ PREPARE: Normalizing and enriching vendor data")
    await emit_stage_started(thread_id, "PREPARE", {})
    
    try:
        agent = AgentRegistry.get("PREPARE")
        
        # Emit tool call started (BigtoolPicker selects enrichment provider)
        await emit_tool_call(thread_id, "PREPARE", "enrich_vendor", "ATLAS", status="started")
        
        result = await agent.execute(state)
        
        bigtool = result.get("bigtool_selections", {}).get("PREPARE", {})
        tool_name = bigtool.get('tool_name', 'enrich_vendor')
        
        vendor = result.get("vendor_profile", {})
        flags = result.get("flags", {})
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "PREPARE", tool_name, "ATLAS",
            params={"vendor_name": vendor.get("original_name")},
            result={"normalized_name": vendor.get("normalized_name"), "risk_score": vendor.get("risk_score")},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"👤 Normalized vendor: {vendor.get('normalized_name')}", stage="PREPARE", log_type="result")
        await emit_log_message(thread_id, "info", f"🏷️ Tax ID: {vendor.get('tax_id', 'N/A')}", stage="PREPARE", log_type="result")
        await emit_log_message(thread_id, "info", f"📊 Risk score: {vendor.get('risk_score', 0):.2f}", stage="PREPARE", log_type="result")
        if flags:
            await emit_log_message(thread_id, "info", f"🚩 Flags computed: {list(flags.keys())}", stage="PREPARE", log_type="result")
        
        await emit_stage_completed(thread_id, "PREPARE", {
            "vendor": vendor.get("normalized_name"),
            "risk_score": vendor.get("risk_score"),
            "bigtool": bigtool
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "PREPARE", str(e))
        await emit_log_message(thread_id, "error", f"❌ PREPARE failed: {str(e)}", stage="PREPARE", log_type="error")
        raise


async def retrieve_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    RETRIEVE 📚 node - fetch PO, GRN, and history from ERP.
    
    Server: ATLAS (ERP connector)
    Operations: fetch_po, fetch_grn, fetch_history
    BigtoolPicker: Selects ERP connector tool
    """
    thread_id = _get_thread_id_from_state(state)
    detected_pos = state.get("parsed_invoice", {}).get("detected_pos", [])
    
    logger.info(f"📚 RETRIEVE: Fetching ERP data for {len(detected_pos)} PO refs")
    await emit_stage_started(thread_id, "RETRIEVE", {"po_count": len(detected_pos)})
    
    try:
        agent = AgentRegistry.get("RETRIEVE")
        
        # Emit tool call started (BigtoolPicker selects ERP connector)
        await emit_tool_call(thread_id, "RETRIEVE", "fetch_erp", "ATLAS", status="started")
        
        result = await agent.execute(state)
        
        bigtool = result.get("bigtool_selections", {}).get("RETRIEVE", {})
        tool_name = bigtool.get('tool_name', 'fetch_erp')
        
        pos = result.get("matched_pos", [])
        grns = result.get("matched_grns", [])
        history = result.get("history", [])
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "RETRIEVE", tool_name, "ATLAS",
            params={"po_refs": detected_pos},
            result={"pos_found": len(pos), "grns_found": len(grns), "history_count": len(history)},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"📝 Fetched {len(pos)} Purchase Orders, {len(grns)} GRNs, {len(history)} historical invoices", stage="RETRIEVE", log_type="result")
        
        await emit_stage_completed(thread_id, "RETRIEVE", {
            "pos_found": len(pos),
            "grns_found": len(grns),
            "history_found": len(history),
            "bigtool": bigtool
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "RETRIEVE", str(e))
        await emit_log_message(thread_id, "error", f"❌ RETRIEVE failed: {str(e)}", stage="RETRIEVE", log_type="error")
        raise


async def match_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    MATCH_TWO_WAY ⚖️ node - 2-way matching Invoice vs PO.
    
    Server: COMMON
    Operations: compute_match_score
    If match_score < threshold → routes to CHECKPOINT_HITL
    """
    thread_id = _get_thread_id_from_state(state)
    invoice_amount = state.get("invoice_payload", {}).get("amount", 0)
    
    logger.info("⚖️ MATCH_TWO_WAY: Computing invoice-PO match score")
    await emit_stage_started(thread_id, "MATCH_TWO_WAY", {"invoice_amount": invoice_amount})
    
    try:
        agent = AgentRegistry.get("MATCH_TWO_WAY")
        
        # Emit tool call started
        await emit_tool_call(thread_id, "MATCH_TWO_WAY", "compute_match", "COMMON", status="started")
        
        result = await agent.execute(state)
        
        match_score = result.get("match_score", 0)
        match_result = result.get("match_result", "UNKNOWN")
        evidence = result.get("match_evidence", {})
        matched_fields = evidence.get("matched_fields", [])
        mismatched_fields = evidence.get("mismatched_fields", [])
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "MATCH_TWO_WAY", "compute_match", "COMMON",
            params={"invoice_amount": invoice_amount},
            result={"match_score": match_score, "match_result": match_result},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"📊 Match score: {match_score:.2%} | Matched: {matched_fields}", stage="MATCH_TWO_WAY", log_type="result")
        if mismatched_fields:
            await emit_log_message(thread_id, "warning", f"⚠️ Mismatched fields: {mismatched_fields}", stage="MATCH_TWO_WAY", log_type="warning")
        
        if match_result == "MATCHED":
            await emit_log_message(thread_id, "info", f"✅ Match PASSED - Proceeding to reconciliation", stage="MATCH_TWO_WAY", log_type="decision")
        else:
            await emit_log_message(thread_id, "warning", f"⚠️ Match FAILED ({match_score:.2%}) - Will require human review", stage="MATCH_TWO_WAY", log_type="decision")
        
        await emit_stage_completed(thread_id, "MATCH_TWO_WAY", {
            "match_score": match_score,
            "match_result": match_result,
            "matched_fields": matched_fields
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "MATCH_TWO_WAY", str(e))
        await emit_log_message(thread_id, "error", f"❌ MATCH failed: {str(e)}", stage="MATCH_TWO_WAY", log_type="error")
        raise


async def checkpoint_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    CHECKPOINT_HITL ⏸️ node - save state for human review.
    
    Server: COMMON
    Operations: save_state_for_human_review, create_checkpoint
    BigtoolPicker: Selects DB tool (Postgres / SQLite / Dynamo)
    Creates LangGraph checkpoint and adds to Human Review queue.
    """
    thread_id = _get_thread_id_from_state(state)
    match_score = state.get("match_score", 0)
    
    logger.info("⏸️ CHECKPOINT_HITL: Creating human review checkpoint")
    await emit_stage_started(thread_id, "CHECKPOINT_HITL", {"match_score": match_score})
    
    try:
        agent = AgentRegistry.get("CHECKPOINT_HITL")
        
        # Emit tool call started (BigtoolPicker selects DB tool)
        await emit_tool_call(thread_id, "CHECKPOINT_HITL", "create_checkpoint", "COMMON", status="started")
        
        result = await agent.execute(state)
        
        bigtool = result.get("bigtool_selections", {}).get("CHECKPOINT_HITL", {})
        checkpoint_id = result.get("hitl_checkpoint_id")
        review_url = result.get("review_url")
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "CHECKPOINT_HITL", "create_checkpoint", "COMMON",
            params={"match_score": match_score},
            result={"checkpoint_id": checkpoint_id},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"💾 Checkpoint created: {checkpoint_id} | Review URL: {review_url}", stage="CHECKPOINT_HITL", log_type="result")
        await emit_log_message(thread_id, "warning", "⏸️ Workflow PAUSED - Awaiting human decision", stage="CHECKPOINT_HITL", log_type="hitl")
        
        await emit_stage_completed(thread_id, "CHECKPOINT_HITL", {
            "checkpoint_id": checkpoint_id,
            "paused": True,
            "bigtool": bigtool
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "CHECKPOINT_HITL", str(e))
        await emit_log_message(thread_id, "error", f"❌ CHECKPOINT failed: {str(e)}", stage="CHECKPOINT_HITL", log_type="error")
        raise


async def hitl_decision_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    HITL_DECISION node - waits for human input.
    
    Uses LangGraph's interrupt() for clean pause/resume.
    This is a non-deterministic node.
    """
    thread_id = _get_thread_id_from_state(state)
    logger.info("👨‍💼 HITL_DECISION: Processing human decision")
    
    # Check if we already have a decision (resuming after interrupt)
    if state.get("human_decision"):
        logger.info(f"Resuming with decision: {state.get('human_decision')}")
        agent = AgentRegistry.get("HITL_DECISION")
        return await agent.execute(state)
    
    # Interrupt and wait for human input
    # This will pause the workflow until resumed via API with Command(resume=...)
    logger.info("⏸️ Interrupting for human review")
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
    decision = human_input.get("decision", "unknown")
    
    # Emit events now that workflow has resumed
    await emit_stage_started(thread_id, "HITL_DECISION", {"decision": decision})
    await emit_log_message(thread_id, "info", f"👨‍💼 Decision: {decision} by {human_input.get('reviewer_id', 'unknown')}" + (f" | Notes: {human_input.get('notes')}" if human_input.get("notes") else ""))
    
    result = {
        "human_decision": decision,
        "reviewer_id": human_input.get("reviewer_id"),
        "reviewer_notes": human_input.get("notes", ""),
        "current_stage": "HITL_DECISION",
        "status": "RUNNING" if decision == "ACCEPT" else "REQUIRES_MANUAL_HANDLING",
        "audit_log": [{
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "stage": "HITL_DECISION",
            "action": f"decision_{decision.lower()}",
            "details": {
                "decision": decision,
                "reviewer_id": human_input.get("reviewer_id"),
                "notes": human_input.get("notes", "")
            }
        }]
    }
    
    await emit_stage_completed(thread_id, "HITL_DECISION", {"decision": decision})
    return result


async def reconcile_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    RECONCILE 📘 node - build accounting entries.
    
    Server: COMMON
    Operations: build_accounting_entries, create_ledger
    Reconstructs payable/receivable ledger entries.
    """
    thread_id = _get_thread_id_from_state(state)
    invoice_amount = state.get("invoice_payload", {}).get("amount", 0)
    
    logger.info("📘 RECONCILE: Building accounting entries")
    await emit_stage_started(thread_id, "RECONCILE", {"invoice_amount": invoice_amount})
    
    try:
        agent = AgentRegistry.get("RECONCILE")
        
        # Emit tool call started
        await emit_tool_call(thread_id, "RECONCILE", "build_accounting_entries", "COMMON", status="started")
        
        result = await agent.execute(state)
        
        entries = result.get("accounting_entries", [])
        report = result.get("reconciliation_report", {})
        
        total_debit = sum(e.get("amount", 0) for e in entries if e.get("type") == "DEBIT")
        total_credit = sum(e.get("amount", 0) for e in entries if e.get("type") == "CREDIT")
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "RECONCILE", "build_accounting_entries", "COMMON",
            params={"invoice_amount": invoice_amount},
            result={"entries_count": len(entries), "total_debit": total_debit, "total_credit": total_credit},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"📊 Created {len(entries)} entries | Debit: ${total_debit:,.2f} | Credit: ${total_credit:,.2f}", stage="RECONCILE", log_type="result")
        
        await emit_stage_completed(thread_id, "RECONCILE", {
            "entries_count": len(entries),
            "total_debit": total_debit,
            "total_credit": total_credit
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "RECONCILE", str(e))
        await emit_log_message(thread_id, "error", f"❌ RECONCILE failed: {str(e)}", stage="RECONCILE", log_type="error")
        raise


async def approve_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    APPROVE 🔄 node - apply invoice approval policy.
    
    Server: ATLAS (if integration needed)
    Operations: apply_invoice_approval_policy
    Auto-approves or escalates based on invoice amount & rules.
    """
    thread_id = _get_thread_id_from_state(state)
    invoice_amount = state.get("invoice_payload", {}).get("amount", 0)
    
    logger.info("🔄 APPROVE: Applying approval policy")
    await emit_stage_started(thread_id, "APPROVE", {"invoice_amount": invoice_amount})
    
    try:
        agent = AgentRegistry.get("APPROVE")
        
        # Emit tool call started
        await emit_tool_call(thread_id, "APPROVE", "apply_approval_policy", "COMMON", status="started")
        
        result = await agent.execute(state)
        
        approval_status = result.get("approval_status", "UNKNOWN")
        approver_id = result.get("approver_id", "system")
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "APPROVE", "apply_approval_policy", "COMMON",
            params={"invoice_amount": invoice_amount},
            result={"approval_status": approval_status, "approver_id": approver_id},
            status="completed"
        )
        
        if approval_status == "APPROVED":
            await emit_log_message(thread_id, "info", f"✅ Auto-approved by {approver_id}", stage="APPROVE", log_type="decision")
        elif approval_status == "ESCALATED":
            await emit_log_message(thread_id, "warning", f"⚠️ Escalated for manual approval to {approver_id}", stage="APPROVE", log_type="decision")
        else:
            await emit_log_message(thread_id, "info", f"📋 Status: {approval_status} | Approver: {approver_id}", stage="APPROVE", log_type="result")
        
        await emit_stage_completed(thread_id, "APPROVE", {
            "approval_status": approval_status,
            "approver_id": approver_id
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "APPROVE", str(e))
        await emit_log_message(thread_id, "error", f"❌ APPROVE failed: {str(e)}", stage="APPROVE", log_type="error")
        raise


async def posting_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    POSTING 🏃 node - post to ERP and schedule payment.
    
    Server: ATLAS
    Operations: post_to_erp, schedule_payment
    BigtoolPicker: Selects ERP/payment system
    """
    thread_id = _get_thread_id_from_state(state)
    invoice_amount = state.get("invoice_payload", {}).get("amount", 0)
    
    logger.info("🏃 POSTING: Posting to ERP and scheduling payment")
    await emit_stage_started(thread_id, "POSTING", {"invoice_amount": invoice_amount})
    
    try:
        agent = AgentRegistry.get("POSTING")
        
        # Emit tool call started (BigtoolPicker selects ERP posting tool)
        await emit_tool_call(thread_id, "POSTING", "post_erp", "ATLAS", status="started")
        
        result = await agent.execute(state)
        
        bigtool = result.get("bigtool_selections", {}).get("POSTING", {})
        tool_name = bigtool.get('tool_name', 'post_erp')
        erp_txn_id = result.get("erp_txn_id")
        payment_id = result.get("scheduled_payment_id")
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "POSTING", tool_name, "ATLAS",
            params={"invoice_amount": invoice_amount},
            result={"erp_txn_id": erp_txn_id, "payment_id": payment_id},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"📝 ERP Txn: {erp_txn_id} | Payment: {payment_id} | Amount: ${invoice_amount:,.2f}", stage="POSTING", log_type="result")
        
        await emit_stage_completed(thread_id, "POSTING", {
            "erp_txn_id": erp_txn_id,
            "scheduled_payment_id": payment_id,
            "bigtool": bigtool
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "POSTING", str(e))
        await emit_log_message(thread_id, "error", f"❌ POSTING failed: {str(e)}", stage="POSTING", log_type="error")
        raise


async def notify_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    NOTIFY ✉️ node - send notifications.
    
    Server: ATLAS
    Operations: notify_vendor, notify_finance_team
    BigtoolPicker: Selects notification channel (Email/Slack/SMS)
    """
    thread_id = _get_thread_id_from_state(state)
    vendor = state.get("vendor_profile", {}).get("normalized_name", "vendor")
    
    logger.info("✉️ NOTIFY: Sending notifications")
    await emit_stage_started(thread_id, "NOTIFY", {"vendor": vendor})
    
    try:
        agent = AgentRegistry.get("NOTIFY")
        
        # Emit tool call started (BigtoolPicker selects notification channel)
        await emit_tool_call(thread_id, "NOTIFY", "send_notification", "ATLAS", status="started")
        
        result = await agent.execute(state)
        
        bigtool = result.get("bigtool_selections", {}).get("NOTIFY", {})
        tool_name = bigtool.get('tool_name', 'send_notification')
        parties = result.get("notified_parties", [])
        status = result.get("notify_status", {})
        
        # Emit tool call completed
        await emit_tool_call(
            thread_id, "NOTIFY", tool_name, "ATLAS",
            params={"vendor": vendor},
            result={"parties_notified": len(parties)},
            status="completed"
        )
        
        await emit_log_message(thread_id, "info", f"📧 Notified {len(parties)} parties (vendor: {vendor}, finance team)", stage="NOTIFY", log_type="result")
        
        await emit_stage_completed(thread_id, "NOTIFY", {
            "parties_notified": len(parties),
            "bigtool": bigtool
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "NOTIFY", str(e))
        await emit_log_message(thread_id, "error", f"❌ NOTIFY failed: {str(e)}", stage="NOTIFY", log_type="error")
        raise


async def complete_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    COMPLETE ✅ node - finalize workflow and output payload.
    
    Server: COMMON
    Operations: output_final_payload, log_completion
    Produces final structured payload and marks workflow complete.
    """
    thread_id = _get_thread_id_from_state(state)
    invoice_id = state.get("invoice_payload", {}).get("invoice_id", "unknown")
    erp_txn = state.get("erp_txn_id", "N/A")
    
    logger.info("✅ COMPLETE: Finalizing workflow")
    await emit_stage_started(thread_id, "COMPLETE", {"invoice_id": invoice_id, "erp_txn": erp_txn})
    
    try:
        agent = AgentRegistry.get("COMPLETE")
        result = await agent.execute(state)
        
        final_payload = result.get("final_payload", {})
        
        await emit_log_message(thread_id, "info", f"📝 Invoice {invoice_id} | ERP Txn: {erp_txn}", stage="COMPLETE", log_type="result")
        
        await emit_stage_completed(thread_id, "COMPLETE", {
            "status": "COMPLETED",
            "invoice_id": invoice_id,
            "erp_txn_id": erp_txn
        })
        
        await emit_log_message(thread_id, "info", "🎉 WORKFLOW COMPLETED SUCCESSFULLY!", stage="COMPLETE", log_type="success")
        
        # Emit workflow complete event
        await emit_workflow_complete(thread_id, "COMPLETED", {
            "invoice_id": invoice_id,
            "erp_txn_id": erp_txn,
            "final_payload": final_payload
        })
        
        return result
    except Exception as e:
        await emit_stage_failed(thread_id, "COMPLETE", str(e))
        await emit_log_message(thread_id, "error", f"❌ COMPLETE failed: {str(e)}", stage="COMPLETE", log_type="error")
        raise


async def manual_handoff_node(state: InvoiceWorkflowState) -> dict[str, Any]:
    """
    MANUAL_HANDOFF ⚠️ node - handles rejected invoices.
    
    Executed when HITL reviewer rejects the invoice.
    Finalizes workflow with REQUIRES_MANUAL_HANDLING status.
    """
    thread_id = _get_thread_id_from_state(state)
    invoice_id = state.get("invoice_payload", {}).get("invoice_id", "unknown")
    reviewer = state.get("reviewer_id", "unknown")
    notes = state.get("reviewer_notes", "No notes provided")
    
    logger.info("⚠️ MANUAL_HANDOFF: Invoice rejected, requiring manual handling")
    await emit_stage_started(thread_id, "MANUAL_HANDOFF", {"invoice_id": invoice_id, "reviewer": reviewer})
    await emit_log_message(thread_id, "warning", f"⚠️ Invoice REJECTED by {reviewer}: {notes}", stage="MANUAL_HANDOFF", log_type="decision")
    
    result = {
        "current_stage": "MANUAL_HANDOFF",
        "status": "REQUIRES_MANUAL_HANDLING",
        "final_payload": {
            "workflow_id": state.get("raw_id"),
            "invoice_id": invoice_id,
            "status": "REQUIRES_MANUAL_HANDLING",
            "reason": "Invoice rejected during human review",
            "reviewer_id": reviewer,
            "reviewer_notes": notes,
            "hitl_checkpoint_id": state.get("hitl_checkpoint_id"),
        },
        "audit_log": [{
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "stage": "MANUAL_HANDOFF",
            "action": "workflow_requires_manual_handling",
            "details": {
                "invoice_id": invoice_id,
                "reason": "Rejected during human review"
            }
        }]
    }
    
    await emit_log_message(thread_id, "warning", "📤 Workflow ended - REQUIRES MANUAL HANDLING", stage="MANUAL_HANDOFF", log_type="warning")
    await emit_stage_completed(thread_id, "MANUAL_HANDOFF", {"status": "REQUIRES_MANUAL_HANDLING"})
    await emit_workflow_complete(thread_id, "REQUIRES_MANUAL_HANDLING", result.get("final_payload"))
    
    return result

