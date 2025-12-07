import json
import time
from pathlib import Path

from agent import run_agent

DEV_PATH = Path("cse476_final_project_dev_data.json")

def normalize(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def evaluate():
    with DEV_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    correct = 0

    for i, item in enumerate(data, start=1):
        question = item["input"]
        expected = item["expected_output"]

        pred = run_agent(question)

        if normalize(pred) == normalize(expected):
            correct += 1

        if i % 20 == 0:
            print(f"{i}/{total} done — current accuracy: {correct}/{i}")

        time.sleep(0.2)

    print(f"FINAL: {correct}/{total} correct  (~{correct/total:.2%})")

if __name__ == "__main__":
    evaluate()
