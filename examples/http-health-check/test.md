---
name: http-health-check
tools: ["Read", "Grep", "Glob", "Bash"]
assertions:
  - The HTTP status code printed for GET /health is exactly 200
  - The response body for GET /health is exactly {"status": "ok"}
  - The server process is stopped after evaluation (no python3 server.py left running)
---

An exec test with a full server lifecycle: start a background process, probe it,
assert on the deterministic output, then tear it down. The `Bash` tool is
required.

Assume `server.py` is in this test's directory.

1. Start the server in the background and give it a moment:

   ```bash
   python3 server.py 8137 & echo "pid=$!"; sleep 1
   ```

2. Probe the endpoint, printing the status code and body separately:

   ```bash
   curl -s -o /tmp/health.body -w "status=%{http_code}\n" http://127.0.0.1:8137/health
   cat /tmp/health.body
   ```

3. **Always** stop the server and clean up, even if an assertion fails:

   ```bash
   kill "$pid" 2>/dev/null; sleep 0.5; rm -f /tmp/health.body
   ```

4. Judge the assertions against the printed `status=` line and body. Confirm
   teardown by checking no matching process remains:

   ```bash
   pgrep -f "[s]erver.py 8137" && echo "STILL RUNNING" || echo "stopped"
   ```

   The `[s]` bracket prevents the `pgrep` command from matching its own command
   line — without it, the check reports a false positive.
