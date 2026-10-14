import unittest

from app.evals import load_cases, run_eval


class EvalSuiteTests(unittest.TestCase):
    def test_fixed_suite_contains_twenty_cases(self) -> None:
        cases = load_cases()
        self.assertEqual(len(cases), 20)
        self.assertGreaterEqual(
            sum(case.expected == "grounded" for case in cases), 10
        )
        self.assertGreaterEqual(
            sum(case.expected == "no_evidence" for case in cases), 5
        )

    def test_baseline_meets_quality_threshold(self) -> None:
        summary = run_eval()
        self.assertGreaterEqual(summary.pass_rate, 0.9)
        self.assertGreaterEqual(summary.grounded_recall, 0.9)
        self.assertGreaterEqual(summary.refusal_accuracy, 0.9)
        self.assertGreaterEqual(summary.citation_accuracy, 0.9)


if __name__ == "__main__":
    unittest.main()
