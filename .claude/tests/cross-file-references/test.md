---
name: cross-file-references
assertions:
  - Every file path mentioned in CLAUDE.md's Architecture section exists on disk
  - The plugin structure tree in README.md matches the actual directory layout (every listed file exists)
  - No test.md files reference tools or files that do not exist in the project
---

Verify that cross-file references are not broken — every path mentioned in documentation actually exists.

1. Read `CLAUDE.md` and extract file paths from the Architecture section. Glob or read each one to confirm it exists.
2. Read `README.md` and find the plugin structure tree. Verify each listed file exists.
3. Glob for any `test.md` files in `./.claude/tests/` and read them. If they reference specific file paths, verify those exist.
