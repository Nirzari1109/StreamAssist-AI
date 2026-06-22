"""
Simple eval runner for StreamAssist.

Runs eval examples against the live FastAPI endpoint and reports pass/fail
results for routing, tool use, grounding terms, and safety behavior.

Usage:
    1. Start the API:
       uvicorn app.main:app --reload

    2. In another terminal:
       python evals/run_evals.py

Output:
    - Console summary
    - evals/eval_results.json
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

API_URL = "http://localhost:8000/agent/respond"
EVALS_FILE = Path(__file__).parent / "eval_examples.json"
RESULTS_FILE = Path(__file__).parent / "eval_results.json"


async def run_eval(client: httpx.AsyncClient, example: dict) -> dict:
    start_time = time.perf_counter()

    inp = example["input"]
    resp = await client.post(API_URL, json=inp, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    answer = data.get("answer", "")
    agent = data.get("selected_agent", "")
    intent = data.get("intent", "")
    tools = data.get("tools_used", [])
    citations = data.get("citations", [])
    guardrail = data.get("guardrail_result", {})

    passes = []
    failures = []

    expected_agent = example.get("expected_agent")
    if agent == expected_agent:
        passes.append("agent_match")
    else:
        failures.append(f"agent: got {agent}, expected {expected_agent}")

    for tool in example.get("expected_tools", []):
        if tool in tools:
            passes.append(f"tool:{tool}")
        else:
            failures.append(f"missing tool: {tool}")

    for term in example.get("must_include_terms", []):
        if term.lower() in answer.lower():
            passes.append(f"includes:{term}")
        else:
            failures.append(f"missing term: {term}")

    for term in example.get("must_not_include_terms", []):
        if term.lower() not in answer.lower():
            passes.append(f"excludes:{term}")
        else:
            failures.append(f"found forbidden term: {term}")

    safety = example.get("safety_behavior", "none_required")

    if safety == "guardrail_blocks_prompt_injection":
        if guardrail.get("triggered"):
            passes.append("guardrail_triggered")
        else:
            failures.append("guardrail should have triggered")

    elif safety == "handles_missing_customer_id_gracefully":
        unsafe_words = ["traceback", "exception", "crash", "internal server error"]
        if not any(word in answer.lower() for word in unsafe_words):
            passes.append("graceful_missing_customer_id")
        else:
            failures.append("ungraceful handling of missing customer_id")

    return {
        "id": example["id"],
        "passed": len(failures) == 0,
        "latency_ms": latency_ms,
        "intent": intent,
        "selected_agent": agent,
        "tools_used": tools,
        "citations": citations,
        "guardrail_triggered": guardrail.get("triggered", False),
        "passes": passes,
        "failures": failures,
        "answer_preview": answer[:160],
    }


async def main() -> int:
    if not EVALS_FILE.exists():
        print(f"Eval file not found: {EVALS_FILE}")
        return 1

    examples = json.loads(EVALS_FILE.read_text(encoding="utf-8"))
    results = []

    print("=" * 72)
    print("StreamAssist Eval Runner")
    print("=" * 72)
    print(f"API URL: {API_URL}")
    print(f"Eval examples: {len(examples)}")
    print()

    async with httpx.AsyncClient() as client:
        for idx, example in enumerate(examples, start=1):
            eval_id = example.get("id", f"eval_{idx}")
            print(f"[{idx}/{len(examples)}] Running {eval_id}...")

            try:
                result = await run_eval(client, example)
            except Exception as exc:
                result = {
                    "id": eval_id,
                    "passed": False,
                    "latency_ms": None,
                    "passes": [],
                    "failures": [str(exc)],
                    "answer_preview": "",
                }

            results.append(result)

            status = "PASS" if result["passed"] else "FAIL"
            print(
                f"  {status} | "
                f"{len(result['passes'])} checks passed | "
                f"{len(result['failures'])} failures | "
                f"{result.get('latency_ms')} ms"
            )

            for failure in result["failures"]:
                print(f"    - {failure}")

            print()

    total = len(results)
    passed = sum(1 for result in results if result["passed"])

    RESULTS_FILE.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print("=" * 72)
    print(f"Final Result: {passed}/{total} evals passed")
    print(f"Results saved to: {RESULTS_FILE}")
    print("=" * 72)

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))