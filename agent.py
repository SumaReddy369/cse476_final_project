"""
CSE 476 Final Project
Simple inference-time agent loop.

This file implements:
  1. Domain routing (classification + specialized prompts).
  2. Chain-of-thought style reasoning for math / planning (run_agent).
  3. A faster, single-call path (run_agent_fast) used for final JSON generation,
     which returns ONLY the final answer, with no intermediate reasoning.

You run run_agent_fast() from generate_answer_template.py on the test set.
"""

import os
import re
import requests
from typing import Literal

# ---------------------------------------------------------------------------
# Basic API wrapper
# ---------------------------------------------------------------------------

API_KEY = os.getenv("OPENAI_API_KEY", "cse476")
API_BASE = os.getenv("API_BASE", "http://10.4.58.53:41701/v1")
MODEL = os.getenv("MODEL_NAME", "bens_model")


def call_model_chat_completions(
    prompt: str,
    system: str = "You are a helpful assistant. Reply with only the final answer—no explanation.",
    model: str = MODEL,
    temperature: float = 0.0,
    timeout: int = 60,
) -> dict:
    """
    Calls an OpenAI-style /v1/chat/completions endpoint and returns:
    {
      'ok': bool,
      'text': str or None,
      'raw': dict or None,
      'status': int,
      'error': str or None,
      'headers': dict
    }
    """
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": 256,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        status = resp.status_code
        hdrs = dict(resp.headers)
        if status == 200:
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "ok": True,
                "text": text,
                "raw": data,
                "status": status,
                "error": None,
                "headers": hdrs,
            }
        else:
            try:
                err_text = resp.json()
            except Exception:
                err_text = resp.text
            return {
                "ok": False,
                "text": None,
                "raw": None,
                "status": status,
                "error": str(err_text),
                "headers": hdrs,
            }
    except requests.RequestException as e:
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "status": -1,
            "error": str(e),
            "headers": {},
        }


# ---------------------------------------------------------------------------
# Domain types and (optional) classifier for the "full" agent
# ---------------------------------------------------------------------------

Domain = Literal["math", "coding", "future_prediction", "planning", "common_sense"]

DOMAIN_LABELS: tuple[Domain, ...] = (
    "math",
    "coding",
    "future_prediction",
    "planning",
    "common_sense",
)


def classify_domain(question: str) -> Domain:
    """
    Use the model once to decide which domain a question belongs to.

    NOTE: For the final JSON generation we will usually NOT use this; instead
    we read the 'domain' field from the data file. This function is kept
    for completeness and for your dev-time experiments.
    """
    system = (
        "You are a router that assigns ONE domain label to each question.\n"
        "Valid labels (all lowercase) are:\n"
        "  - math: algebra, arithmetic, equations, inequalities, numeric puzzles.\n"
        "  - coding: programming questions, code explanation, code editing.\n"
        "  - future_prediction: questions asking what will happen in the future.\n"
        "  - planning: requests for plans, step-by-step strategies, schedules.\n"
        "  - common_sense: everyday reasoning, explanations, comparisons, etc.\n"
        "Reply with ONLY the label word, nothing else."
    )

    user = f"Question:\n{question}\n\nDomain label:"

    r = call_model_chat_completions(
        user,
        system=system,
        model=MODEL,
        temperature=0.0,
    )
    raw = (r.get("text") or "").strip().lower()

    for label in DOMAIN_LABELS:
        if label in raw:
            return label

    # Fallback: if something goes wrong, treat as common_sense
    return "common_sense"


# ---------------------------------------------------------------------------
# (Optional) full multi-step agent pieces (kept for report/code review)
# ---------------------------------------------------------------------------


def solve_math(question: str) -> str:
    """
    Math solver: ask for explicit reasoning AND a clearly marked final answer.
    Used by the 'full' agent, not by run_agent_fast.
    """
    system = (
        "You are a careful mathematician. Solve the problem step by step.\n"
        "At the end, after the token 'FINAL_ANSWER:', write ONLY the final "
        "answer (number or simplified expression) on one line."
    )

    r = call_model_chat_completions(
        question,
        system=system,
        model=MODEL,
        temperature=0.0,
    )
    text = (r.get("text") or "").strip()

    marker = "FINAL_ANSWER:"
    if marker.lower() in text.lower():
        idx = text.lower().rfind(marker.lower())
        candidate = text[idx + len(marker) :].strip()
        if candidate:
            return candidate

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[-1] if lines else text


def solve_coding(question: str) -> str:
    system = (
        "You are a senior software engineer.\n"
        "Answer the programming question clearly and concisely.\n"
        "If code is requested, provide ONLY the relevant code (no explanation), "
        "inside a single code block.\n"
        "If an explanation is requested, answer in 3–6 short sentences."
    )

    r = call_model_chat_completions(
        question,
        system=system,
        model=MODEL,
        temperature=0.0,
    )
    return (r.get("text") or "").strip()


def solve_future_prediction(question: str) -> str:
    system = (
        "You are a careful analyst.\n"
        "The user is asking about the future. You must NOT claim to know the "
        "future with certainty.\n"
        "Briefly explain 2–3 plausible scenarios and the main factors.\n"
        "Limit your answer to 4–6 sentences."
    )

    r = call_model_chat_completions(
        question,
        system=system,
        model=MODEL,
        temperature=0.2,
    )
    return (r.get("text") or "").strip()


