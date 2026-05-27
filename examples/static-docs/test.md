---
name: static-docs
assertions:
  - README.md exists at the project root
  - README.md contains a top-level heading (a line starting with "# ")
  - README.md has an "Installation" section (a heading containing the word Installation)
  - README.md has a "Usage" section (a heading containing the word Usage)
  - README.md states a license (the word "License" or "MIT" appears)
---

A read-only test: no `tools` declared, so the evaluator runs with `Read`, `Grep`,
`Glob` only and cannot execute commands. Use this shape for documentation,
configuration, and structural checks.

1. Read `README.md` at the project root.
2. For each assertion, find the relevant heading or text and confirm it is present.
   Report the exact line you found as evidence.
