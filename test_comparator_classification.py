"""Classification of comparator results.

Phase D D2: the reporting layer must keep these apart, because they mean
completely different things to whoever reads the matrix:

  pass                          the observation matches the declared expectation
  fail                          a real observation contradicts the expectation
  unparseable                   a real observation that is neither number nor error
  input_construction_failure    the keypad built a different expression, so the
                                calculator was never asked the question
  collector_error               the collector itself broke; nothing was learned
  unresolved                    the specification itself is undecided
  unexecuted                    no observation was produced

The distinction that matters most is input_construction_failure vs fail: the
first is a UI defect in how the expression was typed, the second is a maths
defect. Collapsing them hides real bugs, and it is exactly the confusion that
made cases 16 and 45 look like parser failures in Phase B.

These are SYNTHETIC results used to prove the classifier. They are never mixed
into a real comparator run.
"""
import importlib.util
import json
import os
import pathlib
import unittest

PROJECT = pathlib.Path(__file__).resolve().parent
AUDIT = PROJECT / "audit"
RESULTS = AUDIT / "evidence" / "phase-d-20261015" / "comparator_results.json"

_spec = importlib.util.spec_from_file_location("cmp_runner",
                                              AUDIT / "tools" / "run_comparator.py")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


def obs(status="pass", numeric=None, is_error=False, error_text=None,
        error_class="none", detail="", observed=None):
    """A synthetic collector observation, shaped exactly like a real one."""
    return {"id": 1, "input": "x", "observed": observed, "numeric": numeric,
            "is_error": is_error, "error_text": error_text,
            "error_class": error_class, "status": status, "path": "synthetic",
            "detail": detail}


def case(expected=5, expect_error=False, source="keypad-verified", note=None):
    return {"id": 1, "ascii": "x", "internal_expr": "x", "expected": expected,
            "expect_error": expect_error, "internal_expr_source": source,
            "note": note}


class TestCalculatorOutcomes(unittest.TestCase):
    def test_correct_number_is_pass(self):
        v, why = runner.judge(case(expected=5), obs(numeric=5.0))
        self.assertEqual(v, "pass")
        self.assertEqual(why, "")

    def test_wrong_number_is_fail_with_both_values_named(self):
        v, why = runner.judge(case(expected=5), obs(numeric=16.0))
        self.assertEqual(v, "fail")
        self.assertIn("5", why)
        self.assertIn("16.0", why)

    def test_within_tolerance_is_pass(self):
        v, _ = runner.judge(case(expected=0.3), obs(numeric=0.3 + 1e-9))
        self.assertEqual(v, "pass")

    def test_unexpected_error_on_a_numeric_case_is_fail(self):
        v, why = runner.judge(case(expected=5),
                              obs(is_error=True, error_text="Math ERROR"))
        self.assertEqual(v, "fail")
        self.assertIn("Math ERROR", why)

    def test_unparseable_output_is_not_treated_as_a_failure_or_zero(self):
        v, why = runner.judge(case(expected=5), obs(observed="1/2", numeric=None))
        self.assertEqual(v, "unparseable")
        self.assertIn("1/2", why)

    def test_error_case_raises_as_contracted_is_pass(self):
        v, _ = runner.judge(case(expected=None, expect_error=True),
                            obs(is_error=True, error_text="To infinity and beyonddd"))
        self.assertEqual(v, "pass")

    def test_error_case_with_no_error_is_fail(self):
        v, _ = runner.judge(case(expected=None, expect_error=True),
                            obs(numeric=1.0))
        self.assertEqual(v, "fail")


