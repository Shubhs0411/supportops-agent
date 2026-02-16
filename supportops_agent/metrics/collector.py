"""Metrics collection for observability."""

import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics for agent performance monitoring."""

    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}
        self._errors: List[Dict[str, Any]] = []

    def increment(self, metric: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(metric, tags)
        self._counters[key] += value

    def record(self, metric: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value."""
        key = self._make_key(metric, tags)
        self._histograms[key].append(value)
        # Keep only last 1000 values
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def set_gauge(self, metric: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        key = self._make_key(metric, tags)
        self._gauges[key] = value

    def record_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Record an error."""
        self._errors.append(
            {
                "type": error_type,
                "message": error_message,
                "context": context or {},
                "timestamp": time.time(),
            }
        )
        # Keep only last 100 errors
        if len(self._errors) > 100:
            self._errors = self._errors[-100:]

    @contextmanager
    def timer(self, metric: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.record(metric, duration, tags)

    def _make_key(self, metric: str, tags: Optional[Dict[str, str]]) -> str:
        """Make metric key with tags."""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{metric}[{tag_str}]"
        return metric

    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics statistics."""
        histogram_stats = {}
        for key, values in self._histograms.items():
            if values:
                histogram_stats[key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": sorted(values)[len(values) // 2] if values else 0,
                    "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
                    "p99": sorted(values)[int(len(values) * 0.99)] if values else 0,
                }

        return {
            "counters": dict(self._counters),
            "histograms": histogram_stats,
            "gauges": dict(self._gauges),
            "error_count": len(self._errors),
            "recent_errors": self._errors[-10:] if self._errors else [],
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()
        self._gauges.clear()
        self._errors.clear()


# Global metrics instance
_metrics_instance: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance
