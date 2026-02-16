"""Eval runner for agent benchmarks."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

from supportops_agent.agents.graph import run_agent
from supportops_agent.config import settings
from supportops_agent.db import init_db
from supportops_agent.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class EvalResult:
    """Single eval test result."""

    def __init__(self, name: str, expected: Dict[str, Any], actual: Dict[str, Any]):
        self.name = name
        self.expected = expected
        self.actual = actual
        self.passed = True
        self.errors: List[str] = []
        self.latency_ms = 0

    def check(self):
        """Check if result matches expectations."""
        result = self.actual.get("result", {})
        classification = result.get("classification", {})
        routing = result.get("routing", {})
        draft = result.get("draft_response", "")

        # Check category
        if "expected_category" in self.expected:
            expected_cat = self.expected["expected_category"]
            actual_cat = classification.get("category", "")
            if expected_cat.lower() != actual_cat.lower():
                self.passed = False
                self.errors.append(
                    f"Category mismatch: expected {expected_cat}, got {actual_cat}"
                )

        # Check priority range
        if "expected_priority_range" in self.expected:
            expected_range = self.expected["expected_priority_range"]
            actual_priority = classification.get("priority", "")
            if isinstance(expected_range, list):
                if actual_priority not in expected_range:
                    self.passed = False
                    self.errors.append(
                        f"Priority mismatch: expected one of {expected_range}, got {actual_priority}"
                    )

        # Check queue
        if "expected_queue" in self.expected:
            expected_queue = self.expected["expected_queue"]
            actual_queue = routing.get("queue", "")
            if expected_queue.lower() != actual_queue.lower():
                self.passed = False
                self.errors.append(
                    f"Queue mismatch: expected {expected_queue}, got {actual_queue}"
                )

        # Check must_not_contain
        if "must_not_contain" in self.expected:
            for forbidden in self.expected["must_not_contain"]:
                if forbidden.lower() in draft.lower():
                    self.passed = False
                    self.errors.append(f"Response contains forbidden text: {forbidden}")

        # Check must_contain
        if "must_contain" in self.expected:
            for required in self.expected["must_contain"]:
                if required.lower() not in draft.lower():
                    self.passed = False
                    self.errors.append(f"Response missing required text: {required}")

        # Check guardrail events
        guardrail_events = result.get("guardrail_events", [])
        error_events = [e for e in guardrail_events if e.get("severity") == "error"]
        if error_events and not self.expected.get("allow_guardrail_errors", False):
            self.passed = False
            self.errors.append(f"Guardrail errors detected: {len(error_events)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "passed": self.passed,
            "errors": self.errors,
            "latency_ms": self.latency_ms,
            "expected": self.expected,
            "actual_category": self.actual.get("result", {}).get("classification", {}).get("category"),
            "actual_priority": self.actual.get("result", {}).get("classification", {}).get("priority"),
        }


def run_eval_suite(suite_path: Path) -> Dict[str, Any]:
    """Run evaluation suite."""
    # Load suite config
    with open(suite_path, "r") as f:
        suite = yaml.safe_load(f)

    # Initialize database (optional)
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database initialization skipped (optional): {e}")

    results: List[EvalResult] = []
    fixtures_dir = Path(suite_path).parent / "fixtures"

    for test_case in suite.get("tests", []):
        name = test_case["name"]
        fixture_file = test_case.get("fixture", f"{name}.json")
        fixture_path = fixtures_dir / fixture_file

        if not fixture_path.exists():
            logger.warning(f"Fixture not found: {fixture_path}, skipping {name}")
            continue

        # Load fixture
        with open(fixture_path, "r") as f:
            ticket_data = json.load(f)

        # Run agent
        logger.info(f"Running test: {name}")
        start_time = time.time()
        try:
            result = run_agent(ticket_data=ticket_data)
            latency_ms = int((time.time() - start_time) * 1000)

            # Create eval result
            eval_result = EvalResult(
                name=name,
                expected=test_case.get("expected", {}),
                actual={"result": result},
            )
            eval_result.latency_ms = latency_ms
            eval_result.check()
            results.append(eval_result)

        except Exception as e:
            logger.error(f"Test {name} failed with exception: {e}", exc_info=True)
            eval_result = EvalResult(name=name, expected=test_case.get("expected", {}), actual={})
            eval_result.passed = False
            eval_result.errors.append(f"Exception: {str(e)}")
            results.append(eval_result)

    # Calculate stats
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0
    avg_latency = sum(r.latency_ms for r in results) / total if total > 0 else 0

    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{pass_rate:.1f}%",
            "avg_latency_ms": int(avg_latency),
        },
        "results": [r.to_dict() for r in results],
    }


def main():
    """Main eval runner entry point."""
    parser = argparse.ArgumentParser(description="Run agent evaluation suite")
    parser.add_argument(
        "--suite",
        type=str,
        default="evals/suite.yaml",
        help="Path to eval suite YAML file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to output JSON results file",
    )

    args = parser.parse_args()
    suite_path = Path(args.suite)

    if not suite_path.exists():
        logger.error(f"Suite file not found: {suite_path}")
        sys.exit(1)

    # Run suite
    results = run_eval_suite(suite_path)

    # Print summary
    print("\n" + "=" * 80)
    print("EVAL SUITE RESULTS")
    print("=" * 80)
    print(f"Total: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Pass Rate: {results['summary']['pass_rate']}")
    print(f"Avg Latency: {results['summary']['avg_latency_ms']}ms")
    print("=" * 80)

    # Print individual results
    print("\nTest Results:")
    for result in results["results"]:
        status = "✓" if result["passed"] else "✗"
        print(f"{status} {result['name']}: {result['actual_category']} / {result['actual_priority']}")
        if result["errors"]:
            for error in result["errors"]:
                print(f"  - {error}")

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")

    # Exit with error code if any failed
    if results["summary"]["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    import sys

    main()
