"""Policy knowledge base search tool."""

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# Policy directory
POLICY_DIR = Path(__file__).parent.parent.parent / "data" / "policies"


def _load_policies() -> List[Dict[str, str]]:
    """Load all policy documents from data/policies directory."""
    policies = []
    if not POLICY_DIR.exists():
        logger.warning(f"Policy directory not found: {POLICY_DIR}")
        return policies

    for policy_file in POLICY_DIR.glob("*.md"):
        try:
            content = policy_file.read_text(encoding="utf-8")
            # Extract title from first line or filename
            lines = content.split("\n")
            title = lines[0].replace("#", "").strip() if lines else policy_file.stem
            policies.append(
                {
                    "doc_id": policy_file.stem,
                    "title": title,
                    "content": content,
                    "filename": policy_file.name,
                }
            )
        except Exception as e:
            logger.error(f"Error loading policy {policy_file}: {e}")

    return policies


# Cache policies on module load
_POLICIES = _load_policies()


def policy_search(query: str, k: int = 3) -> List[Dict[str, str]]:
    """
    Search policy knowledge base for relevant snippets.

    Args:
        query: Search query string
        k: Number of results to return

    Returns:
        List of policy snippets with title, snippet, and doc_id
    """
    if not _POLICIES:
        logger.warning("No policies loaded")
        return []

    query_lower = query.lower()
    results = []

    for policy in _POLICIES:
        content_lower = policy["content"].lower()
        title_lower = policy["title"].lower()

        # Simple keyword matching
        score = 0
        query_words = query_lower.split()
        for word in query_words:
            if word in title_lower:
                score += 3
            if word in content_lower:
                score += content_lower.count(word)

        if score > 0:
            # Extract relevant snippet (first 300 chars containing query)
            snippet_start = content_lower.find(query_lower)
            if snippet_start == -1:
                # Find first occurrence of any query word
                for word in query_words:
                    snippet_start = content_lower.find(word)
                    if snippet_start != -1:
                        break

            if snippet_start != -1:
                start = max(0, snippet_start - 50)
                end = min(len(policy["content"]), snippet_start + 250)
                snippet = policy["content"][start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(policy["content"]):
                    snippet = snippet + "..."
            else:
                snippet = policy["content"][:300] + "..."

            results.append(
                {
                    "title": policy["title"],
                    "snippet": snippet,
                    "doc_id": policy["doc_id"],
                    "score": score,
                }
            )

    # Sort by score and return top k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]
