---
name: write-test
description: Use when the user asks to "write a test", "add a test case", "create a test for X", "new test file", "add a test.md", or wants to create an AI-evaluated test for the test plugin. Guides through understanding requirements, writing the test file with correct schema, crafting quality assertions, and verifying consistency.
---

# Write a `test.md` Test File

Follow these four steps in order. Do not skip steps or guess requirements.

## Step 1 — Understand What to Test

Ask the user these questions. Do not proceed until you have answers:

1. **What command or workflow is being tested?** (the exact command to run)
2. **What does success look like?** (expected outputs, side effects, state changes)
3. **What does failure look like?** (what should NOT happen)
4. **Which checks can be deterministic?** (exit codes, HTTP status codes, JSON schema validation, file existence, row counts, string matching — anything with a concrete expected value)
5. **Which checks need LLM judgment?** (prose quality, code style, "professional summary," subjective assessments)

Push the user toward deterministic checks. If they say "the API returns the right data," ask: what fields? what values? That's a deterministic check, not an LLM judgment. Reserve LLM assertions for things that genuinely require interpretation.

If the user's answers are vague, push back. "It should work correctly" is not testable. Ask for specifics.

### Make deterministic checks deterministic

The evaluator is an LLM. It's reliable for subjective judgment ("is this a professional summary?") but you should not ask it to *eyeball* a deterministic fact. Instead, have the test body **run a command** that produces the concrete value, then write the assertion against that exact output:

- Don't write: "the response looks like valid JSON with the right items."
- Do write a body step — `curl -s localhost:3000/items | jq 'length'` — and the assertion "The item count printed by the `jq 'length'` command is exactly 3."

The shell command does the deterministic work; the evaluator only reports what it printed. This requires `Bash` in the test's `tools` (see Step 2). Reserve unaided LLM assertions for genuinely subjective things.

## Step 2 — Write the Test File

Create the file at `./.claude/tests/<name>/test.md` using this schema:

```yaml
---
name: string            # Unique test identifier (required, kebab-case)
tools:                  # Optional. Selects the evaluator profile (see below).
  - string
assertions:             # Natural language pass/fail checks (required, list of strings)
  - string
---

The body is freeform markdown — instructions for the evaluator to follow.
Describe the process: what to set up, what to run, what to clean up.
The evaluator follows these instructions, then judges each assertion.
```

#### Choosing `tools` (the evaluator profile)

The evaluator runs as one of two fixed profiles, selected by the `tools` you declare:

- **Omit `tools`, or list only `Read`/`Grep`/`Glob`** → read-only evaluator. Use this for tests that only inspect files (docs, structure, static content).
- **Include `Bash`** → evaluator that can run commands. Use this whenever the body runs anything (servers, curl, scripts, builds).

Only `Read`, `Grep`, `Glob`, and `Bash` are honored — there is no per-tool sandbox beyond these two profiles. If a deterministic check needs to run a command, you must include `Bash`.

### Writing the test body

The body should tell the evaluator:

1. **What to run** — the command or setup steps (requires `Bash`)
2. **What to check** — for deterministic facts, write a command that prints the concrete value, then assert against that output
3. **What to clean up** — teardown steps after evaluation (the evaluator runs cleanup even if an assertion fails)

## Step 3 — Write Good Assertions

Each assertion is a natural language statement the evaluator judges as PASS or FAIL. Quality rules:

1. **Be specific, not vague.** Write "No TODO or FIXME placeholders in committed code" not "code is good quality."
2. **Reference observable evidence.** The evaluator must be able to prove it. "The function handles edge cases" is unjudgeable without knowing which edge cases.
3. **State exact expectations.** Write "Exit code is 0" not "command succeeds." Write "Exactly 2 PRs created targeting dev and main" not "PRs were created."
4. **Test absence explicitly.** Write "No files were committed (create_or_update_file not called)" not "nothing happened."
5. **Qualify subjective judgments.** Write "Posted ticket note is a professional summary mentioning PR links and the health check feature" not "note is good."
6. **One check per assertion.** Split "PR title follows format AND body contains summary" into two assertions.
7. **Back deterministic assertions with command output.** If an assertion checks a concrete value (status code, row count, file existence), have the body run a command that prints it and assert against that output — "The exit code printed by `echo $?` is 0" rather than asking the LLM to judge whether the command "succeeded."

### How the Evaluator Works

The evaluator is strict:

- **Evidence required** for every judgment — no PASS without proof
- **Partial compliance is FAIL** — "mostly correct" fails
- **No intent inference** — the evaluator judges what it observes, not what was intended
- **Missing evidence is FAIL** — if a file doesn't exist or a query fails, the assertion fails

Write assertions with this strictness in mind. If you write "proper error handling," the evaluator has no standard to judge against. Write "returns HTTP 500 with JSON error body when database is unreachable" instead.

## Step 4 — Verify Consistency

Before finishing, check every item:

- [ ] Every deterministic check is backed by a command in the body, not left to LLM eyeballing
- [ ] `tools` includes `Bash` if (and only if) the body runs any command
- [ ] LLM assertions are reserved for genuinely subjective judgments
- [ ] No assertion combines multiple independent checks (split them)
- [ ] Cleanup/teardown steps are described in the body
- [ ] `name` is unique across all test files in `./.claude/tests/`

If any check fails, fix the test file before presenting it to the user.
