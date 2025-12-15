"""MCP Router for routing abilities to COMMON or ATLAS servers."""
from enum import Enum
from typing import Any, Optional
from ..utils.logger import get_logger


class MCPServer(Enum):
    """MCP Server types."""
    COMMON = "COMMON"
    ATLAS = "ATLAS"


class MCPRouter:
    """
    Routes abilities to appropriate MCP server.
    
    COMMON Server: Abilities requiring no external data
    ATLAS Server: Abilities requiring external system interaction
    """
    
    # Routing table mapping abilities to servers
    ROUTING_TABLE = {
        # COMMON Server abilities (no external data)
        "validate_schema": MCPServer.COMMON,
        "persist_raw": MCPServer.COMMON,
        "parse_line_items": MCPServer.COMMON,
        "normalize_vendor": MCPServer.COMMON,
        "compute_flags": MCPServer.COMMON,
        "match_engine": MCPServer.COMMON,
        "build_accounting_entries": MCPServer.COMMON,
        "create_checkpoint": MCPServer.COMMON,
        "finalize_workflow": MCPServer.COMMON,
        
        # ATLAS Server abilities (external systems)
        "ocr_extract": MCPServer.ATLAS,
        "enrich_vendor": MCPServer.ATLAS,
        "fetch_po": MCPServer.ATLAS,
        "fetch_grn": MCPServer.ATLAS,
        "fetch_history": MCPServer.ATLAS,
        "post_to_erp": MCPServer.ATLAS,
        "schedule_payment": MCPServer.ATLAS,
        "send_email": MCPServer.ATLAS,
        "send_slack": MCPServer.ATLAS,
        "authenticate_user": MCPServer.ATLAS,
    }
    
    def __init__(self):
        self.logger = get_logger("mcp_router")
        self._common_server = CommonServer()
        self._atlas_server = AtlasServer()
    
    def get_server(self, ability: str) -> MCPServer:
        """
        Get the appropriate server for an ability.
        
        Args:
            ability: Ability name
            
        Returns:
            MCPServer enum value
        """
        return self.ROUTING_TABLE.get(ability, MCPServer.COMMON)
    
    async def execute(
        self,
        ability: str,
        params: dict = None,
        context: dict = None,
        **kwargs
    ) -> Any:
        """
        Execute an ability on the appropriate MCP server.
        
        Args:
            ability: Ability name to execute
            params: Parameters for the ability
            context: Execution context
            **kwargs: Additional arguments
            
        Returns:
            Ability execution result
        """
        server = self.get_server(ability)
        params = params or {}
        context = context or {}
        
        self.logger.info(
            f"Routing ability '{ability}' to {server.value} server",
            extra={"extra": {"ability": ability, "server": server.value}}
        )
        
        if server == MCPServer.COMMON:
            return await self._common_server.execute(ability, params, **kwargs)
        else:
            return await self._atlas_server.execute(ability, params, **kwargs)
    
    def list_abilities(self, server: MCPServer = None) -> list[str]:
        """
        List available abilities.
        
        Args:
            server: Filter by server type
            
        Returns:
            List of ability names
        """
        if server is None:
            return list(self.ROUTING_TABLE.keys())
        
        return [
            ability for ability, srv in self.ROUTING_TABLE.items()
            if srv == server
        ]


