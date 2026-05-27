#!/usr/bin/env bash
# Tiny example CLI: greets a name, or fails if none is given.
set -euo pipefail

if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
  echo "error: a name argument is required" >&2
  exit 1
fi

echo "Hello, $1!"
