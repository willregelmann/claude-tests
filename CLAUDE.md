## Overview

This is the `test` plugin for Claude Code — an LLM-as-evaluator test framework. It spawns isolated subagents to evaluate natural language assertions, preventing grading-your-own-homework bias.

## Architecture

No build step:

- **`commands/run.md`** — `/test:run` command. Orchestrates test discovery, parses `./.claude/tests/*/test.md` files, picks an evaluator profile per test from its `tools`, spawns evaluator agents (in parallel for multiple tests), collects verdicts, displays summary.
- **`agents/test-runner.md`** — Isolated read-only evaluator agent (`tools: Read, Grep, Glob`). Receives only the test spec (no implementation context). Follows instructions → evaluates assertions with evidence → returns structured VERDICT.
- **`agents/test-runner-exec.md`** — Same evaluator, with `Bash` added (`tools: Read, Grep, Glob, Bash`). Spawned for tests that declare `Bash`.
- **`skills/write-test/SKILL.md`** — Guided skill for authoring `test.md` files. Walks through understanding requirements, schema, assertion quality rules, and consistency verification.
- **`bin/run-tests.py`** — Headless runner for CI. Discovers the same `test.md` files, spawns one isolated `claude -p` evaluator per test (sourcing the evaluator system prompt from the `agents/` files so headless matches interactive), emits a summary + optional JUnit XML, and exits non-zero on failure. Stdlib-only Python.
- **`bin/claude_eval.py`** — Shared module wrapping the isolated `claude -p` evaluator call. Used by both the test runner and the reliability harness so they exercise the identical evaluator.
- **`bin/eval-reliability.py`** — Reliability harness. Runs a labeled calibration set (`eval/cases.json`) through the evaluator N times and reports accuracy, run-to-run agreement, and majority-vote lift. Quantifies the framework's core assumption (an LLM can judge assertions reliably).
- **`.claude-plugin/plugin.json`** — Plugin manifest (name, description, version).

## Key Conventions

- Test files live in the consuming project at `./.claude/tests/<name>/test.md` with YAML frontmatter (`name`, `tools`, `assertions`) and a freeform markdown body.
- Two evaluator profiles, enforced by agent-definition frontmatter (per-spawn tool scoping is not supported by the Agent tool): `test-runner` (`Read, Grep, Glob`) and `test-runner-exec` (adds `Bash`). A test's `tools` frontmatter selects the profile — if it includes `Bash`, `/test:run` spawns `test-runner-exec`; otherwise `test-runner`. Only those four tools are honored in the interactive path.
- The headless runner (`bin/run-tests.py`) is not bound by the agent profiles: it grants the read-only baseline (`Read, Grep, Glob`) plus whatever a test's `tools` declares, passing them through to `claude -p --allowedTools`. This lets headless tests use arbitrary tools (`WebFetch`, `WebSearch`, `mcp__*`, …); the evaluator system prompt is generated from those granted tools so it states them accurately. A test needing tools beyond the four interactive ones is therefore headless-only.
- Assertions are natural language pass/fail — no scoring, weights, or severity levels.
- Tests are independent — no ordering or dependencies between them.
- Deterministic checks are done by running a command in the test body (requires `Bash`) and asserting against its printed output.

## Publishing

No build step. Push to GitHub and users install via:

```
/plugin marketplace add <owner>/claude-tests
/plugin install test@claude-tests
```

Marketplace config lives in `.claude-plugin/marketplace.json`. Bump `version` in `.claude-plugin/plugin.json` when releasing changes.
