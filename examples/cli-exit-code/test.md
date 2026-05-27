---
name: cli-exit-code
tools: ["Read", "Grep", "Glob", "Bash"]
assertions:
  - The exit code printed after running greet.sh with a name argument is 0
  - The stdout of greet.sh with the argument "World" is exactly "Hello, World!"
  - The exit code printed after running greet.sh with no argument is 1
  - The error output when greet.sh is run with no argument contains "name argument is required"
---

An exec test: `tools` includes `Bash`, so the evaluator can run commands. This
shows the deterministic pattern — run the command, print the concrete value
(exit code, stdout), and assert against that output rather than asking the model
to judge whether the command "worked".

Assume `greet.sh` is in this test's directory and is executable.

1. Run the success case and print its exit code explicitly:

   ```bash
   ./greet.sh World; echo "exit=$?"
   ```

2. Run the failure case, capturing stderr and the exit code:

   ```bash
   ./greet.sh 2>/tmp/greet.err; echo "exit=$?"; cat /tmp/greet.err
   ```

3. Judge each assertion against the printed `exit=` values and captured output.
   Clean up: `rm -f /tmp/greet.err`.
