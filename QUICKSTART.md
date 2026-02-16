# Quick Start Guide

## 5-Minute Setup

### 1. Get Gemini API Key
Visit https://makersuite.google.com/app/apikey and create an API key.

### 2. Configure Environment
```bash
# Create .env file
cat > .env << EOF
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
DATABASE_URL=postgresql://supportops:supportops@localhost:5432/supportops
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=supportops-agent
STORE_RAW=false
EOF
```

### 3. Start Services
```bash
docker compose up -d
```

Wait ~10 seconds for services to initialize.

### 4. Run Demo
```bash
# Install dependencies (if not using Docker)
pip install -e .

# Run CLI demo
python -m supportops_agent.cli triage --ticket evals/fixtures/ticket_01.json
```

### 5. View Results
- **API**: http://localhost:8000/docs
- **Jaeger Traces**: http://localhost:16686
- **Test API**: 
  ```bash
  curl -X POST http://localhost:8000/v1/agent/triage \
    -H "Content-Type: application/json" \
    -d '{"ticket_data": {"content": "I need help with my account"}}'
  ```

## Common Commands

```bash
# Start everything
make docker-up

# Run tests
make test

# Run evals
make evals

# View logs
docker compose logs -f api

# Stop everything
make docker-down
```

## Troubleshooting

**"GEMINI_API_KEY not found"**
- Set it in `.env` file

**"Connection refused" (Postgres)**
- Wait a few seconds after `docker compose up`
- Check: `docker compose ps`

**"No traces in Jaeger"**
- Verify `OTEL_EXPORTER_OTLP_ENDPOINT` in `.env`
- Check Jaeger is running: `docker compose ps`
