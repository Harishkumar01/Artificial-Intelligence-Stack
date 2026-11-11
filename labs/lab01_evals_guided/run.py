"""Compatibility launcher for repository verifiers.

Learners should run Promptfoo directly as documented in this lab's README.
This module remains only because the existing root verification scripts invoke
``python -m labs.lab01_evals_guided.run``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


LAB_DIRECTORY = Path(__file__).resolve().parent
ROOT_DIRECTORY = LAB_DIRECTORY.parent.parent
SOLUTION_CONFIG = LAB_DIRECTORY / "promptfooconfig.solution.yaml"
PROMPTFOO_PACKAGE = "promptfoo@0.121.18"


def _promptfoo_result_issues(payload: Any) -> list[str]:
    """Return operational errors without treating ordinary grader fails as errors."""
    if not isinstance(payload, dict):
        return ["Promptfoo wrote results in an unexpected format."]

    results = payload.get("results")
    if not isinstance(results, dict):
        return ["Promptfoo results are missing the expected results object."]

    issues: list[str] = []
    stats = results.get("stats")
    if not isinstance(stats, dict):
        issues.append("Promptfoo results are missing evaluation statistics.")
    else:
        error_count = stats.get("errors", 0)
        if isinstance(error_count, int) and error_count:
            issues.append(f"Promptfoo reported {error_count} evaluation error(s).")

    def inspect_grading_result(grading_result: Any) -> None:
        if not isinstance(grading_result, dict):
            return
        metadata = grading_result.get("metadata")
        if isinstance(metadata, dict) and metadata.get("graderError") is True:
            issues.append(
                str(grading_result.get("reason") or "A model grader failed.")
            )
        component_results = grading_result.get("componentResults")
        if isinstance(component_results, list):
            for component_result in component_results:
                inspect_grading_result(component_result)

    rows = results.get("results")
    if not isinstance(rows, list):
        issues.append("Promptfoo results are missing item-level results.")
    else:
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_error = row.get("error")
            # Promptfoo 0.121.18: ASSERT=1, ERROR=2. Failed assertions
            # also populate row.error; only that known case is non-operational.
            failure_reason = row.get("failureReason")
            if failure_reason == 2:
                issues.append(str(row_error or "Promptfoo reported an evaluation error."))
            elif row_error and not (type(failure_reason) is int and failure_reason == 1):
                issues.append(str(row_error))
            response = row.get("response")
            if isinstance(response, dict) and response.get("error"):
                issues.append(str(response["error"]))
            inspect_grading_result(row.get("gradingResult"))

    return list(dict.fromkeys(issues))


def main() -> int:
    """Run the completed Promptfoo configuration through ``npx``."""
    load_dotenv(ROOT_DIRECTORY / ".env", override=True)

    node = shutil.which("node")
    if node is None:
        print(
            "Promptfoo requires Node.js. Install a supported Node.js "
            "version, then run this command again.",
            file=sys.stderr,
        )
        return 1

    environment = os.environ.copy()
    # The dataset intentionally includes questionable rows. Preserve the
    # former runner's successful exit when evaluation itself completes.
    environment["PROMPTFOO_PASS_RATE_THRESHOLD"] = "0"

    with tempfile.TemporaryDirectory(
        prefix="builder-bootcamp-promptfoo-"
    ) as temporary_directory:
        output_path = Path(temporary_directory) / "results.json"
        command = [
            node,
            str(ROOT_DIRECTORY / "scripts" / "promptfoo.mjs"),
            "eval",
            "-c",
            str(SOLUTION_CONFIG),
            "--no-cache",
            "--output",
            str(output_path),
        ]
        result = subprocess.run(
            command,
            cwd=LAB_DIRECTORY,
            env=environment,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"Could not read Promptfoo results: {error}", file=sys.stderr)
            return 1

        issues = _promptfoo_result_issues(payload)
        if issues:
            print(
                "Promptfoo completed, but the evaluation encountered an "
                "operational error:",
                file=sys.stderr,
            )
            for issue in issues:
                print(f"- {issue}", file=sys.stderr)
            return 1

    print(
        "Review item-level results from the bundle root with: node scripts/promptfoo.mjs view",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
