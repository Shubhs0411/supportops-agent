"""Pydantic schemas for agent state and outputs."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GuardrailEvent(BaseModel):
    """Guardrail violation event."""

    event_type: str = Field(..., description="Type of guardrail event")
    severity: str = Field(..., description="Severity: info, warning, error")
    message: str = Field(..., description="Event message")
    node: Optional[str] = Field(None, description="Node where event occurred")


class ClassificationResult(BaseModel):
    """Classification output."""

    category: str = Field(
        ...,
        description="Category: Billing, Account Access, Bug, Abuse/Safety, Feature Request, Other",
    )
    priority: str = Field(..., description="Priority: P0, P1, P2, P3")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    rationale: str = Field(..., description="Reasoning for classification")


class RoutingResult(BaseModel):
    """Routing decision output."""

    queue: str = Field(
        ...,
        description="Queue: Payments, Identity, Core App, Trust&Safety, Support General",
    )
    team: str = Field(..., description="Team name")
    rationale: str = Field(..., description="Reasoning for routing")


class PolicySnippet(BaseModel):
    """Policy knowledge base snippet."""

    title: str
    snippet: str
    doc_id: str


class AgentState(BaseModel):
    """LangGraph agent state."""

    raw_ticket: Dict[str, Any] = Field(..., description="Original ticket data")
    sanitized_ticket: str = Field(default="", description="PII-redacted ticket content")
    classification_result: Optional[ClassificationResult] = None
    routing_result: Optional[RoutingResult] = None
    policy_snippets: List[PolicySnippet] = Field(default_factory=list)
    draft_response: str = Field(default="", description="Customer response draft")
    final_output: Optional[Dict[str, Any]] = None
    guardrail_events: List[GuardrailEvent] = Field(default_factory=list)
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    ticket_id: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
