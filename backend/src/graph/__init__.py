"""Graph module for LangGraph workflow."""
from .state import InvoiceWorkflowState, create_initial_state

# Lazy imports to avoid circular dependencies
def get_workflow():
    """Get workflow factory function."""
    from .workflow import create_invoice_workflow
    return create_invoice_workflow

__all__ = [
    "InvoiceWorkflowState",
    "create_initial_state",
    "get_workflow",
]
