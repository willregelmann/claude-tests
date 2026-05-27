"""Shared evaluator call used by both the test runner and the reliability
harness, so they exercise the exact same isolated `claude -p` evaluator.

Each call is a fresh subprocess — no shared context — which is what gives the
evaluator its no-implementation-knowledge property.
"""

import json
import subprocess
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def evaluator_system_prompt(use_bash: bool) -> str:
    """Read the plugin's agent file body (sans frontmatter) as the evaluator
    system prompt, so headless matches the interactive agent."""
    agent_file = "test-runner-exec.md" if use_bash else "test-runner.md"
    text = (PLUGIN_ROOT / "agents" / agent_file).read_text()
    _, _, body = text.split("---", 2)
    return body.strip()


def call_evaluator(system_prompt, user_prompt, tools, model, schema):
    """Run one isolated evaluation. Returns (verdict_dict_or_None, seconds, error)."""
    cmd = [
        "claude", "-p", user_prompt,
        "--append-system-prompt", system_prompt,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
    ]
    if tools:
        cmd += ["--allowedTools", *tools, "--permission-mode", "acceptEdits"]
    if model:
        cmd += ["--model", model]

    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start

    if proc.returncode != 0:
        return None, duration, proc.stderr.strip() or "claude exited non-zero"
    try:
        outer = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return None, duration, f"unparseable response: {e}"
    verdict = outer.get("structured_output")
    if verdict is None:
        return None, duration, "no structured_output in response"
    return verdict, duration, None
