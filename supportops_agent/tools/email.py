"""Email preview tool (mocked)."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def send_email_preview(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Preview email that would be sent (mocked, no actual email).

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body

    Returns:
        Mock result with preview info
    """
    # Mock implementation - in production this would send via SendGrid, SES, etc.
    logger.info(f"Email preview (mock): To={to}, Subject={subject}")

    return {
        "status": "preview",
        "to": to,
        "subject": subject,
        "body_preview": body[:200] + "..." if len(body) > 200 else body,
        "message": "Email preview generated (mock - no email sent)",
    }
