# Evaluator reliability

This framework rests on one assumption: **an isolated LLM can judge a natural-language
assertion reliably enough to trust.** That assumption deserves to be measured, not asserted —
so this directory holds a labeled calibration set and a harness that quantifies how the
evaluator actually behaves.

## What it measures

[`bin/eval-reliability.py`](../bin/eval-reliability.py) runs each case in [`cases.json`](cases.json)
through the **same** isolated evaluator the real tests use (shared via `bin/claude_eval.py`),
N times, and reports three things:

- **Accuracy** — do verdicts match the known-correct label?
- **Agreement** — does the judge return the *same* verdict across runs? (run-to-run stability)
- **Voting lift** — how much does taking the majority verdict over N runs improve accuracy
  versus a single shot? This is the cheap reliability lever the harness exists to quantify.

The artifact under test is passed **inline**, so the environment is fully deterministic and any
variance is the judge's own — not flaky servers or timing.

## The calibration set

Cases are tagged by kind:

- **deterministic** — a script could decide these (counts, exact strings, exit codes). The judge
  should be rock-solid here; instability is a real problem.
- **subjective** — genuinely need interpretation ("explains *why*, not just *what*"). The
  framework's intended sweet spot.
- **borderline** — deliberately near the decision boundary (partial compliance, "exactly", "no
  TODOs", "descriptive name"). These are where flakiness shows up, and where strict-evaluator
  wording matters most.

## Running it

```bash
bin/eval-reliability.py                 # 5 runs/case across the set
bin/eval-reliability.py --runs 7        # more samples = tighter estimate
bin/eval-reliability.py --limit 3       # first 3 cases (cheap dev runs)
bin/eval-reliability.py --min-accuracy 0.9   # exit 1 if majority accuracy below (CI gate)
```

Like the test runner, it reuses the local `claude` login (or `CLAUDE_CODE_OAUTH_TOKEN` /
`ANTHROPIC_API_KEY` in CI).

## Latest results

5 runs per case across all 10 cases, run on two models:

| Model | Single-shot accuracy | Majority-vote accuracy | Mean agreement | Flaky cases |
|---|---|---|---|---|
| Sonnet 4.6 | 100% | 100% | 100% | 0 |
| Haiku 4.5 | 100% | 100% | 100% | 0 |

Per-case (identical on both models): every case returned the correct verdict on all 5 runs —
`PASS×5` or `FAIL×5`, agreement 100%, including all four borderline cases (partial sections,
a `TODO` placeholder, exact-body matching, a non-descriptive function name).

**What this says.** The framework's premise holds, and not marginally: on this set even the small
model judged every assertion correctly and identically across runs. There was no flakiness to
mitigate, so majority voting added nothing (+0 pts) — the run-to-run instability that motivates
voting on older models simply didn't appear. Reproduce with `bin/eval-reliability.py --model sonnet`
(or `--model haiku`).

**What this does *not* say.** Ten cases that both models ace don't probe where judgment *breaks* —
the set doesn't currently discriminate between models or surface a failure mode. That's a known
limitation, not a clean bill of health for every assertion you might write. The harness's standing
value is as a **regression guard**: re-run it after a prompt change, a model swap, or when adding a
harder/adversarial class of assertion, and it will quantify any drop. The voting lever and the
`--min-accuracy` CI gate are there for the day a number moves.

## How to read this (when a number moves)

The current numbers are clean, so this is guidance for when they aren't:

- **A deterministic case going flaky** is the actionable signal — an assertion that *should* be
  machine-checkable is being left to the judge. The fix is in test design: back it with a command
  (see the main README) rather than prose.
- **Borderline flakiness** on a weaker model or a harder assertion is the case for majority voting
  on checks you can't make deterministic — quantified by the single-shot vs. majority gap.
- **A miscalibrated majority** (modal verdict ≠ label) is the serious one: the judge is confidently
  wrong, not merely unstable. That points at the assertion wording or the evaluator prompt, and
  voting won't save it.
