"""SQLAlchemy database models."""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Ticket(Base):
    """Support ticket model."""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True, nullable=False)
    raw_content = Column(Text, nullable=True)  # Only if STORE_RAW=true
    sanitized_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "sanitized_content": self.sanitized_content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentRun(Base):
    """Agent execution run model."""

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, index=True, nullable=False)
    request_id = Column(String, index=True, nullable=True)
    trace_id = Column(String, index=True, nullable=True)
    classification_result = Column(JSON, nullable=True)
    routing_result = Column(JSON, nullable=True)
    draft_response = Column(Text, nullable=True)
    final_output = Column(JSON, nullable=False)
    guardrail_events = Column(JSON, nullable=True)
    confidence = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "classification_result": self.classification_result,
            "routing_result": self.routing_result,
            "draft_response": self.draft_response,
            "final_output": self.final_output,
            "guardrail_events": self.guardrail_events,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ToolCall(Base):
    """Tool call audit model."""

    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, index=True, nullable=False)
    tool_name = Column(String, nullable=False)
    tool_input = Column(JSON, nullable=True)
    tool_output = Column(JSON, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_run_id": self.agent_run_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
