"""Human Review Agent - HITL_DECISION Stage."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class HumanReviewAgent(BaseAgent):
    """
    HITL_DECISION Stage Agent (Non-Deterministic).
    
    Processes human review decision after checkpoint.
    Routes workflow based on ACCEPT/REJECT decision.
    Uses ATLAS server for authentication.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="HumanReviewAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["checkpoint_id", "human_decision"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate checkpoint exists and decision provided."""
        return (
            state.get("checkpoint_id") is not None and
            state.get("human_decision") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute HITL_DECISION stage.
        
        - Reads human decision (ACCEPT/REJECT)
        - Updates workflow state based on decision
        - Generates resume token
        
        Returns:
            dict with human_decision processing result, audit_log
        """
        self.logger.info("Starting HITL_DECISION stage - Processing human decision")
        
        try:
            decision = state.get("human_decision", "")
            reviewer_id = state.get("reviewer_id", "unknown")
            reviewer_notes = state.get("reviewer_notes", "")
            checkpoint_id = state.get("checkpoint_id", "")
            
            # Generate resume token
            resume_token = f"RESUME-{uuid4().hex[:8].upper()}"
            
            # Process decision
            if decision == "ACCEPT":
                new_status = "RUNNING"
                action = "decision_accepted"
            else:  # REJECT
                new_status = "REQUIRES_MANUAL_HANDLING"
                action = "decision_rejected"
            
            self.log_execution(
                stage="HITL_DECISION",
                action=action,
                result={
                    "decision": decision,
                    "reviewer_id": reviewer_id,
                    "new_status": new_status
                }
            )
            
            return {
                "human_decision": decision,
                "reviewer_id": reviewer_id,
                "reviewer_notes": reviewer_notes,
                "resume_token": resume_token,
                "current_stage": "HITL_DECISION",
                "status": new_status,
                "audit_log": [self.create_audit_entry(
                    "HITL_DECISION",
                    action,
                    {
                        "checkpoint_id": checkpoint_id,
                        "decision": decision,
                        "reviewer_id": reviewer_id,
                        "reviewer_notes": reviewer_notes,
                        "resume_token": resume_token
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("HITL_DECISION", e, state)
