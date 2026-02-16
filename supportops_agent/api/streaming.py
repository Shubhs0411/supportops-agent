"""Streaming support for real-time agent responses."""

import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi.responses import StreamingResponse

from supportops_agent.agents.graph import create_agent_graph
from supportops_agent.agents.schemas import AgentState

logger = logging.getLogger(__name__)


async def stream_agent_execution(
    ticket_data: Dict[str, Any],
    ticket_id: str = None,
    request_id: str = None,
) -> AsyncGenerator[str, None]:
    """
    Stream agent execution in real-time.

    Yields JSON lines with node execution updates.
    """
    import uuid

    if not request_id:
        request_id = str(uuid.uuid4())

    # Initialize state
    initial_state = AgentState(
        raw_ticket=ticket_data,
        ticket_id=ticket_id or f"TICKET-{uuid.uuid4().hex[:8]}",
        request_id=request_id,
    )

    # Create graph
    graph = create_agent_graph()

    # Stream execution
    try:
        async for event in graph.astream(initial_state.model_dump()):
            # Yield each node's output as it completes
            for node_name, node_output in event.items():
                yield f"data: {json.dumps({'node': node_name, 'state': node_output})}\n\n"

        # Final result
        final_state = graph.invoke(initial_state.model_dump())
        yield f"data: {json.dumps({'type': 'complete', 'result': final_state.get('final_output', {})})}\n\n"

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


def create_streaming_response(ticket_data: Dict[str, Any], **kwargs) -> StreamingResponse:
    """Create a Server-Sent Events streaming response."""
    return StreamingResponse(
        stream_agent_execution(ticket_data, **kwargs),
        media_type="text/event-stream",
    )
