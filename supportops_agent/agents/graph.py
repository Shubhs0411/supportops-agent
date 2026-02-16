"""LangGraph agent implementation with multi-step orchestration."""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

from langgraph.graph import END, StateGraph
from opentelemetry import trace

from supportops_agent.agents.guardrails import (
    detect_prompt_injection,
    redact_pii,
    verify_response_safety,
)
from supportops_agent.agents.prompts import (
    CLASSIFICATION_PROMPT,
    DRAFT_RESPONSE_PROMPT,
    ROUTING_PROMPT,
)
from supportops_agent.agents.schemas import (
    AgentState,
    ClassificationResult,
    PolicySnippet,
    RoutingResult,
)
from supportops_agent.llm.gemini import GeminiClient
from supportops_agent.metrics import get_metrics
from supportops_agent.tools import policy_search

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
metrics = get_metrics()

# Initialize Gemini client
gemini_client = GeminiClient()


def sanitize_node(state: AgentState) -> AgentState:
    """Sanitize ticket content by redacting PII."""
    with tracer.start_as_current_span("sanitize_node") as span, metrics.timer("agent.node.sanitize"):
        # Convert to dict for easier manipulation
        state_dict = state.model_dump() if isinstance(state, AgentState) else state

        raw_ticket = state_dict.get("raw_ticket", {})
        ticket_content = raw_ticket.get("content", "") or json.dumps(raw_ticket)

        # Detect prompt injection
        if detect_prompt_injection(ticket_content):
            logger.warning("Prompt injection detected in ticket")
            state_dict.setdefault("guardrail_events", []).append(
                {
                    "event_type": "prompt_injection",
                    "severity": "warning",
                    "message": "Potential prompt injection attempt detected",
                    "node": "sanitize",
                }
            )

        # Redact PII
        sanitized, events = redact_pii(ticket_content)
        state_dict["sanitized_ticket"] = sanitized

        # Add guardrail events
        for event in events:
            state_dict.setdefault("guardrail_events", []).append(event.model_dump())

        span.set_attribute("pii_redacted", len(events) > 0)
        return AgentState(**state_dict)


def classify_node(state: AgentState) -> AgentState:
    """Classify ticket using Gemini with structured output."""
    with tracer.start_as_current_span("classify_node") as span, metrics.timer("agent.node.classify"):
        # Convert to dict for easier manipulation
        state_dict = state.model_dump() if isinstance(state, AgentState) else state

        sanitized = state_dict.get("sanitized_ticket", "")

        messages = [
            {
                "role": "system",
                "content": "You are a customer support classification expert. Always respond with valid JSON.",
            },
            {
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(ticket_content=sanitized),
            },
        ]

        try:
            result = gemini_client.chat(
                messages=messages,
                response_schema=ClassificationResult,
                temperature=0.0,
            )

            classification = ClassificationResult(**result)
            state_dict["classification_result"] = classification.model_dump()

            span.set_attribute("category", classification.category)
            span.set_attribute("priority", classification.priority)
            span.set_attribute("confidence", classification.confidence)

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Fallback to rule-based classification
            classification = _rule_based_classify(sanitized)
            state_dict["classification_result"] = classification.model_dump()
            state_dict.setdefault("guardrail_events", []).append(
                {
                    "event_type": "classification_fallback",
                    "severity": "warning",
                    "message": f"LLM classification failed, used rule-based: {e}",
                    "node": "classify",
                }
            )

        return AgentState(**state_dict)


def _rule_based_classify(content: str) -> ClassificationResult:
    """Fallback rule-based classifier."""
    content_lower = content.lower()

    # Simple keyword matching
    if any(word in content_lower for word in ["refund", "charge", "billing", "payment", "subscription"]):
        category = "Billing"
        priority = "P1"
    elif any(word in content_lower for word in ["login", "password", "account", "access", "locked"]):
        category = "Account Access"
        priority = "P1"
    elif any(word in content_lower for word in ["bug", "error", "broken", "not working", "crash"]):
        category = "Bug"
        priority = "P2"
    elif any(word in content_lower for word in ["abuse", "harassment", "safety", "violation"]):
        category = "Abuse/Safety"
        priority = "P0"
    elif any(word in content_lower for word in ["feature", "request", "suggestion", "improvement"]):
        category = "Feature Request"
        priority = "P3"
    else:
        category = "Other"
        priority = "P2"

    return ClassificationResult(
        category=category,
        priority=priority,
        confidence=0.6,
        rationale="Rule-based classification fallback",
    )


