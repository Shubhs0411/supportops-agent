FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/policies evals/fixtures

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "supportops_agent.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
