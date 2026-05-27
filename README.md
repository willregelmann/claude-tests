# test

[![tests](https://github.com/willregelmann/claude-tests/actions/workflows/tests.yml/badge.svg)](https://github.com/willregelmann/claude-tests/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/willregelmann/claude-tests)](https://github.com/willregelmann/claude-tests/releases)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An LLM-as-evaluator test framework for Claude Code. Write natural language assertions, and an isolated AI agent judges pass/fail with evidence — no shared context with the implementation session.

**The problem.** When the agent that wrote the code also grades it, you get graded-your-own-homework bias. Every test here runs in a fresh subagent with *no* memory of the implementation — the judge sees only the spec and the observable evidence.

**Does an LLM judge reliably?** Measured, not assumed: on a [labeled calibration set](eval/), both Sonnet 4.6 and Haiku 4.5 reached **100% accuracy and 100% run-to-run agreement** — and the harness stays in the repo to catch any regression.

Runs interactively (`/test:run`) with zero extra setup, or [headlessly in CI](#running-in-ci) with JUnit output and exit codes.

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed and authenticated

### Install the plugin

Add the marketplace, then install the plugin:

```
/plugin marketplace add willregelmann/claude-tests
/plugin install test@claude-tests
```

Verify it's loaded — `/test:run` should appear in the command list:

```
/plugin
```

## Usage

> Looking for working templates? See [`examples/`](examples/) — read-only and `Bash` profiles, a server lifecycle, a deterministic CLI check, and a subjective judgment, each ready to copy into `./.claude/tests/`.

### Writing tests

Tests live in your project at `./.claude/tests/<name>/test.md`. Each test gets its own directory with a `test.md` file containing YAML frontmatter and a freeform markdown body:

```yaml
---
name: health-check
tools: ["Read", "Bash", "Grep", "Glob"]
assertions:
  - Exit code is 0
  - Response status is 200
  - Response body contains "status" key with value "ok"
  - Response includes database connectivity check
  - No error messages in log output
---

Start the server: `npm start &` and wait for it to be ready.

Run the health check:

```bash
curl -s http://localhost:3000/health | tee /tmp/health-check.log
```

After evaluation, stop the server and clean up: `kill %1 && rm -f /tmp/health-check.log`
```

Use the `write-test` skill for guided authoring:

> "Write a test for the deploy script"

Claude will walk you through requirements, schema, assertion quality, and consistency checks.

### Running tests

Run from inside a Claude Code session (it's a slash command, not a shell command):

```
# Run all tests
/test:run

# Run a specific test by name
/test:run health-check
```

Multiple tests run in parallel. Results are displayed as a summary:

```
═══ Test Results ═══

[PASS] health-check            (5/5 assertions, 12s)
[FAIL] deploy-rollback         (3/5 assertions, 45s)

─────────────────────
Total: 1/2 passed
```

Failed assertions include evidence and reason.

### Running in CI

The same tests run headlessly via `bin/run-tests.py` — no Claude Code session required. It spawns one isolated `claude -p` evaluator per test, prints the summary, optionally writes JUnit XML, and exits non-zero if any test fails:

```bash
# all tests; write JUnit for CI to ingest
bin/run-tests.py --junit results.xml

# one test, JSON to stdout, choose the evaluator model
bin/run-tests.py health-check --format json --model sonnet
```

Requires Python 3 and the `claude` CLI on `PATH`. Authentication reuses whatever `claude` is logged into; in CI, set `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`.

A ready-to-use GitHub Actions workflow lives at [`.github/workflows/tests.yml`](.github/workflows/tests.yml). Add a `CLAUDE_CODE_OAUTH_TOKEN` repo secret to enable it; without the secret it skips (so the workflow stays green on forks).

> **Note:** evaluators are LLMs, so verdicts can vary run to run. Treat this as a semantic smoke test, not a deterministic unit-test replacement — keep deterministic checks backed by commands whose exact output the evaluator reports.

### How reliable is the evaluator?

That caveat is measured, not hand-waved. [`eval/`](eval/) holds a labeled calibration set and a harness that runs each case through the same evaluator N times and reports accuracy, run-to-run agreement, and the lift from majority voting:

```bash
bin/eval-reliability.py                 # 5 runs/case across the calibration set
bin/eval-reliability.py --min-accuracy 0.9   # CI gate: exit 1 if majority accuracy drops
```

See [`eval/README.md`](eval/README.md) for methodology and the latest numbers. The short version: on the current calibration set, both Sonnet and Haiku scored **100% accuracy and 100% run-to-run agreement** — including the borderline cases, so there was no flakiness for voting to fix. The harness exists to keep that honest: it re-validates the premise and would catch a regression from a prompt change, a model swap, or a harder class of assertion.

### Test file reference

#### Frontmatter fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | — | Unique test identifier (kebab-case) |
| `tools` | No | `["Read", "Grep", "Glob"]` | Selects the evaluator profile (see below) |
| `assertions` | Yes | — | Natural language pass/fail checks |

#### Body

The markdown body is freeform — instructions for the evaluator to follow. Describe what to set up, run, and clean up. The evaluator follows these instructions, then judges each assertion.

#### Evaluator profiles

The evaluator runs as one of two profiles, with tools enforced by the agent definition (not just advertised):

| `tools` declares | Profile | Can run commands? |
|---|---|---|
| omitted, or only `Read`/`Grep`/`Glob` | `test-runner` (read-only) | No |
| includes `Bash` | `test-runner-exec` | Yes |

In the interactive `/test:run` path these two profiles are the only options — the Agent tool fixes a subagent's tools by its definition, so `Read`, `Grep`, `Glob`, and `Bash` are the honored set. Use the read-only profile for tests that just inspect files; include `Bash` whenever the body runs anything.

**Headless runner — arbitrary tools.** `bin/run-tests.py` passes a test's declared `tools` straight through to `claude -p --allowedTools`, so headless evaluators can be granted any tool a test needs beyond the baseline — e.g. `WebFetch`, `WebSearch`, or `mcp__*` tools — on top of the always-present read-only `Read`/`Grep`/`Glob`. (Tools beyond `Read`/`Grep`/`Glob`/`Bash` are honored only by the headless runner; under interactive `/test:run` such a test falls back to the nearest profile, so assertions needing the extra tool will FAIL there.)

### Writing good assertions

Assertions are natural language statements judged by a strict evaluator:

- **Be specific** — "No TODO or FIXME placeholders in committed code" not "code is good quality"
- **Reference observable evidence** — the evaluator must be able to prove it
- **State exact expectations** — "Exit code is 0" not "command succeeds"
- **Test absence explicitly** — "No PRs were created" not "nothing happened"
- **Qualify subjective judgments** — "Posted note is a professional summary mentioning PR links" not "note is good"
- **One check per assertion** — split compound checks into separate items
- **Match tools to assertions** — every assertion must be verifiable with the declared tools

The evaluator requires evidence for every judgment. Partial compliance is FAIL. Missing evidence is FAIL.

## How it works

```
/test:run happy-path
  │
  ▼
commands/run.md (orchestrator)
  │  discovers ./.claude/tests/happy-path/test.md
  │  parses frontmatter + body
  │  picks evaluator profile from `tools`
  │
  ▼
agents/test-runner[-exec].md (isolated evaluator)
  │  no implementation context
  │  follows instructions → evaluates assertions
  │  returns structured VERDICT with evidence
  │
  ▼
Summary report displayed to user
```

The evaluator agent has zero knowledge of how code was implemented. It only sees the test spec. This prevents grading-your-own-homework bias.

For the reasoning behind these choices — the delivery-model tradeoffs, how tool scoping is actually enforced, how deterministic checks work, and what the reliability numbers do and don't prove — see [DESIGN.md](DESIGN.md).

## Plugin structure

```
test/
├── .claude-plugin/
│   ├── plugin.json            # Plugin manifest
│   └── marketplace.json       # Marketplace metadata
├── commands/
│   └── run.md                 # /test:run command
├── agents/
│   ├── test-runner.md         # Isolated evaluator agent (read-only)
│   └── test-runner-exec.md    # Isolated evaluator agent (+ Bash)
├── skills/
│   └── write-test/
│       └── SKILL.md           # Guided test authoring
├── bin/
│   ├── run-tests.py           # Headless runner for CI (JUnit + exit codes)
│   ├── eval-reliability.py    # Measures evaluator accuracy/agreement
│   └── claude_eval.py         # Shared isolated-evaluator call
├── examples/                  # Copy-paste test templates
└── eval/                      # Evaluator reliability harness + calibration set
```

## License

MIT
