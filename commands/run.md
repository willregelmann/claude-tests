---
description: Run AI-evaluated tests
argument-hint: [name | --all]
allowed-tools: Read, Glob, Agent
---

Run AI-evaluated tests from `./.claude/tests/`.

**Step 1 — Parse arguments:**

- If `$ARGUMENTS` is empty or `--all`: run all tests
- Otherwise: `$ARGUMENTS` is the test name to run

**Step 2 — Discover tests:**

Glob for `.claude/tests/*/test.md` in the current project.

If no test files are found, display "No test files found in `./.claude/tests/`. Create one with the `write-test` skill." and stop.

Read each file and parse the YAML frontmatter to extract: `name`, `tools`, `assertions`.

If a specific test name was given, find the file whose `name` frontmatter matches. If no match, list the available test names and stop.

**Step 3 — Select an evaluator profile per test:**

The evaluator's tools are fixed by the agent definition it is spawned as (per-spawn tool scoping is not supported — enforcement lives in the agent's own frontmatter). Two profiles exist:

- `test:test-runner` — read-only (`Read`, `Grep`, `Glob`). The default.
- `test:test-runner-exec` — adds `Bash` for tests that run commands.

Map each test's `tools` frontmatter to a profile: if it includes `Bash`, use `test:test-runner-exec`; otherwise use `test:test-runner`. Only `Read`, `Grep`, `Glob`, and `Bash` are supported — if a test declares any other tool, warn that it is not honored and fall back based on whether `Bash` is present.

**Step 4 — Execute tests:**

If running multiple tests, assemble all agent prompts first, then spawn all agents in a single message (parallel Agent tool calls — do not call them one at a time).

For each test to run, spawn the profile selected in Step 3 (set `subagent_type` accordingly). The evaluator's tools are fixed by that agent definition; nothing is passed to scope them per spawn.

Assemble the agent prompt from the test file:

```
Test: <name>

Assertions:
1. <first assertion>
2. <second assertion>
...

<body from test file>
```

**Step 5 — Report results:**

After all agents return, parse each agent's VERDICT block. If an agent's response does not contain a parseable VERDICT block, treat it as an ERROR (distinct from PASS/FAIL) and include the raw response snippet in the summary.

Measure duration yourself (wall-clock time from agent spawn to response) — the agent does not track time.

Display the summary:

```
═══ Test Results ═══

[PASS] happy-path              (11/11 assertions, 157s)
[FAIL] insufficient-context    (3/5 assertions, 45s)

─────────────────────
Total: 1/2 passed
```

For any FAIL result, include the failed assertions with their evidence and reason.
