"""Isolated state/write safety tests; fixture judgments do not test AI accuracy."""
import copy
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import maintain as m

A = '10_Knowledge/Notes/A.md'
B = '10_Knowledge/Notes/B.md'
SOURCE = '20_Sources/Notes/source.md'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name).resolve()
        self.write(A, '# A\n这是预设模拟，却被描述为实测收益。\n[[B]]\n')
        self.write(B, '# B\n案例说已验证收益。\n')
        self.write(SOURCE, '# 来源\n这里只运行预设响应，没有真实检索实验。\n')
        self.req = {'purpose': '纠正模拟与实测混淆', 'files': [A, B], 'questions': ['是否夸大实验结论？']}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, body):
        p = self.vault / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding='utf-8')

    def ref(self, path=SOURCE, line=2):
        return {'kind': 'local', 'path': path, 'sha256': m.version(self.vault, path), 'line': line,
                'quote': (self.vault / path).read_text().splitlines()[line-1], 'supports': '限定模拟与实测的边界'}

    def diagnosis(self, decision='建议修订', refs=None):
        return {'authorization': '本测试明确授权维护', 'reviewer': 'test fixture', 'method': '预置判断，仅验证流程',
                'limitations': '不测试 AI 语义判断', 'request': self.req,
                'snapshot_id': m.inspect(self.vault, self.req)['snapshot_id'],
                'findings': [{'key': 'simulation-versus-real', 'claim': '效果未经实测', 'reason': '与来源模拟边界冲突',
                              'next_action': '修订两篇正文后复查', 'targets': [A, B], 'decision': decision,
                              'evidence': refs if refs is not None else [self.ref()]}]}

    def record(self):
        return m.record(self.vault, self.diagnosis())['ids'][0]

    def proposal(self, iid):
        return {'issue_id': iid, 'authorization': '修订模拟边界，保留其余内容', 'acceptance': '两篇明确未实测，不引入断链',
                'snapshot_id': m.inspect(self.vault, self.req)['snapshot_id'],
                'edits': [{'path': p, 'expected_sha256': m.version(self.vault, p),
                           'after': (self.vault / p).read_text().replace('这是预设模拟，却被描述为实测收益。', '这是预设模拟，未验证检索收益。').replace('案例说已验证收益。', '案例仅验证程序分支，未验证检索收益。')}
                          for p in [A, B]]}

    def prepared(self):
        return m.prepare(self.vault, self.proposal(self.record()))['operation_id']

    def verification(self, oid):
        packet = m.inspect(self.vault, self.req)
        return {'operation_id': oid, 'snapshot_id': packet['snapshot_id'], 'reviewer': 'test fixture',
                'method': '预置两篇结果与原来源对照', 'limitations': '未进行检索实验', 'reason': '已撤回效果主张',
                'evidence': [self.ref(A), self.ref(B), self.ref()], 'passed': True,
                'remaining_findings': {f['id']: '与本次语义问题无关，另行保留' for r in packet['structure'].values() for f in r['findings']}}

    def test_inspect_show_are_read_only_and_no_action_does_not_queue(self):
        before = {p: p.read_bytes() for p in self.vault.rglob('*') if p.is_file()}
        m.inspect(self.vault, self.req);m.show(self.vault)
        self.assertEqual(before, {p: p.read_bytes() for p in self.vault.rglob('*') if p.is_file()})
        self.assertEqual(m.record(self.vault, self.diagnosis('无需动作'))['ids'], [])
        self.assertFalse((self.vault / m.STATE).exists())

    def test_stable_issue_dedup_and_read_only_changed_signal(self):
        iid = self.record();before = (self.vault / m.STATE).read_bytes()
        self.assertEqual(m.record(self.vault, self.diagnosis())['changed'], [])
        self.assertEqual(before, (self.vault / m.STATE).read_bytes())
        self.write(SOURCE, '# 来源\n现在需要重新取证。\n')
        self.assertTrue(m.show(self.vault)['issues'][0]['local_evidence_changed'])
        self.assertEqual(m.record(self.vault, self.diagnosis())['ids'], [iid])
        self.assertEqual(len(m.read_db(self.vault)['issues']), 1)

    def test_updated_followup_is_saved_without_duplicate_issue(self):
        data = self.diagnosis('待验证')
        iid = m.record(self.vault, data)['ids'][0]
        revised = copy.deepcopy(data)
        revised['findings'][0]['next_action'] = '先核对已取得的原文，再决定是否需要实验'
        revised['findings'][0]['reason'] = '等待条件已具体化，事实裁定仍为待验证'
        result = m.record(self.vault, revised)
        item = m.read_db(self.vault)['issues'][iid]
        self.assertEqual(item['next_action'], revised['findings'][0]['next_action'])
        self.assertEqual(item['reason'], revised['findings'][0]['reason'])
        self.assertEqual(len(m.read_db(self.vault)['issues']), 1)
        self.assertEqual(result['refreshed'], [iid])
        before = (self.vault / m.STATE).read_bytes()
        self.assertEqual(m.record(self.vault, revised)['refreshed'], [])
        self.assertEqual(before, (self.vault / m.STATE).read_bytes())

    def test_waiting_cannot_be_prepared(self):
        for decision in ['待验证', '待用户判断']:
            iid = m.record(self.vault, self.diagnosis(decision))['ids'][0]
            self.assertEqual(m.read_db(self.vault)['issues'][iid]['status'], 'waiting')
            with self.assertRaisesRegex(ValueError, 'open'):m.prepare(self.vault, self.proposal(iid))

    def test_stale_diagnosis_and_false_citation_rejected(self):
        data = self.diagnosis();self.write(A, '# A\n用户的新内容。\n')
        with self.assertRaisesRegex(ValueError, '输入已变化'):m.record(self.vault, data)
        for changes in [{'quote': '并不存在'}, {'sha256': 'old'}, {'line': 200}]:
            data = self.diagnosis();data['findings'][0]['evidence'][0].update(changes)
            with self.assertRaises(ValueError):m.record(self.vault, data)
        self.assertFalse((self.vault / m.STATE).exists())

    def test_cross_source_raw_material_and_external_read_scope(self):
        self.write('80_Local/sample.txt', 'raw material')
        refs = [self.ref(), {'kind': 'material', 'path': '80_Local/sample.txt', 'sha256': m.version(self.vault, '80_Local/sample.txt'),
                            'locator': '第 1 段', 'observation': '测试原材料', 'supports': '记录实际读取范围'},
                {'kind': 'external', 'url': 'https://example.invalid/paper', 'title': 'fixture', 'accessed': '2026-10-20',
                 'version': 'fixture-v1', 'read_scope': '摘要', 'quote': 'fixture only', 'supports': '测试外部阅读记录'}]
        iid = m.record(self.vault, self.diagnosis(refs=refs))['ids'][0]
        self.assertIn('未联网验证', m.read_db(self.vault)['issues'][iid]['evidence'][-1]['validation'])
        self.assertIn('80_Local/sample.txt', m.read_db(self.vault)['issues'][iid]['basis']['files'])

    def test_unavailable_evidence_remains_waiting_and_blocks_false_absence(self):
        ref = {'kind': 'unavailable', 'path': '80_Local/missing.pdf', 'reason': '此设备没有原材料', 'supports': '无法复验'}
        iid = m.record(self.vault, self.diagnosis('待验证', [ref]))['ids'][0]
        self.assertEqual(m.read_db(self.vault)['issues'][iid]['status'], 'waiting')
        self.write(ref['path'], 'now available')
        with self.assertRaisesRegex(ValueError, '不能登记为缺失'):m.record(self.vault, self.diagnosis('待验证', [ref]))

    def test_refresh_after_index_change_allows_freshly_reviewed_issue(self):
        iid = self.record();self.write('10_Knowledge/Notes/C.md', '# C\n')
        with self.assertRaisesRegex(ValueError, '输入已变化'):m.prepare(self.vault, self.proposal(iid))
        self.assertEqual(m.record(self.vault, self.diagnosis())['refreshed'], [iid])
        self.assertEqual(m.prepare(self.vault, self.proposal(iid))['status'], 'prepared')

    def test_prepare_diff_preserves_working_tree_and_enforces_scope(self):
        self.write(A, (self.vault / A).read_text() + '用户未提交的新段落。\n')
        iid = self.record();data = self.proposal(iid);before = (self.vault / A).read_bytes()
        bad = copy.deepcopy(data);bad['edits'][0]['path'] = SOURCE
        with self.assertRaisesRegex(ValueError, '越界'):m.prepare(self.vault, bad)
        bad = copy.deepcopy(data);bad['edits'][0]['expected_sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, '基线'):m.prepare(self.vault, bad)
        plan = m.prepare(self.vault, data)
        self.assertIn('未验证检索收益', plan['diff'])
        self.assertEqual((self.vault / A).read_bytes(), before)
        m.apply(self.vault, plan['operation_id'])
        self.assertIn('用户未提交的新段落。', (self.vault / A).read_text())
        self.assertEqual(m.read_db(self.vault)['issues'][iid]['status'], 'open')

    def test_partial_apply_survives_cache_deletion_and_vault_relocation(self):
        oid = self.prepared()
        self.assertEqual(m.apply(self.vault, oid, 1)['status'], 'applying')
        cache = self.vault / '99_System/Scripts/knowledge_maintenance/.runs';cache.mkdir(parents=True)
        shutil.rmtree(cache)
        with tempfile.TemporaryDirectory() as new:
            target = Path(new).resolve() / 'vault';shutil.copytree(self.vault, target)
            out = m.apply(target, oid)
            self.assertEqual((out['status'], out['newly_written']), ('awaiting_verification', 1))
        self.assertEqual(m.apply(self.vault, oid)['newly_written'], 1)
        self.assertEqual(m.apply(self.vault, oid)['newly_written'], 0)
        m.verify(self.vault, self.verification(oid))
        db = m.read_db(self.vault)
        self.assertEqual(db['operations'][oid]['status'], 'verified')
        self.assertNotIn('before', db['operations'][oid]['files'][0])

    def test_crash_after_file_write_before_checkpoint_resumes(self):
        oid = self.prepared();real = m.check.atomic_write
        def interrupt(path, text):
            real(path, text)
            if path == self.vault / A:raise KeyboardInterrupt()
        with patch.object(m.check, 'atomic_write', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):m.apply(self.vault, oid)
        self.assertEqual(m.read_db(self.vault)['operations'][oid]['status'], 'applying')
        self.assertEqual(m.apply(self.vault, oid)['newly_written'], 1)

    def test_other_editor_changes_block_write_without_rollback(self):
        oid = self.prepared();m.apply(self.vault, oid, 1)
        a = (self.vault / A).read_bytes();self.write(B, '# B\n用户的新结论。\n')
        with self.assertRaisesRegex(ValueError, '其他编辑'):m.apply(self.vault, oid)
        self.assertEqual((self.vault / A).read_bytes(), a)
        self.assertIn('用户的新结论', (self.vault / B).read_text())
        self.assertEqual(m.read_db(self.vault)['operations'][oid]['status'], 'conflict')

    def test_changed_cross_source_blocks_apply(self):
        oid = self.prepared();self.write(SOURCE, '# 来源\n新的来源内容。\n')
        before = (self.vault / A).read_bytes()
        with self.assertRaisesRegex(ValueError, '其他编辑'):m.apply(self.vault, oid)
        self.assertEqual(before, (self.vault / A).read_bytes())

    def test_write_failure_keeps_first_file_and_can_resume(self):
        oid = self.prepared();real = m.check.atomic_write
        def fail(path, text):
            if path == self.vault / B:raise OSError('fixture disk failure')
            return real(path, text)
        with patch.object(m.check, 'atomic_write', side_effect=fail):
            with self.assertRaises(OSError):m.apply(self.vault, oid)
        op = m.read_db(self.vault)['operations'][oid]
        self.assertEqual(op['status'], 'conflict')
        self.assertEqual(m.version(self.vault, A), op['files'][0]['after_sha256'])
        self.assertEqual(m.version(self.vault, B), op['files'][1]['before_sha256'])
        self.assertEqual(m.apply(self.vault, oid)['newly_written'], 1)

    def test_missing_material_on_new_device_blocks_recovery(self):
        self.write('80_Local/raw.txt', 'raw')
        ref = {'kind': 'material', 'path': '80_Local/raw.txt', 'sha256': m.version(self.vault, '80_Local/raw.txt'),
               'locator': '全文', 'observation': 'fixture', 'supports': '本机材料证据'}
        iid = m.record(self.vault, self.diagnosis(refs=[self.ref(), ref]))['ids'][0]
        oid = m.prepare(self.vault, self.proposal(iid))['operation_id']
        (self.vault / ref['path']).unlink()
        with self.assertRaisesRegex(ValueError, '80_Local/raw.txt'):m.apply(self.vault, oid)
        self.assertEqual(m.read_db(self.vault)['issues'][iid]['status'], 'open')

    def test_two_active_operations_for_same_issue_rejected(self):
        iid = self.record();m.prepare(self.vault, self.proposal(iid))
        with self.assertRaisesRegex(ValueError, '活动操作'):m.prepare(self.vault, self.proposal(iid))
        with self.assertRaisesRegex(ValueError, '待完成修订'):m.record(self.vault, self.diagnosis())

    def test_verify_requires_complete_edits_fresh_input_and_every_file(self):
        oid = self.prepared();m.apply(self.vault, oid, 1)
        with self.assertRaisesRegex(ValueError, '未完整'):m.verify(self.vault, self.verification(oid))
        m.apply(self.vault, oid);data = self.verification(oid)
        for changed in [{'snapshot_id': 'old'}, {'evidence': [self.ref(A)]}, {'passed': False}]:
            with self.assertRaises(ValueError):m.verify(self.vault, {**data, **changed})
        self.assertEqual(m.read_db(self.vault)['operations'][oid]['status'], 'awaiting_verification')

    def test_new_structural_regression_cannot_be_closed(self):
        iid = self.record();data = self.proposal(iid);data['edits'][0]['after'] += '[[不存在的新页面]]\n'
        oid = m.prepare(self.vault, data)['operation_id'];m.apply(self.vault, oid)
        with self.assertRaisesRegex(ValueError, '新结构发现'):m.verify(self.vault, self.verification(oid))

    def test_existing_structural_findings_require_explicit_disposition(self):
        self.write(A, (self.vault / A).read_text() + '[[旧的缺失目标]]\n')
        oid = self.prepared();m.apply(self.vault, oid);data = self.verification(oid)
        self.assertTrue(data['remaining_findings'])
        with self.assertRaisesRegex(ValueError, '逐项说明'):m.verify(self.vault, {**data, 'remaining_findings': {}})
        self.assertEqual(m.verify(self.vault, data)['status'], 'resolved')

    def test_resolved_issue_quiet_until_relevant_evidence_changes(self):
        oid = self.prepared();m.apply(self.vault, oid);m.verify(self.vault, self.verification(oid))
        before = (self.vault / m.STATE).read_bytes()
        data = self.diagnosis();data['findings'][0]['reason'] = '同一问题换一种措辞'
        self.assertEqual(m.record(self.vault, data)['changed'], [])
        self.assertEqual(before, (self.vault / m.STATE).read_bytes())
        self.write(SOURCE, '# 来源\n后来补充了新实验，需重新裁定。\n')
        result = m.record(self.vault, self.diagnosis())
        self.assertEqual(len(result['changed']), 1)
        self.assertEqual(m.show(self.vault)['issues'][0]['status'], 'open')

    def test_cancel_preserves_partial_changes_and_allows_new_plan(self):
        oid = self.prepared();m.apply(self.vault, oid, 1)
        before = (self.vault / A).read_bytes()
        m.cancel(self.vault, {'operation_id': oid, 'authorization': '本测试授权取消', 'reason': '改用另一修订方案'})
        self.assertEqual(before, (self.vault / A).read_bytes())
        iid = self.record();proposal = self.proposal(iid);proposal['edits'] = [proposal['edits'][1]]
        self.assertNotEqual(m.prepare(self.vault, proposal)['operation_id'], oid)

    def test_symlinks_traversal_hidden_and_system_edits_rejected(self):
        for name in ['../outside.md', '/tmp/outside.md', '.obsidian/a.md', '10_Knowledge//A.md']:
            with self.assertRaises(ValueError):m.inspect(self.vault, {**self.req, 'files': [name]})
        self.write('99_System/rule.md', '# Rule\n')
        with self.assertRaises(ValueError):m.editable(self.vault, '99_System/rule.md')
        link = self.vault / '10_Knowledge/Notes/link.md';link.symlink_to(self.vault / A)
        with self.assertRaises(ValueError):m.editable(self.vault, '10_Knowledge/Notes/link.md')

    def test_corrupt_ledger_and_competing_process_lock_rejected(self):
        oid = self.prepared();db = m.read_db(self.vault)
        db['operations'][oid]['files'][0]['after'] = 'tampered'
        m.check.save_json(self.vault / m.STATE, db)
        with self.assertRaisesRegex(ValueError, '指纹不符'):m.show(self.vault)
        lock = self.vault / '99_System/State/.maintenance.lock'
        with lock.open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, '另一个维护进程'):
                with m.locked(self.vault):pass

    def test_cli_show_and_bad_request(self):
        command = [sys.executable, str(Path(m.__file__)), 'show', '--vault', str(self.vault)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['issues'], [])
        command[2] = 'record'
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('error', json.loads(result.stdout))


if __name__ == '__main__':
    unittest.main()
