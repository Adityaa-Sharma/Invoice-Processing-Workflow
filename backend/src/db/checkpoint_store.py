"""Checkpoint store for LangGraph workflow persistence."""
import sqlite3
from typing import Optional
from contextlib import asynccontextmanager

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.memory import MemorySaver

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger("checkpoint_store")

# Global singleton for sync SqliteSaver (thread-safe)
_sync_checkpointer: Optional[SqliteSaver] = None
_sync_connection: Optional[sqlite3.Connection] = None


def get_sync_checkpointer(db_url: str = None) -> SqliteSaver:
    """
    Get synchronous SqliteSaver for state persistence.
    Uses a singleton pattern with thread-safe connection.
    """
    global _sync_checkpointer, _sync_connection
    
    if _sync_checkpointer is not None:
        return _sync_checkpointer
    
    db_url = db_url or settings.DATABASE_URL
    logger.info(f"Creating sync checkpoint saver for: {db_url}")
    
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        
        # Create thread-safe connection
        _sync_connection = sqlite3.connect(db_path, check_same_thread=False)
        _sync_checkpointer = SqliteSaver(_sync_connection)
        
        logger.info(f"SqliteSaver created for: {db_path}")
        return _sync_checkpointer
    
    else:
        logger.warning(f"Unsupported DB URL: {db_url}, using MemorySaver")
        return MemorySaver()


@asynccontextmanager
async def get_async_checkpointer(db_url: str = None):
    """
    Async context manager for AsyncSqliteSaver.
    
    Usage:
        async with get_async_checkpointer() as checkpointer:
            workflow = create_workflow(checkpointer)
            await workflow.ainvoke(...)
    """
    db_url = db_url or settings.DATABASE_URL
    
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        # Ensure absolute path
        if not db_path.startswith("/") and not db_path[1:2] == ":":
            import os
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", db_path)
            db_path = os.path.abspath(db_path)
        
        logger.info(f"Creating async checkpoint saver for: {db_path}")
        
        async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
            logger.info(f"AsyncSqliteSaver initialized, type: {type(saver)}")
            yield saver
    else:
        logger.warning(f"Unsupported DB URL: {db_url}, using MemorySaver")
        yield MemorySaver()


# For backwards compatibility - use sync version
def get_checkpointer(db_url: str = None) -> SqliteSaver:
    """Get checkpoint saver (sync version for compatibility)."""
    return get_sync_checkpointer(db_url)


def get_memory_checkpointer() -> MemorySaver:
    """
    Get in-memory checkpoint saver for testing.
    
    Returns:
        MemorySaver instance (no persistence)
    """
    logger.info("Creating in-memory checkpoint saver")
    return MemorySaver()


class CheckpointManager:
    """
    Manager for workflow checkpoints.
    
    Provides higher-level operations on top of LangGraph's checkpointer.
    Uses the sync SqliteSaver for simplicity.
    """
    
    def __init__(self, checkpointer: Optional[SqliteSaver] = None):
        self.checkpointer = checkpointer or get_sync_checkpointer()
        self.logger = get_logger("checkpoint_manager")
    
    def get_checkpoint_state(self, thread_id: str) -> Optional[dict]:
        """
        Get the current checkpoint state for a thread.
        
        Args:
            thread_id: Workflow thread ID
            
        Returns:
            State dict if checkpoint exists, None otherwise
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = self.checkpointer.get(config)
            
            if checkpoint:
                return checkpoint.get("channel_values", {})
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting checkpoint for thread {thread_id}: {e}")
            return None
    
    def list_threads(self) -> list[str]:
        """
        List all thread IDs with checkpoints.
        
        Returns:
            List of thread IDs
        """
        try:
            # This depends on SqliteSaver implementation
            # For now, return empty list as this requires direct DB query
            return []
        except Exception as e:
            self.logger.error(f"Error listing threads: {e}")
            return []
