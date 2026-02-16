"""Mock ticket system integration tool."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def create_ticket_in_system(ticket: Dict[str, Any]) -> Dict[str, str]:
    """
    Create a ticket in external system (mocked).

    Args:
        ticket: Ticket data dictionary

    Returns:
        Mock result with ticket_id and status
    """
    # Mock implementation - in production this would call ServiceNow, Zendesk, etc.
    ticket_id = f"TICKET-{hash(str(ticket)) % 1000000:06d}"
    logger.info(f"Mock ticket created: {ticket_id}")

    return {
        "ticket_id": ticket_id,
        "status": "created",
        "message": "Ticket created successfully (mock)",
    }
