"""Bigtool Picker - Orchestrator for MCP servers.

BigtoolPicker acts as the main orchestrator that routes tool requests
to the appropriate MCP server (COMMON or ATLAS) based on capability.
"""
import asyncio
from typing import Optional, Any
from ..utils.logger import get_logger
from ..mcp.client import MCPClient


class BigtoolPicker:
    """
    Singleton orchestrator for MCP server tools.
    
    BigtoolPicker manages tool selection and routes execution requests
    to the appropriate MCP server (COMMON for internal ops, ATLAS for external).
    """
    
    _instance: Optional["BigtoolPicker"] = None
    
    # Tool pools organized by capability
    POOLS = {
        "ocr": ["google_vision", "aws_textract", "tesseract"],
        "enrichment": ["clearbit", "people_data_labs", "vendor_db"],
        "erp_connector": ["sap_sandbox", "netsuite", "mock_erp"],
        "db": ["postgres", "sqlite", "dynamodb"],
        "email": ["sendgrid", "ses", "smartlead"],
        "storage": ["s3", "gcs", "local_fs"],
    }
    
    # Mapping capabilities to MCP tools
    CAPABILITY_TO_MCP_TOOL = {
        # OCR and parsing
        "ocr": "extract_ocr",
        "parsing": "parse_line_items",
        
        # Enrichment and normalization
        "enrichment": "enrich_vendor",
        "normalize": "normalize_vendor",
        
        # ERP operations
        "erp_connector": "fetch_po_data",
        "po_data": "fetch_po_data",
        "grn_data": "fetch_grn_data",
        
        # Storage and database
        "storage": "persist_invoice",
        "db": "persist_audit",
        "validation": "validate_invoice_schema",
        
        # Email and notifications
        "email": "send_notification",
        
        # Accounting and policy
        "accounting": "build_entries",
        "policy": "apply_policy",
        "matching": "compute_match",
        
        # Checkpoint operations
        "checkpoint": "create_checkpoint",
        "payment": "schedule_payment",
    }
    
    # Simulated tool availability (in production: real health checks)
    AVAILABILITY = {
        # OCR tools
        "google_vision": True,
        "aws_textract": True,
        "tesseract": True,
        
        # Enrichment tools
        "clearbit": True,
        "people_data_labs": True,
        "vendor_db": True,
        
        # ERP connectors
        "sap_sandbox": False,  # Simulating unavailable
        "netsuite": False,     # Simulating unavailable
        "mock_erp": True,
        
        # Databases
        "postgres": True,
        "sqlite": True,
        "dynamodb": False,
        
        # Email providers
        "sendgrid": True,
        "ses": True,
        "smartlead": False,
        
        # Storage
        "s3": True,
        "gcs": True,
        "local_fs": True,
    }
    
    # Tool priorities (lower is better)
    PRIORITIES = {
        # OCR - ordered by accuracy
        "google_vision": 1,
        "aws_textract": 2,
        "tesseract": 3,
        
        # Enrichment - ordered by data quality
        "clearbit": 1,
        "people_data_labs": 2,
        "vendor_db": 3,
        
        # ERP - ordered by preference
        "sap_sandbox": 1,
        "netsuite": 2,
        "mock_erp": 3,
        
        # DB - ordered by preference
        "postgres": 1,
        "sqlite": 2,
        "dynamodb": 3,
        
        # Email - ordered by reliability
        "sendgrid": 1,
        "ses": 2,
        "smartlead": 3,
        
        # Storage - ordered by preference
        "s3": 1,
        "gcs": 2,
        "local_fs": 3,
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._mcp_client: Optional[MCPClient] = None
        self.logger = get_logger("bigtool")
        self._initialized = True
    
    @property
    def mcp_client(self) -> MCPClient:
        """Get or create MCP client instance."""
        if self._mcp_client is None:
            self._mcp_client = MCPClient()
        return self._mcp_client
    
    async def execute(
        self,
        capability: str,
        params: dict[str, Any] = None,
        context: dict = None
    ) -> dict[str, Any]:
        """
        Execute a capability via MCP server.
        
        This is the main orchestration method that:
        1. Selects the best tool for the capability
        2. Maps capability to MCP tool
        3. Routes request to appropriate MCP server
        4. Returns the result
        
        Args:
            capability: Required capability (e.g., "ocr", "enrichment", "validation")
            params: Parameters to pass to the MCP tool
            context: Optional context for tool selection
            
        Returns:
            dict with execution result
        """
        params = params or {}
        context = context or {}
        
        # Map capability to MCP tool
        mcp_tool = self.CAPABILITY_TO_MCP_TOOL.get(capability)
        if not mcp_tool:
            self.logger.error(f"No MCP tool mapping for capability: {capability}")
            return {
                "success": False,
                "error": f"No MCP tool mapping for capability: {capability}",
                "capability": capability
            }
        
        # Select best tool from pool (for logging/context)
        selection = self.select(capability, context)
        
        self.logger.info(
            f"Executing capability: {capability} via MCP tool: {mcp_tool}",
            extra={"extra": {
                "capability": capability,
                "mcp_tool": mcp_tool,
                "selected_implementation": selection.get("selected_tool"),
                "params": params
            }}
        )
        
        try:
            # Route to MCP server via client
            result = await self.mcp_client.call_tool(mcp_tool, params)
            
            return {
                "success": True,
                "capability": capability,
                "mcp_tool": mcp_tool,
                "selected_implementation": selection.get("selected_tool"),
                "result": result
            }
        except Exception as e:
            self.logger.error(f"MCP tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "capability": capability,
                "mcp_tool": mcp_tool
            }
    
    def execute_sync(
        self,
        capability: str,
        params: dict[str, Any] = None,
        context: dict = None
    ) -> dict[str, Any]:
        """
        Synchronous wrapper for execute().
        
        Use this when calling from synchronous code.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            self.execute(capability, params, context)
        )
    
    def select(
        self,
        capability: str,
        context: dict = None,
        pool_hint: list[str] = None
    ) -> dict[str, Any]:
        """
        Select the best available tool for a capability.
        
        Args:
            capability: Required capability (e.g., "ocr", "enrichment")
            context: Optional context for selection (file type, size, etc.)
            pool_hint: Optional list of preferred tools
            
        Returns:
            dict with selected tool info and selection metadata
        """
        context = context or {}
        
        # Get pool for capability
        pool = self.POOLS.get(capability, [])
        if not pool:
            self.logger.warning(f"No pool found for capability: {capability}")
            return self._create_selection_result(
                capability=capability,
                selected=None,
                reason="no_pool_found",
                pool=[]
            )
        
        # Filter by pool_hint if provided
        if pool_hint:
            pool = [t for t in pool if t in pool_hint]
        
        # Get available tools sorted by priority
        available_tools = [
            t for t in pool
            if self._is_available(t)
        ]
        
        if not available_tools:
            self.logger.warning(f"No available tools for capability: {capability}")
            return self._create_selection_result(
                capability=capability,
                selected=None,
                reason="no_available_tools",
                pool=pool
            )
        
        # Sort by priority
        available_tools.sort(key=lambda t: self.PRIORITIES.get(t, 999))
        
        # Select best available tool
        selected = available_tools[0]
        
        self.logger.info(
            f"Selected tool: {selected} for capability: {capability}",
            extra={"extra": {
                "capability": capability,
                "selected": selected,
                "pool": pool,
                "available": available_tools
            }}
        )
        
        return self._create_selection_result(
            capability=capability,
            selected=selected,
            reason=f"best_available_by_priority",
            pool=pool,
            available=available_tools
        )
    
    def _is_available(self, tool: str) -> bool:
        """Check if a tool is available."""
        return self.AVAILABILITY.get(tool, False)
    
    def _create_selection_result(
        self,
        capability: str,
        selected: Optional[str],
        reason: str,
        pool: list[str],
        available: list[str] = None
    ) -> dict[str, Any]:
        """Create standardized selection result."""
        return {
            "capability": capability,
            "selected_tool": selected,
            "pool": pool,
            "available": available or [],
            "reason": reason,
            "success": selected is not None
        }
    
    def get_pool(self, capability: str) -> list[str]:
        """Get all tools in a capability pool."""
        return self.POOLS.get(capability, [])
    
    def check_availability(self, tool: str) -> bool:
        """Check if a specific tool is available."""
        return self._is_available(tool)
    
    def set_availability(self, tool: str, available: bool) -> None:
        """Set tool availability (for testing/simulation)."""
        self.AVAILABILITY[tool] = available
    
    def list_capabilities(self) -> list[str]:
        """List all available capabilities."""
        return list(self.POOLS.keys())
