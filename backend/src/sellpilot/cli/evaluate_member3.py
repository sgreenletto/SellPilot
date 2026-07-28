import argparse
import asyncio
import json
from pathlib import Path

from sellpilot.core.config import REPOSITORY_ROOT
from sellpilot.evaluation.member3 import evaluate_member3, render_markdown_report

DEFAULT_DATASET = (
    REPOSITORY_ROOT / "data" / "evaluation" / "member3" / "v1" / "evaluation_cases.json"
)
DEFAULT_REPORT = REPOSITORY_ROOT / "docs" / "testing" / "member3-ai-evaluation-report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the reproducible member-three AI quality evaluation"
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true", help="Print the machine-readable result")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(evaluate_member3(args.dataset.resolve()))
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_markdown_report(result), encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"report={report}")
        print(f"failure_count={result['failure_count']}")


if __name__ == "__main__":
    main()
