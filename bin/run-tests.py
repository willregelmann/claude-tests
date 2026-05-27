#!/usr/bin/env python3
"""Headless test runner for the `test` plugin — CI-friendly LLM-as-evaluator.

Discovers ./.claude/tests/*/test.md, spawns one isolated `claude -p` evaluator
per test (fresh context = no implementation knowledge, same as the interactive
/test:run), and judges each natural-language assertion. Emits a human summary,
optional JUnit XML, and a non-zero exit code if any test fails.

The evaluator instructions are read from the plugin's own agent files
(agents/test-runner.md, agents/test-runner-exec.md) so the headless and
interactive evaluators stay identical.

Auth: reuses whatever the local `claude` CLI is logged into. In CI, set
CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token`) or ANTHROPIC_API_KEY.

Usage:
  bin/run-tests.py [name]            # run all tests, or one by name
  bin/run-tests.py --junit out.xml   # also write JUnit XML
  bin/run-tests.py --model sonnet    # evaluator model (default: sonnet)
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Verdict schema the evaluator must return as structured output.
VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string", "enum": ["PASS", "FAIL"]},
        "assertions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "assertion": {"type": "string"},
                    "result": {"type": "string", "enum": ["PASS", "FAIL"]},
                    "evidence": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["assertion", "result", "evidence"],
            },
        },
    },
    "required": ["result", "assertions"],
}

READONLY_TOOLS = ["Read", "Grep", "Glob"]
EXEC_TOOLS = ["Read", "Grep", "Glob", "Bash"]


def parse_test_file(path: Path):
    """Parse a test.md into (frontmatter dict, body). Minimal YAML for the
    documented schema: `name` scalar, `tools`/`assertions` string lists."""
    text = path.read_text()
    if not text.startswith("---"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    _, fm_text, body = text.split("---", 2)

    fm = {"name": None, "tools": [], "assertions": []}
    current_list = None
    for raw in fm_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and current_list is not None:
            fm[current_list].append(line.lstrip()[2:].strip().strip('"'))
            continue
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key in ("tools", "assertions"):
                if val:  # inline list e.g. tools: ["Read", "Bash"]
                    fm[key] = [v.strip().strip('"').strip("'")
                               for v in val.strip("[]").split(",") if v.strip()]
                    current_list = None
                else:
                    current_list = key
            elif key == "name":
                fm["name"] = val.strip('"')
                current_list = None
    if not fm["name"]:
        fm["name"] = path.parent.name
    return fm, body.strip()


def discover_tests(name_filter):
    tests = []
    for path in sorted(Path(".claude/tests").glob("*/test.md")):
        fm, body = parse_test_file(path)
        if name_filter and fm["name"] != name_filter:
            continue
        tests.append((fm, body, path.parent))
    return tests


def evaluator_system_prompt(use_bash: bool) -> str:
    """Read the plugin's agent file body (sans frontmatter) as the evaluator
    system prompt, so headless matches the interactive agent."""
    agent_file = "test-runner-exec.md" if use_bash else "test-runner.md"
    text = (PLUGIN_ROOT / "agents" / agent_file).read_text()
    _, _, body = text.split("---", 2)
    return body.strip()


def run_one(fm, body, test_dir, model):
    use_bash = "Bash" in fm["tools"]
    tools = EXEC_TOOLS if use_bash else READONLY_TOOLS
    system = evaluator_system_prompt(use_bash)

    numbered = "\n".join(f"{i}. {a}" for i, a in enumerate(fm["assertions"], 1))
    prompt = (
        f"Test: {fm['name']}\n"
        f"Test directory: {test_dir}\n"
        "Files referenced by this test (scripts, fixtures) live in its test "
        "directory unless stated otherwise; resolve relative paths against it. "
        "Your working directory is the project root.\n\n"
        f"Assertions:\n{numbered}\n\n"
        f"{body}\n\n"
        "Evaluate every assertion and return the structured verdict."
    )

    cmd = [
        "claude", "-p", prompt,
        "--append-system-prompt", system,
        "--allowedTools", *tools,
        "--permission-mode", "acceptEdits",
        "--output-format", "json",
        "--json-schema", json.dumps(VERDICT_SCHEMA),
    ]
    if model:
        cmd += ["--model", model]

    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start

    if proc.returncode != 0:
        return _error_verdict(fm, duration, proc.stderr.strip() or "claude exited non-zero")

    try:
        outer = json.loads(proc.stdout)
        verdict = outer.get("structured_output")
        if verdict is None:
            # Fallback: some versions nest it; otherwise treat as error.
            return _error_verdict(fm, duration, "no structured_output in response")
    except json.JSONDecodeError as e:
        return _error_verdict(fm, duration, f"unparseable response: {e}")

    verdict["name"] = fm["name"]
    verdict["duration"] = duration
    verdict["error"] = None
    return verdict


def _error_verdict(fm, duration, message):
    return {
        "name": fm["name"],
        "result": "ERROR",
        "assertions": [],
        "duration": duration,
        "error": message,
    }


def print_summary(verdicts):
    print("\n═══ Test Results ═══\n")
    passed_tests = 0
    for v in verdicts:
        total = len(v["assertions"])
        npass = sum(1 for a in v["assertions"] if a["result"] == "PASS")
        if v["result"] == "PASS":
            passed_tests += 1
        tag = {"PASS": "PASS", "FAIL": "FAIL", "ERROR": "ERR "}[v["result"]]
        print(f"[{tag}] {v['name']:<28} ({npass}/{total} assertions, {v['duration']:.0f}s)")
        if v["result"] == "ERROR":
            print(f"       error: {v['error']}")
        for a in v["assertions"]:
            if a["result"] == "FAIL":
                print(f"       ✗ {a['assertion']}")
                if a.get("reason"):
                    print(f"         reason: {a['reason']}")
    print("\n────────────────────")
    print(f"Total: {passed_tests}/{len(verdicts)} passed")
    return passed_tests


def write_junit(verdicts, path):
    suites = ET.Element("testsuites")
    for v in verdicts:
        total = len(v["assertions"])
        failures = sum(1 for a in v["assertions"] if a["result"] == "FAIL")
        errors = 1 if v["result"] == "ERROR" else 0
        suite = ET.SubElement(
            suites, "testsuite",
            name=v["name"], tests=str(total),
            failures=str(failures), errors=str(errors),
            time=f"{v['duration']:.3f}",
        )
        if v["result"] == "ERROR":
            case = ET.SubElement(suite, "testcase", name="(evaluation)", classname=v["name"])
            err = ET.SubElement(case, "error", message=v["error"] or "evaluation error")
            err.text = v["error"] or ""
        for a in v["assertions"]:
            case = ET.SubElement(suite, "testcase", name=a["assertion"], classname=v["name"])
            if a["result"] == "FAIL":
                fail = ET.SubElement(case, "failure", message=a.get("reason", "assertion failed"))
                fail.text = f"evidence: {a.get('evidence', '')}\nreason: {a.get('reason', '')}"
    xml = minidom.parseString(ET.tostring(suites)).toprettyxml(indent="  ")
    Path(path).write_text(xml)
    print(f"\nJUnit XML written to {path}")


def main():
    ap = argparse.ArgumentParser(description="Headless LLM-as-evaluator test runner")
    ap.add_argument("name", nargs="?", help="run a single test by name (default: all)")
    ap.add_argument("--junit", metavar="PATH", help="write JUnit XML to PATH")
    ap.add_argument("--model", default="sonnet", help="evaluator model (default: sonnet)")
    ap.add_argument("--format", choices=["text", "json"], default="text",
                    help="summary format on stdout (default: text)")
    args = ap.parse_args()

    tests = discover_tests(args.name)
    if not tests:
        target = f" matching '{args.name}'" if args.name else ""
        print(f"No test files found{target} in ./.claude/tests/", file=sys.stderr)
        return 2

    verdicts = [run_one(fm, body, test_dir, args.model) for fm, body, test_dir in tests]

    if args.format == "json":
        print(json.dumps(verdicts, indent=2))
    else:
        print_summary(verdicts)

    if args.junit:
        write_junit(verdicts, args.junit)

    failed = sum(1 for v in verdicts if v["result"] != "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
