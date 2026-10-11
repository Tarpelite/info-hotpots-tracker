import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "pipeline", "site"))

import build_site_data as bsd  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "sample_data.json")


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


class BuildSiteDataTest(unittest.TestCase):
    def build(self, data):
        return bsd.clip_strings(bsd.build_site_doc(data))

    def test_keeps_frontend_fields_and_drops_unused(self):
        doc = self.build(load_fixture())
        self.assertEqual(set(doc), {"metadata", "teams", "tables"})
        self.assertEqual(set(doc["metadata"]), {"snapshot_date", "snapshot_file", "imported_at"})
        team = doc["teams"][0]
        self.assertNotIn("raw_records", team)
        self.assertNotIn("scoreBreakdown", team)
        self.assertNotIn("evidence", team["leaders"][0])
        self.assertEqual(team["leaders"][0]["profile_url"], "https://example.com/p1")
        self.assertEqual(set(team["raw_record"]), set(bsd.RAW_RECORD_KEYS))
        self.assertNotIn("evidenceSummary", team["raw_record"])
        self.assertEqual(team["raw_record"]["leader"], {"role": "负责人"})
        self.assertEqual(team["raw_record"]["members"][0], {"id": "m1", "name": "李四"})
        self.assertEqual(set(doc["tables"]["teams"][0]), set(bsd.TABLE_TEAM_KEYS))
        self.assertEqual(set(doc["tables"]["relations"][0]), set(bsd.TABLE_RELATION_KEYS))
        self.assertEqual(set(doc["tables"]["coverage"][0]), set(bsd.TABLE_COVERAGE_KEYS))

    def test_evidence_keeps_identity_fields_and_drops_body(self):
        doc = self.build(load_fixture())
        row = doc["tables"]["evidence"][0]
        self.assertEqual(set(row), set(bsd.TABLE_EVIDENCE_KEYS))
        self.assertEqual(row["evidence_id"], "E1")
        self.assertEqual(row["title"], "标题一")
        self.assertEqual(row["source_url"], "https://example.com/news/1")
        self.assertEqual(row["source_name"], "来源")
        self.assertEqual(row["published_at"], "2026-10-05")
        self.assertNotIn("raw_path", row)
        self.assertNotIn("evidence", doc)

    def test_summary_cut_to_excerpt_limit(self):
        data = load_fixture()
        data["tables"]["evidence"][0]["summary"] = "正" * 600
        doc = self.build(data)
        summary = doc["tables"]["evidence"][0]["summary"]
        self.assertEqual(len(summary), bsd.EXCERPT_LIMIT)
        self.assertTrue(summary.endswith("…"))

    def test_short_summary_unchanged(self):
        doc = self.build(load_fixture())
        self.assertEqual(doc["tables"]["evidence"][0]["summary"], "摘要")

    def test_long_plain_string_capped_and_url_kept(self):
        data = load_fixture()
        data["tables"]["teams"][0]["direction"] = "方" * 800
        long_url = "https://example.com/" + "x" * 700
        data["tables"]["evidence"][0]["source_url"] = long_url
        doc = self.build(data)
        self.assertEqual(len(doc["tables"]["teams"][0]["direction"]), bsd.STRING_LIMIT)
        self.assertEqual(doc["tables"]["evidence"][0]["source_url"], long_url)

    def test_self_check_passes_on_clean_doc(self):
        doc = self.build(load_fixture())
        self.assertEqual(bsd.self_check(doc), [])

    def test_self_check_flags_long_string_and_body_field(self):
        doc = self.build(load_fixture())
        doc["tables"]["teams"][0]["direction"] = "长" * 501
        doc["tables"]["evidence"][0]["raw_text"] = "正文"
        problems = bsd.self_check(doc)
        self.assertTrue(any("501" in p or "> 500" in p for p in problems))
        self.assertTrue(any("body field kept" in p for p in problems))

    def test_self_check_flags_oversize_output(self):
        doc = self.build(load_fixture())
        self.assertTrue(bsd.self_check(doc, max_bytes=10))

    def test_cli_writes_output_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "data.json")
            out = os.path.join(tmp, "site", "data.json")
            with open(src, "w", encoding="utf-8") as handle:
                json.dump(load_fixture(), handle, ensure_ascii=False)
            self.assertEqual(bsd.main(["--data", src, "--output", out]), 0)
            with open(out, encoding="utf-8") as handle:
                self.assertEqual(set(json.load(handle)), {"metadata", "teams", "tables"})

    def test_cli_exits_nonzero_when_self_check_fails(self):
        original = bsd.SIZE_LIMIT
        bsd.SIZE_LIMIT = 10
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, "data.json")
                out = os.path.join(tmp, "data_out.json")
                with open(src, "w", encoding="utf-8") as handle:
                    json.dump(load_fixture(), handle, ensure_ascii=False)
                self.assertEqual(bsd.main(["--data", src, "--output", out]), 1)
        finally:
            bsd.SIZE_LIMIT = original


if __name__ == "__main__":
    unittest.main()
