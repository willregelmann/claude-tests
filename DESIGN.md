# Design

The reasoning behind how this plugin is built — the decisions that aren't obvious from the code, and the alternatives that were considered and rejected. Written so the *why* is legible, not just the *what*.

## The problem

When you ask a coding agent to verify its own work, you get graded-your-own-homework bias. The agent that just wrote the code has, in its context, every reason the code *should* work — the intent, the assumptions, the "I'll handle that edge case later." Ask it "did this succeed?" and it grades against intent, not evidence. It is the worst possible judge of its own output for exactly the reason it was the right author.

Traditional tests sidestep this by being mechanical — an assertion either holds or it doesn't, and the code's author can't argue with `assertEqual`. But mechanical tests can't express "the commit message is a professional summary" or "no placeholder code was left behind." Those need judgment. The goal here is to keep the judgment while removing the bias.

## Core principle: evaluator isolation

Every test is judged by a **fresh agent that has no memory of the implementation**. It receives only the test spec — the assertions and the instructions — and the ability to gather evidence (read files, run commands). It never sees the conversation that produced the code, the author's intent, or the reasoning. It can only judge what it can observe.

This is the whole idea. Everything else in the design is in service of preserving that isolation while making it usable. Two consequences fall out immediately:

- The evaluator must be **strict by construction** — evidence required for every verdict, partial compliance is FAIL, no inferring intent. A lenient isolated judge would give back the bias through the front door.
- The isolation has to be **structural, not requested**. "Please ignore what you know" doesn't work on an LLM. The isolation has to come from the agent genuinely not having the context.

## Why a Claude Code plugin (and not an MCP server, CLI, or the Agent SDK)

This was the load-bearing decision, and it isn't obvious. The framework needs two properties at once:

1. **Isolation** — the judge must not share context with the implementer.
2. **Zero extra setup** — a developer should be able to run tests without provisioning a separate API key or paying separately; it should ride on the agent session they already have.

Mapping the options against both:

