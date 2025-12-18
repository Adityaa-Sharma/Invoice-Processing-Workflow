"""Event Emitter Service for Real-Time Stage Updates.

Provides Server-Sent Events (SSE) capability for streaming
workflow stage updates to the frontend in real-time.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator
from collections import defaultdict

from ..utils.logger import get_logger

logger = get_logger("event_emitter")


class WorkflowEventEmitter:
    """
    Singleton event emitter for broadcasting workflow stage updates.
    
    Uses asyncio queues to manage per-thread event streams.
    """
    
    _instance: Optional["WorkflowEventEmitter"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Thread ID → list of subscriber queues
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        # Thread ID → event history (for late subscribers)
        self._event_history: dict[str, list[dict]] = defaultdict(list)
        self._initialized = True
        logger.info("WorkflowEventEmitter initialized")
    
    async def emit(
        self,
        thread_id: str,
        stage: str,
        status: str,
        data: dict = None
    ) -> None:
        """
        Emit a stage update event to all subscribers for a thread.
        
        Args:
            thread_id: Workflow thread ID
            stage: Current stage name
            status: Stage status (started, completed, failed, paused)
            data: Additional event data
        """
        event = {
            "type": "stage_update",
            "thread_id": thread_id,
            "stage": stage,
            "status": status,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store in history
        self._event_history[thread_id].append(event)
        
        logger.info(
            f"📡 Event emitted: {stage} → {status}",
            extra={"extra": {"thread_id": thread_id, "stage": stage, "status": status}}
        )
        
        # Broadcast to all subscribers
        subscribers = self._subscribers.get(thread_id, [])
        for queue in subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Failed to emit event: {e}")
    
    async def emit_log(
        self,
        thread_id: str,
        level: str,
        message: str,
        details: dict = None,
        stage: str = None,
        log_type: str = None
    ) -> None:
        """
        Emit a log event to subscribers.
        
        Args:
            thread_id: Workflow thread ID
            level: Log level (info, warning, error)
            message: Log message
            details: Additional log details
            stage: Current stage (for grouping)
            log_type: Log type (info, tool_call, llm_call, result, etc.)
        """
        event = {
            "type": "log",
            "thread_id": thread_id,
            "level": level,
            "message": message,
            "stage": stage,
            "log_type": log_type or "info",
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._event_history[thread_id].append(event)
        
        subscribers = self._subscribers.get(thread_id, [])
        for queue in subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Failed to emit log event: {e}")
    
    async def emit_tool_call(
        self,
        thread_id: str,
        stage: str,
        tool_name: str,
        server: str,
        params: dict = None,
        result: dict = None,
        status: str = "started"
    ) -> None:
        """
        Emit a tool call event for tracking MCP tool invocations.
        
        Args:
            thread_id: Workflow thread ID
            stage: Current workflow stage
            tool_name: Name of the tool being called
            server: MCP server (COMMON or ATLAS)
            params: Tool parameters
            result: Tool result (if completed)
            status: Call status (started, completed, failed)
        """
        event = {
            "type": "tool_call",
            "thread_id": thread_id,
            "stage": stage,
            "tool_name": tool_name,
            "server": server,
            "params": params or {},
            "result": result or {},
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._event_history[thread_id].append(event)
        
        logger.info(
            f"🔧 Tool call: {tool_name}@{server} → {status}",
            extra={"extra": {"thread_id": thread_id, "tool": tool_name, "server": server}}
        )
        
        subscribers = self._subscribers.get(thread_id, [])
        for queue in subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Failed to emit tool_call event: {e}")
    
    async def subscribe(
        self,
        thread_id: str,
        include_history: bool = True
    ) -> AsyncGenerator[dict, None]:
        """
        Subscribe to events for a specific thread.
        
        Args:
            thread_id: Workflow thread ID to subscribe to
            include_history: Whether to replay past events
            
        Yields:
            Event dicts as they occur
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[thread_id].append(queue)
        
        logger.info(f"New subscriber for thread: {thread_id}")
        
        workflow_already_complete = False
        
        try:
            # Send history first if requested
            if include_history:
                for event in self._event_history.get(thread_id, []):
                    yield event
                    # Check if workflow already completed in history
                    if event.get("type") == "stage_update" and event.get("status") == "workflow_complete":
                        workflow_already_complete = True
            
            # Send welcome event
            yield {
                "type": "connected",
                "thread_id": thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # If workflow already complete from history, don't wait for more events
            if workflow_already_complete:
                logger.info(f"Workflow already complete for thread: {thread_id}, closing SSE")
                return
            
            # Stream new events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                    
                    # Check if workflow completed
                    if event.get("type") == "stage_update" and event.get("status") == "workflow_complete":
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
        finally:
            # Cleanup subscriber
            if queue in self._subscribers.get(thread_id, []):
                self._subscribers[thread_id].remove(queue)
            logger.info(f"Subscriber disconnected for thread: {thread_id}")
    
    def clear_thread(self, thread_id: str) -> None:
        """Clear event history for a thread."""
        if thread_id in self._event_history:
            del self._event_history[thread_id]
        if thread_id in self._subscribers:
            del self._subscribers[thread_id]


# Singleton instance
_emitter: Optional[WorkflowEventEmitter] = None


def get_event_emitter() -> WorkflowEventEmitter:
    """Get the global event emitter instance."""
    global _emitter
    if _emitter is None:
        _emitter = WorkflowEventEmitter()
    return _emitter


async def emit_stage_started(thread_id: str, stage: str, details: dict = None) -> None:
    """Convenience function to emit stage started event."""
    emitter = get_event_emitter()
    await emitter.emit(thread_id, stage, "started", details)


async def emit_stage_completed(thread_id: str, stage: str, result: dict = None) -> None:
    """Convenience function to emit stage completed event."""
    emitter = get_event_emitter()
    await emitter.emit(thread_id, stage, "completed", result)


async def emit_stage_failed(thread_id: str, stage: str, error: str) -> None:
    """Convenience function to emit stage failed event."""
    emitter = get_event_emitter()
    await emitter.emit(thread_id, stage, "failed", {"error": error})


async def emit_workflow_complete(thread_id: str, final_status: str, data: dict = None) -> None:
    """Convenience function to emit workflow complete event."""
    emitter = get_event_emitter()
    await emitter.emit(thread_id, "WORKFLOW", "workflow_complete", {
        "final_status": final_status,
        **(data or {})
    })


async def emit_log_message(
    thread_id: str,
    level: str,
    message: str,
    details: dict = None,
    stage: str = None,
    log_type: str = None
) -> None:
    """Convenience function to emit log message."""
    emitter = get_event_emitter()
    await emitter.emit_log(thread_id, level, message, details, stage, log_type)


async def emit_tool_call(
    thread_id: str,
    stage: str,
    tool_name: str,
    server: str,
    params: dict = None,
    result: dict = None,
    status: str = "started"
) -> None:
    """Convenience function to emit tool call event."""
    emitter = get_event_emitter()
    await emitter.emit_tool_call(thread_id, stage, tool_name, server, params, result, status)
