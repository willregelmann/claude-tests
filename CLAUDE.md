## Overview

This is the `test` plugin for Claude Code — an LLM-as-evaluator test framework. It spawns isolated subagents to evaluate natural language assertions, preventing grading-your-own-homework bias.

## Architecture

Four files, no build step:

- **`commands/run.md`** — `/run` command. Orchestrates test discovery, parses `./.claude/tests/*/test.md` files, spawns `test-runner` agents (in parallel for multiple tests), collects verdicts, displays summary.
- **`agents/test-runner.md`** — Isolated evaluator agent. Receives only the test spec (no implementation context). Follows instructions → evaluates assertions with evidence → returns structured VERDICT.
- **`skills/write-test/SKILL.md`** — Guided skill for authoring `test.md` files. Walks through understanding requirements, schema, assertion quality rules, and consistency verification.
- **`.claude-plugin/plugin.json`** — Plugin manifest (name, description, version).

## Key Conventions

- Test files live in the consuming project at `./.claude/tests/<name>/test.md` with YAML frontmatter (`name`, `tools`, `assertions`) and a freeform markdown body.
- The test-runner agent defaults to read-only tools `["Read", "Grep", "Glob"]`. Each test file can override via `tools` frontmatter.
- Assertions are natural language pass/fail — no scoring, weights, or severity levels.
- Tests are independent — no ordering or dependencies between them.
- Test directories can contain a `tools/` subdirectory with stdio MCP servers for deterministic checks. The `/run` command auto-discovers them and exposes them to the evaluator as native `mcp__*` tools.

## Publishing

No build step. Push to GitHub and users install via:

```
/plugin marketplace add <owner>/claude-tests
/plugin install test@claude-tests
```

Marketplace config lives in `.claude-plugin/marketplace.json`. Bump `version` in `.claude-plugin/plugin.json` when releasing changes.