def retrieve_policy_node(state: AgentState) -> AgentState:
    """Retrieve relevant policy snippets."""
    with tracer.start_as_current_span("retrieve_policy_node") as span:
        # Convert to dict for easier manipulation
        state_dict = state.model_dump() if isinstance(state, AgentState) else state

        classification = state_dict.get("classification_result", {})
        category = classification.get("category", "")

        # Build search query from classification
        query = f"{category} support policy"
        if category == "Billing":
            query = "refund policy billing"
        elif category == "Account Access":
            query = "account recovery policy"

        start_time = time.time()
        snippets = policy_search(query, k=3)
        duration_ms = int((time.time() - start_time) * 1000)

        # Convert to PolicySnippet models
        policy_snippets = [
            PolicySnippet(
                title=s.get("title", ""),
                snippet=s.get("snippet", ""),
                doc_id=s.get("doc_id", ""),
            ).model_dump()
            for s in snippets
        ]

        state_dict["policy_snippets"] = policy_snippets

        # Log tool call
        state_dict.setdefault("tool_calls", []).append(
            {
                "tool_name": "policy_search",
                "tool_input": {"query": query, "k": 3},
                "tool_output": {"snippets": len(snippets)},
                "duration_ms": duration_ms,
            }
        )

        span.set_attribute("policies_found", len(snippets))
        return AgentState(**state_dict)


def route_node(state: AgentState) -> AgentState:
    """Determine routing based on classification."""
    with tracer.start_as_current_span("route_node") as span:
        # Convert to dict for easier manipulation
        state_dict = state.model_dump() if isinstance(state, AgentState) else state

        classification = state_dict.get("classification_result", {})

        messages = [
            {
                "role": "system",
                "content": "You are a routing expert. Always respond with valid JSON.",
            },
            {
                "role": "user",
                "content": ROUTING_PROMPT.format(
                    classification=json.dumps(classification, indent=2)
                ),
            },
        ]

        try:
            result = gemini_client.chat(
                messages=messages,
                response_schema=RoutingResult,
                temperature=0.0,
            )

            routing = RoutingResult(**result)
            state_dict["routing_result"] = routing.model_dump()

            span.set_attribute("queue", routing.queue)
            span.set_attribute("team", routing.team)

        except Exception as e:
            logger.error(f"Routing failed: {e}")
            # Fallback routing
            category = classification.get("category", "Other")
            routing = _rule_based_route(category)
            state_dict["routing_result"] = routing.model_dump()

        return AgentState(**state_dict)


def _rule_based_route(category: str) -> RoutingResult:
    """Fallback rule-based routing."""
    routing_map = {
        "Billing": ("Payments", "Payments Team"),
        "Account Access": ("Identity", "Identity Team"),
        "Bug": ("Core App", "Engineering Team"),
        "Abuse/Safety": ("Trust&Safety", "Trust & Safety Team"),
        "Feature Request": ("Core App", "Product Team"),
        "Other": ("Support General", "Support Team"),
    }

    queue, team = routing_map.get(category, ("Support General", "Support Team"))
    return RoutingResult(
        queue=queue,
        team=team,
        rationale=f"Rule-based routing for {category}",
    )


