# Building Production-Grade Agentic AI: A Complete Reference Implementation

> **How to ship reliable, observable, and safe AI agents for customer support—with real code, real tests, and zero hand-waving.**

## 🎯 Production-Ready Features

This project includes **10+ advanced production features** demonstrating senior engineering skills:

- ✅ **Response Caching** - In-memory cache with TTL for cost optimization
- ✅ **Circuit Breaker** - Resilience pattern for handling API failures
- ✅ **Retry with Exponential Backoff** - Handles transient failures gracefully
- ✅ **Comprehensive Metrics** - Prometheus-style metrics with percentiles
- ✅ **Rate Limiting** - Sliding window rate limiting (60 req/min)
- ✅ **Streaming Support** - Server-Sent Events for real-time updates
- ✅ **Batch Processing** - Process multiple tickets efficiently
- ✅ **Human Feedback Loop** - Collect corrections for continuous improvement
- ✅ **Enhanced Observability** - Metrics, traces, error tracking
- ✅ **Production Security** - Rate limiting, input validation, PII protection

**See [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md) for detailed documentation.**

## The Problem We're Solving

Customer support teams are drowning in tickets. Every email, chat message, and support request needs to be:
- **Classified** (Billing? Account Access? Bug?)
- **Prioritized** (P0 critical outage vs P3 feature request)
- **Routed** (Which team should handle this?)
- **Responded to** (Draft a helpful, policy-compliant response)

Doing this manually doesn't scale. But building an AI system that can handle this reliably? That's the hard part.

## What Makes This "Agentic"?

This isn't just a chatbot. It's an **agentic AI system**—meaning it:

1. **Orchestrates multiple steps** (not just one prompt → response)
2. **Calls tools** (searches knowledge bases, checks policies)
3. **Makes decisions** (classification, routing, priority)
4. **Self-verifies** (checks its own output for safety)
5. **Maintains state** (remembers context across steps)

Think of it like a human support agent: they don't just read a ticket and respond. They:
- Check policies
- Look up account history
- Verify information
- Draft a response
- Review it for compliance
- Route to the right team

That's what this agent does—automatically.

## Architecture: The 8-Node Workflow

