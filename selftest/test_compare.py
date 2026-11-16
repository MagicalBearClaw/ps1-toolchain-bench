import math
import unittest

from ps1bench.compare import Variant, compare_pair, delta_pct, check_variant


def variant(**kw):
    base = dict(toolchain="gcc", opt="-O2", built=True, stdout="hi\n",
                exit_code=0, cycles=1000, sizes={"text": 400, "data": 40, "bss": 8})
    base.update(kw)
    return Variant(**base)


class DeltaTest(unittest.TestCase):
    def test_relative_percent(self):
        self.assertAlmostEqual(delta_pct(200, 210), 5.0)
        self.assertAlmostEqual(delta_pct(200, 190), -5.0)

    def test_zero_baseline(self):
        self.assertEqual(delta_pct(0, 0), 0.0)
        self.assertTrue(math.isinf(delta_pct(0, 4)))


class CheckVariantTest(unittest.TestCase):
    def test_expected_exit_and_stdout(self):
        self.assertEqual(check_variant(variant(), expected_exit=0, expected_stdout="hi\n"), [])

    def test_wrong_exit_code(self):
        problems = check_variant(variant(exit_code=3), expected_exit=0, expected_stdout=None)
        self.assertEqual(problems, ["exit code 3, expected 0"])

    def test_wrong_stdout(self):
        problems = check_variant(variant(stdout="ho\n"), expected_exit=0, expected_stdout="hi\n")
        self.assertEqual(problems, ["stdout differs from expected.txt"])

    def test_timeout(self):
        problems = check_variant(variant(exit_code=None, error="timed out after 60 s"),
                                 expected_exit=0, expected_stdout=None)
        self.assertEqual(problems, ["timed out after 60 s"])


class ComparePairTest(unittest.TestCase):
    def test_same_behaviour_within_threshold(self):
        cmp = compare_pair(variant(), variant(toolchain="clang", cycles=1040),
                           thresholds={"text": 5.0, "data": 5.0, "cycles": 5.0})
        self.assertEqual(cmp.problems, [])
        self.assertEqual(cmp.over_threshold, [])
        self.assertAlmostEqual(cmp.deltas["cycles"], 4.0)

    def test_stdout_mismatch_is_a_problem(self):
        cmp = compare_pair(variant(), variant(toolchain="clang", stdout="x\n"),
                           thresholds={"text": 5.0, "data": 5.0, "cycles": 5.0})
        self.assertEqual(cmp.problems, ["stdout differs between gcc and clang"])

    def test_exit_mismatch_is_a_problem(self):
        cmp = compare_pair(variant(), variant(toolchain="clang", exit_code=1),
                           thresholds={"text": 5.0, "data": 5.0, "cycles": 5.0})
        self.assertEqual(cmp.problems, ["exit code differs between gcc (0) and clang (1)"])

    def test_metric_over_threshold(self):
        cmp = compare_pair(variant(), variant(toolchain="clang", sizes={"text": 440, "data": 40, "bss": 8}),
                           thresholds={"text": 5.0, "data": 5.0, "cycles": 5.0})
        self.assertEqual(cmp.over_threshold, ["text"])

    def test_improvement_is_never_over_threshold(self):
        cmp = compare_pair(variant(), variant(toolchain="clang", cycles=500),
                           thresholds={"text": 5.0, "data": 5.0, "cycles": 5.0})
        self.assertEqual(cmp.over_threshold, [])


if __name__ == "__main__":
    unittest.main()
