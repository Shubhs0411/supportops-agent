#!/bin/bash
# Run SupportOps Agent on a ticket

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 SupportOps Agent${NC}"
echo "=================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Run ./setup.sh first.${NC}"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create .env file with your GEMINI_API_KEY"
    exit 1
fi

# Check if API key is set
if grep -q "your_gemini_api_key_here\|your_key_here" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: GEMINI_API_KEY appears to be a placeholder${NC}"
    echo "Please update .env with your actual API key"
    exit 1
fi

# Parse arguments
TICKET_FILE=""
INTERACTIVE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            TICKET_FILE="$2"
            shift 2
            ;;
        -i|--interactive)
            INTERACTIVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -f, --file FILE       Path to ticket JSON file"
            echo "  -i, --interactive     Interactive mode (create ticket from input)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 -f evals/fixtures/ticket_01.json"
            echo "  $0 --interactive"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Interactive mode
if [ "$INTERACTIVE" = true ]; then
    echo "📝 Interactive Ticket Creation"
    echo "=============================="
    echo ""
    read -p "Enter ticket content: " TICKET_CONTENT
    
    # Create temporary ticket file
    TICKET_FILE=$(mktemp /tmp/ticket_XXXXXX.json)
    cat > "$TICKET_FILE" << EOF
{
  "content": "$TICKET_CONTENT",
  "metadata": {
    "source": "interactive",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  }
}
EOF
    echo "Created temporary ticket file: $TICKET_FILE"
    echo ""
fi

# Check if ticket file is provided
if [ -z "$TICKET_FILE" ]; then
    echo -e "${RED}❌ No ticket file provided${NC}"
    echo "Usage: $0 -f <ticket_file.json>"
    echo "   Or: $0 --interactive"
    exit 1
fi

# Check if ticket file exists
if [ ! -f "$TICKET_FILE" ]; then
    echo -e "${RED}❌ Ticket file not found: $TICKET_FILE${NC}"
    exit 1
fi

# Check for Docker (optional)
if command -v docker &> /dev/null; then
    echo "🐳 Docker detected (optional)"
    if ! docker compose ps 2>/dev/null | grep -q "postgres.*Up"; then
        echo "ℹ️  Docker services not running (optional - using SQLite instead)"
    fi
else
    echo "ℹ️  Docker not installed (optional - using SQLite instead)"
fi

# Run the agent
echo ""
echo -e "${GREEN}🚀 Running agent triage...${NC}"
echo ""

python -m supportops_agent.cli triage --ticket "$TICKET_FILE"

# Clean up temp file if interactive
if [ "$INTERACTIVE" = true ] && [ -f "$TICKET_FILE" ]; then
    rm "$TICKET_FILE"
fi

echo ""
echo -e "${GREEN}✅ Complete!${NC}"
echo ""
if command -v docker &> /dev/null && docker compose ps 2>/dev/null | grep -q "jaeger.*Up"; then
    echo "📊 View traces in Jaeger: http://localhost:16686"
fi
echo "📖 API docs: http://localhost:8000/docs (if API server is running)"
