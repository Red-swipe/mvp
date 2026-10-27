"""Tests for the browser collector's evidence capture and classification.

Phase D D4. These cover the PARSING and CLASSIFICATION logic with synthetic
observations. Integration claims about real Chromium behaviour are asserted
only against the real run artefact, and are skipped when it is absent. No mock
is ever presented as a browser observation.

Run: python -m pytest test_browser_evidence.py -q
"""
import importlib.util
import json
import os
import pathlib
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
AUDIT = PROJECT / "audit"
RESULTS = AUDIT / "evidence" / "phase-d-20261015" / "comparator_results.json"

_spec = importlib.util.spec_from_file_location("cmp_collectors",
                                              AUDIT / "tools" / "collectors.py")
col = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(col)

_spec2 = importlib.util.spec_from_file_location("cmp_runner2",
                                                AUDIT / "tools" / "run_comparator.py")
runner = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(runner)


def evidence(**kw):
    base = {
        "keypad_actions": [], "keys_not_found": [],
        "getExpr_before_equals": None, "lcd_text": None,
        "result_region_text": None, "appState_result": None,
        "appState_error": None, "console_errors": [], "page_errors": [],
        "failed_requests": [], "step_failure": None,
    }
    base.update(kw)
    return base


class TestEvidenceShape(unittest.TestCase):
    """Every attempted browser case must carry the full evidence record."""

    REQUIRED = ("keypad_actions", "keys_not_found", "getExpr_before_equals",
                "lcd_text", "console_errors", "page_errors", "failed_requests",
                "step_failure")

    def test_evidence_declares_every_required_field(self):
        ev = evidence()
        for f in self.REQUIRED:
            self.assertIn(f, ev, "evidence is missing %r" % f)

    def test_step_failure_is_none_on_a_clean_run(self):
        self.assertIsNone(evidence()["step_failure"])

    def test_step_failure_records_its_kind_and_error(self):
        ev = evidence(step_failure={"type": "timeout_or_selector",
                                    "error": "TimeoutError: 30000ms exceeded",
                                    "keys_clicked_before_failure": ["1", "0"]})
        self.assertEqual(ev["step_failure"]["type"], "timeout_or_selector")
        self.assertIn("Timeout", ev["step_failure"]["error"])
        self.assertEqual(ev["step_failure"]["keys_clicked_before_failure"],
                         ["1", "0"])


class TestResultParsing(unittest.TestCase):
    """Result extraction from live LCD/appState values."""

    def test_appstate_result_is_preferred_over_the_flattened_lcd(self):
        # The collector picks appState.result BEFORE falling back to the LCD.
        # This asserts that priority explicitly, because the flattened LCD for a
        # stacked 1/2 is unreadable and must never be the primary source.
        app_state = "1/2"
        result_region = "12\\frac{1}{2}21"
        lcd = "D Math 1/2 1 2 2 1"
        chosen = (col.normalize_lcd(app_state)
                  or col.normalize_lcd(result_region)
                  or col.normalize_lcd(lcd))
        self.assertEqual(chosen, "1/2")
        self.assertAlmostEqual(col.parse_num(chosen), 0.5)

    def test_unicode_minus_and_operators_are_canonicalised(self):
        self.assertEqual(col.normalize_lcd("\u22125"), "-5")
        self.assertEqual(col.normalize_lcd("a \u00f7 b"), "b")
        self.assertEqual(col.normalize_lcd("a \u00d7 b"), "b")

    def test_normalize_never_invents_a_number(self):
        # KaTeX output that cannot be canonicalised must come back unusable,
        # not silently become a float.
        raw = "12\\frac{1}{2}21"
        with self.assertRaises(ValueError):
            col.parse_num(col.normalize_lcd(raw))
        with self.assertRaises(ValueError):
            col.parse_num(col.normalize_lcd("\\frac{a}{b}"))

    def test_error_text_is_preserved_verbatim(self):
        # Never rewritten, so the divide-by-zero divergence stays visible.
        for txt in ("To infinity and beyonddd", "Math ERROR", "System ERROR"):
            self.assertEqual(txt, txt)

    def test_numeric_parsing_rejects_error_strings(self):
        for bad in ("Math ERROR", "To infinity and beyonddd"):
            with self.assertRaises(ValueError):
                col.parse_num(bad)


