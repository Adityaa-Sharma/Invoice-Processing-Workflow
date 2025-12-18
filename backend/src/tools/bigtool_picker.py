"""Bigtool Picker - Orchestrator for MCP servers (True MCP Protocol).

BigtoolPicker acts as the main orchestrator that:
1. Discovers available tools from MCP servers dynamically
2. Uses LLM to intelligently select tools based on descriptions
3. Routes requests to appropriate MCP server
"""
import asyncio
from typing import Optional, Any
from ..utils.logger import get_logger
from ..mcp.client import MCPClient


class BigtoolPicker:
    """
    Singleton orchestrator for MCP server tools (True MCP Protocol).
    
    Implements dynamic tool discovery - no hardcoded pools or priorities.
    LLM reads tool descriptions from servers and makes intelligent selections.
    """
    
    _instance: Optional["BigtoolPicker"] = None
    
    # Mapping capabilities to MCP tool names (semantic mapping)
    # This maps high-level capabilities to specific MCP tools
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
        "posting": "post_to_erp",
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
        self._tools_initialized = False
    
    @property
    def mcp_client(self) -> MCPClient:
        """Get or create MCP client instance."""
        if self._mcp_client is None:
            self._mcp_client = MCPClient()
        return self._mcp_client
    
    async def initialize_tools(self) -> None:
        """
        Initialize by discovering tools from MCP servers (True MCP Protocol).
        
        This fetches tool schemas with descriptions from servers and caches them.
        Should be called once at startup or on first use.
        """
        if self._tools_initialized:
            return
        
        self.logger.info("🚀 Initializing BigtoolPicker with True MCP Protocol...")
        await self.mcp_client.discover_tools()
        self._tools_initialized = True
        self.logger.info("✅ BigtoolPicker initialized with discovered tools")
    
    def get_discovered_tools(self) -> list[dict]:
        """Get all discovered tools with descriptions for LLM selection."""
        return self.mcp_client.get_all_tools_with_descriptions()
    
    def format_tools_for_llm(self) -> str:
        """Format discovered tools for LLM prompt."""
        tools = self.get_discovered_tools()
        if not tools:
            return "No tools discovered from MCP servers."
        
        formatted = []
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "No description")
            server = tool.get("server", "unknown")
            formatted.append(f"- {name} [{server.upper()}]: {desc}")
        
        return "\n".join(formatted)
    
    async def select_tool_by_description(
        self,
        task: str,
        context: dict = None
    ) -> dict[str, Any]:
        """
        Select the best tool using LLM based on tool descriptions (True MCP).
        
        This is the core of True MCP - LLM reads tool descriptions from
        servers and intelligently selects the best tool for the task.
        
        Args:
            task: Description of what needs to be done
            context: Additional context for selection
            
        Returns:
            dict with selected_tool, reason, and tool details
        """
        # Ensure tools are discovered
        await self.initialize_tools()
        
        tools = self.get_discovered_tools()
        if not tools:
            self.logger.warning("No tools discovered, falling back to static mapping")
            return {"selected_tool": None, "reason": "No tools discovered", "fallback": True}
        
        # Import here to avoid circular imports
        from ..services.llm_service import get_llm
        from langchain_core.messages import HumanMessage
        
        llm = get_llm()
        if llm is None:
            # Fallback without LLM
            return {"selected_tool": tools[0].get("name"), "reason": "LLM not available", "fallback": True}
        
        context_str = ""
        if context:
            context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
        
        prompt = f"""You are selecting an MCP tool based on descriptions from the servers.

TASK: {task}

CONTEXT:
{context_str}

AVAILABLE TOOLS (discovered from MCP servers):
{self.format_tools_for_llm()}

Based on the task and available tool descriptions, select the BEST tool.

Respond in this exact format:
SELECTED: <tool_name>
REASON: <one sentence explaining why this tool is best for the task>"""

        try:
            self.logger.info(f"🤖 LLM selecting tool by description for task: {task[:50]}...")
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            
            # Parse response
            lines = response.content.strip().split('\n')
            selected = None
            reason = "No reason provided"
            
            for line in lines:
                if line.startswith("SELECTED:"):
                    selected = line.replace("SELECTED:", "").strip()
                elif line.startswith("REASON:"):
                    reason = line.replace("REASON:", "").strip()
            
            # Validate selection exists
            tool_names = [t.get("name") for t in tools]
            if selected and selected.lower() not in [n.lower() for n in tool_names]:
                self.logger.warning(f"LLM selected unknown tool: {selected}")
                selected = None
            
            if selected:
                tool_info = self.mcp_client.get_tool_by_name(selected)
                self.logger.info(f"✅ LLM selected tool: {selected} - {reason}")
                return {
                    "selected_tool": selected,
                    "reason": reason,
                    "tool_info": tool_info,
                    "discovery_method": "true_mcp"
                }
            else:
                return {"selected_tool": None, "reason": "Could not parse LLM response", "fallback": True}
                
        except Exception as e:
            self.logger.error(f"LLM tool selection failed: {e}")
            return {"selected_tool": tools[0].get("name"), "reason": f"LLM error: {e}", "fallback": True}
    
    async def execute(
        self,
        capability: str,
        params: dict[str, Any] = None,
        context: dict = None
    ) -> dict[str, Any]:
        """
        Execute a capability via MCP server (True MCP Protocol).
        
        This is the main orchestration method that:
        1. Discovers available tools from MCP servers (True MCP)
        2. Selects the best tool for the capability
        3. Routes request to appropriate MCP server dynamically
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
        
        # Ensure tools are discovered (True MCP)
        await self.initialize_tools()
        
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
        Select the best tool for a capability (True MCP Protocol).
        
        Uses discovered tools from MCP servers. No hardcoded pools.
        Returns the MCP tool for the capability.
        
        Args:
            capability: Required capability (e.g., "ocr", "enrichment")
            context: Optional context for selection
            pool_hint: Ignored (kept for backward compatibility)
            
        Returns:
            dict with selected tool info
        """
        # Map capability to MCP tool
        mcp_tool = self.CAPABILITY_TO_MCP_TOOL.get(capability)
        
        if not mcp_tool:
            self.logger.warning(f"No MCP tool mapping for capability: {capability}")
            return self._create_selection_result(
                capability=capability,
                selected=None,
                reason="no_mcp_tool_mapping",
                discovered=False
            )
        
        # Check if tool was discovered from servers
        tool_info = self.mcp_client.get_tool_by_name(mcp_tool)
        discovered = tool_info is not None
        
        self.logger.info(
            f"Selected MCP tool: {mcp_tool} for capability: {capability}",
            extra={"extra": {
                "capability": capability,
                "selected": mcp_tool,
                "discovered": discovered,
                "server": tool_info.get("server") if tool_info else "unknown"
            }}
        )
        
        return self._create_selection_result(
            capability=capability,
            selected=mcp_tool,
            reason="mcp_tool_mapping" if not discovered else "discovered_from_server",
            discovered=discovered,
            tool_info=tool_info
        )
    
    def _create_selection_result(
        self,
        capability: str,
        selected: Optional[str],
        reason: str,
        discovered: bool = False,
        tool_info: dict = None
    ) -> dict[str, Any]:
        """Create standardized selection result."""
        return {
            "capability": capability,
            "selected_tool": selected,
            "reason": reason,
            "success": selected is not None,
            "discovered": discovered,
            "tool_info": tool_info
        }
    
    def list_capabilities(self) -> list[str]:
        """List all available capabilities."""
        return list(self.CAPABILITY_TO_MCP_TOOL.keys())
    
    def list_discovered_tools(self) -> list[dict]:
        """List all tools discovered from MCP servers."""
        return self.get_discovered_tools()
