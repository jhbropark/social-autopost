import json
import unittest
from collections import Counter
from pathlib import Path

RECEIPTS = Path(__file__).resolve().parents[1] / "out" / "daily" / "publish-receipts.json"


class PublishReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(RECEIPTS.read_text(encoding="utf-8"))
        cls.records = cls.document["records"]

    def test_two_runs_have_six_confirmed_posts_and_two_linkedin_failures(self):
        self.assertEqual(Counter(r["outcome"] for r in self.records), {"published": 6, "failed": 2})
        self.assertEqual(Counter(r["platform"] for r in self.records if r["outcome"] == "published"),
                         {"instagram": 4, "facebook": 2})
        self.assertEqual(Counter(r["platform"] for r in self.records if r["outcome"] == "failed"),
                         {"linkedin": 2})

    def test_each_date_has_its_own_run_and_platform_receipts(self):
        for day, run_id in [("2026-10-23", "39892654501"), ("2026-10-24", "40056312336")]:
            rows = [r for r in self.records if r["date"] == day]
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r["run_url"].endswith(run_id) for r in rows))
            self.assertEqual(Counter(r["platform"] for r in rows if r["outcome"] == "published"),
                             {"instagram": 2, "facebook": 1})
            linkedin = [r for r in rows if r["platform"] == "linkedin"]
            self.assertEqual(len(linkedin), 1)
            self.assertEqual(linkedin[0]["outcome"], "failed")
            self.assertEqual(linkedin[0]["http_status"], 401)
            self.assertIsNone(linkedin[0]["provider_id"])
            self.assertIsNone(linkedin[0]["permalink"])

    def test_confirmed_receipts_have_unique_ids_and_source_links(self):
        successes = [r for r in self.records if r["outcome"] == "published"]
        ids = [r["provider_id"] for r in successes]
        self.assertTrue(all(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(r["permalink"].startswith("https://") for r in successes))
        self.assertTrue(all(r["run_url"].startswith("https://github.com/") for r in self.records))


if __name__ == "__main__":
    unittest.main()
