# Testing Guide

## Quick Test Methods

### 1. Using the API (Easiest)

**Via Browser (Interactive Docs):**
1. Open: http://localhost:8000/docs
2. Click on `POST /v1/agent/triage`
3. Click "Try it out"
4. Paste this JSON:
```json
{
  "ticket_data": {
    "content": "I need a refund for order #123456. My email is customer@example.com"
  }
}
```
5. Click "Execute"
6. See the full agent output!

**Via curl:**
```bash
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_data": {
      "content": "I need a refund for order #123456"
    }
  }' | jq
```

### 2. Using the CLI

```bash
# Test with a sample ticket
./demo.sh

# Or test with your own ticket file
./run_agent.sh -f evals/fixtures/ticket_02.json

# Interactive mode
./run_agent.sh --interactive
```

### 3. Run the Full Evaluation Suite

```bash
# Run all 12 test cases
make evals

# Or directly
python -m supportops_agent.evals.run --suite evals/suite.yaml
```

## Test Scenarios

### Test 1: Refund Request (Billing)
```bash
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_data": {
      "content": "I need a refund for my subscription. I paid $29.99 last month but didn't use it."
    }
  }'
```

**Expected:**
- Category: Billing
- Priority: P1
- Queue: Payments
- PII should be redacted

### Test 2: Account Access Issue
```bash
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_data": {
      "content": "I can't log into my account. I've tried resetting my password but the email never arrives. My username is johndoe."
    }
  }'
```

**Expected:**
- Category: Account Access
- Priority: P1
- Queue: Identity
- Email/username should be redacted

### Test 3: Bug Report
```bash
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_data": {
      "content": "The app crashes every time I try to upload a file. Steps: 1) Open app 2) Tap upload 3) App crashes immediately."
    }
  }'
```

**Expected:**
- Category: Bug
- Priority: P1 or P2
- Queue: Core App

### Test 4: Safety/Abuse Report
```bash
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_data": {
      "content": "Someone is harassing me on your platform. They keep sending threatening messages. This is urgent."
    }
  }'
```

**Expected:**
- Category: Abuse/Safety
- Priority: P0 or P1
- Queue: Trust&Safety

### Test 5: Feature Request
```bash
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_data": {
      "content": "I'd love to see a dark mode feature added to the mobile app. It would be really helpful for using the app at night."
    }
  }'
```

**Expected:**
- Category: Feature Request
- Priority: P2 or P3
- Queue: Core App

## What to Check in Results

1. **Classification:**
   - ✅ Correct category
   - ✅ Appropriate priority (P0-P3)
   - ✅ Confidence score (0.0-1.0)
   - ✅ Rationale provided

2. **Routing:**
   - ✅ Correct queue/team
   - ✅ Matches classification

3. **Draft Response:**
   - ✅ Professional and empathetic
   - ✅ No PII in response
   - ✅ Policy citations when relevant
   - ✅ Appropriate length (120-180 words)

4. **Guardrails:**
   - ✅ PII detected and redacted
   - ✅ No false promises
   - ✅ Safety checks passed

5. **Suggested Actions:**
   - ✅ Relevant to category
   - ✅ Actionable items

## Unit Tests

```bash
# Run all unit tests
pytest -q

# Run specific test file
pytest tests/test_guardrails.py -v

# Run with coverage
pytest --cov=supportops_agent tests/
```

## Integration Test Flow

1. **Create a ticket:**
```bash
curl -X POST http://localhost:8000/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I need help with my account",
    "ticket_id": "TEST-001"
  }'
```

2. **Run triage on that ticket:**
```bash
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TEST-001"
  }'
```

3. **Get ticket with results:**
```bash
curl http://localhost:8000/v1/tickets/TEST-001
```

## Performance Testing

```bash
# Time a single request
time curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{"ticket_data": {"content": "I need a refund"}}'

# Run evals to see latency stats
make evals
```

## Debugging

If something doesn't work:

1. **Check logs:** Look at the terminal where the server is running
2. **Check database:** `ls -la supportops.db` (if using SQLite)
3. **Check API health:** `curl http://localhost:8000/healthz`
4. **View trace:** Check the `trace_id` in the response (if Jaeger is running)

## Example Full Test Session

```bash
# 1. Health check
curl http://localhost:8000/healthz

# 2. Create ticket
TICKET_ID=$(curl -s -X POST http://localhost:8000/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{"content": "I need a refund"}' | jq -r '.ticket_id')

# 3. Run triage
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d "{\"ticket_id\": \"$TICKET_ID\"}" | jq

# 4. Get results
curl http://localhost:8000/v1/tickets/$TICKET_ID | jq
```
