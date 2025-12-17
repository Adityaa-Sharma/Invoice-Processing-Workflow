"""FastAPI dependencies for dependency injection."""
from functools import lru_cache
from typing import Generator

from sqlalchemy.orm import Session

from ..db.session import SessionLocal, get_db
from ..db.checkpoint_store import get_checkpointer
from ..graph.workflow import create_invoice_workflow
from ..tools.bigtool_picker import BigtoolPicker
from ..tools.mcp_router import MCPRouter


@lru_cache()
def get_bigtool() -> BigtoolPicker:
    """
    Get BigtoolPicker instance (cached singleton).
    
    Returns:
        BigtoolPicker instance
    """
    return BigtoolPicker()


@lru_cache()
def get_mcp_router() -> MCPRouter:
    """
    Get MCPRouter instance (cached singleton).
    
    Returns:
        MCPRouter instance
    """
    return MCPRouter()


async def get_workflow(use_memory: bool = False):
    """
    Get compiled workflow instance.
    
    Args:
        use_memory: If True, use in-memory checkpointer (for testing)
        
    Returns:
        Compiled StateGraph workflow (as async context manager if using DB)
    """
    if use_memory:
        checkpointer = get_memory_checkpointer()
        return create_invoice_workflow(checkpointer=checkpointer)
    else:
        # Return the sync checkpointer version for simple cases
        checkpointer = get_checkpointer()
        return create_invoice_workflow(checkpointer=checkpointer)


def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session dependency.
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