class TestInputConstructionVsCalculatorFailure(unittest.TestCase):
    """The distinction Phase B could not make."""

    def test_input_build_is_not_a_calculator_failure(self):
        v, why = runner.judge(case(expected=4),
                              obs(status="pass", error_class="input_build",
                                  detail="keypad built '-(2(())^(2))'"))
        self.assertEqual(v, "input_construction_failure")
        self.assertNotEqual(v, "fail")
        self.assertIn("keypad built", why)

    def test_input_build_wins_over_a_wrong_numeric_observation(self):
        # Even if a number came back, a mis-built expression is a UI defect.
        v, _ = runner.judge(case(expected=4),
                            obs(numeric=99.0, error_class="input_build",
                                detail="keypad built something else"))
        self.assertEqual(v, "input_construction_failure")

    def test_real_evaluator_failure_still_reads_as_fail(self):
        v, _ = runner.judge(case(expected=98),
                            obs(is_error=True, error_text="Math ERROR",
                                error_class="system"))
        self.assertEqual(v, "fail")


class TestInfrastructureVsCalculatorFailure(unittest.TestCase):
    def test_collector_error_is_infrastructure(self):
        v, why = runner.judge(case(expected=5),
                              obs(status="collector_error",
                                  detail="node exited 1"))
        self.assertEqual(v, "collector_error")
        self.assertIn("node exited 1", why)

    def test_collector_error_is_never_scored_as_pass(self):
        for expected in (5, None):
            v, _ = runner.judge(case(expected=expected),
                                obs(status="collector_error", detail="x"))
            self.assertNotEqual(v, "pass")

    def test_unexecuted_is_not_a_failure(self):
        v, why = runner.judge(case(expected=5),
                              obs(status="unexecuted",
                                  detail="no keypad sequence"))
        self.assertEqual(v, "unexecuted")
        self.assertNotEqual(v, "fail")
        self.assertIn("no keypad sequence", why)

    def test_absent_observation_is_unexecuted(self):
        v, _ = runner.judge(case(expected=5), None)
        self.assertEqual(v, "unexecuted")


class TestUnresolvedSpecification(unittest.TestCase):
    UNRES = {"id": 35, "ascii": "5+5 then x2", "internal_expr": None,
             "expected": None, "expect_error": False,
             "internal_expr_source": "unresolved",
             "note": "UNRESOLVED. contested Ans-chaining expectation"}

    def test_unresolved_outranks_any_observation(self):
        for o in (None,
                  obs(numeric=20.0),
                  obs(is_error=True, error_text="Math ERROR"),
                  obs(status="unexecuted", detail="no expression"),
                  obs(status="collector_error", detail="boom"),
                  obs(error_class="input_build", detail="wrong")):
            v, _ = runner.judge(self.UNRES, o)
            self.assertEqual(v, "unresolved",
                             "unresolved must not become %r" % (v,))

    def test_unresolved_reason_is_the_cases_own_note(self):
        _, why = runner.judge(self.UNRES, None)
        self.assertIn("contested", why)

    def test_a_case_with_a_real_expectation_is_not_unresolved(self):
        v, _ = runner.judge(case(expected=20), obs(numeric=20.0))
        self.assertEqual(v, "pass")


class TestVerdictVocabularyIsClosed(unittest.TestCase):
    def test_every_verdict_judge_can_return_is_declared_in_the_matrix_legend(self):
        # The .md legend maps verdicts to short codes. A new verdict without a
        # legend entry would render as a bare token and mislead a reader.
        legend = {
            "pass": "PASS", "fail": "FAIL", "unresolved": "UNRES",
            "unexecuted": "N/A", "input_construction_failure": "INPUT",
            "unparseable": "PARSE", "collector_error": "COLL",
        }
        produced = {
            runner.judge(case(expected=5), obs(numeric=5.0))[0],
            runner.judge(case(expected=5), obs(numeric=6.0))[0],
            runner.judge({"id": 1, "expected": None, "expect_error": False,
                          "internal_expr_source": "unresolved",
                          "note": "n"}, None)[0],
            runner.judge(case(expected=5), None)[0],
            runner.judge(case(expected=5), obs(status="collector_error",
                                              detail="x"))[0],
            runner.judge(case(expected=5), obs(error_class="input_build",
                                              detail="x"))[0],
            runner.judge(case(expected=5), obs(observed="junk"))[0],
        }
        self.assertTrue(produced.issubset(set(legend)),
                        "verdict missing from the matrix legend: %s"
                        % (produced - set(legend)))


