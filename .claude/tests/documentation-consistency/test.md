---
name: documentation-consistency
assertions:
  - CLAUDE.md and README.md both use the test path convention ./.claude/tests/<name>/test.md (not the old .claude/tests/*.test.md pattern)
  - Both files describe two evaluator profiles, a read-only one (Read, Grep, Glob) and one that adds Bash
  - No documentation file (README.md, CLAUDE.md, commands/run.md, skills/write-test/SKILL.md) claims co-located MCP tools or a per-test tools/ subdirectory of stdio MCP servers
  - CLAUDE.md lists the correct plugin components (commands/run.md, agents/test-runner.md, agents/test-runner-exec.md, skills/write-test/SKILL.md, bin/run-tests.py, plugin.json)
  - The test path glob in commands/run.md matches the convention documented in CLAUDE.md and README.md (uses .claude/tests/)
  - README.md and CLAUDE.md refer to the command as /test:run, never as a bare /run or a shell command like "claude /run"
  - skills/write-test/SKILL.md describes the same two evaluator profiles as CLAUDE.md
  - README.md includes marketplace.json in its plugin structure tree
---

Check that conventions are described consistently across all documentation files. Documentation drift is the primary risk in a multi-file project like this.

1. Read all four files: `CLAUDE.md`, `README.md`, `skills/write-test/SKILL.md`, and `commands/run.md`.
2. Check the glob pattern used for test discovery in `commands/run.md`.
3. For each assertion, search for the relevant convention in each file and confirm they match.
4. Check that `README.md` lists `marketplace.json` inside `.claude-plugin/` in its structure tree.
