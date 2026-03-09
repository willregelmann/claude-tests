---
name: plugin-structure
assertions:
  - plugin.json exists at .claude-plugin/plugin.json
  - plugin.json is valid JSON containing a "name" field with value "test"
  - plugin.json contains a "version" field with a semver string
  - plugin.json contains a "description" field that is a non-empty string
  - commands/run.md exists
  - agents/test-runner.md exists
  - skills/write-test/SKILL.md exists
  - .claude-plugin/marketplace.json exists and is valid JSON containing "name", "owner", and "plugins" fields
  - No other unexpected top-level directories exist besides .claude-plugin, commands, agents, skills, claude, and dotfiles/config
---

Verify the plugin has the expected file structure and valid manifest.

1. Glob for all files in the project root to understand the directory layout.
2. Read `.claude-plugin/plugin.json` and validate its contents.
3. Read `.claude-plugin/marketplace.json` and validate it contains `name`, `owner`, and `plugins` fields.
4. Confirm each expected file exists by reading it.
5. Check that no unexpected top-level directories have been added (the plugin should stay minimal).
