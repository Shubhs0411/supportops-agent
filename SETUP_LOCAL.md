# Local Setup Guide

## Step-by-Step Instructions

### 1. Get Your Gemini API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the API key (you'll need it in step 3)

### 2. Install Dependencies

```bash
# Make sure you have Python 3.11+
python --version

# Install the project
pip install -e ".[dev]"
```

### 3. Create `.env` File with Your API Key

```bash
# Copy the example file
cp .env.example .env

# Edit .env and replace 'your_gemini_api_key_here' with your actual key
# You can use any text editor:
nano .env
# or
vim .env
# or
code .env  # if using VS Code
```

Your `.env` file should look like:
```bash
GEMINI_API_KEY=AIzaSy...your_actual_key_here...
GEMINI_MODEL=gemini-1.5-flash
DATABASE_URL=postgresql://supportops:supportops@localhost:5432/supportops
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=supportops-agent
STORE_RAW=false
```

### 4. Start Services with Docker

```bash
# Start PostgreSQL and Jaeger
docker compose up -d

# Wait a few seconds for services to start
sleep 5

# Verify services are running
docker compose ps
```

You should see:
- `postgres` - running
- `jaeger` - running

### 5. Run the Demo

**Option A: Using CLI (Recommended for first run)**
```bash
python -m supportops_agent.cli triage --ticket evals/fixtures/ticket_01.json
```

**Option B: Start the API Server**
```bash
# In one terminal, start the API
uvicorn supportops_agent.api.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, test it
curl -X POST http://localhost:8000/v1/agent/triage \
  -H "Content-Type: application/json" \
  -d '{"ticket_data": {"content": "I need a refund for my order"}}'
```

**Option C: Using Makefile**
```bash
# Start API server
make run

# Or run demo
make demo
```

### 6. View Results

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/healthz
- **Jaeger Traces**: http://localhost:16686

## Quick Test

After setup, test everything works:

```bash
# 1. Test the CLI
python -m supportops_agent.cli triage --ticket evals/fixtures/ticket_01.json

# 2. Run the evaluation suite
python -m supportops_agent.evals.run --suite evals/suite.yaml

# 3. Run unit tests
pytest -q
```

## Troubleshooting

### "GEMINI_API_KEY not found" or "API key not set"
- Make sure you created `.env` file (not `.env.example`)
- Check the file is in the project root directory
- Verify the key starts with `GEMINI_API_KEY=` (no spaces around `=`)

### "Connection refused" to PostgreSQL
- Make sure Docker is running: `docker ps`
- Start services: `docker compose up -d`
- Wait 10-15 seconds for Postgres to initialize
- Check logs: `docker compose logs postgres`

### "Module not found" errors
- Install dependencies: `pip install -e ".[dev]"`
- Make sure you're in the project root directory

### API key invalid
- Verify you copied the entire key (they're long!)
- Check for extra spaces or quotes
- Get a new key from https://makersuite.google.com/app/apikey if needed

## File Locations

- **API Key**: `.env` file in project root
- **Logs**: Console output (structured JSON)
- **Database**: PostgreSQL in Docker (port 5432)
- **Traces**: Jaeger UI at http://localhost:16686

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [QUICKSTART.md](QUICKSTART.md) for quick reference
- Explore the API at http://localhost:8000/docs
