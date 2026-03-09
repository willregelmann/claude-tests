---
name: write-test
description: Use when the user asks to "write a test", "add a test case", "create a test for X", "new test file", "add a test.md", or wants to create an AI-evaluated test for the test plugin. Guides through understanding requirements, writing the test file with correct schema, crafting quality assertions, and verifying consistency.
---

# Write a `test.md` Test File

Follow these five steps in order. Do not skip steps or guess requirements.

## Step 1 — Understand What to Test

Ask the user these questions. Do not proceed until you have answers:

1. **What command or workflow is being tested?** (the exact command to run)
2. **What does success look like?** (expected outputs, side effects, state changes)
3. **What does failure look like?** (what should NOT happen)
4. **Which checks can be deterministic?** (exit codes, HTTP status codes, JSON schema validation, file existence, row counts, string matching — anything with a concrete expected value)
5. **Which checks need LLM judgment?** (prose quality, code style, "professional summary," subjective assessments)

Push the user toward deterministic checks. If they say "the API returns the right data," ask: what fields? what values? That's a deterministic check, not an LLM judgment. Reserve LLM assertions for things that genuinely require interpretation.

If the user's answers are vague, push back. "It should work correctly" is not testable. Ask for specifics.

## Step 2 — Build Co-located Tools for Deterministic Checks

Before writing the test file, take every deterministic check from Step 1 and turn it into a co-located MCP tool. This is the most important step — **deterministic checks should not be left to LLM judgment.**

### Why co-located tools matter

The evaluator agent is an LLM. It's great at subjective judgment ("is this a professional summary?") but unreliable for deterministic checks ("does the JSON response contain exactly 3 items?"). Co-located tools give you:

- **Deterministic results** — a script returns pass/fail, not an LLM's interpretation
- **Typed interfaces** — the evaluator calls a named tool with defined parameters, not a freeform bash command
- **Reproducibility** — the same tool gives the same answer every time
- **Scoped access** — each tool does one thing with a clear contract

### How to create them

Place tools in `./.claude/tests/<name>/tools/`. Each script is a stdio MCP server — it reads JSON-RPC from stdin and writes JSON-RPC to stdout.

```
./.claude/tests/health-check/
├── test.md
└── tools/
    ├── check-status.sh        # Hits endpoint, returns status code
    └── validate-response.py   # Validates JSON schema of response
```

### Guidelines

- **One tool per concern.** `check-status` and `validate-schema` are separate tools.
- **Return structured data.** The tool's response should include the evidence — don't just return true/false. Return the actual value so the evaluator can report it.
- **Make scripts executable.** `chmod +x` each script.
- **Use any language.** Bash, Python, Node — whatever suits the check. The only requirement is stdin/stdout JSON-RPC.
- **Reference tools in the test body.** Tell the evaluator which tool to call and what to check. Example: "Use the `check_status` tool to verify the endpoint returns 200."

The `/run` command auto-discovers `tools/` and exposes them to the evaluator as `mcp__*` tools — no configuration needed.

### What to make into a co-located tool

| Check type | Co-located tool? | Example |
|---|---|---|
| Exit code / status code | Yes | `check-exit-code.sh` |
| JSON schema validation | Yes | `validate-response.py` |
| Row count / record exists | Yes | `check-db.sh` |
| File exists / has content | Yes | `check-file.sh` |
| String matching / regex | Yes | `match-output.sh` |
| HTTP endpoint returns expected data | Yes | `check-endpoint.sh` |
| "Professional summary" / prose quality | No — LLM assertion | |
| "Descriptive commit messages" | No — LLM assertion | |
| "Proper error handling" | No — LLM assertion | |

**Rule of thumb:** If you can write an `if` statement for it, it should be a co-located tool. If it requires reading comprehension, it's an LLM assertion.

## Step 3 — Write the Test File

Create the file at `./.claude/tests/<name>/test.md` using this schema:

```yaml
---
name: string            # Unique test identifier (required, kebab-case)
tools:                  # Tools available to the evaluator (optional, defaults to ["Read", "Grep", "Glob"])
  - string
assertions:             # Natural language pass/fail checks (required, list of strings)
  - string
---

The body is freeform markdown — instructions for the evaluator to follow.
Describe the process: what to set up, what to run, what to clean up.
The evaluator follows these instructions, then judges each assertion.
```

### Writing the test body

The body should tell the evaluator:

1. **What to run** — the command or setup steps
2. **Which co-located tools to call** — name them explicitly, e.g. "Use the `check_status` tool to verify the endpoint returns 200"
3. **What to clean up** — teardown steps after evaluation

For assertions backed by co-located tools, write the assertion to match the tool's output. Example: "The `check_status` tool returns HTTP 200 for the /health endpoint" — this is deterministic because the tool does the actual check, and the evaluator just reports what the tool returned.

## Step 4 — Write Good Assertions

Each assertion is a natural language statement the evaluator judges as PASS or FAIL. Quality rules:

1. **Be specific, not vague.** Write "No TODO or FIXME placeholders in committed code" not "code is good quality."
2. **Reference observable evidence.** The evaluator must be able to prove it. "The function handles edge cases" is unjudgeable without knowing which edge cases.
3. **State exact expectations.** Write "Exit code is 0" not "command succeeds." Write "Exactly 2 PRs created targeting dev and main" not "PRs were created."
4. **Test absence explicitly.** Write "No files were committed (create_or_update_file not called)" not "nothing happened."
5. **Qualify subjective judgments.** Write "Posted ticket note is a professional summary mentioning PR links and the health check feature" not "note is good."
6. **One check per assertion.** Split "PR title follows format AND body contains summary" into two assertions.
7. **Back deterministic assertions with co-located tools.** If an assertion checks a concrete value (status code, row count, file existence), there should be a co-located tool for it. The assertion then becomes "The `check_status` tool returns 200" rather than asking the LLM to run curl and interpret the result.

### How the Evaluator Works

The evaluator is strict:

- **Evidence required** for every judgment — no PASS without proof
- **Partial compliance is FAIL** — "mostly correct" fails
- **No intent inference** — the evaluator judges what it observes, not what was intended
- **Missing evidence is FAIL** — if a file doesn't exist or a query fails, the assertion fails

Write assertions with this strictness in mind. If you write "proper error handling," the evaluator has no standard to judge against. Write "returns HTTP 500 with JSON error body when database is unreachable" instead.

## Step 5 — Verify Consistency

Before finishing, check every item:

- [ ] Every deterministic check has a co-located tool (not left to LLM judgment)
- [ ] Every co-located tool referenced in the body exists in `tools/` and is executable
- [ ] Co-located tools return structured data with evidence, not just true/false
- [ ] LLM assertions are reserved for genuinely subjective judgments
- [ ] No assertion combines multiple independent checks (split them)
- [ ] `name` is unique across all test files in `./.claude/tests/`

If any check fails, fix the test file before presenting it to the user.