def draft_node(state: AgentState) -> AgentState:
    """Draft customer response."""
    with tracer.start_as_current_span("draft_node") as span:
        # Convert to dict for easier manipulation
        state_dict = state.model_dump() if isinstance(state, AgentState) else state

        # Use sanitized ticket (PII already redacted)
        sanitized = state_dict.get("sanitized_ticket", "")
        # If sanitized is empty, try to get content from raw_ticket but ensure it's a string
        if not sanitized:
            raw_ticket = state_dict.get("raw_ticket", {})
            if isinstance(raw_ticket, dict):
                sanitized = raw_ticket.get("content", json.dumps(raw_ticket))
            else:
                sanitized = str(raw_ticket)

        classification = state_dict.get("classification_result", {})
        policy_snippets = state_dict.get("policy_snippets", [])

        # Format policy snippets
        policy_text = "\n".join(
            [
                f"- {s.get('title', '')}: {s.get('snippet', '')[:200]}..."
                for s in policy_snippets
            ]
        ) or "No specific policies found"

        messages = [
            {
                "role": "system",
                "content": "You are a professional customer support agent. Write empathetic, helpful responses.",
            },
            {
                "role": "user",
                "content": DRAFT_RESPONSE_PROMPT.format(
                    ticket_content=sanitized,
                    category=classification.get("category", "Unknown"),
                    priority=classification.get("priority", "P2"),
                    policy_snippets=policy_text,
                ),
            },
        ]

        try:
            result = gemini_client.chat(messages=messages, temperature=0.3)
            draft = result.get("text", "").strip()

            # Extract just the response if it's wrapped in JSON
            if draft.startswith("{") and "text" in draft:
                try:
                    parsed = json.loads(draft)
                    draft = parsed.get("text", draft)
                except json.JSONDecodeError:
                    # If parsing fails, fall back to original draft
                    logger.warning("Failed to parse JSON-wrapped draft response, using raw text")

            # Additional PII check on draft response - redact any PII that leaked through
            draft_redacted, pii_events = redact_pii(draft)
            if pii_events:
                logger.warning(f"PII detected in draft response, redacting: {len(pii_events)} instances")
                draft = draft_redacted
                # Add guardrail events for PII in response
                for event in pii_events:
                    event_dict = event.model_dump()
                    event_dict["node"] = "draft"
                    event_dict["severity"] = "error"  # PII in response is more serious
                    state_dict.setdefault("guardrail_events", []).append(event_dict)

            state_dict["draft_response"] = draft

            span.set_attribute("response_length", len(draft))

        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            state_dict["draft_response"] = _fallback_response(classification)
            state_dict.setdefault("guardrail_events", []).append(
                {
                    "event_type": "draft_fallback",
                    "severity": "warning",
                    "message": f"LLM draft failed, used fallback: {e}",
                    "node": "draft",
                }
            )

        return AgentState(**state_dict)


def _fallback_response(classification: Dict[str, Any]) -> str:
    """Safe fallback response."""
    category = classification.get("category", "inquiry")
    return f"""Thank you for contacting us regarding your {category.lower()} issue.

We have received your request and our team is reviewing it. We will get back to you within 24-48 hours with an update.

If this is urgent, please reply to this message and we will prioritize your request.

Best regards,
Customer Support Team"""


def verify_node(state: AgentState) -> AgentState:
    """Verify response safety and compliance."""
    with tracer.start_as_current_span("verify_node") as span:
        # Convert to dict for easier manipulation
        state_dict = state.model_dump() if isinstance(state, AgentState) else state

        response = state_dict.get("draft_response", "")
        policy_snippets = state_dict.get("policy_snippets", [])

        is_safe, events = verify_response_safety(response, policy_snippets)

        # Add guardrail events
        for event in events:
            state_dict.setdefault("guardrail_events", []).append(event.model_dump())

        if not is_safe:
            logger.warning("Response failed safety verification, attempting rewrite")
            # Attempt one rewrite
            try:
                messages = [
                    {
                        "role": "system",
                        "content": "You are a customer support agent. Fix the following response to remove any issues.",
                    },
                    {
                        "role": "user",
                        "content": f"""The following response has safety issues. Please rewrite it to be safe and compliant:

Issues found:
{json.dumps([e.model_dump() for e in events], indent=2)}

Original response:
{response}

Provide a safe, compliant rewrite:""",
                    },
                ]

                result = gemini_client.chat(messages=messages, temperature=0.0)
                rewritten = result.get("text", "").strip()
                if rewritten:
                    state_dict["draft_response"] = rewritten
                    state_dict.setdefault("guardrail_events", []).append(
                        {
                            "event_type": "response_rewritten",
                            "severity": "info",
                            "message": "Response rewritten due to safety issues",
                            "node": "verify",
                        }
                    )
            except Exception as e:
                logger.error(f"Response rewrite failed: {e}")
                # Use ultra-safe fallback
                state_dict["draft_response"] = _fallback_response(
                    state_dict.get("classification_result", {})
                )

        span.set_attribute("verification_passed", is_safe)
        return AgentState(**state_dict)


