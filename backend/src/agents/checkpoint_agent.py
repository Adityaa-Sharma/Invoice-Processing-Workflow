"""Checkpoint Agent - CHECKPOINT_HITL Stage."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class CheckpointAgent(BaseAgent):
    """
    CHECKPOINT_HITL Stage Agent.
    
    Creates checkpoint for human review when matching fails.
    Persists state and adds entry to human review queue.
    Uses COMMON server for DB operations.
    Uses Bigtool to select DB provider.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="CheckpointAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "match_score", "match_result"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("match_result") == "FAILED" and
            state.get("invoice_payload") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute CHECKPOINT_HITL stage.
        
        - Creates checkpoint ID
        - Persists workflow state (mock)
        - Creates review ticket in queue
        - Generates review URL
        
        Returns:
            dict with checkpoint_id, review_url, paused_reason, audit_log
        """
        self.logger.info("Starting CHECKPOINT_HITL stage - Creating checkpoint for human review")
        
        try:
            invoice = state.get("invoice_payload", {})
            match_score = state.get("match_score", 0)
            match_evidence = state.get("match_evidence", {})
            
            # Mock bigtool selection for DB
            bigtool_selection = {
                "CHECKPOINT_HITL": {
                    "capability": "db",
                    "selected_tool": "sqlite",
                    "pool": ["postgres", "sqlite", "dynamodb"],
                    "reason": "sqlite configured for demo environment"
                }
            }
            
            # Generate checkpoint ID
            checkpoint_id = f"CHKPT-{uuid4().hex[:12].upper()}"
            
            # Generate review URL
            review_url = f"/human-review/{checkpoint_id}"
            
            # Determine pause reason
            mismatched = match_evidence.get("mismatched_fields", [])
            paused_reason = f"Match score {match_score:.2f} below threshold. Mismatched: {', '.join(mismatched)}"
            
            self.log_execution(
                stage="CHECKPOINT_HITL",
                action="create_checkpoint",
                result={
                    "hitl_checkpoint_id": checkpoint_id,
                    "match_score": match_score
                },
                bigtool_selection=bigtool_selection["CHECKPOINT_HITL"]
            )
            
            return {
                "hitl_checkpoint_id": checkpoint_id,
                "review_url": review_url,
                "paused_reason": paused_reason,
                "current_stage": "CHECKPOINT_HITL",
                "status": "PAUSED",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "CHECKPOINT_HITL",
                    "checkpoint_created",
                    {
                        "hitl_checkpoint_id": checkpoint_id,
                        "invoice_id": invoice.get("invoice_id"),
                        "match_score": match_score,
                        "paused_reason": paused_reason,
                        "review_url": review_url,
                        "db_tool": "sqlite"
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("CHECKPOINT_HITL", e, state)
