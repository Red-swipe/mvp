"""Tests for the audit comparator's own helpers.

These cover the comparison utilities only. They deliberately do NOT assert
calculator behaviour: the 46-case battery does that, and its results are
evidence, not a pass/fail gate, because the adjacency and divide-by-zero
contracts are still undecided (audit/docs/adjacency_contract.md,
audit/docs/divzero_contract.md).

Run: python -m pytest test_comparator_tools.py -q
"""
import importlib.util
import json
import os
import pathlib
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = PROJECT / "audit" / "tools"

_spec = importlib.util.spec_from_file_location("comparator_collectors", TOOLS / "collectors.py")
collectors = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collectors)

CASES_JSON = PROJECT / "audit" / "data" / "cases.json"


class TestParseNum(unittest.TestCase):
    """parse_num is copied verbatim from test_file_mode; pin its behaviour."""

    def test_plain_float(self):
        self.assertAlmostEqual(collectors.parse_num("5"), 5.0)
        self.assertAlmostEqual(collectors.parse_num(" 110.25 "), 110.25)

    def test_proper_and_mixed_fractions(self):
        self.assertAlmostEqual(collectors.parse_num("1/2"), 0.5)
        self.assertAlmostEqual(collectors.parse_num("4 1/2"), 4.5)
        self.assertAlmostEqual(collectors.parse_num("-2 1/2"), -2.5)

    def test_percent(self):
        self.assertAlmostEqual(collectors.parse_num("50%"), 0.5)

    def test_unparseable_raises_and_is_never_zero(self):
        for bad in ("Math ERROR", "To infinity and beyonddd", "", "abc"):
            with self.assertRaises(ValueError, msg=bad):
                collectors.parse_num(bad)


class TestNormalizeLcd(unittest.TestCase):
    """The LCD emits typographic characters float() cannot read."""

    def test_unicode_minus(self):
        self.assertEqual(collectors.normalize_lcd("\u22126"), "-6")

    def test_takes_last_token(self):
        self.assertEqual(collectors.normalize_lcd("D Math 3(-2) \u22126 \u22126"), "-6")

    def test_collapses_whitespace_and_zero_width(self):
        self.assertEqual(collectors.normalize_lcd("  a \u200b  b "), "b")

    def test_none_and_empty(self):
        self.assertIsNone(collectors.normalize_lcd(None))
        self.assertIsNone(collectors.normalize_lcd("   "))


class TestCloseEnough(unittest.TestCase):
    def test_tolerance(self):
        self.assertTrue(collectors.close_enough(0.5, 0.5 + 1e-9))
        self.assertFalse(collectors.close_enough(0.5, 0.6))

    def test_fraction_against_decimal(self):
        # The display-format finding from raw/context.md: 1/2 must compare
        # equal to 0.5 even though the calculator may print a fraction.
        self.assertTrue(collectors.close_enough("1/2", "0.5"))


class TestBatteryTable(unittest.TestCase):
    """Structural guarantees about the declarative table."""

    @classmethod
    def setUpClass(cls):
        with open(CASES_JSON, encoding="utf-8") as f:
            cls.doc = json.load(f)
        cls.cases = cls.doc["cases"]

    def test_exactly_46_cases_with_unique_ids_1_to_46(self):
        self.assertEqual(len(self.cases), 46)
        self.assertEqual(sorted(c["id"] for c in self.cases), list(range(1, 47)))

    def test_every_case_declares_its_provenance(self):
        for c in self.cases:
            self.assertIn(c["internal_expr_source"],
                          ("keypad-verified", "harness-derived", "unresolved"),
                          msg="case %d" % c["id"])

    def test_unresolved_cases_have_no_expected_value(self):
        for c in self.cases:
            if c["internal_expr_source"] == "unresolved":
                self.assertIsNone(c["expected"], msg="case %d" % c["id"])
                self.assertTrue(c.get("note"), msg="case %d must explain why" % c["id"])

    def test_error_cases_have_no_numeric_expectation(self):
        for c in self.cases:
            if c["expect_error"]:
                self.assertIsNone(c["expected"], msg="case %d" % c["id"])

    def test_numeric_cases_have_a_numeric_expectation(self):
        for c in self.cases:
            if not c["expect_error"] and c["internal_expr_source"] != "unresolved":
                self.assertIsInstance(c["expected"], (int, float),
                                      msg="case %d" % c["id"])

    def test_every_keypad_sequence_points_at_a_real_case(self):
        seqs = self.doc["keypad_sequences"]
        known = set(str(c["id"]) for c in self.cases)
        extra = set(seqs.get("_extra_not_in_source_46", {}))
        for key in set(seqs) - {"_note", "_extra_not_in_source_46"}:
            self.assertIn(key, known, "keypad sequence %s has no case" % key)
        for key in extra:
            self.assertIn(key, known, "extra sequence %s has no case" % key)

    def test_only_case_35_is_unresolved(self):
        unresolved = [c["id"] for c in self.cases
                      if c["internal_expr_source"] == "unresolved"]
        self.assertEqual(unresolved, [35])


if __name__ == "__main__":
    unittest.main()