def persist_node(state: AgentState) -> AgentState:
    """Persist results to database."""
    with tracer.start_as_current_span("persist_node") as span:
        from supportops_agent.db import AgentRun, get_db

        # Convert to dict for easier manipulation
        state_dict = state.model_dump() if isinstance(state, AgentState) else state

        # Generate suggested actions if not present
        suggested_actions = state_dict.get("suggested_actions", [])
        if not suggested_actions:
            classification = state_dict.get("classification_result", {})
            category = classification.get("category", "")
            if category == "Billing":
                suggested_actions = ["Review refund policy", "Check payment status", "Verify order details"]
            elif category == "Account Access":
                suggested_actions = ["Verify identity", "Reset password", "Check account status"]
            elif category == "Bug":
                suggested_actions = ["Reproduce issue", "Check logs", "Assign to engineering"]
            elif category == "Abuse/Safety":
                suggested_actions = ["Review content", "Check user history", "Escalate to Trust & Safety"]
            else:
                suggested_actions = ["Review ticket", "Gather more information"]

        # Build final output
        final_output = {
            "ticket_id": state_dict.get("ticket_id"),
            "classification": state_dict.get("classification_result"),
            "routing": state_dict.get("routing_result"),
            "draft_response": state_dict.get("draft_response"),
            "suggested_actions": suggested_actions,
            "guardrail_events": state_dict.get("guardrail_events", []),
            "confidence": state_dict.get("classification_result", {}).get("confidence") if state_dict.get("classification_result") else None,
        }

        state_dict["final_output"] = final_output

        # Persist to database (optional, skip if DB unavailable)
        try:
            with get_db() as db:
                agent_run = AgentRun(
                    ticket_id=state_dict.get("ticket_id", "unknown"),
                    request_id=state_dict.get("request_id"),
                    trace_id=state_dict.get("trace_id"),
                    classification_result=state_dict.get("classification_result"),
                    routing_result=state_dict.get("routing_result"),
                    draft_response=state_dict.get("draft_response"),
                    final_output=final_output,
                    guardrail_events=state_dict.get("guardrail_events"),
                    confidence=str(state_dict.get("classification_result", {}).get("confidence", 0.0)) if state_dict.get("classification_result") else "0.0",
                )
                db.add(agent_run)
                db.commit()

                state_dict["agent_run_id"] = agent_run.id
                logger.info(f"Agent run persisted to database: {agent_run.id}")

        except Exception as e:
            logger.warning(f"Database persistence skipped (optional): {e}")
            # Don't fail the flow, just log - database is optional

        span.set_attribute("persisted", True)
        return AgentState(**state_dict)


def return_node(state: AgentState) -> AgentState:
    """Final return node."""
    return state


def create_agent_graph() -> StateGraph:
    """Create LangGraph agent graph."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("sanitize", sanitize_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve_policy", retrieve_policy_node)
    workflow.add_node("route", route_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("persist", persist_node)
    workflow.add_node("return", return_node)

    # Define edges
    workflow.set_entry_point("sanitize")
    workflow.add_edge("sanitize", "classify")
    workflow.add_edge("classify", "retrieve_policy")
    workflow.add_edge("retrieve_policy", "route")
    workflow.add_edge("route", "draft")
    workflow.add_edge("draft", "verify")
    workflow.add_edge("verify", "persist")
    workflow.add_edge("persist", "return")
    workflow.add_edge("return", END)

    return workflow.compile()


def run_agent(
    ticket_data: Dict[str, Any],
    ticket_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the agent on a ticket.

    Args:
        ticket_data: Raw ticket data dictionary
        ticket_id: Optional ticket ID
        request_id: Optional request ID for tracing

    Returns:
        Final agent output dictionary
    """
    with tracer.start_as_current_span("run_agent") as span:
        if not request_id:
            request_id = str(uuid.uuid4())

        # Get trace ID
        trace_id = format(span.get_span_context().trace_id, "032x") if span.get_span_context().is_valid else None

        # Initialize state
        initial_state = AgentState(
            raw_ticket=ticket_data,
            ticket_id=ticket_id or f"TICKET-{uuid.uuid4().hex[:8]}",
            request_id=request_id,
            trace_id=trace_id,
        )

        # Create and run graph
        graph = create_agent_graph()
        result = graph.invoke(initial_state.model_dump())

        # Return final output with trace info
        final_output = result.get("final_output", {})
        final_output["trace_id"] = trace_id
        final_output["request_id"] = request_id
        return final_output
