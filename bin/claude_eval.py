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


def evaluator_system_prompt(tools) -> str:
    """Build the evaluator system prompt for an arbitrary granted tool set.

    The shared evaluator instructions (Process, assertion rules, output format)
    are reused verbatim from the test-runner agent file so headless stays
    aligned with the interactive agent; only the tools paragraph is generated
    dynamically, so the evaluator is told accurately which tools it may use —
    whether that is the read-only baseline, +Bash, or WebFetch/WebSearch/MCP
    tools a test declares.

    `tools` may be a list of tool names or (legacy) a bool meaning "use Bash".
    """
    if isinstance(tools, bool):  # back-compat with the old use_bash signature
        tools = ["Read", "Grep", "Glob", "Bash"] if tools else ["Read", "Grep", "Glob"]
    tools = list(tools)

    # Reuse everything from "**Process:**" onward from the canonical agent file.
    text = (PLUGIN_ROOT / "agents" / "test-runner.md").read_text()
    _, _, body = text.split("---", 2)
    shared = "**Process:**" + body.split("**Process:**", 1)[1]

    intro = (
        "You are an unbiased test evaluator. You have no knowledge of how the "
        "code under test was implemented. You only know what the test file "
        "tells you."
    )
    tool_list = ", ".join(f"`{t}`" for t in tools)
    tools_para = (
        f"You have been granted exactly these tools: {tool_list}. Use them only "
        "as the test body requires, to gather the evidence each assertion needs. "
        "If an assertion requires a capability you have not been granted, judge "
        "that assertion FAIL with that as the reason."
    )
    if "Bash" in tools:
        tools_para += (
            " Run only the commands the test body instructs, and always perform "
            "any cleanup the test body specifies — even if an assertion fails "
            "partway through."
        )
    return f"{intro}\n\n{tools_para}\n\n{shared}".strip()


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
