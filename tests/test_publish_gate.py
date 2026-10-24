import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publish_gate


class PublishGateTests(unittest.TestCase):
    def test_guard_allows_clean_state(self):
        with tempfile.TemporaryDirectory() as td, patch.object(publish_gate, "MARKER", Path(td) / "pending.json"):
            publish_gate.guard()

    def test_guard_blocks_unresolved_state(self):
        with tempfile.TemporaryDirectory() as td, patch.object(publish_gate, "MARKER", Path(td) / "pending.json"):
            publish_gate.MARKER.write_text('{"status":"pending"}')
            with self.assertRaisesRegex(SystemExit, "Unresolved publish marker"):
                publish_gate.guard()

    def test_begin_pushes_marker_before_publish(self):
        with tempfile.TemporaryDirectory() as td, patch.object(publish_gate, "MARKER", Path(td) / "out/pending.json"), patch.object(publish_gate, "git") as git:
            publish_gate.begin()
            self.assertTrue(publish_gate.MARKER.exists())
            self.assertEqual([c.args for c in git.call_args_list], [
                ("add", str(publish_gate.MARKER)),
                ("commit", "-m", "chore: mark publish pending"),
                ("push",),
            ])


if __name__ == "__main__":
    unittest.main()
