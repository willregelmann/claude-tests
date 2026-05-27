---
name: commit-quality
assertions:
  - The commit message subject line is a concise, imperative summary under ~72 characters
  - The body explains why the change was made, not only what changed
  - The message references the issue or PR it resolves
  - Overall, the message reads as a professional summary a maintainer would accept (no placeholder text, no "wip", no profanity)
---

A subjective test — the framework's real sweet spot. These assertions need
reading comprehension, not an `if` statement, so they're left to the LLM
evaluator. The test is read-only (no `tools` declared).

Note how each subjective assertion is still *qualified*: "professional summary a
maintainer would accept" with concrete disqualifiers, not just "the message is
good". Vague assertions give the evaluator no standard to judge against.

1. Read `sample-commit-msg.txt` in this test's directory.
2. Judge each assertion against the message, quoting the relevant lines as
   evidence. Be strict: a missing issue reference or a what-only body is a FAIL.