def solve_planning(question: str) -> str:
    system = (
        "You are an organized planner.\n"
        "Read the user's request and return a concrete numbered plan.\n"
        "Use 5–10 numbered steps. Each step should be a single concise sentence."
    )

    r = call_model_chat_completions(
        question,
        system=system,
        model=MODEL,
        temperature=0.0,
    )
    return (r.get("text") or "").strip()


def solve_common_sense(question: str) -> str:
    system = (
        "You are a helpful assistant focused on everyday reasoning and explanations.\n"
        "Answer in 3–6 sentences, using clear, direct language."
    )

    r = call_model_chat_completions(
        question,
        system=system,
        model=MODEL,
        temperature=0.0,
    )
    return (r.get("text") or "").strip()


def refine_answer(question: str, draft: str, domain: Domain) -> str:
    """
    Second pass: have the model quickly review the draft answer for obvious issues.
    Used only in the 'full' agent, not in run_agent_fast.
    """
    system = (
        "You are a strict reviewer.\n"
        "You are given a QUESTION and a DRAFT ANSWER.\n"
        "If the draft answer looks correct, clear, and relevant, simply repeat it.\n"
        "If you see a clear mistake, contradiction, or missing part, rewrite a better "
        "final answer.\n"
        "Reply with ONLY the improved final answer, no commentary."
    )

    user = f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{draft}\n\nFINAL ANSWER:"

    temp = 0.0 if domain == "math" else 0.1

    r = call_model_chat_completions(
        user,
        system=system,
        model=MODEL,
        temperature=temp,
    )
    text = (r.get("text") or "").strip()
    return text or draft


def run_agent(question: str) -> str:
    """
    Full inference-time loop for a single question (used for dev experiments).

    1. Classify the domain.
    2. Route to the appropriate solver.
    3. Run a self-review pass to catch obvious mistakes.
    """
    domain = classify_domain(question)

    if domain == "math":
        draft = solve_math(question)
    elif domain == "coding":
        draft = solve_coding(question)
    elif domain == "future_prediction":
        draft = solve_future_prediction(question)
    elif domain == "planning":
        draft = solve_planning(question)
    else:
        draft = solve_common_sense(question)

    final = refine_answer(question, draft, domain)
    return final.strip()


# ---------------------------------------------------------------------------
# FAST path: used for final JSON – answer ONLY, no reasoning.
# ---------------------------------------------------------------------------


def run_agent_fast(question: str, domain: str | None = None) -> str:
    """
    Lightweight single-call version used for final test generation.

    It still uses domain-specific prompts, but always asks the model
    to return ONLY the final answer, with no reasoning or scratch work.
    """
    # If we weren't given a domain label from the data, fall back to classifier.
    if domain is None:
        domain = classify_domain(question)

    # Normalize to one of our known labels if someone passes weird casing.
    domain = (domain or "common_sense").lower()
    if domain not in DOMAIN_LABELS:
        domain = "common_sense"

    if domain == "math":
        system = (
            "You are a careful mathematician.\n"
            "Read the math or word problem and solve it internally.\n"
            "Then reply with ONLY the final numeric answer or very short phrase\n"
            "that the student should write. Do NOT show steps or explanation.\n"
            "Do NOT include words like 'Answer', 'Final answer', or any symbols\n"
            "other than what belongs in the answer itself."
        )
    elif domain == "coding":
        system = (
            "You are a coding assistant.\n"
            "Reply with ONLY what the question is asking for: either a single\n"
            "letter choice (A, B, C, etc.), a function name, or a short code\n"
            "snippet. Do NOT add any explanation. Do NOT use markdown or\n"
            "surround your answer with backticks."
        )
    elif domain == "planning":
        system = (
            "You are a planner.\n"
            "Reply with the final plan only. If the question asks for steps,\n"
            "answer as a numbered list of steps. Do NOT include any meta\n"
            "commentary or justification."
        )
    elif domain == "future_prediction":
        system = (
            "You are a concise analyst.\n"
            "Answer the question with 1–3 sentences that directly state your\n"
            "best assessment. Do NOT include phrases like 'In conclusion' or\n"
            "'Explanation:'—just the answer itself."
        )
    else:  # common_sense
        system = (
            "You are a concise question-answering assistant.\n"
            "Reply with ONLY the final answer that directly responds to the\n"
            "question: a short phrase or 1–2 sentences. Do NOT show your\n"
            "reasoning or discuss how you arrived at the answer."
        )

    r = call_model_chat_completions(
        question,
        system=system,
        model=MODEL,
        temperature=0.0,
    )
    text = (r.get("text") or "").strip()

    # Safety net for math: if the model still returns a sentence with numbers,
    # keep just the last number as the final output.
    if domain == "math":
        m = re.findall(r"-?\d+(?:\.\d+)?", text)
        if m:
            # If there is extra text around it, just return the last numeric token.
            if text.strip() != m[-1]:
                return m[-1]

    return text


# ---------------------------------------------------------------------------
# Small manual smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_qs = [
        ("Solve for x: 3x + 5 = 20.", "math"),
        ("Write a Python function that returns the square of a number.", "coding"),
        ("How likely is it that humans will live on Mars by 2100?", "future_prediction"),
        ("Help me plan a 3-month roadmap to learn basic web development.", "planning"),
        ("Why does an ice cube float in water?", "common_sense"),
    ]

    for q, d in demo_qs:
        print("QUESTION:", q)
        print("DOMAIN:", d)
        print("FAST AGENT ANSWER:", run_agent_fast(q, domain=d))
        print("-" * 40)
