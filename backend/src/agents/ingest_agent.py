"""Ingest Agent - INTAKE Stage."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState
from ..utils.validators import validate_invoice_payload


class IngestAgent(BaseAgent):
    """
    INTAKE Stage Agent.
    
    Validates payload schema and persists raw invoice data.
    Uses COMMON server for validation and storage.
    Uses Bigtool to select storage provider.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="IngestAgent", config=config)
    
    def get_required_fields(self) -> list[str]:
        return ["invoice_payload"]
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate invoice payload exists."""
        return "invoice_payload" in state and state["invoice_payload"] is not None
    
    async def execute(self, state: InvoiceWorkflowState) -> dict[str, Any]:
        """
        Execute INTAKE stage.
        
        - Validates invoice payload schema
        - Persists raw invoice (mock)
        - Generates raw_id and timestamp
        
        Returns:
            dict with raw_id, ingest_ts, validated, audit_log
        """
        self.logger.info("Starting INTAKE stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            
            # Validate schema
            is_valid = validate_invoice_payload(invoice)
            
            if not is_valid:
                self.logger.warning("Invoice payload validation failed")
                return {
                    "validated": False,
                    "current_stage": "INTAKE",
                    "status": "FAILED",
                    "error": "Invalid invoice payload schema",
                    "audit_log": [self.create_audit_entry(
                        "INTAKE",
                        "validation_failed",
                        {"reason": "Invalid schema"}
                    )]
                }
            
            # Generate raw_id (simulating storage)
            raw_id = f"RAW-{uuid4().hex[:12].upper()}"
            ingest_ts = datetime.now(timezone.utc).isoformat()
            
            # Mock bigtool selection for storage
            bigtool_selection = {
                "INTAKE": {
                    "capability": "storage",
                    "selected_tool": "local_fs",
                    "pool": ["s3", "gcs", "local_fs"],
                    "reason": "local_fs available and fastest for demo"
                }
            }
            
            self.log_execution(
                stage="INTAKE",
                action="ingest_invoice",
                result={"raw_id": raw_id, "validated": True},
                bigtool_selection=bigtool_selection["INTAKE"]
            )
            
            return {
                "raw_id": raw_id,
                "ingest_ts": ingest_ts,
                "validated": True,
                "current_stage": "INTAKE",
                "bigtool_selections": bigtool_selection,
                "audit_log": [self.create_audit_entry(
                    "INTAKE",
                    "invoice_ingested",
                    {
                        "raw_id": raw_id,
                        "invoice_id": invoice.get("invoice_id"),
                        "tool": "local_fs"
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("INTAKE", e, state)
