"""Tests for agent tools."""

import pytest

from supportops_agent.tools import create_ticket_in_system, policy_search, send_email_preview


def test_policy_search():
    """Test policy search tool."""
    results = policy_search("refund", k=2)
    assert isinstance(results, list)
    assert len(results) <= 2
    if results:
        assert "title" in results[0]
        assert "snippet" in results[0]
        assert "doc_id" in results[0]


def test_policy_search_empty():
    """Test policy search with no matches."""
    results = policy_search("nonexistent_query_xyz_123", k=3)
    assert isinstance(results, list)


def test_create_ticket_in_system():
    """Test ticket creation tool."""
    ticket_data = {"content": "Test ticket", "priority": "P1"}
    result = create_ticket_in_system(ticket_data)
    assert "ticket_id" in result
    assert "status" in result
    assert result["status"] == "created"


def test_send_email_preview():
    """Test email preview tool."""
    result = send_email_preview(
        to="test@example.com",
        subject="Test Subject",
        body="Test email body content",
    )
    assert "status" in result
    assert result["status"] == "preview"
    assert "to" in result
    assert "subject" in result
