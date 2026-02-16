# Scripts Guide

## Quick Start

### 1. Setup (First Time Only)

```bash
./setup.sh
```

This will:
- Create a Python virtual environment (`venv/`)
- Install all dependencies
- Create `.env` file template
- Check Docker installation

**After setup, edit `.env` and add your `GEMINI_API_KEY`**

### 2. Run Demo

```bash
./demo.sh
```

Runs the agent on a sample ticket (`evals/fixtures/ticket_01.json`).

### 3. Run Agent on Your Ticket

```bash
# With a JSON file
./run_agent.sh -f evals/fixtures/ticket_02.json

# Interactive mode (type ticket content)
./run_agent.sh --interactive
```

## Script Details

### `setup.sh`
Initial setup script. Run once to:
- Create virtual environment
- Install dependencies
- Create `.env` file

**Usage:**
```bash
./setup.sh
```

### `demo.sh`
Quick demo script that:
- Activates venv
- Checks Docker services
- Runs agent on sample ticket
- Shows results

**Usage:**
```bash
./demo.sh
```

### `run_agent.sh`
Full agent runner with options:
- Run on a ticket file
- Interactive mode
- Auto-starts Docker services

**Usage:**
```bash
# Run on a file
./run_agent.sh -f path/to/ticket.json

# Interactive mode
./run_agent.sh -i

# Help
./run_agent.sh -h
```

## Manual Steps

If scripts don't work, here's what they do:

### Setup
```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Create .env (edit with your API key)
cp .env.example .env
# Then edit .env and add GEMINI_API_KEY

# Start Docker services
docker compose up -d
```

### Run Demo
```bash
source venv/bin/activate
python -m supportops_agent.cli triage --ticket evals/fixtures/ticket_01.json
```

### Run Agent
```bash
source venv/bin/activate
python -m supportops_agent.cli triage --ticket your_ticket.json
```

## Troubleshooting

### "Permission denied" when running scripts
```bash
chmod +x setup.sh demo.sh run_agent.sh
```

### "Virtual environment not found"
Run `./setup.sh` first

### "GEMINI_API_KEY not found"
Edit `.env` file and add your API key:
```bash
GEMINI_API_KEY=your_actual_key_here
```

### "Docker services not running"
```bash
docker compose up -d
```
