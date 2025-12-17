"""
MCP Client for communicating with MCP servers.

Provides a unified client to communicate with COMMON and ATLAS MCP servers.
Uses HTTP to call running FastMCP server endpoints.
"""
from typing import Any, Optional
from datetime import datetime, timezone
import httpx
import asyncio

from ..utils.logger import get_logger

logger = get_logger("mcp.client")

# Server URLs
COMMON_SERVER_URL = "http://localhost:8001"
ATLAS_SERVER_URL = "http://localhost:8002"

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


class MCPClient:
    """
    Unified MCP Client for communicating with COMMON and ATLAS servers.
    
    Routes tool calls to the appropriate server based on TOOL_SERVER_MAP.
    """
    
    _instance: Optional["MCPClient"] = None
    
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
    
    def _get_server_url(self, tool_name: str) -> str:
        """Get server URL for a tool."""
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
        
        try:
            # Call the tool endpoint on the MCP server
            response = await self.http_client.post(
                f"{server_url}/tools/{tool_name}",
                json=params
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
            self.logger.error(f"{server_name}.{tool_name} request error: {e}")
            return {
                "success": False,
                "server": server_name,
                "tool": tool_name,
                "error": f"Connection error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"{server_name}.{tool_name} failed: {e}")
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
