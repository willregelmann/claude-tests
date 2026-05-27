#!/usr/bin/env python3
"""Measure how reliable the LLM evaluator is.

The framework's premise is that an isolated LLM can judge assertions. This
harness tests that premise on a labeled calibration set (eval/cases.json): it
runs each case through the *same* evaluator N times and reports

  - accuracy   — do verdicts match the known-correct label?
  - agreement  — does the judge return the same verdict across runs? (stability)
  - the lift from majority voting over N runs vs. a single shot

Single-shot accuracy is computed per run; majority accuracy takes the modal
verdict of the N runs. If voting helps, majority accuracy > single-shot — i.e.
a cheap reliability lever for the deterministic-ish cases.

The artifact under test is passed inline, so the environment is deterministic
and any variance is the judge's own.

Usage:
  bin/eval-reliability.py                 # 5 runs/case, sonnet
  bin/eval-reliability.py --runs 7        # more samples = tighter estimate
  bin/eval-reliability.py --limit 3       # first 3 cases (cheap dev runs)
  bin/eval-reliability.py --min-accuracy 0.9   # exit 1 if majority acc below
"""

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from claude_eval import call_evaluator, evaluator_system_prompt

ASSERTION_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string", "enum": ["PASS", "FAIL"]},
        "evidence": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["result"],
}


def evaluate_case(case, model):
    system = evaluator_system_prompt(["Read", "Grep", "Glob"])
    prompt = (
        "Artifact under test:\n"
        "------------------------------------------------------------\n"
        f"{case['artifact']}\n"
        "------------------------------------------------------------\n\n"
        f"Assertion: {case['assertion']}\n\n"
        "Judge this single assertion as PASS or FAIL based only on the artifact "
        "above. Return the structured verdict."
    )
    verdict, _, error = call_evaluator(system, prompt, tools=[], model=model,
                                       schema=ASSERTION_SCHEMA)
    if error is not None:
        return "ERROR"
    return verdict.get("result", "ERROR")


def run(cases, runs, model, concurrency):
    # Flatten to (case_index, run_index) tasks and run them concurrently.
    tasks = [(ci, case) for ci, case in enumerate(cases) for _ in range(runs)]
    results = [[] for _ in cases]
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [(ci, pool.submit(evaluate_case, case, model)) for ci, case in tasks]
        for ci, fut in futures:
            results[ci].append(fut.result())
    return results


def summarize(cases, results, runs):
    rows = []
    total_correct_runs = 0
    majority_correct = 0
    agreements = []
    for case, verdicts in zip(cases, results):
        counts = Counter(verdicts)
        modal, modal_n = counts.most_common(1)[0]
        agreement = modal_n / len(verdicts)
        agreements.append(agreement)
        correct_runs = sum(1 for v in verdicts if v == case["expected"])
        total_correct_runs += correct_runs
        maj_ok = modal == case["expected"]
        majority_correct += int(maj_ok)
        dist = " ".join(f"{v}×{n}" for v, n in counts.most_common())
        rows.append({
            "name": case["name"], "kind": case["kind"],
            "expected": case["expected"], "distribution": dist,
            "agreement": agreement, "majority": modal, "majority_correct": maj_ok,
        })
    n_cases = len(cases)
    return {
        "rows": rows,
        "single_shot_accuracy": total_correct_runs / (n_cases * runs),
        "majority_accuracy": majority_correct / n_cases,
        "mean_agreement": sum(agreements) / n_cases,
        "flaky": [r["name"] for r in rows if r["agreement"] < 1.0],
        "miscalibrated": [r["name"] for r in rows if not r["majority_correct"]],
        "runs": runs, "n_cases": n_cases,
    }


def print_report(s):
    print(f"\n═══ Evaluator Reliability ({s['runs']} runs × {s['n_cases']} cases) ═══\n")
    print(f"{'case':<24} {'kind':<13} {'exp':<5} {'distribution':<18} {'agree':<6} {'maj':<5} ok")
    print("─" * 80)
    for r in s["rows"]:
        ok = "✓" if r["majority_correct"] else "✗"
        print(f"{r['name']:<24} {r['kind']:<13} {r['expected']:<5} "
              f"{r['distribution']:<18} {r['agreement']*100:>4.0f}% {r['majority']:<5} {ok}")
    print("─" * 80)
    print(f"Single-shot accuracy : {s['single_shot_accuracy']*100:.1f}%  "
          f"(any one run matches the label)")
    print(f"Majority-vote accuracy: {s['majority_accuracy']*100:.1f}%  "
          f"(modal verdict of {s['runs']} runs)")
    lift = (s['majority_accuracy'] - s['single_shot_accuracy']) * 100
    print(f"Voting lift          : {lift:+.1f} pts")
    print(f"Mean agreement       : {s['mean_agreement']*100:.1f}%  (run-to-run stability)")
    if s["flaky"]:
        print(f"Flaky cases          : {', '.join(s['flaky'])}")
    if s["miscalibrated"]:
        print(f"Miscalibrated (maj)  : {', '.join(s['miscalibrated'])}")


def main():
    ap = argparse.ArgumentParser(description="Measure LLM evaluator reliability")
    ap.add_argument("--cases", default="eval/cases.json")
    ap.add_argument("--runs", type=int, default=5, help="evaluations per case (default 5)")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--limit", type=int, help="only the first N cases (cheap dev runs)")
    ap.add_argument("--only", help="run a single case by name")
    ap.add_argument("--concurrency", type=int, default=4, help="parallel evaluations")
    ap.add_argument("--min-accuracy", type=float,
                    help="exit 1 if majority-vote accuracy is below this (0-1)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args()

    cases = json.loads(open(args.cases).read())["cases"]
    if args.only:
        cases = [c for c in cases if c["name"] == args.only]
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        print("no cases selected", file=sys.stderr)
        return 2

    results = run(cases, args.runs, args.model, args.concurrency)
    summary = summarize(cases, results, args.runs)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_report(summary)

    if args.min_accuracy is not None and summary["majority_accuracy"] < args.min_accuracy:
        print(f"\nFAIL: majority accuracy {summary['majority_accuracy']:.2f} "
              f"< threshold {args.min_accuracy}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
