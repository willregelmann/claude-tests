---
name: write-test
description: Use when the user asks to "write a test", "add a test case", "create a test for X", "new test file", "add a test.md", or otherwise wants to create an AI-evaluated test for the test plugin. Infers what to test from the codebase, adapts the closest example, writes quality assertions, and runs the test to confirm it works.
---

# Write a `test.md` Test File

Goal: produce a high-quality, **runnable** test with minimal back-and-forth. Infer what you can from the repo, confirm only what you must, then prove it runs before handing it over.

## Step 1 — Understand what to test (infer first, ask least)

Work out these five things. **Infer them from the codebase and the developer's request before asking** — read the command, script, or file under test, the code around it, and any relevant docs:

1. **What command or workflow** is being tested
2. **What success looks like** — outputs, side effects, state changes
3. **What failure looks like** — what should NOT happen
4. **Which checks are deterministic** — exit codes, HTTP status, counts, exact strings, file existence
5. **Which checks need genuine LLM judgment** — prose quality, "professional summary," subjective calls

Then **draft first and confirm**, rather than running a quiz: "Based on `deploy.sh`, I'll test that it exits 0 on a clean deploy, writes `dist/`, and prints no errors — anything to add or correct?" Only ask the developer about things you genuinely can't determine from the repo or where intent is ambiguous. Push back only on real vagueness — "it should work" isn't testable; "the build produces `dist/app.js`" is.

### Make deterministic checks deterministic

The evaluator is an LLM. It's reliable for subjective judgment ("is this a professional summary?") but you should not ask it to *eyeball* a deterministic fact. Instead, have the test body **run a command** that produces the concrete value, then write the assertion against that exact output:

- Don't write: "the response looks like valid JSON with the right items."
- Do write a body step — `curl -s localhost:3000/items | jq 'length'` — and the assertion "The item count printed by the `jq 'length'` command is exactly 3."

The shell command does the deterministic work; the evaluator only reports what it printed. This requires `Bash` in the test's `tools` (see Step 3). Reserve unaided LLM assertions for genuinely subjective things.

## Step 2 — Start from the closest example

The repo ships templates in [`examples/`](../../examples/). Adapt the nearest one instead of authoring from a blank file:

| If the test… | Start from |
|---|---|
| only inspects files (docs, config, structure) | `examples/static-docs` |
| runs a command and checks its exit code / output | `examples/cli-exit-code` |
| needs a service or process running | `examples/http-health-check` |
| judges something subjective | `examples/commit-quality` |

Copy its shape, then replace the command, assertions, and any fixtures with the real target.

## Step 3 — Write the test file

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

Under the interactive `/test:run`, only `Read`, `Grep`, `Glob`, and `Bash` are honored — there is no per-tool sandbox beyond these two profiles. If a deterministic check needs to run a command, you must include `Bash`.

The **headless runner** (`bin/run-tests.py`, used in CI) is not limited to the two profiles: it grants the read-only baseline plus whatever you declare, so a test can list arbitrary tools — e.g. `tools: ["WebFetch"]` to let the evaluator read a cited source, or an `mcp__*` tool. Such a test runs fully only headless; under interactive `/test:run` it falls back to the nearest profile and assertions needing the extra tool will FAIL. Prefer deterministic local evidence (`Bash` + a command) where you can; reach for network/MCP tools only when the assertion genuinely needs them.

### Writing the test body

The body should tell the evaluator:

1. **What to run** — the command or setup steps (requires `Bash`)
2. **What to check** — for deterministic facts, write a command that prints the concrete value, then assert against that output
3. **What to clean up** — teardown steps after evaluation (the evaluator runs cleanup even if an assertion fails)

If the test needs helper scripts or fixtures, put them in the test's own directory; the evaluator is told that directory and resolves relative paths against it.

## Step 4 — Write good assertions

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

## Step 5 — Run it and confirm

Don't hand over an unproven test. Run it:

- In a session: `/test:run <name>`
- Headless: `bin/run-tests.py <name>`

Confirm it behaves: a test of working code should **PASS**, and each assertion's evidence should be what you expected to see. If it fails unexpectedly, the cause is usually one of — a deterministic check left to eyeballing, a missing `Bash` in `tools`, a fixture path the evaluator couldn't resolve, or an assertion that bundled two checks. Fix and re-run. Where practical, sanity-check that the test can also **FAIL** by pointing it at broken input — a test that can't fail isn't testing anything.

Final checklist before you call it done:

- [ ] Every deterministic check is backed by a command, not LLM eyeballing
- [ ] `tools` includes `Bash` if (and only if) the body runs a command
- [ ] Subjective assertions are qualified; one check per assertion
- [ ] Cleanup/teardown is described in the body
- [ ] `name` is unique across `./.claude/tests/`
- [ ] The test was actually run and behaved as intended
