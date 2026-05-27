# Examples

Copy-paste templates showing how to write tests for the `test` plugin. Each
folder is a complete `test.md` (plus any fixtures it needs). To use one, copy
it into your project under `./.claude/tests/<name>/` and run `/test:run <name>`
(or `bin/run-tests.py <name>` headlessly).

> These live under `examples/` on purpose — they are **not** discovered by the
> runner, so they won't execute as part of this repo's own suite.

| Example | Profile | Demonstrates |
|---|---|---|
| [`static-docs`](static-docs/) | read-only | Assertions over files only — no commands run |
| [`cli-exit-code`](cli-exit-code/) | exec (`Bash`) | Running a command and asserting its exact exit code + output |
| [`http-health-check`](http-health-check/) | exec (`Bash`) | Server lifecycle: start → probe → assert → tear down |
| [`commit-quality`](commit-quality/) | read-only | A genuinely subjective LLM judgment — the framework's sweet spot |

## Picking a profile

- Omit `tools` (or list only `Read`/`Grep`/`Glob`) → **read-only** evaluator.
- Add `Bash` to `tools` → evaluator that can **run commands**.

## Deterministic vs. subjective

Don't ask the LLM to eyeball a deterministic fact. Have the body run a command
that prints the concrete value, then assert against that output (see
`cli-exit-code` and `http-health-check`). Reserve unaided judgment for things
that actually need interpretation (see `commit-quality`).
