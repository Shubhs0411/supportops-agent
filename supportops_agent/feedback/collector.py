"""Collect and store human feedback for agent improvements."""

import logging
import time
from typing import Any, Dict, List, Optional

from supportops_agent.db import get_db
from supportops_agent.db.models import AgentRun

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects human feedback on agent outputs."""

    def __init__(self):
        """Initialize feedback collector."""
        self._feedback: List[Dict[str, Any]] = []

    def record_feedback(
        self,
        agent_run_id: int,
        feedback_type: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        corrections: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record human feedback on an agent run.

        Args:
            agent_run_id: ID of the agent run
            feedback_type: Type of feedback (correction, rating, comment)
            rating: Optional rating (1-5)
            comment: Optional text comment
            corrections: Optional dict of corrections (e.g., {"category": "Billing", "priority": "P2"})
        """
        feedback = {
            "agent_run_id": agent_run_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "comment": comment,
            "corrections": corrections,
            "timestamp": time.time(),
        }

        self._feedback.append(feedback)

        # Persist to database
        try:
            with get_db() as db:
                agent_run = db.query(AgentRun).filter(AgentRun.id == agent_run_id).first()
                if agent_run:
                    # Store feedback in agent_run (we could add a feedback table later)
                    if not agent_run.final_output:
                        agent_run.final_output = {}
                    if "feedback" not in agent_run.final_output:
                        agent_run.final_output["feedback"] = []
                    agent_run.final_output["feedback"].append(feedback)
                    db.commit()
                    logger.info(f"Feedback recorded for agent_run_id={agent_run_id}")
        except Exception as e:
            logger.error(f"Failed to persist feedback: {e}")

    def get_feedback_for_run(self, agent_run_id: int) -> List[Dict[str, Any]]:
        """Get all feedback for a specific agent run."""
        return [f for f in self._feedback if f["agent_run_id"] == agent_run_id]

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """Get all collected feedback."""
        return self._feedback


# Global feedback collector
_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get global feedback collector."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector
