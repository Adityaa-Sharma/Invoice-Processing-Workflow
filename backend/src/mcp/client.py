"""
MCP Client for communicating with MCP servers.

Provides a unified client to communicate with COMMON and ATLAS MCP servers.
Uses HTTP to call running FastMCP server endpoints.

If MCP servers are not running, falls back to mock responses for demo/testing.
"""
from typing import Any, Optional
from datetime import datetime, timezone
import httpx
import asyncio
import os

from ..utils.logger import get_logger

logger = get_logger("mcp.client")

# Server URLs
COMMON_SERVER_URL = "http://localhost:8001"
ATLAS_SERVER_URL = "http://localhost:8002"

# Enable mock fallback (set to True if MCP servers not running)
MOCK_FALLBACK_ENABLED = os.environ.get("MCP_MOCK_FALLBACK", "true").lower() == "true"

# Tool to server mapping
TOOL_SERVER_MAP = {
    # COMMON server tools (internal operations)
    "validate_invoice_schema": "common",
    "persist_invoice": "common",
    "persist_audit": "common",
    "parse_line_items": "common",
    "normalize_vendor": "common",
    "create_checkpoint": "common",
    "get_checkpoint": "common",
    "compute_match": "common",
    "build_entries": "common",
    
    # ATLAS server tools (external operations)
    "extract_ocr": "atlas",
    "enrich_vendor": "atlas",
    "fetch_po_data": "atlas",
    "fetch_grn_data": "atlas",
    "post_to_erp": "atlas",
    "schedule_payment": "atlas",
    "send_notification": "atlas",
    "apply_policy": "atlas",
}

# Mock responses for when MCP servers are not running
MOCK_RESPONSES = {
    "validate_invoice_schema": {"valid": True, "errors": []},
    "persist_invoice": {"stored": True, "location": "local_fs://invoices/mock"},
    "persist_audit": {"stored": True, "audit_id": "AUDIT-MOCK-001"},
    "parse_line_items": {"parsed": True, "items_count": 3},
    "normalize_vendor": lambda p: {"normalized_name": (p.get("vendor_name", "") or "").upper().strip()},
    "create_checkpoint": {"checkpoint_created": True, "checkpoint_id": "CP-MOCK-001"},
    "get_checkpoint": {"checkpoint_id": "CP-MOCK-001", "state": {}},
    "compute_match": {"matched": True, "score": 0.95, "evidence": []},
    "build_entries": {"entries_created": 2, "balanced": True, "entries": []},
    "extract_ocr": {"text": "Mock OCR text", "confidence": 0.95, "provider": "google_vision"},
    "enrich_vendor": {"enriched": True, "company_size": "medium", "industry": "Technology"},
    "fetch_po_data": {"pos": [], "count": 0},
    "fetch_grn_data": {"grns": [], "count": 0},
    "post_to_erp": {"posted": True, "txn_id": "ERP-MOCK-001"},
    "schedule_payment": {"scheduled": True, "payment_id": "PAY-MOCK-001"},
    "send_notification": {"sent": True, "message_id": "NOTIF-MOCK-001"},
    "apply_policy": {"applied": True, "policy_id": "POL-001"},
}


