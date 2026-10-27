"""Data-validation tests for audit/data/cases.json and the comparator runner.

Covers D1: the battery table must be internally consistent, and the runner must
report its counts accurately so a green-looking matrix cannot hide a case that
was silently skipped.

Run: python -m pytest test_comparator_battery.py -q
"""
import importlib.util
import json
import pathlib
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
AUDIT = PROJECT / "audit"
CASES_JSON = AUDIT / "data" / "cases.json"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = _load(AUDIT / "tools" / "run_comparator.py", "comparator_runner")

REQUIRED_STR_FIELDS = ("ascii", "internal_expr_source")
VALID_PROVENANCE = ("keypad-verified", "harness-derived", "unresolved")


class TestBatteryShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CASES_JSON, encoding="utf-8") as f:
            cls.doc = json.load(f)
        cls.cases = cls.doc["cases"]

    def test_exactly_46_cases(self):
        self.assertEqual(len(self.cases), 46)

    def test_ids_are_unique_and_contiguous_1_to_46(self):
        ids = [c["id"] for c in self.cases]
        self.assertEqual(len(set(ids)), len(ids), "duplicate case ids present")
        self.assertEqual(sorted(ids), list(range(1, 47)))

    def test_every_case_has_the_required_fields(self):
        for c in self.cases:
            for f in ("id", "ascii", "internal_expr", "expected",
                      "expect_error", "internal_expr_source"):
                self.assertIn(f, c, "case %s missing field %r" % (c.get("id"), f))

    def test_field_types_are_valid(self):
        for c in self.cases:
            self.assertIsInstance(c["id"], int)
            self.assertIsInstance(c["ascii"], str)
            self.assertIsInstance(c["expect_error"], bool)
            self.assertIn(c["internal_expr_source"], VALID_PROVENANCE)
            for f in REQUIRED_STR_FIELDS:
                if f in c:
                    self.assertIsInstance(c[f], str)
            self.assertTrue(c["internal_expr"] is None
                            or isinstance(c["internal_expr"], str))
            self.assertTrue(c["expected"] is None
                            or isinstance(c["expected"], (int, float)))

    def test_no_silent_numeric_expectation_on_error_cases(self):
        for c in self.cases:
            if c["expect_error"]:
                self.assertIsNone(c["expected"], "case %d is an error case" % c["id"])

    def test_unresolved_cases_declare_no_expectation_and_explain_why(self):
        unresolved = [c for c in self.cases
                      if c["internal_expr_source"] == "unresolved"]
        self.assertTrue(unresolved, "expected at least one explicitly unresolved case")
        for c in unresolved:
            self.assertIsNone(c["expected"],
                              "case %d must not carry a fabricated expectation" % c["id"])
            self.assertTrue(c.get("note"),
                            "case %d must record why it is unresolved" % c["id"])

    def test_every_error_case_declares_its_expectation(self):
        # An error case must be either explicitly unresolved or carry a note
        # saying the string contract is still open.
        for c in self.cases:
            if c["expect_error"]:
                self.assertTrue(
                    c.get("note"),
                    "error case %d must document its error contract status" % c["id"])

    def test_cases_with_an_expression_are_all_provenanced(self):
        for c in self.cases:
            if c["internal_expr"] is None:
                self.assertEqual(c["internal_expr_source"], "unresolved",
                                 "case %d has no expression but is not unresolved"
                                 % c["id"])

    def test_meta_declares_the_schema_and_provenance_vocabulary(self):
        meta = self.doc["_meta"]
        self.assertIn("schema", meta)
        for term in VALID_PROVENANCE:
            self.assertIn(term, meta["provenance_of_internal_expr"],
                          "provenance vocabulary is missing %r" % term)
            self.assertTrue(meta["provenance_of_internal_expr"][term],
                            "provenance %r has no explanation" % term)
        self.assertIn("source_document", meta)

    def test_meta_records_both_open_decision_gates(self):
        # Phase D Gate A and Gate B must stay visible in the data, not only in
        # prose, so a consumer of the JSON sees that they are undecided.
        meta = self.doc["_meta"]
        self.assertIn("adjacency_decision", meta)
        self.assertIn("divzero_decision", meta)


