#!/bin/bash
# Demo script to run the SupportOps Agent

set -e

echo "🚀 SupportOps Agent Demo"
echo "========================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Activate venv
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your GEMINI_API_KEY"
    echo "Example:"
    echo "  GEMINI_API_KEY=your_key_here"
    exit 1
fi

# Check if API key is set
if grep -q "your_gemini_api_key_here\|your_key_here" .env 2>/dev/null; then
    echo "⚠️  Warning: GEMINI_API_KEY appears to be a placeholder"
    echo "Please update .env with your actual API key"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for Docker (optional)
if command -v docker &> /dev/null; then
    echo "🐳 Docker detected (optional)"
    if docker compose ps 2>/dev/null | grep -q "postgres.*Up"; then
        echo "✅ Docker services are running"
    else
        echo "ℹ️  Docker services not running (optional - using SQLite instead)"
    fi
else
    echo "ℹ️  Docker not installed (optional - using SQLite instead)"
fi

# Run the demo
echo ""
echo "🤖 Running agent triage on sample ticket..."
echo ""

python -m supportops_agent.cli triage --ticket evals/fixtures/ticket_01.json

echo ""
echo "✅ Demo complete!"
echo ""
if command -v docker &> /dev/null && docker compose ps 2>/dev/null | grep -q "jaeger.*Up"; then
    echo "📊 View traces in Jaeger: http://localhost:16686"
fi
echo "📖 API docs: http://localhost:8000/docs (if API server is running)"
