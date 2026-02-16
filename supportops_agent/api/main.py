"""FastAPI main application with OpenTelemetry instrumentation."""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel

from supportops_agent.agents.graph import run_agent
from supportops_agent.api.rate_limit import RateLimitMiddleware
from supportops_agent.api.streaming import create_streaming_response
from supportops_agent.config import settings
from supportops_agent.db import Ticket, get_db, init_db
from supportops_agent.feedback import get_feedback_collector
from supportops_agent.logging import setup_logging
from supportops_agent.metrics import get_metrics

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Setup OpenTelemetry (optional, only if endpoint configured)
# Check if endpoint is set and not empty/comment
otel_endpoint = settings.otel_exporter_otlp_endpoint
if otel_endpoint and otel_endpoint.strip() and not otel_endpoint.strip().startswith("#"):
    try:
        trace.set_tracer_provider(TracerProvider())
        otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint.strip(), insecure=True)
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        logger.info(f"OpenTelemetry configured: {otel_endpoint}")
    except Exception as e:
        logger.warning(f"OpenTelemetry setup failed (optional): {e}")
        # Continue without tracing
else:
    logger.info("OpenTelemetry disabled (no endpoint configured)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed (optional): {e}")
        logger.info("Continuing without database persistence")
    logger.info("Application startup complete")
    yield
    # Shutdown
    logger.info("Application shutdown")


app = FastAPI(
    title="SupportOps Agent API",
    description="Production-grade AI observability reference project for customer support",
    version="0.1.0",
    lifespan=lifespan,
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Add rate limiting (60 requests per minute)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)


@app.get("/")
async def root():
    """Root endpoint - redirects to API docs."""
    return RedirectResponse(url="/docs")


# Request/Response models
class TicketCreate(BaseModel):
    """Ticket creation request."""

    content: str
    ticket_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TriageRequest(BaseModel):
    """Agent triage request."""

    ticket_id: Optional[str] = None
    ticket_data: Optional[Dict[str, Any]] = None


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "supportops-agent"}


@app.get("/metrics")
async def get_metrics_endpoint():
    """Get metrics for monitoring."""
    metrics = get_metrics()
    return metrics.get_stats()


@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    from supportops_agent.cache import get_cache

    cache = get_cache()
    return cache.stats()


@app.post("/v1/tickets")
async def create_ticket(ticket: TicketCreate):
    """Create a new support ticket."""
    request_id = str(uuid.uuid4())
    ticket_id = ticket.ticket_id or f"TICKET-{uuid.uuid4().hex[:8]}"

    try:
        with get_db() as db:
            db_ticket = Ticket(
                ticket_id=ticket_id,
                raw_content=ticket.content if settings.store_raw else None,
                sanitized_content=ticket.content,  # Will be sanitized by agent
            )
            db.add(db_ticket)
            db.commit()

        return {
            "ticket_id": ticket_id,
            "request_id": request_id,
            "status": "created",
        }
    except Exception as e:
        logger.error(f"Failed to create ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/agent/triage")
async def triage_ticket(request: TriageRequest):
    """Run agent triage on a ticket."""
    with get_metrics().timer("api.triage.total"):
        request_id = str(uuid.uuid4())

    try:
        # Get ticket data
        if request.ticket_id:
            with get_db() as db:
                db_ticket = db.query(Ticket).filter(Ticket.ticket_id == request.ticket_id).first()
                if not db_ticket:
                    raise HTTPException(status_code=404, detail="Ticket not found")
                ticket_data = {
                    "content": db_ticket.sanitized_content,
                    "ticket_id": db_ticket.ticket_id,
                }
        elif request.ticket_data:
            ticket_data = request.ticket_data
        else:
            raise HTTPException(status_code=400, detail="Either ticket_id or ticket_data required")

        # Run agent
        with get_metrics().timer("api.triage.agent_execution"):
            result = run_agent(
                ticket_data=ticket_data,
                ticket_id=ticket_data.get("ticket_id"),
                request_id=request_id,
            )

        get_metrics().increment("api.triage.success")

        return {
            "request_id": request_id,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Triage failed: {e}", exc_info=True)
        get_metrics().increment("api.triage.errors")
        get_metrics().record_error("api.triage.failure", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/agent/triage/stream")
async def triage_ticket_stream(request: TriageRequest):
    """Stream agent triage execution in real-time (Server-Sent Events)."""
    request_id = str(uuid.uuid4())

    # Get ticket data
    if request.ticket_id:
        with get_db() as db:
            db_ticket = db.query(Ticket).filter(Ticket.ticket_id == request.ticket_id).first()
            if not db_ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")
            ticket_data = {
                "content": db_ticket.sanitized_content,
                "ticket_id": db_ticket.ticket_id,
            }
    elif request.ticket_data:
        ticket_data = request.ticket_data
    else:
        raise HTTPException(status_code=400, detail="Either ticket_id or ticket_data required")

    return create_streaming_response(ticket_data, ticket_id=ticket_data.get("ticket_id"), request_id=request_id)


@app.post("/v1/agent/triage/batch")
async def triage_tickets_batch(tickets: List[TriageRequest]):
    """Process multiple tickets in batch."""
    results = []

    for ticket_request in tickets:
        try:
            # Get ticket data
            if ticket_request.ticket_id:
                with get_db() as db:
                    db_ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_request.ticket_id).first()
                    if not db_ticket:
                        results.append({"ticket_id": ticket_request.ticket_id, "error": "Not found"})
                        continue
                    ticket_data = {
                        "content": db_ticket.sanitized_content,
                        "ticket_id": db_ticket.ticket_id,
                    }
            elif ticket_request.ticket_data:
                ticket_data = ticket_request.ticket_data
            else:
                results.append({"error": "Either ticket_id or ticket_data required"})
                continue

            # Run agent
            result = run_agent(ticket_data=ticket_data, ticket_id=ticket_data.get("ticket_id"))
            results.append({"ticket_id": ticket_data.get("ticket_id"), "result": result})

        except Exception as e:
            logger.error(f"Batch triage failed for ticket: {e}")
            results.append({"ticket_id": ticket_request.ticket_id or "unknown", "error": str(e)})

    return {"processed": len(results), "results": results}


@app.get("/v1/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get ticket and agent outputs."""
    try:
        with get_db() as db:
            ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")

            # Get agent runs for this ticket
            from supportops_agent.db import AgentRun

            agent_runs = db.query(AgentRun).filter(AgentRun.ticket_id == ticket_id).all()

            return {
                "ticket": ticket.to_dict(),
                "agent_runs": [run.to_dict() for run in agent_runs],
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class FeedbackRequest(BaseModel):
    """Feedback submission request."""

    agent_run_id: int
    feedback_type: str  # "correction", "rating", "comment"
    rating: Optional[int] = None  # 1-5
    comment: Optional[str] = None
    corrections: Optional[Dict[str, Any]] = None  # {"category": "Billing", "priority": "P2"}


@app.post("/v1/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit human feedback on an agent run."""
    feedback_collector = get_feedback_collector()

    feedback_collector.record_feedback(
        agent_run_id=feedback.agent_run_id,
        feedback_type=feedback.feedback_type,
        rating=feedback.rating,
        comment=feedback.comment,
        corrections=feedback.corrections,
    )

    get_metrics().increment("feedback.submitted", tags={"type": feedback.feedback_type})

    return {"status": "recorded", "agent_run_id": feedback.agent_run_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
