#!/usr/bin/env python3
"""Minimal health-check server for the example. Stdlib only.

GET /health -> 200 {"status": "ok"}
anything else -> 404

Usage: python3 server.py [port]   (default 8137)
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # quiet


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8137
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
