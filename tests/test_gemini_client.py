"""Tests for Gemini client (mocked)."""

import pytest
from unittest.mock import Mock, patch

from supportops_agent.llm.gemini import GeminiClient


@pytest.fixture
def gemini_client():
    """Create Gemini client instance."""
    with patch("supportops_agent.llm.gemini.genai"):
        client = GeminiClient(api_key="test-key", model="gemini-1.5-flash")
        return client


def test_gemini_client_init(gemini_client):
    """Test Gemini client initialization."""
    assert gemini_client.api_key == "test-key"
    assert gemini_client.model_name == "gemini-1.5-flash"


def test_parse_json_response():
    """Test JSON parsing with retry logic."""
    client = GeminiClient(api_key="test-key")
    
    # Valid JSON
    valid_json = '{"key": "value"}'
    result = client._parse_json_response(valid_json)
    assert result == {"key": "value"}
    
    # JSON in markdown code block
    markdown_json = "```json\n{\"key\": \"value\"}\n```"
    result = client._parse_json_response(markdown_json)
    assert result == {"key": "value"}
