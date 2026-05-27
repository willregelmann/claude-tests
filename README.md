# test

An LLM-as-evaluator test framework for Claude Code. Write natural language assertions, and an isolated AI agent judges pass/fail with evidence — no shared context with the implementation session.

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

Only `Read`, `Grep`, `Glob`, and `Bash` are honored. Use the read-only profile for tests that just inspect files; include `Bash` whenever the body runs anything.

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
└── skills/
    └── write-test/
        └── SKILL.md           # Guided test authoring
```

## License

MIT