Here's how a ticket flows through the system:

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Ticket                           │
│  "I need a refund for order #123456, email: user@ex.com"    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Agent Workflow                    │
│                                                               │
│  1. SANITIZE → 2. CLASSIFY → 3. RETRIEVE → 4. ROUTE        │
│     (PII)         (Gemini)     (Policy KB)    (Gemini)      │
│                                                               │
│  5. DRAFT → 6. VERIFY → 7. PERSIST → 8. RETURN             │
│     (Gemini)   (Safety)    (Database)   (Output)            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Structured Output                         │
│  • Classification: Billing / P1                              │
│  • Routing: Payments Team                                    │
│  • Draft Response: (PII-redacted, policy-compliant)          │
│  • Guardrail Events: [PII detected, redacted]                │
└─────────────────────────────────────────────────────────────┘
```

### Node-by-Node Breakdown

**1. Sanitize Node**
- Detects PII: emails, phones, credit cards, order IDs, addresses
- Redacts them: `user@example.com` → `[EMAIL_REDACTED]`
- Logs guardrail events for audit

**2. Classify Node**
- Uses Gemini to classify ticket into categories
- Assigns priority (P0-P3) with confidence score
- Falls back to rule-based classifier if LLM fails

**3. Retrieve Policy Node**
- Searches local knowledge base (`data/policies/*.md`)
- Finds relevant policy snippets (refund policy, account recovery, etc.)
- Returns top 3 most relevant snippets

**4. Route Node**
- Decides which queue/team should handle the ticket
- Based on classification + policy context
- Options: Payments, Identity, Core App, Trust&Safety, Support General

**5. Draft Node**
- Generates customer-facing response
- Uses sanitized ticket (no PII)
- Cites relevant policies
- Keeps tone empathetic and professional

**6. Verify Node**
- Checks response for PII leaks
- Verifies no false promises ("refund issued" when it wasn't)
- Ensures policy citations are present
- Validates tone and length

**7. Persist Node**
- Saves everything to database (SQLite or PostgreSQL)
- Stores classification, routing, draft, guardrail events
- Creates audit trail for compliance

**8. Return Node**
- Packages final structured output
- Includes trace IDs for observability
- Returns JSON to API/CLI

## The Tech Stack

### Core Framework: LangGraph
- **Why**: Explicit state management, visualizable workflows, production-ready
- **What**: Orchestrates the 8-node workflow with typed state (Pydantic models)

### LLM: Google Gemini
- **Why**: Fast, cost-effective, good structured output support
- **Model**: `gemini-2.5-flash-lite` (configurable)
- **What**: Powers classification, routing, and response drafting

### Observability: OpenTelemetry
- **Why**: Industry standard, vendor-agnostic
- **What**: Traces every node execution, tool call, and LLM interaction
- **Export**: Jaeger (optional, for visualization)

### Database: SQLite (default) or PostgreSQL
- **Why**: SQLite for local dev, PostgreSQL for production
- **What**: Stores tickets, agent runs, tool calls, guardrail events

### API: FastAPI
- **Why**: Modern, fast, automatic docs
- **What**: REST API with `/v1/tickets`, `/v1/agent/triage`, etc.

## Key Features

### 1. Runtime Guardrails

**PII Redaction**
- Detects: emails, phones, credit cards, SSNs, order IDs, addresses
- Redacts: Replaces with `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`, etc.
- Verifies: Double-checks draft responses for PII leaks

**Prompt Injection Defense**
- Detects: "ignore previous instructions", "system:", jailbreak attempts
- Logs: All injection attempts are logged as guardrail events
- Protects: System prompts are hardened, responses verified

**False Promise Prevention**
- Checks: Response doesn't claim actions were taken unless confirmed
- Patterns: "refund issued", "account restored", "issue resolved"
- Rewrites: Automatically rewrites unsafe responses

**Policy Compliance**
- Verifies: Responses cite relevant policies when applicable
- Validates: Tone, length (120-180 words), next steps present

### 2. Observability

**Structured Logging**
- JSON format with `request_id`, `ticket_id`, `trace_id`
- Logs every node execution, tool call, guardrail event
- Searchable and parseable

**OpenTelemetry Traces**
- Full trace for every agent run
- Spans for each node, tool call, LLM interaction
- View in Jaeger UI (if configured)

**Database Audit Trail**
- Every agent run stored with full context
- Tool calls logged with inputs/outputs/duration
- Guardrail events tracked for compliance

### 3. Evaluation Suite

**12 Test Cases**
- Cover all categories and edge cases
- Include PII, prompt injection, high severity scenarios
- Deterministic checks (category, priority, queue, PII detection)

**Pass/Fail Reporting**
- JSON output + console summary
- Per-test diffs showing what failed
- Latency metrics per test

**Continuous Validation**
- Run `make evals` to validate agent performance
- Catch regressions before deployment
- Track improvements over time

## Getting Started

### Prerequisites
- Python 3.11+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- (Optional) Docker for PostgreSQL/Jaeger

### Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd supportops-agent
./setup.sh

# 2. Add your API key to .env
# Edit .env and set: GEMINI_API_KEY=your_key_here

# 3. Run demo
./demo.sh

# 4. Start API server
./start_api.sh
# Visit http://localhost:8000/docs
```

### Test It

```bash
# Quick test via API
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{"ticket_data": {"content": "I need a refund for order #123456"}}'

# Run full eval suite
make evals
```

## Real-World Example

Let's trace a real ticket through the system:

**Input:**
```json
{
  "content": "I need a refund for order #123456. My email is customer@example.com and I paid with card ending in 1234."
}
```

**Step 1: Sanitize**
- Detects: `customer@example.com`, `#123456`, `1234`
- Redacts: `[EMAIL_REDACTED]`, `[ORDER_ID_REDACTED]`, `[CARD_REDACTED]`
- Output: "I need a refund for [ORDER_ID_REDACTED]. My email is [EMAIL_REDACTED]..."

**Step 2: Classify**
- Gemini analyzes sanitized content
- Output: `{category: "Billing", priority: "P1", confidence: 0.95}`

**Step 3: Retrieve Policy**
- Searches for "refund policy"
- Finds: `data/policies/refund_policy.md`
- Returns: Top 3 snippets about refund eligibility

**Step 4: Route**
- Based on "Billing" + "P1"
- Output: `{queue: "Payments", team: "Payments Team"}`

**Step 5: Draft**
- Gemini generates response using:
  - Sanitized ticket (no PII)
  - Classification context
  - Policy snippets
- Output: Professional, empathetic response citing refund policy

**Step 6: Verify**
- Checks: No PII? ✅ (already sanitized)
- Checks: No false promises? ✅
- Checks: Policy cited? ✅
- Output: Response approved

**Step 7: Persist**
- Saves to database:
  - Ticket ID, classification, routing, draft
  - Guardrail events (PII detected: 3 instances)
  - Trace ID for observability

**Step 8: Return**
```json
{
  "ticket_id": "TICKET-abc123",
  "classification": {
    "category": "Billing",
    "priority": "P1",
    "confidence": 0.95
  },
  "routing": {
    "queue": "Payments",
    "team": "Payments Team"
  },
  "draft_response": "Thank you for contacting us regarding your refund request...",
  "guardrail_events": [
    {"event_type": "pii_detected", "severity": "warning", ...}
  ]
}
```

## Why This Matters

### For Developers
- **Reference Implementation**: See how to build production-grade agents
- **Best Practices**: Observability, guardrails, testing all in one place
- **Real Code**: No abstractions, everything is runnable

### For Product Teams
- **Proven Patterns**: Multi-step workflows, tool calling, state management
- **Safety First**: PII redaction, prompt injection defense, compliance checks
- **Observable**: Full traces, logs, audit trails

### For AI/ML Engineers
- **LangGraph Patterns**: How to structure agent workflows
- **Evaluation Framework**: Deterministic tests for non-deterministic systems
- **Guardrail Implementation**: Runtime safety checks that actually work

## Project Structure

```
supportops-agent/
├── supportops_agent/
│   ├── agents/
│   │   ├── graph.py          # LangGraph workflow (8 nodes)
│   │   ├── schemas.py        # Pydantic state models
│   │   ├── prompts.py         # Prompt templates
│   │   └── guardrails.py     # PII detection, safety checks
│   ├── llm/
│   │   └── gemini.py         # Gemini client wrapper
│   ├── tools/
│   │   ├── policy_search.py  # Knowledge base search
│   │   ├── ticket_system.py   # Mock ticket creation
│   │   └── email.py           # Mock email preview
│   ├── db/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── session.py          # Database session
│   ├── api/
│   │   └── main.py            # FastAPI application
│   └── evals/
│       └── run.py             # Evaluation runner
├── data/
│   └── policies/              # Policy knowledge base
├── evals/
│   ├── suite.yaml            # Test suite config
│   └── fixtures/             # 12 test tickets
└── tests/                     # Unit tests
```

## Key Design Decisions

### Why LangGraph?
- **Explicit State**: Pydantic models make state visible and type-safe
- **Visualizable**: Can draw the graph, see execution flow
- **Production-Ready**: Built for real systems, not demos

### Why Multi-Step?
- **Reliability**: Each step can be tested, monitored, debugged independently
- **Observability**: See exactly where things go wrong
- **Flexibility**: Easy to add/remove/modify steps

### Why Guardrails?
- **Safety**: PII leaks, false promises, prompt injection are real risks
- **Compliance**: Many industries require audit trails
- **Trust**: Users need to know the system is safe

### Why SQLite by Default?
- **Developer Experience**: No Docker required for local dev
- **Production Path**: Easy to switch to PostgreSQL
- **Simplicity**: One file, zero config

## Evaluation Results

Running `make evals` tests 12 scenarios:

- ✅ **8 Pass** (66.7%): Most classifications, routing, and responses are correct
- ⚠️ **4 Fail**: Edge cases around PII in responses, prompt injection handling

**What This Tells Us:**
- Core functionality works (classification, routing, drafting)
- Guardrails are detecting issues (PII detection logged)
- Edge cases need refinement (response PII redaction, injection defense)

This is **normal** for AI systems. The evaluation suite helps us:
- Catch regressions
- Track improvements
- Identify edge cases

## Next Steps

### For Your Team
1. **Customize Policies**: Add your own policies to `data/policies/`
2. **Tune Prompts**: Adjust `supportops_agent/agents/prompts.py` for your use case
3. **Add Tools**: Extend `supportops_agent/tools/` with real integrations
4. **Expand Evals**: Add more test cases to `evals/suite.yaml`

### For Production
1. **Switch to PostgreSQL**: Update `DATABASE_URL` in `.env`
2. **Enable Jaeger**: Set `OTEL_EXPORTER_OTLP_ENDPOINT`
3. **Add Monitoring**: Integrate with your observability stack
4. **Scale**: Deploy API behind load balancer, add caching

## Lessons Learned

### What Works
- **Explicit State**: Pydantic models make debugging easy
- **Multi-Step Workflows**: Breaking tasks into steps improves reliability
- **Guardrails**: Runtime checks catch issues LLMs miss
- **Evaluation Suite**: Deterministic tests for non-deterministic systems

### What's Hard
- **PII in Responses**: LLMs sometimes include PII even when told not to
- **Prompt Injection**: Sophisticated attacks require multiple layers of defense
- **Priority Calibration**: Getting priority right requires domain knowledge
- **LLM Non-Determinism**: Same input can produce different outputs

### Best Practices
- **Always Sanitize First**: Redact PII before any LLM call
- **Verify Outputs**: Don't trust LLM outputs blindly
- **Log Everything**: You'll need audit trails for compliance
- **Test Continuously**: Run evals regularly to catch regressions

## Contributing

This is a reference implementation. Feel free to:
- Fork and customize for your use case
- Add more tools, nodes, or guardrails
- Improve the evaluation suite
- Share your learnings

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file.

---

**Built with ❤️ for the AI observability community.**

*This project demonstrates production-grade patterns for building reliable, observable, and safe agentic AI systems. Use it as a reference, learn from it, and adapt it to your needs.*
