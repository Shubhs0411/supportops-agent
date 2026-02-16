# Local Setup (No Docker Required)

This guide shows how to run SupportOps Agent locally **without Docker**.

## Quick Start

### 1. Setup Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

Or use the setup script:
```bash
./setup.sh
```

### 2. Create `.env` File

Create a `.env` file in the project root:

```bash
cat > .env << 'EOF'
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=gemini-1.5-flash
DATABASE_URL=sqlite:///./supportops.db
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=supportops-agent
STORE_RAW=false
EOF
```

**Important**: Replace `your_actual_api_key_here` with your Gemini API key from https://makersuite.google.com/app/apikey

### 3. Run Demo

```bash
# Activate venv (if not already)
source venv/bin/activate

# Run demo
./demo.sh
```

Or manually:
```bash
python -m supportops_agent.cli triage --ticket evals/fixtures/ticket_01.json
```

## What's Different Without Docker?

### Database
- **With Docker**: Uses PostgreSQL
- **Without Docker**: Uses SQLite (file: `supportops.db`)
- **Result**: Same functionality, just a local file instead of a database server

### Observability
- **With Docker**: Traces sent to Jaeger UI
- **Without Docker**: Traces still logged, but not sent to Jaeger
- **Result**: You still get structured logs with trace IDs, just no visual UI

### Everything Else
- Agent functionality: **Identical**
- API endpoints: **Identical**
- CLI: **Identical**
- Evals: **Identical**

## Running the Agent

### CLI Demo
```bash
source venv/bin/activate
./demo.sh
```

### Run on Your Ticket
```bash
source venv/bin/activate
./run_agent.sh -f evals/fixtures/ticket_02.json
```

### Interactive Mode
```bash
source venv/bin/activate
./run_agent.sh --interactive
```

### Start API Server
```bash
source venv/bin/activate
uvicorn supportops_agent.api.main:app --reload --host 0.0.0.0 --port 8000
```

Then visit: http://localhost:8000/docs

## File Locations

- **Database**: `supportops.db` (SQLite file in project root)
- **Environment**: `.env` (in project root)
- **Logs**: Console output (structured JSON)

## Troubleshooting

### "GEMINI_API_KEY not found"
- Make sure `.env` file exists in project root
- Check the key is set: `grep GEMINI_API_KEY .env`
- No spaces around `=` sign

### "Module not found"
- Activate venv: `source venv/bin/activate`
- Install dependencies: `pip install -e ".[dev]"`

### "Database error"
- SQLite file is created automatically
- If issues, delete `supportops.db` and run again
- Make sure you have write permissions in project directory

### "Permission denied" on scripts
```bash
chmod +x setup.sh demo.sh run_agent.sh
```

## Testing

```bash
source venv/bin/activate

# Run unit tests
pytest -q

# Run evals
python -m supportops_agent.evals.run --suite evals/suite.yaml
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [SCRIPTS.md](SCRIPTS.md) for script details
- Explore the API at http://localhost:8000/docs (if running API server)