class MCPClient:
    """
    Unified MCP Client for communicating with COMMON and ATLAS servers.
    
    Implements True MCP Protocol with:
    - Dynamic tool discovery from servers
    - Tool descriptions for LLM-based selection
    - Automatic server routing based on discovered tools
    
    Falls back to mock responses if servers are not running.
    """
    
    _instance: Optional["MCPClient"] = None
    _servers_checked: bool = False
    _servers_available: dict[str, bool] = {"common": None, "atlas": None}
    _discovered_tools: dict[str, dict] = {}  # Cache discovered tools
    _tool_to_server: dict[str, str] = {}  # Dynamic tool → server mapping
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logger = logger
        self.common_url = COMMON_SERVER_URL
        self.atlas_url = ATLAS_SERVER_URL
        self._http_client: Optional[httpx.AsyncClient] = None
        self._initialized = True
        self._tools_discovered = False
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
    
    async def discover_tools(self, force: bool = False) -> dict[str, list[dict]]:
        """
        Discover available tools from MCP servers (True MCP Protocol).
        
        Fetches tool schemas with descriptions from both COMMON and ATLAS servers.
        Results are cached for performance.
        
        Args:
            force: Force re-discovery even if already cached
            
        Returns:
            Dict with server names as keys and tool lists as values
        """
        if self._tools_discovered and not force:
            return self._discovered_tools
        
        self.logger.info("🔍 Discovering tools from MCP servers (True MCP Protocol)...")
        
        discovered = {"common": [], "atlas": []}
        
        # Discover from COMMON server
        try:
            response = await self.http_client.get(f"{self.common_url}/tools", timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", []) if isinstance(data, dict) else data
                discovered["common"] = tools
                
                # Build dynamic tool → server mapping
                for tool in tools:
                    tool_name = tool.get("name") if isinstance(tool, dict) else tool
                    self._tool_to_server[tool_name] = "common"
                
                self.logger.info(f"✅ COMMON server: discovered {len(tools)} tools")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not discover tools from COMMON: {e}")
        
        # Discover from ATLAS server
        try:
            response = await self.http_client.get(f"{self.atlas_url}/tools", timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", []) if isinstance(data, dict) else data
                discovered["atlas"] = tools
                
                # Build dynamic tool → server mapping
                for tool in tools:
                    tool_name = tool.get("name") if isinstance(tool, dict) else tool
                    self._tool_to_server[tool_name] = "atlas"
                
                self.logger.info(f"✅ ATLAS server: discovered {len(tools)} tools")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not discover tools from ATLAS: {e}")
        
        self._discovered_tools = discovered
        self._tools_discovered = True
        
        self.logger.info(f"📋 Total tools discovered: {len(self._tool_to_server)}")
        return discovered
    
    def get_all_tools_with_descriptions(self) -> list[dict]:
        """
        Get all discovered tools with their descriptions.
        
        Used by LLM to intelligently select tools based on descriptions.
        
        Returns:
            List of tool schemas with name, description, and inputSchema
        """
        all_tools = []
        for server, tools in self._discovered_tools.items():
            for tool in tools:
                if isinstance(tool, dict):
                    tool["server"] = server
                    all_tools.append(tool)
        return all_tools
    
    def get_tool_by_name(self, tool_name: str) -> Optional[dict]:
        """Get a specific tool's schema by name."""
        for tools in self._discovered_tools.values():
            for tool in tools:
                if isinstance(tool, dict) and tool.get("name") == tool_name:
                    return tool
        return None
    
    def _get_server_url(self, tool_name: str) -> str:
        """Get server URL for a tool (uses dynamic discovery if available)."""
        # First check dynamically discovered mapping
        if tool_name in self._tool_to_server:
            server = self._tool_to_server[tool_name]
            if server == "atlas":
                return self.atlas_url
            return self.common_url
        
        # Fallback to static mapping
        server = TOOL_SERVER_MAP.get(tool_name, "common")
        if server == "atlas":
            return self.atlas_url
        return self.common_url
    
    async def call_tool(self, tool_name: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """
        Call a tool on the appropriate MCP server.
        
        Routes the call to COMMON or ATLAS based on TOOL_SERVER_MAP.
        
        Args:
            tool_name: Name of the tool to call
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        params = params or {}
        server_url = self._get_server_url(tool_name)
        server_name = "ATLAS" if server_url == self.atlas_url else "COMMON"
        
        self.logger.info(
            f"Calling {server_name}.{tool_name}",
            extra={"extra": {"tool": tool_name, "server": server_name, "params": params}}
        )
        
    def _get_mock_response(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Get mock response for a tool when servers aren't available."""
        mock = MOCK_RESPONSES.get(tool_name, {"success": True, "mock": True})
        if callable(mock):
            return mock(params)
        return mock
    
    async def call_tool(self, tool_name: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """
        Call a tool on the appropriate MCP server.
        
        Routes the call to COMMON or ATLAS based on TOOL_SERVER_MAP.
        Falls back to mock responses if MOCK_FALLBACK_ENABLED and server unavailable.
        
        Args:
            tool_name: Name of the tool to call
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        params = params or {}
        server_url = self._get_server_url(tool_name)
        server_name = "ATLAS" if server_url == self.atlas_url else "COMMON"
        
        self.logger.info(
            f"Calling {server_name}.{tool_name}",
            extra={"extra": {"tool": tool_name, "server": server_name, "params": params}}
        )
        
        try:
            # Call the tool endpoint on the MCP server
            response = await self.http_client.post(
                f"{server_url}/tools/{tool_name}",
                json=params,
                timeout=5.0  # Quick timeout for connection check
            )
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "success": True,
                "server": server_name,
                "tool": tool_name,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"{server_name}.{tool_name} HTTP error: {e}")
            return {
                "success": False,
                "server": server_name,
                "tool": tool_name,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except httpx.RequestError as e:
            self.logger.warning(f"{server_name}.{tool_name} request error: {e}")
            
            # Fallback to mock if enabled
            if MOCK_FALLBACK_ENABLED:
                self.logger.info(f"Using mock fallback for {tool_name}")
                mock_result = self._get_mock_response(tool_name, params)
                return {
                    "success": True,
                    "server": f"{server_name} (MOCK)",
                    "tool": tool_name,
                    "result": mock_result,
                    "mock": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "success": False,
                "server": server_name,
                "tool": tool_name,
                "error": f"Connection error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"{server_name}.{tool_name} failed: {e}")
            
            # Fallback to mock if enabled
            if MOCK_FALLBACK_ENABLED:
                self.logger.info(f"Using mock fallback for {tool_name}")
                mock_result = self._get_mock_response(tool_name, params)
                return {
                    "success": True,
                    "server": f"{server_name} (MOCK)",
                    "tool": tool_name,
                    "result": mock_result,
                    "mock": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "success": False,
                "server": server_name,
                "tool": tool_name,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def health_check(self) -> dict[str, Any]:
        """Check health of MCP servers."""
        results = {"common": False, "atlas": False}
        
        try:
            # Check COMMON server
            response = await self.http_client.get(f"{self.common_url}/health")
            results["common"] = response.status_code == 200
        except Exception:
            results["common"] = False
        
        try:
            # Check ATLAS server
            response = await self.http_client.get(f"{self.atlas_url}/health")
            results["atlas"] = response.status_code == 200
        except Exception:
            results["atlas"] = False
        
        return {
            "servers": results,
            "all_healthy": all(results.values()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def list_tools(self) -> dict[str, list[str]]:
        """List available tools from both servers."""
        tools = {"common": [], "atlas": []}
        
        try:
            response = await self.http_client.get(f"{self.common_url}/tools")
            if response.status_code == 200:
                tools["common"] = response.json()
        except Exception as e:
            self.logger.error(f"Failed to list COMMON tools: {e}")
        
        try:
            response = await self.http_client.get(f"{self.atlas_url}/tools")
            if response.status_code == 200:
                tools["atlas"] = response.json()
        except Exception as e:
            self.logger.error(f"Failed to list ATLAS tools: {e}")
        
        return tools


# Singleton accessor
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get singleton MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
