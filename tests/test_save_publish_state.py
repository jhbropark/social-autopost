import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "save_publish_state.sh"


def run(cmd, cwd, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


class SavePublishStateTests(unittest.TestCase):
    def test_rejected_push_is_reported(self):
        # Isolated bare remote and clones: never contacts a publishing platform
        # or the network. A rejecting hook models a protected/rejected state push.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            remote = root / "remote.git"
            run(["git", "init", "--bare", str(remote)], root)
            work = root / "work"
            run(["git", "clone", str(remote), str(work)], root)
            run(["git", "checkout", "-b", "main"], work)
            run(["git", "config", "user.name", "fixture"], work)
            run(["git", "config", "user.email", "fixture@example.invalid"], work)
            (work / "out/daily").mkdir(parents=True)
            (work / "out/daily/plan.json").write_text('{"_links":{}}')
            run(["git", "add", "."], work)
            run(["git", "commit", "-m", "fixture"], work)
            run(["git", "push", "-u", "origin", "main"], work)
            run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], remote)
            hook = remote / "hooks/pre-receive"
            hook.write_text("#!/bin/sh\necho rejected-by-fixture >&2\nexit 1\n")
            hook.chmod(0o755)
            (work / "out/daily/plan.json").write_text('{"_links":{"instagram":"confirmed"}}')
            result = run(["bash", str(HELPER), "out/daily/plan.json", "fixture save"], work, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("rejected-by-fixture", result.stderr)

    def test_rebase_conflict_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            remote = root / "remote.git"
            run(["git", "init", "--bare", str(remote)], root)
            work = root / "work"
            run(["git", "clone", str(remote), str(work)], root)
            run(["git", "checkout", "-b", "main"], work)
            run(["git", "config", "user.name", "fixture"], work)
            run(["git", "config", "user.email", "fixture@example.invalid"], work)
            (work / "plan.json").write_text("base\n")
            run(["git", "add", "."], work)
            run(["git", "commit", "-m", "base"], work)
            run(["git", "push", "-u", "origin", "main"], work)
            other = root / "other"
            run(["git", "clone", str(remote), str(other)], root)
            run(["git", "config", "user.name", "fixture"], other)
            run(["git", "config", "user.email", "fixture@example.invalid"], other)
            (other / "plan.json").write_text("remote\n")
            run(["git", "commit", "-am", "remote update"], other)
            run(["git", "push"], other)
            (work / "plan.json").write_text("local publish state\n")
            run(["git", "add", "plan.json"], work)
            run(["git", "commit", "-m", "local state"], work)
            result = run(["git", "pull", "--rebase", "-q"], work, check=False)
            self.assertNotEqual(result.returncode, 0)

if __name__ == "__main__":
    unittest.main()
