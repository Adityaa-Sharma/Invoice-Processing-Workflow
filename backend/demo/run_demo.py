"""
Demo script for Invoice Processing Workflow.

This script demonstrates the full workflow execution including:
- Invoice submission
- All 12 processing stages
- Bigtool selections
- MCP routing
- HITL checkpoint/resume (simulated)
- Final output

Run with: python -m demo.run_demo
"""
import asyncio
import json
from datetime import datetime, timezone

from src.graph.workflow import create_invoice_workflow, get_workflow_stages
from src.graph.state import create_initial_state
from src.db.checkpoint_store import get_memory_checkpointer
from src.tools.bigtool_picker import BigtoolPicker
from langgraph.types import Command


def print_header(title: str):
    """Print section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_stage(stage: str, result: dict):
    """Print stage result summary."""
    print(f"\n📍 Stage: {stage}")
    print(f"   Status: {result.get('status', 'N/A')}")
    
    # Print bigtool selection if any
    selections = result.get("bigtool_selections", {})
    if stage in selections:
        sel = selections[stage]
        print(f"   🔧 Bigtool: {sel.get('selected_tool')} (capability: {sel.get('capability')})")


async def run_matched_workflow():
    """Run workflow with matching invoice (no HITL)."""
    print_header("DEMO 1: Invoice Processing - Matched Flow")
    print("Invoice will match PO and complete without human review")
    
    # Sample invoice that will match
    invoice = {
        "invoice_id": "INV-DEMO-001",
        "vendor_name": "Acme Technologies Inc.",
        "vendor_tax_id": "TAX-789012",
        "invoice_date": "2024-01-15",
        "due_date": "2024-02-15",
        "amount": 15000.00,
        "currency": "USD",
        "line_items": [
            {"desc": "Enterprise Software License", "qty": 5, "unit_price": 2000.0, "total": 10000.0},
            {"desc": "Premium Support Package", "qty": 1, "unit_price": 5000.0, "total": 5000.0}
        ],
        "attachments": ["invoice_demo_001.pdf"]
    }
    
    print("\n📄 Input Invoice:")
    print(json.dumps(invoice, indent=2))
    
    # Create workflow
    checkpointer = get_memory_checkpointer()
    workflow = create_invoice_workflow(checkpointer)
    
    # Create initial state
    initial_state = create_initial_state(invoice)
    config = {"configurable": {"thread_id": "demo-matched-001"}}
    
    print("\n🚀 Starting workflow execution...")
    
    # Execute workflow
    result = await workflow.ainvoke(initial_state, config)
    
    # Print results
    print_header("Workflow Results")
    
    print(f"\n✅ Final Status: {result.get('status')}")
    print(f"📍 Final Stage: {result.get('current_stage')}")
    
    if result.get("match_score"):
        print(f"\n📊 Match Score: {result.get('match_score'):.2f}")
        print(f"   Match Result: {result.get('match_result')}")
    
    if result.get("erp_txn_id"):
        print(f"\n💰 ERP Transaction: {result.get('erp_txn_id')}")
        print(f"   Payment Scheduled: {result.get('scheduled_payment_id')}")
    
    # Print bigtool selections
    print("\n🔧 Bigtool Selections:")
    for stage, selection in result.get("bigtool_selections", {}).items():
        print(f"   {stage}: {selection.get('selected_tool')} ({selection.get('capability')})")
    
    # Print audit log summary
    audit_log = result.get("audit_log", [])
    print(f"\n📋 Audit Log Entries: {len(audit_log)}")
    for entry in audit_log[-5:]:  # Last 5 entries
        print(f"   - [{entry.get('stage')}] {entry.get('action')}")
    
    # Print final payload
    if result.get("final_payload"):
        print("\n📦 Final Payload:")
        print(json.dumps(result.get("final_payload"), indent=2, default=str))
    
    return result


async def run_hitl_workflow():
    """Run workflow with HITL checkpoint and resume."""
    print_header("DEMO 2: Invoice Processing - HITL Flow")
    print("Invoice will fail matching and require human review")
    
    # Invoice that will fail matching (modified to force mismatch)
    invoice = {
        "invoice_id": "INV-DEMO-002",
        "vendor_name": "Different Vendor Corp",
        "vendor_tax_id": None,  # Missing tax ID
        "invoice_date": "2024-01-20",
        "due_date": "2024-02-20",
        "amount": 25000.00,  # Amount won't match
        "currency": "USD",
        "line_items": [
            {"desc": "Consulting Services", "qty": 100, "unit_price": 250.0, "total": 25000.0}
        ],
        "attachments": ["invoice_demo_002.pdf"]
    }
    
    print("\n📄 Input Invoice:")
    print(json.dumps(invoice, indent=2))
    
    # Create workflow
    checkpointer = get_memory_checkpointer()
    workflow = create_invoice_workflow(checkpointer)
    
    # Create initial state
    initial_state = create_initial_state(invoice)
    config = {"configurable": {"thread_id": "demo-hitl-001"}}
    
    print("\n🚀 Starting workflow execution...")
    
    # Execute workflow (will pause at HITL)
    result = await workflow.ainvoke(initial_state, config)
    
    print(f"\n⏸️  Workflow Status: {result.get('status')}")
    print(f"   Current Stage: {result.get('current_stage')}")
    
    if result.get("checkpoint_id"):
        print(f"\n🔖 Checkpoint Created:")
        print(f"   Checkpoint ID: {result.get('checkpoint_id')}")
        print(f"   Review URL: {result.get('review_url')}")
        print(f"   Paused Reason: {result.get('paused_reason')}")
        
        # Simulate human review
        print("\n👤 Simulating Human Review...")
        print("   Reviewer: admin-001")
        print("   Decision: ACCEPT")
        print("   Notes: Verified with vendor, amount confirmed")
        
        # Resume with ACCEPT decision
        print("\n▶️  Resuming workflow with ACCEPT decision...")
        
        resume_result = await workflow.ainvoke(
            Command(resume={
                "decision": "ACCEPT",
                "reviewer_id": "admin-001",
                "notes": "Verified with vendor, amount confirmed"
            }),
            config
        )
        
        result = resume_result
        
        print(f"\n✅ Resumed - Status: {result.get('status')}")
        print(f"   Stage: {result.get('current_stage')}")
    
    # Print final results
    if result.get("status") == "COMPLETED":
        print("\n🎉 Workflow completed successfully after human review!")
        
        if result.get("final_payload"):
            print("\n📦 Final Payload:")
            print(json.dumps(result.get("final_payload"), indent=2, default=str))
    
    return result


async def demo_bigtool_selection():
    """Demonstrate Bigtool selection logic."""
    print_header("DEMO 3: Bigtool Selection")
    
    bigtool = BigtoolPicker()
    
    capabilities = ["ocr", "enrichment", "erp_connector", "db", "email", "storage"]
    
    print("\n🔧 Tool Selection for Each Capability:\n")
    
    for capability in capabilities:
        result = bigtool.select(capability)
        print(f"   {capability.upper()}:")
        print(f"      Pool: {result.get('pool')}")
        print(f"      Selected: {result.get('selected_tool')}")
        print(f"      Reason: {result.get('reason')}")
        print()


async def main():
    """Run all demos."""
    print("\n" + "🌟" * 30)
    print(" INVOICE PROCESSING WORKFLOW DEMO")
    print(" LangGraph + HITL + Bigtool + MCP")
    print("🌟" * 30)
    
    # Show workflow stages
    print_header("Workflow Stages")
    stages = get_workflow_stages()
    for i, stage in enumerate(stages, 1):
        mode_icon = "🤖" if stage["mode"] == "deterministic" else "👤"
        print(f"   {i:2}. {stage['id']:20} {mode_icon} {stage['mode']}")
    
    # Run demos
    await run_matched_workflow()
    await demo_bigtool_selection()
    
    # Note about HITL demo
    print_header("HITL Demo Note")
    print("""
The HITL (Human-in-the-Loop) demo requires the LangGraph interrupt
mechanism which pauses the workflow and waits for external input.

In a real application:
1. Workflow pauses at CHECKPOINT_HITL when match fails
2. Review item is added to human_review_queue
3. Human accesses /human-review/pending endpoint
4. Human submits decision via /human-review/decision
5. Workflow resumes with Command(resume={decision: ...})

See the API endpoints for full HITL implementation.
    """)
    
    print("\n" + "✅" * 30)
    print(" DEMO COMPLETE")
    print("✅" * 30 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
