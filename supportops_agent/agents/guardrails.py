"""Guardrail functions for safety and compliance."""

import logging
import re
from typing import List, Tuple

from supportops_agent.agents.schemas import GuardrailEvent

logger = logging.getLogger(__name__)

# PII patterns
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
ORDER_ID_PATTERN = re.compile(r"\b(?:ORDER|ORD|#)[-]?\d{6,}\b", re.IGNORECASE)

# Address patterns (simplified)
ADDRESS_PATTERN = re.compile(r"\b\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b", re.IGNORECASE)

# Prompt injection patterns
# These are intentionally broad and case-insensitive to catch common jailbreak templates.
PROMPT_INJECTION_PATTERNS = [
    # Direct override attempts
    r"ignore\s+all\s+previous\s+instructions?",  # e.g. "Ignore all previous instructions"
    r"ignore\s+(?:previous|all|the)\s+instructions?",  # simpler cases
    r"forget\s+(?:previous|all|the)\s+instructions?",
    r"disregard\s+(?:previous|above)\s+instructions?",
    # Role / system prompt manipulation
    r"you\s+are\s+now\s+(?:a|an)\s+",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"\[INST\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    # Explicit jailbreak cues
    r"jailbreak",
    r"bypass",
    r"override",
]


def detect_pii(text: str) -> List[Tuple[str, str]]:
    """
    Detect PII in text.

    Returns:
        List of (pii_type, matched_text) tuples
    """
    findings = []

    for match in EMAIL_PATTERN.finditer(text):
        findings.append(("email", match.group()))

    for match in PHONE_PATTERN.finditer(text):
        findings.append(("phone", match.group()))

    for match in CREDIT_CARD_PATTERN.finditer(text):
        findings.append(("credit_card", match.group()))

    for match in SSN_PATTERN.finditer(text):
        findings.append(("ssn", match.group()))

    for match in ORDER_ID_PATTERN.finditer(text):
        findings.append(("order_id", match.group()))

    for match in ADDRESS_PATTERN.finditer(text):
        findings.append(("address", match.group()))

    return findings


def redact_pii(text: str) -> Tuple[str, List[GuardrailEvent]]:
    """
    Redact PII from text.

    Returns:
        Tuple of (redacted_text, guardrail_events)
    """
    events = []
    redacted = text

    findings = detect_pii(text)
    if findings:
        for pii_type, matched in findings:
            if pii_type == "email":
                redacted = redacted.replace(matched, "[EMAIL_REDACTED]")
            elif pii_type == "phone":
                redacted = redacted.replace(matched, "[PHONE_REDACTED]")
            elif pii_type == "credit_card":
                redacted = redacted.replace(matched, "[CARD_REDACTED]")
            elif pii_type == "ssn":
                redacted = redacted.replace(matched, "[SSN_REDACTED]")
            elif pii_type == "order_id":
                redacted = redacted.replace(matched, "[ORDER_ID_REDACTED]")
            elif pii_type == "address":
                redacted = redacted.replace(matched, "[ADDRESS_REDACTED]")

        events.append(
            GuardrailEvent(
                event_type="pii_detected",
                severity="warning",
                message=f"Detected and redacted {len(findings)} PII instances",
                node="sanitize",
            )
        )

    return redacted, events


def detect_prompt_injection(text: str) -> bool:
    """Detect potential prompt injection attempts."""
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def verify_response_safety(
    response: str, policy_snippets: List[dict]
) -> Tuple[bool, List[GuardrailEvent]]:
    """
    Verify response safety and compliance.

    Returns:
        Tuple of (is_safe, guardrail_events)
    """
    events = []
    is_safe = True

    # Check for PII
    pii_findings = detect_pii(response)
    if pii_findings:
        is_safe = False
        events.append(
            GuardrailEvent(
                event_type="pii_in_response",
                severity="error",
                message=f"PII detected in response: {len(pii_findings)} instances",
                node="verify",
            )
        )

    # Check for false promises
    false_promise_patterns = [
        r"refund\s+(?:has\s+been|was)\s+issued",
        r"account\s+(?:has\s+been|was)\s+restored",
        r"issue\s+(?:has\s+been|was)\s+resolved",
        r"we\s+have\s+(?:already|just)\s+(?:refunded|restored|fixed)",
    ]

    response_lower = response.lower()
    for pattern in false_promise_patterns:
        if re.search(pattern, response_lower):
            is_safe = False
            events.append(
                GuardrailEvent(
                    event_type="false_promise",
                    severity="error",
                    message=f"False promise detected: {pattern}",
                    node="verify",
                )
            )

    # Check for policy citation (if applicable)
    if policy_snippets and len(response) > 100:
        has_citation = any(
            snippet.get("title", "").lower() in response_lower
            for snippet in policy_snippets
        )
        if not has_citation and len(policy_snippets) > 0:
            events.append(
                GuardrailEvent(
                    event_type="missing_policy_citation",
                    severity="warning",
                    message="Response should cite relevant policy but doesn't",
                    node="verify",
                )
            )

    # Check length (120-180 words recommended)
    word_count = len(response.split())
    if word_count < 50:
        events.append(
            GuardrailEvent(
                event_type="response_too_short",
                severity="warning",
                message=f"Response is too short: {word_count} words",
                node="verify",
            )
        )
    elif word_count > 250:
        events.append(
            GuardrailEvent(
                event_type="response_too_long",
                severity="warning",
                message=f"Response is too long: {word_count} words",
                node="verify",
            )
        )

    return is_safe, events
