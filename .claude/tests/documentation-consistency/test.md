---
name: documentation-consistency
assertions:
  - CLAUDE.md and README.md both use the test path convention ./.claude/tests/<name>/test.md (not the old .claude/tests/*.test.md pattern)
  - Both files agree that default evaluator tools are Read, Grep, and Glob
  - Both files document the co-located MCP tools convention with a tools/ subdirectory
  - CLAUDE.md lists the correct plugin components (commands/run.md, agents/test-runner.md, skills/write-test/SKILL.md, plugin.json)
  - The test path glob in commands/run.md matches the convention documented in CLAUDE.md and README.md (uses .claude/tests/)
  - skills/write-test/SKILL.md references the same default tools as CLAUDE.md
  - README.md includes marketplace.json in its plugin structure tree
---

Check that conventions are described consistently across all documentation files. Documentation drift is the primary risk in a multi-file project like this.

1. Read all three files: `CLAUDE.md`, `README.md`, `skills/write-test/SKILL.md`.
2. Also read `commands/run.md` to check the glob pattern used for test discovery.
3. For each assertion, search for the relevant convention in each file and confirm they match.
4. Check that `README.md` lists `marketplace.json` inside `.claude-plugin/` in its structure tree.
