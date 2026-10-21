"""Behavior tests, isolated fixtures only. No semantic-accuracy claims from mocked reviews."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("maintenance_check", Path(__file__).with_name("check.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.folder = self.root / "state"
        self.folder.mkdir()
        self.config = {"name": "test", "files": ["A.md", "B.md"], "index_roots": ["notes"],
                       "questions": [{"id": "Q", "prompt": "是否有证据？"}]}
        (self.vault / "notes").mkdir()
        self.write("A.md", "# A\n已有边界：未验证检索收益。\n[[B]]\n")
        self.write("B.md", "# B\n只有预设响应模拟。\n")
        # Names are indexed independently of the explicitly selected source files.
        self.config["index_roots"] = ["."]

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        p = self.vault / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def scan(self, limit=None):
        return m.scan(self.vault, self.config, self.folder, limit)

    def findings(self, state):
        return [f for r in state["completed"].values() for f in r["findings"]]

    def review(self, state):
        return {"snapshot_id": state["snapshot_id"], "reviewer": "test fixture, not an AI evaluation",
                "method": "预置记录，仅测试证据交接", "limitations": "不验证语义判断质量",
                "decisions": [{"question_id": "Q", "decision": "无需动作", "reason": "边界已明确",
                               "action": "保留原文", "evidence": [{"path": "A.md", "line": 2, "quote": "未验证检索收益"}]}]}

    def test_baseline_remains_pending_and_inputs_unchanged(self):
        before = {p: p.read_bytes() for p in self.vault.rglob("*.md")}
        state = self.scan()
        self.assertEqual(state["status"], "awaiting_semantic_review")
        self.assertEqual(self.findings(state), [])
        self.assertEqual(before, {p: p.read_bytes() for p in self.vault.rglob("*.md")})

    def test_missing_link_location_and_id_stability(self):
        self.write("A.md", "# A\n[[Missing]]\n")
        first = self.findings(self.scan())[0]
        self.assertEqual((first["line"], first["kind"], first["decision"]), (2, "missing", "建议修订"))
        self.write("A.md", "# A\n\n[[Missing]]\n")
        second = self.findings(self.scan())[0]
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["line"], 3)

    def test_code_comments_and_display_alias_are_not_links_to_missing_pages(self):
        self.write("A.md", "# A\n[[B|别名]]\n`[[Inline]]`\n````md\n[[Fence]]\n```\n[[StillFence]]\n````\n<!-- [[Comment]] -->\n%% [[Comment2]] %%\n\\[[Escaped]]\n")
        self.assertEqual(self.findings(self.scan()), [])

    def test_alias_candidate_and_ambiguous_name_are_not_guessed(self):
        self.write("notes/C.md", "---\naliases:\n  - 旧称\n---\n# C\n")
        self.write("notes/B.md", "# Another B\n")
        self.write("A.md", "[[旧称]]\n[[B]]\n")
        self.assertEqual({f["kind"] for f in self.findings(self.scan())}, {"alias_candidate", "ambiguous"})

    def test_unsupported_alias_index_does_not_claim_missing(self):
        self.write("notes/C.md", "---\naliases: [unquoted, yaml]\n---\n")
        self.write("A.md", "[[unquoted]]\n")
        self.assertEqual(self.findings(self.scan())[0]["kind"], "index_incomplete")

    def test_markdown_parentheses_spaces_anchors_and_url_encoding(self):
        self.write("notes/有 空格(概念).md", "# 测试标题\n段落 ^sample\n")
        self.write("A.md", "[x](<notes/有 空格(概念).md#测试标题>)\n[x](notes/有%20空格(概念).md#^sample)\n[[B#B]]\n[web](https://example.invalid/)\n")
        state = self.scan()
        self.assertEqual(self.findings(state), [])
        self.assertEqual(state["completed"]["A.md"]["external_unchecked"], 1)

    def test_unknown_syntax_and_short_attachments_need_review(self):
        self.write("A.md", "[ref][id]\n[[unclosed\n![[photo.png]]\n[[B#Missing heading]]\n")
        kinds = {f["kind"] for f in self.findings(self.scan())}
        self.assertEqual(kinds, {"unsupported", "asset_unchecked", "anchor_needs_review"})

    def test_missing_material_and_missing_primary_do_not_pass(self):
        self.write("A.md", "[材料](80_Local/missing.pdf)\n")
        (self.vault / "B.md").unlink()
        state = self.scan()
        self.assertEqual(state["completed"]["B.md"]["execution"], "read_failed")
        self.assertEqual({f["decision"] for f in self.findings(state)}, {"待验证"})

    def test_interruption_resumes_checkpoint_and_deduplicates(self):
        real = m.check_file
        def interrupted(vault, source, snap):
            if source == "B.md":
                raise KeyboardInterrupt()
            return real(vault, source, snap)
        with patch.object(m, "check_file", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.scan()
        checkpoint = m.read_json(self.folder / "state.json")
        self.assertEqual(list(checkpoint["completed"]), ["A.md"])
        state = self.scan()
        self.assertEqual(state["last_scan"]["processed_files"], 1)
        self.assertEqual(self.scan()["last_scan"]["processed_files"], 0)

    def test_input_change_invalidates_review_and_retains_history(self):
        first = self.scan()
        m.accept_review(self.vault, self.config, self.folder, self.review(first))
        self.write("B.md", "# B\n现只有模拟；效果仍待核验。\n")
        second = self.scan()
        self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertIsNone(second["review"])
        self.assertTrue((self.folder / ("history-" + first["snapshot_id"] + ".json")).exists())
        with self.assertRaisesRegex(ValueError, "版本不匹配"):
            m.accept_review(self.vault, self.config, self.folder, self.review(first))

    def test_new_duplicate_target_invalidates_checkpoint(self):
        first = self.scan(1)
        self.write("notes/B.md", "# duplicate\n")
        second = self.scan()
        self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(self.findings(second)[0]["kind"], "ambiguous")

    def test_changed_linked_anchor_invalidates_checkpoint(self):
        self.write("notes/C.md", "# Valid\n")
        self.write("A.md", "[[C#Valid]]\n")
        first = self.scan()
        self.write("notes/C.md", "# Changed\n")
        second = self.scan()
        self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(self.findings(second)[0]["kind"], "anchor_needs_review")

    def test_review_handoff_checks_coverage_citations_and_version(self):
        state = self.scan()
        valid = self.review(state)
        for invalid in ({**valid, "decisions": []}, {**valid, "snapshot_id": "old"}):
            with self.assertRaises(ValueError):
                m.accept_review(self.vault, self.config, self.folder, invalid)
        invalid = copy.deepcopy(valid)
        invalid["decisions"][0]["evidence"][0]["quote"] = "不存在的证据"
        with self.assertRaisesRegex(ValueError, "证据与原文不符"):
            m.accept_review(self.vault, self.config, self.folder, invalid)
        result = m.accept_review(self.vault, self.config, self.folder, valid)
        self.assertEqual(result["status"], "complete_scoped_review")
        self.assertEqual(self.scan()["status"], "complete_scoped_review")

    def test_structural_failure_cannot_be_hidden_by_no_action_review(self):
        self.write("A.md", "# A\n已有边界：未验证检索收益。\n[[Missing]]\n")
        state = self.scan()
        result = m.accept_review(self.vault, self.config, self.folder, self.review(state))
        self.assertEqual(result["status"], "complete_with_findings")

    def test_revised_judgment_keeps_previous_evidence_record(self):
        state = self.scan()
        first = self.review(state)
        m.accept_review(self.vault, self.config, self.folder, first)
        revised = copy.deepcopy(first)
        revised["decisions"][0]["reason"] = "改进裁定说明，但保留同一输入版本"
        m.accept_review(self.vault, self.config, self.folder, revised)
        history = self.folder / ("review-history-" + m.digest(first) + ".json")
        self.assertEqual(m.read_json(history), first)

    def test_mutation_during_scan_marks_stale(self):
        real = m.check_file
        def changed(vault, source, snap):
            result = real(vault, source, snap)
            if source == "B.md":
                self.write("B.md", "# Updated mid-run\n")
            return result
        with patch.object(m, "check_file", side_effect=changed):
            state = self.scan()
        self.assertEqual(state["status"], "stale_input")

    def test_path_escape_and_state_clobber_are_refused(self):
        with self.assertRaises(ValueError):
            m.bounded(self.vault, "../outside.md")
        with self.assertRaises(ValueError):
            with m.state_folder(self.vault / "notes", self.vault):
                pass
        (self.folder / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "非空"):
            with m.state_folder(self.folder, self.vault):
                pass
        self.assertEqual((self.folder / "keep.txt").read_text(), "keep")

    def test_symlink_link_cannot_read_outside_vault(self):
        outside = self.root / "secret.md"
        outside.write_text("# Secret")
        (self.vault / "escape.md").symlink_to(outside)
        self.write("A.md", "[x](escape.md#Secret)\n")
        self.assertEqual(self.findings(self.scan())[0]["kind"], "outside_vault")

    def test_state_lock_excludes_second_writer(self):
        with m.state_folder(self.folder, self.vault):
            with self.assertRaisesRegex(ValueError, "另一次"):
                with m.state_folder(self.folder, self.vault):
                    pass


if __name__ == "__main__":
    unittest.main()
