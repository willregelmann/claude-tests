---
description: Run AI-evaluated tests
argument-hint: [name | --all]
allowed-tools: Read, Glob, Bash, Agent
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

**Step 3 — Discover co-located MCP tools:**

For each test directory, check if a `tools/` subdirectory exists (e.g., `.claude/tests/<name>/tools/`). If it does, glob for executable scripts inside it. Each script is a stdio MCP server. Collect the list of tool scripts (absolute paths) per test — these will be passed to the agent spawn so the evaluator can call them as native `mcp__*` tools without needing `Bash` access.

**Step 4 — Execute tests:**

If running multiple tests, assemble all agent prompts first, then spawn all agents in a single message (parallel Agent tool calls — do not call them one at a time).

For each test to run, spawn a `test:test-runner` agent (use `subagent_type: "test:test-runner"`). The agent inherits all tools from the parent context (the Agent tool does not support per-invocation tool scoping). If co-located MCP tools were discovered in Step 3, include them in the agent's prompt so the evaluator knows they are available.

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
