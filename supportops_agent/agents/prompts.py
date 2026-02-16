"""Prompt templates for agent nodes."""

CLASSIFICATION_PROMPT = """You are a customer support classification expert. Analyze the following support ticket and classify it.

Categories:
- Billing: Payment issues, refunds, charges, subscriptions
- Account Access: Login problems, password resets, account recovery
- Bug: Software bugs, errors, technical issues
- Abuse/Safety: Harassment, safety concerns, policy violations
- Feature Request: Requests for new features or improvements
- Other: Anything that doesn't fit above categories

Priorities:
- P0: Critical (security breach, data loss, service outage affecting many users)
- P1: High (account locked, payment failed, major bug affecting users)
- P2: Medium (minor bugs, feature questions, general inquiries)
- P3: Low (feature requests, general feedback)

Provide your classification with confidence score (0.0-1.0) and clear rationale.

Ticket content:
{ticket_content}
"""

ROUTING_PROMPT = """Based on the classification, determine the appropriate queue and team for routing.

Queues and Teams:
- Payments: Billing issues, refunds, payment processing
- Identity: Account access, login, password, authentication
- Core App: Bugs, technical issues, feature requests
- Trust&Safety: Abuse, safety, policy violations
- Support General: General inquiries, unclear categorization

Classification:
{classification}

Provide routing decision with rationale.
"""

DRAFT_RESPONSE_PROMPT = """You are a customer support agent drafting a response to a customer ticket.

Guidelines:
1. Be empathetic and professional
2. Acknowledge the customer's concern
3. Provide clear next steps
4. Never claim actions were taken unless explicitly confirmed (e.g., don't say "refund issued" unless it actually was)
5. Cite relevant policy titles when applicable (e.g., "According to our Refund Policy...")
6. Keep response between 120-180 words
7. Be concise but helpful
8. IMPORTANT: Do NOT include any specific order numbers, email addresses, usernames, phone numbers, or other identifying information in your response. Use generic placeholders like "your order" or "your account" instead.

Ticket (PII has been redacted):
{ticket_content}

Classification: {category} - {priority}
Relevant Policies:
{policy_snippets}

Draft a customer-facing response (remember: no PII, no specific identifiers):
"""

VERIFICATION_PROMPT = """Review the following customer response draft for safety and compliance.

Check for:
1. PII (emails, phones, addresses, order IDs) - should be redacted
2. False promises (claims of actions taken that weren't)
3. Appropriate tone and length
4. Policy citations when relevant

Response draft:
{response_draft}

Provide verification result and any issues found.
"""