class TestVerdictLegendAndFailureReport(unittest.TestCase):
    """The legend and the grouped report are data, so they cannot drift."""

    def test_every_verdict_has_a_code_and_a_meaning(self):
        for v, (code, meaning) in runner.VERDICT_LEGEND.items():
            self.assertTrue(code, "verdict %r has no short code" % v)
            self.assertTrue(meaning, "verdict %r has no explanation" % v)

    def test_verdict_code_is_stable(self):
        self.assertEqual(runner.verdict_code("pass"), "PASS")
        self.assertEqual(runner.verdict_code("input_construction_failure"), "INPUT")
        self.assertEqual(runner.verdict_code("collector_error"), "COLL")
        self.assertEqual(runner.verdict_code("unresolved"), "UNRES")
        self.assertEqual(runner.verdict_code(None), "-")

    def test_unknown_verdict_is_surfaced_not_hidden(self):
        self.assertEqual(runner.verdict_code("brand_new_thing"), "brand_new_thing")

    def test_only_fail_counts_as_a_calculator_defect(self):
        self.assertEqual(runner.DEFECT_VERDICTS, ("fail",))
        for v in ("unresolved", "input_construction_failure", "unexecuted",
                  "collector_error", "unparseable"):
            self.assertNotIn(v, runner.DEFECT_VERDICTS,
                             "%s must not be counted as a calculator defect" % v)

    def _row(self, cid, verdicts):
        row = {"id": cid, "ascii": "a%d" % cid, "internal_expr": "e",
               "internal_expr_source": "keypad-verified", "expected": 1,
               "expect_error": False}
        for p in runner.PATHS:
            row[p] = {"verdict": verdicts.get(p, "pass"), "why": "because",
                      "observed": None, "numeric": None, "error_text": None,
                      "error_class": None, "getExpr": None, "detail": ""}
        return row

    def test_failure_report_groups_by_verdict_and_names_every_cell(self):
        import tempfile
        rows = [self._row(1, {"node_bridge": "fail",
                              "browser_file": "input_construction_failure",
                              "http": "collector_error"}),
                self._row(2, {"engine": "unresolved"})]
        with tempfile.TemporaryDirectory() as d:
            p = runner.write_failure_report(rows, d)
            text = open(p, encoding="utf-8").read()
        for token in ("## FAIL", "## INPUT", "## COLL", "## UNRES"):
            self.assertIn(token, text)
        # case 1 fails on three collectors, each must be listed with its reason
        self.assertIn("case 1", text)
        self.assertIn("because", text)
        self.assertIn("case 2", text)
        self.assertNotIn("## PASS", text)

    def test_failure_report_says_so_when_everything_passes(self):
        import tempfile
        rows = [self._row(1, {})]
        with tempfile.TemporaryDirectory() as d:
            p = runner.write_failure_report(rows, d)
            text = open(p, encoding="utf-8").read()
        self.assertIn("No non-passing results.", text)


class TestRealRunUsesEveryClassification(unittest.TestCase):
    """If a real run exists, prove the classifier produced several classes."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(RESULTS):
            raise unittest.SkipTest("no comparator run at %s" % RESULTS)
        with open(RESULTS, encoding="utf-8") as f:
            cls.doc = json.load(f)

    def test_real_run_contains_more_than_pass(self):
        verdicts = {c[p]["verdict"] for c in self.doc["cases"]
                    for p in self.doc["paths"]}
        self.assertTrue({"fail"} <= verdicts or {"unexecuted"} <= verdicts,
                        "a real run with only PASS is suspicious: %s" % verdicts)

    def test_every_real_failure_names_a_reason(self):
        for c in self.doc["cases"]:
            for p in self.doc["paths"]:
                if c[p]["verdict"] in ("fail", "unexecuted",
                                       "input_construction_failure",
                                       "collector_error", "unresolved"):
                    self.assertTrue(c[p]["why"],
                                    "case %s path %s" % (c["id"], p))


if __name__ == "__main__":
    unittest.main()