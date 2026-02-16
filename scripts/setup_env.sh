#!/bin/bash
# Setup script to create .env file from .env.example

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env file from .env.example"
        echo "Please edit .env and add your GEMINI_API_KEY"
    else
        echo "Creating .env file with default values..."
        cat > .env << EOF
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_BASE_URL=

# Database
DATABASE_URL=postgresql://supportops:supportops@localhost:5432/supportops

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=supportops-agent

# Security
STORE_RAW=false
EOF
        echo "Created .env file. Please edit it and add your GEMINI_API_KEY"
    fi
else
    echo ".env file already exists"
fi
