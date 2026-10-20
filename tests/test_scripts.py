import subprocess
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))

import check_brief  # noqa: E402
import check_debrief  # noqa: E402
import manifest  # noqa: E402
import small_sample  # noqa: E402

EX = R / 'examples' / 'claims-demo'
BRIEF = (EX / 'brief.md').read_text(encoding='utf-8')
DEBRIEF = (EX / 'debrief.md').read_text(encoding='utf-8')
LOG = check_debrief.parse_log((EX / 'session-log.md').read_text(encoding='utf-8'))


class BriefTests(unittest.TestCase):
    def test_example_passes(self):
        errors, _ = check_brief.check(BRIEF)
        self.assertEqual(errors, [])

    def test_template_fails(self):
        errors, _ = check_brief.check((R / 'templates' / 'demo-brief.md').read_text(encoding='utf-8'))
        self.assertGreater(len(errors), 8)

    def test_synthetic_data_is_error_unless_allowed(self):
        text = BRIEF.replace('数据来源：真实脱敏', '数据来源：合成')
        self.assertTrue(any('红线一' in e for e in check_brief.check(text)[0]))
        errors, warnings = check_brief.check(text, allow_synthetic=True)
        self.assertFalse(any('红线一' in e for e in errors))
        self.assertTrue(any('红线一' in w for w in warnings))

    def test_one_failure_example_is_not_enough(self):
        text = BRIEF.replace('- F2：', '- 备注：').replace('- F3：', '- 备注：')
        self.assertTrue(any('失败样例不足' in e for e in check_brief.check(text)[0]))

    def test_missing_ask_and_signals(self):
        text = BRIEF.replace('- ask：', '- 想法：')
        self.assertTrue(any('ask' in e for e in check_brief.check(text)[0]))
        text = BRIEF.replace('- 失败信号：', '- 备忘：')
        self.assertTrue(any('失败信号' in e for e in check_brief.check(text)[0]))

    def test_simplest_alternative_missing_warns(self):
        errors, warnings = check_brief.check(BRIEF)
        self.assertFalse(any('最简替代方案' in w for w in warnings))
        text = BRIEF.replace('- 最简替代方案：', '- 备注：')
        errors, warnings = check_brief.check(text)
        self.assertEqual(errors, [])
        self.assertTrue(any('最简替代方案' in w for w in warnings))

    def test_missing_user_is_error(self):
        text = BRIEF.replace('- 使用者：2 名理赔员（资历不同）', '- 使用者：待填')
        self.assertTrue(any('使用者' in e for e in check_brief.check(text)[0]))

    def test_soft_target_is_error(self):
        text = BRIEF.replace('- 为什么不是软柿子：', '- 备注：')
        self.assertTrue(any('软柿子' in e for e in check_brief.check(text)[0]))


class DebriefTests(unittest.TestCase):
    def test_log_parsed(self):
        self.assertEqual(len(LOG), 11)
        self.assertEqual(LOG['L11'], '解读')

    def test_example_passes(self):
        errors, _ = check_debrief.check(DEBRIEF, LOG, BRIEF)
        self.assertEqual(errors, [])

    def test_template_fails(self):
        text = (R / 'templates' / 'debrief.md').read_text(encoding='utf-8')
        self.assertGreater(len(check_debrief.check(text, LOG)[0]), 3)

    def test_inference_cannot_be_cited(self):
        text = DEBRIEF.replace('证据：L9,L10', '证据：L9,L11')
        errors, _ = check_debrief.check(text, LOG, BRIEF)
        self.assertTrue(any('解读' in e for e in errors))

    def test_verified_needs_two_qualifying_records(self):
        text = DEBRIEF.replace('证据：L9,L10', '证据：L10')
        self.assertTrue(any('已验证' in e for e in check_debrief.check(text, LOG, BRIEF)[0]))

    def test_vague_praise_cannot_verify_value(self):
        text = DEBRIEF.replace('价值判断：部分｜证据：L1,L2,L5', '价值判断：已验证｜证据：L2,L5,L6')
        self.assertTrue(any('价值判断判为已验证' in e for e in check_debrief.check(text, LOG, BRIEF)[0]))

    def test_proceed_requires_value_and_trust_verified(self):
        text = DEBRIEF.replace('建议结论：Iterate', '建议结论：Proceed')
        errors, _ = check_debrief.check(text, LOG, BRIEF)
        self.assertTrue(any('Proceed' in e for e in errors))

    def test_proceed_can_pass_when_conditions_hold(self):
        text = (DEBRIEF.replace('建议结论：Iterate', '建议结论：Proceed')
                .replace('价值判断：部分｜证据：L1,L2,L5', '价值判断：已验证｜证据：L1,L4')
                .replace('- 试点范围建议：', '- 试点范围建议：理赔员 A、B 所在小组，仅印刷体车损件'))
        errors, _ = check_debrief.check(text, LOG, BRIEF)
        self.assertEqual(errors, [])

    def test_iterate_needs_followups(self):
        text = DEBRIEF.replace('- 补验证：价值轴', '- 备注：价值轴')
        self.assertTrue(any('补验证' in e for e in check_debrief.check(text, LOG, BRIEF)[0]))

    def test_unknown_id_and_missing_ask(self):
        text = DEBRIEF.replace('证据：L9,L10', '证据：L9,L99')
        self.assertTrue(any('L99' in e for e in check_debrief.check(text, LOG, BRIEF)[0]))
        text = DEBRIEF.replace('ask 结果：部分获批', 'ask 结果：不清楚')
        self.assertTrue(any('ask' in e for e in check_debrief.check(text, LOG, BRIEF)[0]))

    def test_brief_requires_comparison_section(self):
        text = DEBRIEF.split('## 对照事前登记')[0] + '## ask 结果\n- ask 结果：待回复\n'
        self.assertTrue(any('对照事前登记' in e for e in check_debrief.check(text, LOG, BRIEF)[0]))


