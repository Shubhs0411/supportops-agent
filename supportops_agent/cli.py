"""CLI interface for SupportOps Agent."""

import argparse
import json
import logging
import sys
from pathlib import Path

from supportops_agent.agents.graph import run_agent
from supportops_agent.config import settings
from supportops_agent.db import init_db
from supportops_agent.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def triage_command(args):
    """Run triage on a ticket file."""
    ticket_path = Path(args.ticket)
    if not ticket_path.exists():
        logger.error(f"Ticket file not found: {ticket_path}")
        sys.exit(1)

    # Load ticket data
    try:
        with open(ticket_path, "r") as f:
            ticket_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load ticket file: {e}")
        sys.exit(1)

    # Initialize database (optional)
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped (optional): {e}")

    # Run agent
    logger.info(f"Running triage on ticket: {ticket_path}")
    try:
        result = run_agent(ticket_data=ticket_data)

        # Print results
        print("\n" + "=" * 80)
        print("TRIAGE RESULT")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print("=" * 80)

        # Print trace info if available
        if "trace_id" in str(result):
            print(f"\nTrace ID: {result.get('trace_id', 'N/A')}")
            if settings.otel_exporter_otlp_endpoint:
                print(f"View in Jaeger: http://localhost:16686/trace/{result.get('trace_id', '')}")

    except Exception as e:
        logger.error(f"Triage failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="SupportOps Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Triage command
    triage_parser = subparsers.add_parser("triage", help="Run triage on a ticket")
    triage_parser.add_argument(
        "--ticket",
        type=str,
        required=True,
        help="Path to ticket JSON file",
    )

    args = parser.parse_args()

    if args.command == "triage":
        triage_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
