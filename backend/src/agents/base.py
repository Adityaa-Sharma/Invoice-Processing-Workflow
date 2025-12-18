"""Base agent class for all workflow agents."""
from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING
from ..utils.logger import get_logger, create_audit_entry
from ..tools.bigtool_picker import BigtoolPicker
from ..services.llm_service import invoke_agent

if TYPE_CHECKING:
    from ..graph.state import InvoiceWorkflowState


class BaseAgent(ABC):
    """
    Abstract base class for all workflow agents.
    
    Provides common functionality and enforces interface for
    all stage-specific agents in the invoice processing workflow.
    
    Features:
    - BigtoolPicker integration for dynamic tool selection (True MCP Protocol)
    - LLM integration for intelligent processing
    - MCP server routing via BigtoolPicker
    """
    
    def __init__(self, name: str, config: dict = None):
        """
        Initialize base agent.
        
        Args:
            name: Agent name (e.g., "IngestAgent")
            config: Optional configuration dict
        """
        self.name = name
        self.config = config or {}
        self.logger = get_logger(f"agent.{name.lower()}")
        self._bigtool: Optional[BigtoolPicker] = None
    
    @property
    def bigtool(self) -> BigtoolPicker:
        """Get BigtoolPicker instance (singleton)."""
        if self._bigtool is None:
            self._bigtool = BigtoolPicker()
        return self._bigtool
    
    async def execute_with_bigtool(
        self,
        capability: str,
        params: dict[str, Any] = None,
        context: dict = None
    ) -> dict[str, Any]:
        """
        Execute a capability via BigtoolPicker -> MCP server.
        
        This routes the request through:
        1. BigtoolPicker (selects best tool from pool)
        2. MCPClient (routes to COMMON or ATLAS server)
        3. MCP Server (executes the tool)
        
        Args:
            capability: Required capability (e.g., "ocr", "enrichment")
            params: Parameters for the tool
            context: Context for tool selection
            
        Returns:
            dict with execution result
        """
        self.logger.info(f"Executing capability via Bigtool: {capability}")
        result = await self.bigtool.execute(capability, params, context)
        return result
    
    async def select_tool(
        self,
        capability: str,
        context: dict = None,
        use_llm: bool = True
    ) -> dict[str, Any]:
        """
        Select best tool for a capability.
        
        Uses True MCP Protocol - discovers tools from servers and
        uses LLM to select based on tool descriptions.
        
        Args:
            capability: Required capability
            context: Context for selection
            use_llm: Whether to use LLM for selection (True MCP always uses LLM)
            
        Returns:
            dict with selected tool and reasoning
        """
        if use_llm:
            # True MCP: Use LLM to select based on discovered tool descriptions
            result = await self.bigtool.select_tool_by_description(
                task=f"Select tool for {capability} capability",
                context=context or {}
            )
            return result
        else:
            # Fallback to capability mapping
            return self.bigtool.select(capability, context)
    
    async def invoke_llm(
        self,
        stage: str,
        task: str,
        context: dict[str, Any],
        output_format: str = None
    ) -> dict[str, Any]:
        """
        Invoke LLM for intelligent processing.
        
        Args:
            stage: Current workflow stage
            task: Task description
            context: Context data
            output_format: Expected output format
            
        Returns:
            dict with LLM response
        """
        return await invoke_agent(stage, task, context, output_format)
    
    @abstractmethod
    async def execute(self, state: "InvoiceWorkflowState") -> dict[str, Any]:
        """
        Execute the agent's logic.
        
        Args:
            state: Current workflow state
            
        Returns:
            dict: State updates to merge into workflow state
        """
        pass
    
    def validate_input(self, state: "InvoiceWorkflowState") -> bool:
        """
        Validate required input fields exist.
        
        Override in subclass for specific validation.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if valid, False otherwise
        """
        return True
    
    def get_required_fields(self) -> list[str]:
        """
        Get list of required state fields for this agent.
        
        Override in subclass to specify requirements.
        
        Returns:
            List of required field names
        """
        return []
    
    def log_execution(
        self,
        stage: str,
        action: str,
        result: dict[str, Any],
        bigtool_selection: dict = None
    ) -> None:
        """
        Standard logging for agent execution.
        
        Args:
            stage: Current workflow stage
            action: Action performed
            result: Execution result
            bigtool_selection: Optional bigtool selection info
        """
        log_data = {
            "stage": stage,
            "action": action,
            "agent": self.name,
        }
        
        if bigtool_selection:
            log_data["bigtool"] = bigtool_selection
        
        self.logger.info(
            f"Agent executed: {action}",
            extra={"extra": log_data}
        )
    
    def create_audit_entry(
        self,
        stage: str,
        action: str,
        details: dict = None
    ) -> dict:
        """
        Create audit log entry for this agent's action.
        
        Args:
            stage: Current workflow stage
            action: Action performed
            details: Additional details
            
        Returns:
            Audit log entry dict
        """
        return create_audit_entry(stage, action, details)
    
    def handle_error(
        self,
        stage: str,
        error: Exception,
        state: "InvoiceWorkflowState"
    ) -> dict[str, Any]:
        """
        Handle error and return error state updates.
        
        Args:
            stage: Current workflow stage
            error: Exception that occurred
            state: Current workflow state
            
        Returns:
            State updates with error info
        """
        self.logger.error(
            f"Error in {stage}: {str(error)}",
            extra={"extra": {"stage": stage, "error": str(error)}}
        )
        
        return {
            "current_stage": stage,
            "status": "FAILED",
            "error": str(error),
            "error_log": [{
                "stage": stage,
                "error": str(error),
                "agent": self.name,
            }]
        }
