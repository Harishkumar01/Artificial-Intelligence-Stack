"""Adapt the shared Builder Bootcamp JSONL dataset into Promptfoo tests."""

import json
from pathlib import Path


def generate_tests(config=None):
    """Return Promptfoo test cases while preserving each source ``item``."""
    config = config or {}
    dataset = config.get("dataset", "../data/sample_01.jsonl")
    dataset_path = (Path(__file__).parent / dataset).resolve()

    tests = []
    with dataset_path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            item = json.loads(line)["item"]
            tests.append(
                {
                    "description": item["input"],
                    "vars": {"item": item},
                    "metadata": {
                        "expected_tool": item["expected_tool"],
                        "expected_category": item["expected_category"],
                    },
                }
            )
    return tests
