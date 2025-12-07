#!/usr/bin/env python3
"""
Generate an answer file that matches the expected auto-grader format.

Reads the input questions from cse_476_final_project_test_data.json and writes
an answers JSON file where each entry contains a string under the "output" key.

build_answers() calls run_agent_fast(...) from agent.py to produce real answers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from agent import run_agent_fast

INPUT_PATH = Path("cse_476_final_project_test_data.json")
OUTPUT_PATH = Path("cse_476_final_project_answers.json")


def load_questions(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise ValueError("Input file must contain a list of question objects.")
    return data


def build_answers(questions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    For each question, call the fast agent and store ONLY the final answer
    string under the 'output' key.
    """
    answers: List[Dict[str, str]] = []
    total = len(questions)

    for idx, question in enumerate(questions, start=1):
        q_text = question.get("input", "")
        q_domain = question.get("domain")  # use provided domain label

        # Single fast call per question (no extra reasoning calls)
        final_answer = run_agent_fast(q_text, domain=q_domain)

        # Ensure it's a clean string with no surrounding whitespace
        final_answer = str(final_answer).strip()

        answers.append({"output": final_answer})

        # Light progress log every 200 questions (and at the end)
        if idx % 200 == 0 or idx == total:
            print(f"Finished {idx}/{total} questions")

    return answers


def validate_results(
    questions: List[Dict[str, Any]], answers: List[Dict[str, Any]]
) -> None:
    if len(questions) != len(answers):
        raise ValueError(
            f"Mismatched lengths: {len(questions)} questions vs {len(answers)} answers."
        )
    for idx, answer in enumerate(answers):
        if "output" not in answer:
            raise ValueError(f"Missing 'output' field for answer index {idx}.")
        if not isinstance(answer["output"], str):
            raise TypeError(
                f"Answer at index {idx} has non-string output: {type(answer['output'])}"
            )
        if len(answer["output"]) >= 5000:
            raise ValueError(
                f"Answer at index {idx} exceeds 5000 characters "
                f"({len(answer['output'])} chars). Please make sure your answer "
                f"does not include any intermediate results."
            )


def main() -> None:
    questions = load_questions(INPUT_PATH)
    answers = build_answers(questions)

    with OUTPUT_PATH.open("w", encoding="utf-8") as fp:
        json.dump(answers, fp, ensure_ascii=False, indent=2)

    with OUTPUT_PATH.open("r", encoding="utf-8") as fp:
        saved_answers = json.load(fp)
    validate_results(questions, saved_answers)
    print(
        f"Wrote {len(answers)} answers to {OUTPUT_PATH} "
        "and validated format successfully."
    )


if __name__ == "__main__":
    main()
