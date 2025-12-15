"""Base agent class for all workflow agents."""
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING
from ..utils.logger import get_logger, create_audit_entry

if TYPE_CHECKING:
    from ..graph.state import InvoiceWorkflowState


class BaseAgent(ABC):
    """
    Abstract base class for all workflow agents.
    
    Provides common functionality and enforces interface for
    all stage-specific agents in the invoice processing workflow.
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
