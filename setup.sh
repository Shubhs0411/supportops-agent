#!/bin/bash
# Setup script for SupportOps Agent

set -e

echo "🔧 SupportOps Agent Setup"
echo "========================"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version"

# Create venv
echo ""
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate venv
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -e ".[dev]"

echo "✅ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file (SQLite - no Docker needed)..."
    cat > .env << 'EOF'
# Gemini API Configuration
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_BASE_URL=

# Database (SQLite - no Docker needed)
DATABASE_URL=sqlite:///./supportops.db

# Observability (optional - leave empty if no Jaeger)
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=supportops-agent

# Security
STORE_RAW=false
EOF
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your GEMINI_API_KEY"
    echo "   Get your key from: https://makersuite.google.com/app/apikey"
else
    echo "✅ .env file already exists"
fi

# Check Docker (optional)
echo ""
echo "🐳 Checking Docker (optional)..."
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✅ Docker is installed (optional)"
    echo ""
    echo "To start services, run:"
    echo "  docker compose up -d"
else
    echo "ℹ️  Docker not found (optional)"
    echo "   The agent will use SQLite instead of PostgreSQL"
    echo "   Traces will be logged but not sent to Jaeger"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your GEMINI_API_KEY"
echo "  2. Start services: docker compose up -d"
echo "  3. Run demo: ./demo.sh"
echo "  4. Or run agent: ./run_agent.sh"
