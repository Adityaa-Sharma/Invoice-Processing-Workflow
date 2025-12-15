"""Notify Agent - NOTIFY Stage."""
from datetime import datetime, timezone
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState


class NotifyAgent(BaseAgent):
    """
    NOTIFY Stage Agent.
    
    Notifies vendor and internal finance team.
    Uses ATLAS server for email/notification services.
    Uses Bigtool to select email provider.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="NotifyAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload", "posted", "erp_txn_id"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required fields exist."""
        return (
            state.get("posted") is True and
            state.get("erp_txn_id") is not None
        )
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute NOTIFY stage.
        
        - Sends notification to vendor
        - Notifies internal finance team
        
        Returns:
            dict with notify_status, notified_parties, audit_log
        """
        self.logger.info("Starting NOTIFY stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            erp_txn_id = state.get("erp_txn_id", "")
            scheduled_payment_id = state.get("scheduled_payment_id", "")
            
            # Mock bigtool selection for email
            bigtool_selection = {
                "NOTIFY": {
                    "capability": "email",
                    "selected_tool": "sendgrid",
                    "pool": ["sendgrid", "ses", "smartlead"],
                    "reason": "sendgrid configured as primary email provider"
                }
            }
            
            # Mock send notifications
            vendor_notification = self._notify_vendor(invoice, scheduled_payment_id)
            finance_notification = self._notify_finance_team(invoice, erp_txn_id)
            
            notified_parties = [
                vendor_notification["recipient"],
                *finance_notification["recipients"]
            ]
            
            notify_status = {
                "vendor_notified": vendor_notification["sent"],
                "finance_notified": finance_notification["sent"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.log_execution(
                stage="NOTIFY",
                action="send_notifications",
                result={
                    "parties_notified": len(notified_parties),
                    "email_tool": "sendgrid"
                },
                bigtool_selection=bigtool_selection["NOTIFY"]
            )
            
            return {
                "notify_status": notify_status,
                "notified_parties": notified_parties,
                "current_stage": "NOTIFY",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "NOTIFY",
                    "notifications_sent",
                    {
                        "invoice_id": invoice.get("invoice_id"),
                        "vendor_notified": vendor_notification["sent"],
                        "finance_notified": finance_notification["sent"],
                        "parties_count": len(notified_parties),
                        "email_tool": "sendgrid"
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("NOTIFY", e, state)
    
    def _notify_vendor(self, invoice: dict, payment_id: str) -> dict:
        """Mock send notification to vendor."""
        vendor_email = f"{invoice.get('vendor_name', 'vendor').lower().replace(' ', '.')}@example.com"
        
        return {
            "sent": True,
            "recipient": vendor_email,
            "subject": f"Invoice {invoice.get('invoice_id')} Approved",
            "message": f"Your invoice has been approved. Payment ID: {payment_id}"
        }
    
    def _notify_finance_team(self, invoice: dict, erp_txn_id: str) -> dict:
        """Mock send notification to finance team."""
        return {
            "sent": True,
            "recipients": [
                "finance@company.com",
                "accounts.payable@company.com"
            ],
            "subject": f"Invoice {invoice.get('invoice_id')} Posted",
            "message": f"Invoice posted to ERP. Transaction ID: {erp_txn_id}"
        }
