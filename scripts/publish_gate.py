#!/usr/bin/env python3
"""Fail-closed gate for daily external publishing.

A pending marker is committed before any platform calls. It is removed only
after the workflow reports a fully successful publish and state persistence.
If posting or persistence fails, future scheduled runs stop for manual review.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

MARKER = Path("out/daily/publish_pending.json")


def git(*args):
    subprocess.run(["git", *args], check=True)


def guard():
    if MARKER.exists():
        raise SystemExit("Unresolved publish marker exists; reconcile platform posts and state, then clear it manually.")


def begin():
    guard()
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(json.dumps({
        "run_id": os.environ.get("GITHUB_RUN_ID", "unknown"),
        "status": "pending",
    }, indent=2) + "\n", encoding="utf-8")
    git("add", str(MARKER))
    git("commit", "-m", "chore: mark publish pending")
    git("push")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"guard", "begin"}:
        raise SystemExit("usage: publish_gate.py guard|begin")
    (guard if sys.argv[1] == "guard" else begin)()
