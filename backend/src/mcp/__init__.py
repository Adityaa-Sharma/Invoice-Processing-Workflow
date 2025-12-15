"""MCP (Model Context Protocol) servers module using FastMCP.

Architecture:
- COMMON Server (port 8001): Internal operations - validation, persistence, parsing
- ATLAS Server (port 8002): External operations - OCR, enrichment, ERP, payments
- MCPClient: Unified client for communicating with both servers

Usage:
    1. Start servers: python run_servers.py
    2. Use BigtoolPicker to orchestrate tool calls
"""
from .client import MCPClient, get_mcp_client, COMMON_SERVER_URL, ATLAS_SERVER_URL

__all__ = [
    "MCPClient",
    "get_mcp_client",
    "COMMON_SERVER_URL",
    "ATLAS_SERVER_URL",
]