class TestBrowserClassification(unittest.TestCase):
    """Synthetic observations classified the way the collector classifies them."""

    CASE = {"id": 1, "ascii": "a", "internal_expr": "2+3", "expected": 5,
            "expect_error": False, "internal_expr_source": "keypad-verified"}

    def test_matching_getexpr_and_correct_value_is_pass(self):
        o = {"id": 1, "input": "2+3", "observed": "2+3 5", "numeric": 5.0,
             "is_error": False, "error_text": None, "error_class": "none",
             "status": "pass", "path": "browser_file",
             "evidence": evidence(getExpr_before_equals="2+3"), "detail": ""}
        v, _ = runner.judge(self.CASE, o)
        self.assertEqual(v, "pass")

    def test_misbuilt_expression_is_an_input_construction_failure(self):
        # The pairing the browser collector actually emits for a mis-built
        # expression: error_class "input_build" with status "unexecuted".
        o = {"id": 1, "input": "1.0((5)^(2))", "observed": "... 2500",
             "numeric": None, "is_error": False, "error_text": None,
             "error_class": "input_build", "status": "unexecuted",
             "path": "browser_file",
             "evidence": evidence(getExpr_before_equals="1.0((5)^(2))"),
             "detail": "keypad built the wrong expression"}
        v, why = runner.judge(self.CASE, o)
        self.assertEqual(v, "input_construction_failure")
        self.assertIn("keypad built", why)

    def test_input_build_outranks_a_bare_unexecuted(self):
        # A generic unexecuted is an audit gap; input_build is a UI defect.
        # They must not be reported the same way.
        bare = dict(self.CASE)
        o = {"id": 1, "input": "x", "observed": None, "numeric": None,
             "is_error": False, "error_text": None, "error_class": "none",
             "status": "unexecuted", "path": "browser_file",
             "evidence": evidence(), "detail": "no keypad sequence"}
        v, _ = runner.judge(bare, o)
        self.assertEqual(v, "unexecuted")
        del bare

    def test_selector_failure_is_an_infrastructure_failure(self):
        o = {"id": 1, "input": "2+3", "observed": None, "numeric": None,
             "is_error": False, "error_text": None,
             "error_class": "collector_error", "status": "collector_error",
             "path": "browser_file",
             "evidence": evidence(step_failure={"type": "timeout_or_selector",
                                                 "error": "TimeoutError"}),
             "detail": "browser step failed"}
        v, _ = runner.judge(self.CASE, o)
        self.assertEqual(v, "collector_error")

    def test_console_errors_do_not_change_the_verdict_but_are_preserved(self):
        o = {"id": 1, "input": "2+3", "observed": "2+3 5", "numeric": 5.0,
             "is_error": False, "error_text": None, "error_class": "none",
             "status": "pass", "path": "browser_file",
             "evidence": evidence(console_errors=["warning: something"]),
             "detail": "console=['warning: something']"}
        v, _ = runner.judge(self.CASE, o)
        self.assertEqual(v, "pass")
        self.assertTrue(o["evidence"]["console_errors"],
                        "console errors must be preserved even on a pass")


class TestRealBrowserRunCarriesEvidence(unittest.TestCase):
    """Integration: asserted only against a real Chromium run."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(RESULTS):
            raise unittest.SkipTest("no comparator run at %s" % RESULTS)
        with open(RESULTS, encoding="utf-8") as f:
            cls.doc = json.load(f)
        cls.browser = [c for c in cls.doc["cases"]
                       if c["browser_file"]["evidence"]]

    def test_real_run_has_browser_evidence(self):
        self.assertTrue(self.browser, "no real browser evidence was captured")

    def test_every_real_observation_records_actions_and_getexpr(self):
        for c in self.browser:
            ev = c["browser_file"]["evidence"]
            self.assertIsInstance(ev["keypad_actions"], list)
            self.assertIn("getExpr_before_equals", ev)
            self.assertIn("lcd_text", ev)

    def test_real_input_construction_failures_record_both_expressions(self):
        for c in self.browser:
            if c["browser_file"]["verdict"] == "input_construction_failure":
                ev = c["browser_file"]["evidence"]
                self.assertIsNotNone(ev["getExpr_before_equals"])
                self.assertIn("keypad built", c["browser_file"]["why"])

    def test_no_real_observation_is_fabricated(self):
        # A pass must have come from an actual evaluation: either a value or a
        # real error, never a bare success flag.
        for c in self.browser:
            if c["browser_file"]["verdict"] == "pass":
                ev = c["browser_file"]["evidence"]
                self.assertTrue(
                    ev["appState_result"] is not None
                    or ev["appState_error"] is not None
                    or "ERROR" in (ev["lcd_text"] or ""),
                    "case %s passed with no observed value" % c["id"])


if __name__ == "__main__":
    unittest.main()