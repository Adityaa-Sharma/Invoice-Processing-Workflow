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
    Uses BigtoolPicker to select storage provider.
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
        
        - Uses BigtoolPicker to select storage provider
        - Validates invoice payload schema via COMMON server
        - Persists raw invoice via MCP storage tool
        - Generates raw_id and timestamp
        
        Returns:
            dict with raw_id, ingest_ts, validated, audit_log
        """
        self.logger.info("Starting INTAKE stage")
        
        try:
            invoice = state.get("invoice_payload", {})
            
            # Step 1: Use BigtoolPicker to select storage tool
            tool_selection = await self.select_tool(
                capability="storage",
                context={
                    "invoice_id": invoice.get("invoice_id"),
                    "has_attachments": bool(invoice.get("attachments")),
                    "data_size": len(str(invoice)),
                },
                use_llm=True
            )
            
            bigtool_selection = {
                "INTAKE": {
                    "capability": "storage",
                    "selected_tool": tool_selection.get("selected_tool", "local_fs"),
                    "pool": tool_selection.get("pool", ["s3", "gcs", "local_fs"]),
                    "reason": tool_selection.get("reason", "BigtoolPicker selection")
                }
            }
            
            # Step 2: Validate schema via COMMON server
            validation_result = await self.execute_with_bigtool(
                capability="validation",
                params={
                    "invoice": invoice,
                    "schema_type": "invoice_payload"
                },
                context={"stage": "INTAKE"}
            )
            
            # Check validation (with fallback to local validation)
            is_valid = validation_result.get("valid", validate_invoice_payload(invoice))
            
            if not is_valid:
                self.logger.warning("Invoice payload validation failed")
                return {
                    "validated": False,
                    "current_stage": "INTAKE",
                    "status": "FAILED",
                    "error": validation_result.get("error", "Invalid invoice payload schema"),
                    "audit_log": [self.create_audit_entry(
                        "INTAKE",
                        "validation_failed",
                        {"reason": validation_result.get("errors", ["Invalid schema"])}
                    )]
                }
            
            # Step 3: Persist invoice via storage tool
            ingest_ts = datetime.now(timezone.utc).isoformat()
            
            storage_result = await self.execute_with_bigtool(
                capability="storage",
                params={
                    "action": "persist_invoice",
                    "invoice": invoice,
                    "timestamp": ingest_ts
                },
                context={"stage": "INTAKE"}
            )
            
            # Get raw_id from storage (with fallback to generated ID)
            raw_id = storage_result.get("raw_id") or f"RAW-{uuid4().hex[:12].upper()}"
            
            self.log_execution(
                stage="INTAKE",
                action="ingest_invoice",
                result={
                    "raw_id": raw_id,
                    "validated": True,
                    "storage_tool": tool_selection.get("selected_tool")
                },
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
                        "tool": tool_selection.get("selected_tool", "local_fs"),
                        "bigtool_used": True
                    }
                )]
            }
            
        except Exception as e:
            return self.handle_error("INTAKE", e, state)