class TestNoCaseIsSilentlyOmitted(unittest.TestCase):
    """The runner's OUTPUT must account for every loaded case on every collector.

    These read the comparator results artefact, not the declarative table: the
    collector columns exist only after a run.
    """
    RESULTS = AUDIT / "evidence" / "phase-d-20261015" / "comparator_results.json"

    @classmethod
    def setUpClass(cls):
        import os
        if not os.path.exists(cls.RESULTS):
            raise unittest.SkipTest(
                "no comparator run yet at %s; run "
                "python audit/tools/run_comparator.py first" % cls.RESULTS)
        with open(cls.RESULTS, encoding="utf-8") as f:
            doc = json.load(f)
        cls.cases = doc["cases"]
        cls.paths = doc["paths"]
        with open(CASES_JSON, encoding="utf-8") as f:
            cls.declared = json.load(f)["cases"]

    def test_every_case_id_appears_in_every_collector_column(self):
        for c in self.cases:
            for p in self.paths:
                self.assertIn(p, c,
                              "case %s missing collector column %r" % (c["id"], p))

    def test_result_artefact_covers_every_declared_case(self):
        declared = sorted(c["id"] for c in self.declared)
        reported = sorted(c["id"] for c in self.cases)
        self.assertEqual(reported, declared,
                         "the runner dropped or invented cases")

    def test_verdicts_are_from_the_declared_vocabulary(self):
        allowed = {"pass", "fail", "unresolved", "unexecuted", "unparseable",
                   "input_construction_failure", "collector_error"}
        for c in self.cases:
            for p in self.paths:
                self.assertIn(c[p]["verdict"], allowed,
                              "case %s path %s" % (c["id"], p))

    def test_every_verdict_carries_a_reason_when_not_passing(self):
        for c in self.cases:
            for p in self.paths:
                if c[p]["verdict"] != "pass":
                    self.assertTrue(
                        c[p]["why"],
                        "case %s path %s verdict %r has no reason"
                        % (c["id"], p, c[p]["verdict"]))

    def test_all_five_collectors_are_registered(self):
        self.assertEqual(len(self.paths), 5)
        self.assertEqual(set(self.paths),
                         {"engine", "safe_eval", "node_bridge", "http",
                          "browser_file"})


class TestRunnerCounts(unittest.TestCase):
    """summarize() must not under-report or double-count."""

    PATHS = runner.PATHS

    def _rows(self, verdict_map):
        """verdict_map: {path: {id: verdict}}"""
        ids = list(verdict_map[self.PATHS[0]])
        rows = []
        for i in ids:
            row = {"id": i}
            for p in self.PATHS:
                row[p] = {"verdict": verdict_map[p][i], "why": "",
                          "observed": None, "numeric": None,
                          "error_text": None, "error_class": None,
                          "getExpr": None, "detail": ""}
            rows.append(row)
        return rows

    def test_empty_table(self):
        self.assertEqual(runner.summarize([]),
                         {"loaded": 0, "executed": 0, "unresolved": 0,
                          "skipped": 0, "failed": 0})

    def test_single_pass_case_counts_once_per_path(self):
        rows = self._rows({p: {1: "pass"} for p in self.PATHS})
        s = runner.summarize(rows)
        self.assertEqual(s["loaded"], 1)
        self.assertEqual(s["executed"], 5)
        self.assertEqual(s["failed"], 0)
        self.assertEqual(s["unresolved"], 0)
        self.assertEqual(s["skipped"], 0)

    def test_counts_partition_every_case_path_pair(self):
        verdicts = ["pass", "fail", "unresolved", "unexecuted", "unparseable",
                    "input_construction_failure", "collector_error"]
        ids = list(range(1, 8))
        rows = self._rows({p: dict(zip(ids, verdicts)) for p in self.PATHS})
        s = runner.summarize(rows)
        # every pair must land in exactly one bucket
        self.assertEqual(s["executed"] + s["unresolved"] + s["skipped"],
                         len(ids) * len(self.PATHS))
        self.assertEqual(s["executed"], 3 * len(self.PATHS))   # pass+fail+unparseable
        self.assertEqual(s["failed"], 1 * len(self.PATHS))
        self.assertEqual(s["unresolved"], 1 * len(self.PATHS))
        self.assertEqual(s["skipped"], 3 * len(self.PATHS))

    def test_failed_is_a_subset_of_executed(self):
        rows = self._rows({p: {1: "fail", 2: "pass"} for p in self.PATHS})
        s = runner.summarize(rows)
        self.assertLessEqual(s["failed"], s["executed"])

    def test_skipped_does_not_inflate_executed(self):
        rows = self._rows({p: {1: "collector_error", 2: "unexecuted",
                               3: "input_construction_failure"}
                           for p in self.PATHS})
        s = runner.summarize(rows)
        self.assertEqual(s["executed"], 0)
        self.assertEqual(s["skipped"], 3 * len(self.PATHS))


if __name__ == "__main__":
    unittest.main()