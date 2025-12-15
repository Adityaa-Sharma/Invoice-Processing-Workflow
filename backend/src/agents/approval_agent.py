"""Approval Agent - APPROVE Stage."""
from datetime import datetime, timezone
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class ApprovalAgent(BaseAgent):
    """
    APPROVE Stage Agent.
    
    Applies invoice approval policy based on amount and rules.
    Uses ATLAS server for workflow integration if needed.
    """
    
    # Approval thresholds
    AUTO_APPROVE_LIMIT = 10000.0  # Auto-approve if amount <= this
    MANAGER_APPROVE_LIMIT = 50000.0  # Manager can approve up to this
    
    def __init__(self, config: dict = None):
        super().__init__(name="ApprovalAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "reconciliation_report"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("invoice_payload") is not None and
            state.get("reconciliation_report") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute APPROVE stage.
        
        - Checks invoice amount against approval limits
        - Auto-approves or escalates based on rules
        
        Returns:
            dict with approval_status, approver_id, audit_log
        """
        self.logger.info("Starting APPROVE stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            vendor = state.get("vendor_profile", {})
            
            amount = invoice.get("amount", 0)
            
            # Apply approval policy
            approval_result = self._apply_approval_policy(amount, vendor)
            
            self.log_execution(
                stage="APPROVE",
                action="apply_policy",
                result={
                    "amount": amount,
                    "approval_status": approval_result["status"],
                    "approver": approval_result["approver_id"]
                }
            )
            
            return {
                "approval_status": approval_result["status"],
                "approver_id": approval_result["approver_id"],
                "current_stage": "APPROVE",
                "audit_log": [self.create_audit_entry(
                    "APPROVE",
                    "approval_processed",
                    {
                        "invoice_id": invoice.get("invoice_id"),
                        "amount": amount,
                        "approval_status": approval_result["status"],
                        "approver_id": approval_result["approver_id"],
                        "policy_applied": approval_result["policy"]
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("APPROVE", e, state)
    
    def _apply_approval_policy(self, amount: float, vendor: dict) -> dict:
        """
        Apply approval policy based on amount and vendor risk.
        
        Returns approval decision with approver info.
        """
        risk_score = vendor.get("risk_score", 0) if vendor else 0
        
        # Check for high-risk vendor
        if risk_score > 0.5:
            return {
                "status": "APPROVED_WITH_REVIEW",
                "approver_id": "MANAGER-REVIEW",
                "policy": "high_risk_vendor"
            }
        
        # Auto-approve small amounts
        if amount <= self.AUTO_APPROVE_LIMIT:
            return {
                "status": "AUTO_APPROVED",
                "approver_id": "SYSTEM",
                "policy": "auto_approve_small_amount"
            }
        
        # Manager approval for medium amounts
        if amount <= self.MANAGER_APPROVE_LIMIT:
            return {
                "status": "APPROVED",
                "approver_id": "MGR-001",
                "policy": "manager_approval"
            }
        
        # Executive approval for large amounts
        return {
            "status": "APPROVED",
            "approver_id": "EXEC-001",
            "policy": "executive_approval"
        }