class CommonServer:
    """
    COMMON MCP Server - handles abilities requiring no external data.
    
    Mock implementation for demo purposes.
    """
    
    def __init__(self):
        self.logger = get_logger("mcp.common")
    
    async def execute(self, ability: str, params: dict = None, **kwargs) -> Any:
        """Execute ability on COMMON server."""
        self.logger.info(f"Executing ability: {ability}")
        
        # Mock implementations
        handlers = {
            "validate_schema": self._validate_schema,
            "persist_raw": self._persist_raw,
            "parse_line_items": self._parse_line_items,
            "normalize_vendor": self._normalize_vendor,
            "compute_flags": self._compute_flags,
            "match_engine": self._match_engine,
            "build_accounting_entries": self._build_entries,
            "create_checkpoint": self._create_checkpoint,
            "finalize_workflow": self._finalize_workflow,
        }
        
        handler = handlers.get(ability, self._default_handler)
        return await handler(params or {}, **kwargs)
    
    async def _validate_schema(self, params: dict, **kwargs) -> dict:
        return {"valid": True, "errors": []}
    
    async def _persist_raw(self, params: dict, **kwargs) -> dict:
        return {"stored": True, "location": "local_fs://invoices/"}
    
    async def _parse_line_items(self, params: dict, **kwargs) -> dict:
        return {"parsed": True, "items_count": len(params.get("line_items", []))}
    
    async def _normalize_vendor(self, params: dict, **kwargs) -> dict:
        name = params.get("name", "").upper().strip()
        return {"normalized_name": name}
    
    async def _compute_flags(self, params: dict, **kwargs) -> dict:
        return {"flags": [], "risk_level": "LOW"}
    
    async def _match_engine(self, params: dict, **kwargs) -> dict:
        return {"matched": True, "score": 0.95}
    
    async def _build_entries(self, params: dict, **kwargs) -> dict:
        return {"entries_created": 2, "balanced": True}
    
    async def _create_checkpoint(self, params: dict, **kwargs) -> dict:
        return {"checkpoint_created": True}
    
    async def _finalize_workflow(self, params: dict, **kwargs) -> dict:
        return {"finalized": True}
    
    async def _default_handler(self, params: dict, **kwargs) -> dict:
        return {"success": True, "mock": True}


class AtlasServer:
    """
    ATLAS MCP Server - handles abilities requiring external systems.
    
    Mock implementation for demo purposes.
    """
    
    def __init__(self):
        self.logger = get_logger("mcp.atlas")
    
    async def execute(self, ability: str, params: dict = None, **kwargs) -> Any:
        """Execute ability on ATLAS server."""
        self.logger.info(f"Executing ability: {ability}")
        
        # Mock implementations
        handlers = {
            "ocr_extract": self._ocr_extract,
            "enrich_vendor": self._enrich_vendor,
            "fetch_po": self._fetch_po,
            "fetch_grn": self._fetch_grn,
            "fetch_history": self._fetch_history,
            "post_to_erp": self._post_to_erp,
            "schedule_payment": self._schedule_payment,
            "send_email": self._send_email,
            "send_slack": self._send_slack,
            "authenticate_user": self._authenticate_user,
        }
        
        handler = handlers.get(ability, self._default_handler)
        return await handler(params or {}, **kwargs)
    
    async def _ocr_extract(self, params: dict, **kwargs) -> dict:
        return {
            "text": "Mock OCR extracted text",
            "confidence": 0.95,
            "tool": "google_vision"
        }
    
    async def _enrich_vendor(self, params: dict, **kwargs) -> dict:
        return {
            "enriched": True,
            "company_size": "medium",
            "industry": "Technology",
            "tool": "clearbit"
        }
    
    async def _fetch_po(self, params: dict, **kwargs) -> dict:
        return {"pos": [], "count": 0}
    
    async def _fetch_grn(self, params: dict, **kwargs) -> dict:
        return {"grns": [], "count": 0}
    
    async def _fetch_history(self, params: dict, **kwargs) -> dict:
        return {"history": [], "count": 0}
    
    async def _post_to_erp(self, params: dict, **kwargs) -> dict:
        return {"posted": True, "txn_id": "ERP-MOCK-001"}
    
    async def _schedule_payment(self, params: dict, **kwargs) -> dict:
        return {"scheduled": True, "payment_id": "PAY-MOCK-001"}
    
    async def _send_email(self, params: dict, **kwargs) -> dict:
        return {"sent": True, "message_id": "EMAIL-MOCK-001"}
    
    async def _send_slack(self, params: dict, **kwargs) -> dict:
        return {"sent": True, "channel": params.get("channel", "#general")}
    
    async def _authenticate_user(self, params: dict, **kwargs) -> dict:
        return {"authenticated": True, "user_id": params.get("user_id")}
    
    async def _default_handler(self, params: dict, **kwargs) -> dict:
        return {"success": True, "mock": True}
