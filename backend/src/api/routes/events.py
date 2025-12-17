"""Server-Sent Events (SSE) endpoint for real-time workflow updates."""
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...services.event_emitter import get_event_emitter
from ...utils.logger import get_logger

router = APIRouter(prefix="/events", tags=["Events"])
logger = get_logger("api.events")


@router.get("/workflow/{thread_id}")
async def stream_workflow_events(thread_id: str):
    """
    Stream real-time workflow events via Server-Sent Events (SSE).
    
    This endpoint provides a live stream of:
    - Stage started/completed events
    - Log messages
    - Heartbeats (every 30s to keep connection alive)
    - Workflow completion event
    
    Usage:
        const eventSource = new EventSource(`/events/workflow/${threadId}`);
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };
    
    Args:
        thread_id: Workflow thread ID to subscribe to
    """
    logger.info(f"🔌 SSE connection requested for thread: {thread_id}")
    
    async def event_generator():
        """Generate SSE events with proper streaming."""
        emitter = get_event_emitter()
        event_count = 0
        
        async for event in emitter.subscribe(thread_id, include_history=True):
            event_count += 1
            event_type = event.get("type", "unknown")
            stage = event.get("stage", "")
            status = event.get("status", "")
            
            logger.info(f"📡 SSE event #{event_count}: {event_type} | {stage} → {status}")
            
            # Format as SSE with event type
            event_data = json.dumps(event)
            # Add a small delay to ensure proper streaming (not buffering)
            await asyncio.sleep(0.01)
            yield f"data: {event_data}\n\n"
            
            # Stop if workflow complete
            if status == "workflow_complete":
                logger.info(f"🏁 SSE stream ending for thread: {thread_id} after {event_count} events")
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Type": "text/event-stream",
        }
    )


@router.get("/health")
async def events_health():
    """Check if SSE endpoint is healthy."""
    return {"status": "healthy", "service": "sse_events"}