| Approach | Isolation | Zero extra auth | Notes |
|---|---|---|---|
| **Claude Code plugin** (chosen) | ✅ native subagents | ✅ rides the running session | Subagents get a fresh context window *inside* the already-authenticated session |
| MCP server | ⚠️ | ❌ | An MCP server has no model of its own. To judge, it either asks the host to sample (poorly supported) or brings its own API key — and if it borrows the *calling* agent's context, the bias returns |
| Standalone CLI / Agent SDK | ✅ fresh process | ❌ | A fresh subprocess is genuinely isolated, but every non-interactive path needs its own credential (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`) — there is no reuse of subscription login |

The plugin is the **only** option that delivers both properties simultaneously, because Claude Code subagents provide a fresh context window *within* the authenticated session. An MCP server is actively the wrong shape: consumed by the same agent that wrote the code, it reintroduces exactly the bias the project exists to remove.

The catch — and it's a real one — is that "zero extra auth" only holds **interactively**. The moment you go headless (CI), you need a credential no matter what, because there's no live session to borrow. That's not a flaw in the choice; it's an inherent property of the problem (see [Headless execution](#headless-execution-and-ci)).

## Tool scoping: enforced profiles, not advertised lists

The evaluator should run with least privilege — a docs test has no business running shell commands. The intuitive design is a per-test `tools` list the orchestrator passes when spawning the judge.

That design is a lie, and an early version of this plugin shipped it as one. **The `Agent`/`Task` tool does not support per-spawn tool scoping** — a spawned subagent inherits the parent's tools regardless of what the caller requests. So a per-test `tools` field can be *parsed* but never *enforced*; a test declaring read-only access could still run arbitrary `Bash`.

What Claude Code *does* enforce is the `tools:` field in a subagent's **own definition**. So scoping has to live there. The resolution is two fixed evaluator profiles:

- `agents/test-runner.md` — `Read, Grep, Glob` (read-only)
- `agents/test-runner-exec.md` — adds `Bash`

A test's `tools` frontmatter doesn't *grant* tools; it *selects a profile*. `/test:run` reads it and spawns the matching `subagent_type`. Selection is per-invocation (supported); enforcement is per-definition (supported). The sandbox is real because it's anchored where the platform actually enforces it.

The lesson generalizes: **don't document a capability the platform doesn't enforce.** The honesty pass that fixed this is in the git history on purpose.

## Deterministic checks: commands, not MCP tools

Not everything should be left to LLM judgment. "Exactly 3 items in the response" is a deterministic fact; asking the model to eyeball it invites avoidable error. An earlier design proposed co-located `tools/` directories of stdio MCP servers, auto-discovered per test and exposed as `mcp__*` tools.

This is impossible as described: **Claude Code has no runtime MCP registration.** MCP servers are wired up at session start via `.mcp.json` / `plugin.json`, not discovered and mounted mid-session per test.

The replacement is simpler and needs no new machinery: for a deterministic check, the test body **runs a command that prints the concrete value**, and the assertion is written against that output — "the count printed by `jq 'length'` is exactly 3." The shell does the deterministic work; the evaluator only reports what it saw. Determinism comes from the command, judgment stays with the model, and there's no MCP plumbing that doesn't exist.

## Headless execution and CI

The interactive plugin can't gate a build — and `claude -p` can't run slash commands, so you can't just script `/test:run`. So CI gets a separate entry point, `bin/run-tests.py`, that:

- Discovers the same `.claude/tests/*/test.md` specs.
- Spawns **one `claude -p` subprocess per test** — a fresh process is isolated by construction, which preserves the core principle for free.
- Requests a **structured verdict via `--json-schema`**, so verdicts are machine-readable without parsing free text (the orchestrator parsing prose was itself a fragility worth removing).
- Sources the evaluator's system prompt **from the same `agents/` files** the interactive path uses (via `bin/claude_eval.py`), so headless and interactive judge identically — one evaluator, two front ends.
- Emits JUnit XML and a non-zero exit code.

Auth in CI is a `CLAUDE_CODE_OAUTH_TOKEN` (or API key) — the unavoidable cost of leaving the interactive session. The workflow skips cleanly when the secret is absent, so it stays green on forks rather than failing loudly.

One non-obvious bug surfaced only when real co-located fixtures were used: the evaluator runs from the project root and was never told *where its test's directory was*, so `python3 server.py` couldn't resolve. Both the command and the runner now pass the test directory in the prompt. This is the kind of gap that's invisible until you actually use the thing — which is why the examples exist.

## Measuring the evaluator (reliability)

The framework rests on an empirical claim — "an isolated LLM judges these assertions reliably" — and a claim like that should be measured, not asserted. `bin/eval-reliability.py` runs a labeled calibration set (`eval/cases.json`) through the *same* evaluator N times and reports accuracy, run-to-run agreement, and the lift from majority voting.

The honest result: on the current set, both Sonnet 4.6 and Haiku 4.5 scored **100% accuracy and 100% agreement**, including the borderline cases. The run-to-run instability that would justify majority voting on older models simply isn't present on current ones — voting is retained as a cheap lever, but it's insurance, not a fix for a problem that exists today.

The honest limitation: ten cases that both models ace don't probe where judgment *breaks*. The harness's standing value is as a **regression guard** — re-run it after a prompt change, a model swap, or when adding a harder class of assertion, and it quantifies any drop (with a `--min-accuracy` gate for CI). It validates the premise; it does not certify every assertion anyone might write.

## Notable tradeoffs and limitations

- **Nondeterminism.** LLM verdicts can in principle vary; on current models, measurably, they don't (above). Treat tests as semantic smoke tests, and back anything genuinely deterministic with a command.
- **Cost and latency.** Each test is a full agent invocation — seconds and tokens, not milliseconds. Fine for a focused suite or a CI gate; not a millions-of-assertions unit-test replacement.
- **Cleanup is cooperative.** Teardown lives in the test body and the evaluator is instructed to run it even on failure, but there's no enforced sandbox teardown. Long-lived resources (servers) rely on the body cleaning up.
- **Interactive-only zero-auth.** The headline DX (no extra key) holds in a session; CI needs a credential. Inherent, not incidental.

## Roads not taken

- **MCP server** — wrong shape for the isolation requirement; reintroduces author bias unless it brings its own model.
- **Standalone CLI on the raw API** — isolated, but throws away the zero-auth advantage that motivates the plugin form.
- **Per-test arbitrary tool lists** — can't be enforced by the platform; replaced with two enforced profiles.
- **Co-located MCP tool servers** — no runtime registration exists; replaced with command-output assertions.
- **Scored / weighted / severity-tiered assertions** — deliberately omitted. A test passes only if every assertion passes; natural-language pass/fail keeps the mental model small and the verdicts unambiguous.
