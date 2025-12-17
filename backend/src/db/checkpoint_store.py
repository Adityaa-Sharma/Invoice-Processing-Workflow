"""Checkpoint store for LangGraph workflow persistence."""
import sqlite3
import os
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger("checkpoint_store")

# Global singletons
_sync_checkpointer: Optional[SqliteSaver] = None
_sync_connection: Optional[sqlite3.Connection] = None
_memory_checkpointer: Optional[MemorySaver] = None


def _get_db_path(db_url: str = None) -> str:
    """Get absolute database path from URL."""
    db_url = db_url or settings.DATABASE_URL
    db_path = db_url.replace("sqlite:///", "")
    
    # Ensure absolute path
    if not os.path.isabs(db_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(base_dir, db_path)
    
    return os.path.abspath(db_path)


def get_checkpointer() -> MemorySaver:
    """
    Get MemorySaver for workflow persistence.
    Uses singleton pattern for consistent state across requests.
    
    Note: Using MemorySaver for demo. For production, use PostgresSaver.
    """
    global _memory_checkpointer
    
    if _memory_checkpointer is not None:
        return _memory_checkpointer
    
    logger.info("Creating MemorySaver checkpoint store")
    _memory_checkpointer = MemorySaver()
    
    logger.info("MemorySaver created and ready")
    return _memory_checkpointer


# Aliases
def get_async_checkpointer() -> MemorySaver:
    """Get checkpointer for async workflows (uses MemorySaver which supports both)."""
    return get_checkpointer()


def get_sync_checkpointer(db_url: str = None) -> SqliteSaver:
    """
    Get sync SqliteSaver for state persistence.
    Uses a singleton pattern with thread-safe connection.
    For async workflows, use get_async_checkpointer instead.
    """
    global _sync_checkpointer, _sync_connection
    
    if _sync_checkpointer is not None:
        return _sync_checkpointer
    
    db_path = _get_db_path(db_url)
    logger.info(f"Creating SqliteSaver checkpoint store for: {db_path}")
    
    # Create thread-safe connection
    _sync_connection = sqlite3.connect(db_path, check_same_thread=False)
    _sync_checkpointer = SqliteSaver(_sync_connection)
    
    logger.info(f"SqliteSaver created and ready for: {db_path}")
    return _sync_checkpointer


# Alias for backwards compatibility
def get_sync_checkpointer(db_url: str = None) -> SqliteSaver:
    """Alias for get_checkpointer."""
    return get_checkpointer(db_url)


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
