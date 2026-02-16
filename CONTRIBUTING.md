# Contributing to SupportOps Agent

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository
2. Run `make setup` to install dependencies
3. Copy `.env.example` to `.env` and configure your Gemini API key
4. Start services with `make docker-up`
5. Run tests with `make test`

## Code Style

- Use `ruff` for linting: `ruff check .`
- Format code with `ruff format .`
- Type hints are required for all functions
- Follow PEP 8 with line length of 100

## Testing

- Write tests for all new features
- Run tests with `pytest -q`
- Ensure all tests pass before submitting PRs

## Pull Requests

1. Create a feature branch
2. Make your changes
3. Ensure tests pass
4. Submit a PR with a clear description
