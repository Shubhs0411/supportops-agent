#!/bin/bash
# Start the FastAPI server

set -e

echo "🚀 Starting SupportOps Agent API Server"
echo "========================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

# Activate venv
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your GEMINI_API_KEY"
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

echo ""
echo "🌐 Starting API server on http://localhost:8000"
echo "📖 API docs will be available at http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

# Start the server
uvicorn supportops_agent.api.main:app --reload --host 0.0.0.0 --port 8000
