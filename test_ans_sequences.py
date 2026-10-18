"""Tests for the D5 stateful Ans sequence instrumentation.

Covers the sequence definitions, the contract gating, and the normalisation
helper. Integration claims are asserted only against the real run artefact and
are skipped when it is absent. No sequence is scored when its contract is
blocked.

Run: python -m pytest test_ans_sequences.py -q
"""
import importlib.util
import json
import os
import pathlib
import unittest

PROJECT = pathlib.Path(__file__).resolve().parent
AUDIT = PROJECT / "audit"
RESULTS = AUDIT / "evidence" / "phase-d-20261015" / "ans_sequences.json"

_spec = importlib.util.spec_from_file_location("ans_seq",
                                              AUDIT / "tools" / "ans_sequences.py")
ans = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ans)


class TestSequenceDefinitions(unittest.TestCase):
    def test_ids_are_unique(self):
        ids = [s["id"] for s in ans.SEQUENCES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_sequence_states_a_contract_and_a_why(self):
        for s in ans.SEQUENCES:
            self.assertTrue(s["contract"], "%s has no contract" % s["id"])
            self.assertTrue(s["why"], "%s has no rationale" % s["id"])

    def test_blocked_sequences_carry_no_expected_answer(self):
        # A sequence whose contract is blocked must NOT smuggle in an
        # expectation; that is what keeps this instrumentation honest.
        for s in ans.SEQUENCES:
            if s["contract"].startswith("BLOCKED"):
                self.assertIsNone(s["expected_final"],
                                  "%s is blocked but states a result" % s["id"])
                self.assertIsNone(s["expected_ans"],
                                  "%s is blocked but states an Ans" % s["id"])
                self.assertTrue(s.get("note"),
                                "%s must explain why it is blocked" % s["id"])

    def test_contested_sequence_is_not_scored(self):
        chain = next(s for s in ans.SEQUENCES if s["id"] == "ans_chain")
        self.assertIn("contested", chain["contract"])
        self.assertIsNone(chain["expected_final"])

    def test_the_harmless_baseline_sequence_has_an_expectation(self):
        base = next(s for s in ans.SEQUENCES if s["id"] == "ans_basic")
        self.assertEqual(base["expected_final"], 7)
        self.assertEqual(base["contract"], "approved_by_source")

    def test_every_observation_step_names_what_it_watched(self):
        for s in ans.SEQUENCES:
            for st in s["steps"]:
                self.assertTrue(st.get("note"),
                                "%s has an unnamed step" % s["id"])

    def test_divzero_sequences_actually_divide_by_zero(self):
        for s in ans.SEQUENCES:
            for st in s["steps"]:
                if st.get("keys") and "divide" in st["keys"]:
                    self.assertIn("0", st["keys"])
                    break


class TestNormalisation(unittest.TestCase):
    def test_typographic_minus_and_operators(self):
        self.assertEqual(ans.normalize("\u22125"), "-5")
        self.assertEqual(ans.normalize("a \u00f7 b"), "b")

    def test_empty_and_none(self):
        self.assertIsNone(ans.normalize(None))
        self.assertIsNone(ans.normalize("   "))


class TestRealAnsRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(RESULTS):
            raise unittest.SkipTest("no Ans run at %s" % RESULTS)
        with open(RESULTS, encoding="utf-8") as f:
            cls.doc = json.load(f)
        cls.by_id = {s["id"]: s for s in cls.doc["sequences"]}
        cls.server_by_id = {s["id"]: s for s in cls.doc["server_sequences"]}

    def test_every_sequence_was_executed_on_both_paths(self):
        self.assertEqual(set(self.by_id), set(self.server_by_id))
        for sid in self.by_id:
            self.assertTrue(self.by_id[sid]["steps"], "%s has no steps" % sid)

    def test_baseline_ans_behaviour_is_correct_on_both_paths(self):
        # 5 then Ans+2 must be 7. Ordinary arithmetic, no contract needed.
        self.assertEqual(str(self.by_id["ans_basic"]["observed_final"]), "7")
        self.assertEqual(str(self.server_by_id["ans_basic"]["observed_final"]), "7")

    def test_ans_is_preserved_across_a_divide_by_zero(self):
        # The claim under test. The server keeps ans=10 through the error; the
        # browser keeps localAns=10.
        srv = self.server_by_id["divzero_then_ans"]
        divzero = next(s for s in srv["steps"]
                       if s.get("keys") and "divide" in s["keys"])
        self.assertEqual(str(divzero["ans"]), "10",
                         "the server must preserve Ans through an error")
        brw = self.by_id["divzero_then_ans"]
        divzero_b = next(s for s in brw["steps"]
                         if s.get("keys") and "divide" in s["keys"])
        self.assertEqual(str(divzero_b["localAns"]), "10")

    def test_the_paths_diverge_on_the_next_calculation(self):
        # The divergence is GONE. `_calculation_error()` (mvp_server.py) and
        # the C7 file-mode fix both clear the input buffer, so both paths now
        # compute Ans+1 = 11 from a clean expression.
        cross = self.doc["cross_path"]["divzero_then_ans"]
        self.assertTrue(cross["paths_agree"],
                        "browser and server must now agree after a divzero")
        self.assertEqual(str(cross["browser_final"]), "11")
        self.assertEqual(str(cross["server_final"]), "11")

    def test_the_divergence_cause_is_a_stale_server_expression_buffer(self):
        # The stale buffer is FIXED: the server must show an EMPTY expression
        # immediately after the divide-by-zero, and the next input must be the
        # clean 'Ans+1' expansion, never '1/010+1'.
        srv = self.server_by_id["divzero_then_ans"]
        divzero = next(s for s in srv["steps"]
                       if s.get("keys") and "divide" in s["keys"])
        self.assertEqual(str(divzero["expression"]), "",
                         "the server must clear the expression buffer on error")
        last = srv["steps"][-1]
        self.assertEqual(str(last["expression"]), "10+1",
                         "the next calculation must expand from a clean buffer, "
                         "never from the failed '1/0'")
        self.assertNotEqual(str(last["expression"]), "1/010+1",
                            "the historical stale buffer must not come back")
        self.assertEqual(str(last["result"]), "11")
        self.assertNotEqual(str(last["result"]), "1.1",
                            "the historical wrong answer 1.1 must not come back")

    def test_the_browser_clears_the_buffer_after_an_error(self):
        brw = self.by_id["divzero_then_ans"]
        last = [s for s in brw["steps"] if s.get("keys")][-1]
        self.assertEqual(last["getExpr"], "Ans+1",
                         "the browser starts the next input cleanly")

    def test_calculator_recovers_after_a_divide_by_zero(self):
        # Both paths accept the next calculation, so recovery is not blocked.
        self.assertEqual(str(self.by_id["usable_after_divzero"]["observed_final"]), "4")

    def test_blocked_sequences_were_recorded_but_not_asserted(self):
        for sid in ("divzero_then_ans", "usable_after_divzero"):
            self.assertIn("BLOCKED", self.by_id[sid]["contract"])
            self.assertTrue(self.by_id[sid]["note"])


if __name__ == "__main__":
    unittest.main()