class RetroTests(unittest.TestCase):
    def retro_text(self, **repl):
        text = DEBRIEF.replace('- 建议结论：Iterate', '- 建议结论：Iterate\n- 复盘类型：回溯')
        for k, v in repl.items():
            text = text.replace(k, v)
        return text

    def test_retro_requires_marker(self):
        errors, _ = check_debrief.check(DEBRIEF, LOG, BRIEF, retro=True)
        self.assertTrue(any('复盘类型：回溯' in e for e in errors))

    def test_retro_blocks_verified_and_proceed(self):
        errors, _ = check_debrief.check(self.retro_text(), LOG, BRIEF, retro=True)
        self.assertTrue(any('不得判已验证' in e for e in errors))
        text = self.retro_text(**{'信任与权限：已验证': '信任与权限：部分'})
        self.assertEqual(check_debrief.check(text, LOG, BRIEF, retro=True)[0], [])
        proceed = text.replace('建议结论：Iterate', '建议结论：Proceed')
        errors, _ = check_debrief.check(proceed, LOG, BRIEF, retro=True)
        self.assertTrue(any('回溯复盘不作新决策' in e for e in errors))

    def test_retro_marker_without_flag_warns(self):
        _, warnings = check_debrief.check(self.retro_text(), LOG, BRIEF)
        self.assertTrue(any('--retro' in w for w in warnings))


class SmallSampleTests(unittest.TestCase):
    def test_wilson_two_of_three(self):
        lo, hi = small_sample.wilson(2, 3)
        self.assertAlmostEqual(lo, 0.2077, places=3)
        self.assertAlmostEqual(hi, 0.9385, places=3)

    def test_bounds_and_errors(self):
        lo, hi = small_sample.wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertLess(hi, 0.35)
        for k, n in ((1, 0), (4, 3), (-1, 3)):
            with self.assertRaises(ValueError):
                small_sample.wilson(k, n)
        with self.assertRaises(ValueError):
            small_sample.wilson(1, 3, conf=0.5)


class ManifestTests(unittest.TestCase):
    def test_detects_missing_and_changed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'a').mkdir()
            (root / 'a' / 'x.md').write_text('x')
            (root / 'y.md').write_text('y')
            expected = manifest.collect(root)
            (root / 'a' / 'x.md').unlink()
            (root / 'y.md').write_text('changed')
            (root / 'z.md').write_text('z')
            result = manifest.compare(expected, manifest.collect(root))
            self.assertEqual(result, (['a/x.md'], ['y.md'], ['z.md']))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-I', *map(str, args)], capture_output=True, text=True)

    def test_example_exit_codes(self):
        r = self.run_cli(R / 'scripts' / 'check_brief.py', EX / 'brief.md')
        self.assertEqual(r.returncode, 0, r.stdout)
        r = self.run_cli(R / 'scripts' / 'check_debrief.py', EX / 'debrief.md', '--log', EX / 'session-log.md',
                         '--brief', EX / 'brief.md')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_small_sample_cli(self):
        r = self.run_cli(R / 'scripts' / 'small_sample.py', '--k', '2', '--n', '3')
        self.assertEqual(r.returncode, 0, r.stdout)
        r = self.run_cli(R / 'scripts' / 'small_sample.py', '--k', '2', '--n', '3', '--json')
        self.assertIn('3 件中 2 件', r.stdout)

    def test_template_exit_code(self):
        r = self.run_cli(R / 'scripts' / 'check_brief.py', R / 'templates' / 'demo-brief.md')
        self.assertEqual(r.returncode, 1)


if __name__ == '__main__':
    unittest.main()
