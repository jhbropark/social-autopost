import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "save_publish_state.sh"


def run(cmd, cwd, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def seed(root):
    remote = root / "remote.git"
    run(["git", "init", "--bare", str(remote)], root)
    work = root / "work"
    run(["git", "clone", str(remote), str(work)], root)
    run(["git", "checkout", "-b", "main"], work)
    run(["git", "config", "user.name", "fixture"], work)
    run(["git", "config", "user.email", "fixture@example.invalid"], work)
    (work / "plan.json").write_text("base\n")
    run(["git", "add", "plan.json"], work)
    run(["git", "commit", "-m", "base"], work)
    run(["git", "push", "-u", "origin", "main"], work)
    run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], remote)
    return remote, work


class SavePublishStateTests(unittest.TestCase):
    def test_rejected_push_is_reported_by_helper(self):
        with tempfile.TemporaryDirectory(prefix="state-save-") as td:
            root = Path(td)
            remote, work = seed(root)
            hook = remote / "hooks" / "pre-receive"
            hook.write_text("#!/bin/sh\necho rejected-by-fixture >&2\nexit 1\n")
            hook.chmod(0o755)
            (work / "plan.json").write_text("published locally\n")
            result = run(["bash", str(HELPER), "plan.json", "fixture save"], work, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("rejected-by-fixture", result.stderr)

    def test_rebase_conflict_is_reported_by_helper(self):
        with tempfile.TemporaryDirectory(prefix="state-save-") as td:
            root = Path(td)
            remote, work = seed(root)
            other = root / "other"
            run(["git", "clone", str(remote), str(other)], root)
            run(["git", "config", "user.name", "fixture"], other)
            run(["git", "config", "user.email", "fixture@example.invalid"], other)
            (other / "plan.json").write_text("remote update\n")
            run(["git", "commit", "-am", "remote update"], other)
            run(["git", "push"], other)
            (work / "plan.json").write_text("published locally\n")
            result = run(["bash", str(HELPER), "plan.json", "fixture save"], work, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue("CONFLICT" in result.stdout or "CONFLICT" in result.stderr)

if __name__ == "__main__":
    unittest.main()
