"""Checkpoint store for LangGraph workflow persistence."""
import sqlite3
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger("checkpoint_store")


def get_checkpointer(db_url: str = None) -> SqliteSaver:
    """
    Get LangGraph checkpoint saver for state persistence.
    
    Uses LangGraph's built-in SqliteSaver for checkpoint storage.
    This enables workflow pause/resume functionality.
    
    Args:
        db_url: Database URL (defaults to settings.DATABASE_URL)
        
    Returns:
        SqliteSaver instance for LangGraph checkpointing
    """
    db_url = db_url or settings.DATABASE_URL
    
    logger.info(f"Creating checkpoint saver for: {db_url}")
    
    if db_url.startswith("sqlite"):
        # Extract path from sqlite URL
        db_path = db_url.replace("sqlite:///", "")
        
        # Create connection with check_same_thread=False for async support
        conn = sqlite3.connect(db_path, check_same_thread=False)
        
        # Create and return SqliteSaver
        saver = SqliteSaver(conn)
        
        logger.info(f"SqliteSaver created for: {db_path}")
        return saver
    
    else:
        # For other databases, fall back to memory saver
        logger.warning(f"Unsupported DB URL: {db_url}, using MemorySaver")
        return MemorySaver()


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
    """
    
    def __init__(self, checkpointer: Optional[SqliteSaver] = None):
        self.checkpointer = checkpointer or get_checkpointer()
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
