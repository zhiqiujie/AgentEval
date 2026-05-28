"""AgentEval - AI Agent Automated Testing Demo

Usage:
    python run_eval.py                  # default (respects .env settings)
    python run_eval.py --mock           # force mock mode
    python run_eval.py --api            # force real API mode
    python run_eval.py --case-file cases/cases.json
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.agent_client import AgentClient
from src.case_loader import load_cases, CaseLoadError
from src.evaluator import Evaluator
from src.scorer import score_result
from src.reporter import generate_reports


def main():
    parser = argparse.ArgumentParser(description="AgentEval - AI Agent Automated Testing Demo")
    parser.add_argument("--mock", action="store_true", help="Force mock mode")
    parser.add_argument("--api", action="store_true", help="Force real API mode")
    parser.add_argument("--case-file", default="cases/cases.json", help="Path to test cases JSON file")
    args = parser.parse_args()

    # Determine mock/api mode
    use_mock = None
    if args.mock:
        use_mock = True
    elif args.api:
        use_mock = False

    print("=" * 60)
    print("AgentEval - AI Agent Automated Testing Demo")
    print("=" * 60)

    # Load cases
    try:
        cases = load_cases(args.case_file)
    except CaseLoadError as e:
        print(f"[ERROR] Failed to load cases: {e}")
        sys.exit(1)

    print(f"\nLoaded {len(cases)} test cases from {args.case_file}")

    # Initialize client
    client = AgentClient(use_mock=use_mock)
    mode = "MOCK" if client.use_mock else "API"
    print(f"Mode: {mode}")
    if not client.use_mock and not client.api_key:
        print("[WARNING] API key not set, falling back to mock mode")
        client.use_mock = True
        mode = "MOCK (fallback)"

    # Run evaluation
    print("\nRunning evaluation...")
    evaluator = Evaluator(client)
    raw_results = evaluator.run(cases)

    # Score results
    for r in raw_results:
        score, passed, reason = score_result(r)
        r["score"] = score
        r["passed"] = passed
        r["reason"] = reason

    # Generate reports
    generate_reports(raw_results)

    # Terminal summary
    total = len(raw_results)
    passed_count = sum(1 for r in raw_results if r["passed"])
    pass_rate = (passed_count / total * 100) if total > 0 else 0
    avg_latency = sum(r["latency_ms"] for r in raw_results) / total if total > 0 else 0

    print("\n" + "-" * 60)
    print("Evaluation finished.")
    print(f"Total cases: {total}")
    print(f"Passed cases: {passed_count}")
    print(f"Pass rate: {pass_rate:.2f}%")
    print(f"Average latency: {avg_latency:.2f} ms")
    print(f"CSV report: reports/results.csv")
    print(f"HTML report: reports/report.html")

    # Category breakdown
    cat_stats = {}
    for r in raw_results:
        cat = r["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "passed": 0}
        cat_stats[cat]["total"] += 1
        if r["passed"]:
            cat_stats[cat]["passed"] += 1

    print("\nCategory breakdown:")
    for cat in sorted(cat_stats):
        stats = cat_stats[cat]
        cat_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({cat_rate:.1f}%)")

    print("-" * 60)

    return 0 if pass_rate >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
