"""Tests for the D3 keypad coverage inventory.

The inventory is a measurement tool, so the tests cover its LOGIC (sequence
selection, validity rules, accounting) rather than re-running the browser.
Browser observations live in
audit/evidence/phase-d-20261015/keypad_inventory.json and are only asserted
against if that artefact already exists.

Run: python -m pytest test_keypad_inventory.py -q
"""
import importlib.util
import json
import os
import pathlib
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
AUDIT = PROJECT / "audit"
INVENTORY = AUDIT / "evidence" / "phase-d-20261015" / "keypad_inventory.json"

_spec = importlib.util.spec_from_file_location(
    "keypad_inventory", AUDIT / "tools" / "build_keypad_inventory.py")
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)


class TestDerivedSequences(unittest.TestCase):
    """A derived sequence must only use controls the keypad really exposes."""

    def setUp(self):
        with open(AUDIT / "data" / "cases.json", encoding="utf-8") as f:
            self.doc = json.load(f)

    def test_derived_sequences_only_reference_documented_keys(self):
        # The 51 unique data-key values observed in frontend.html. Kept here as
        # a fixture so a typo in a derived sequence fails loudly instead of
        # silently becoming an "unconstructable" case.
        known = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "ac", "alpha",
                 "ans", "calc", "cos", "decimal", "del", "divide", "dpad_center",
                 "dpad_down", "dpad_left", "dpad_right", "dpad_up", "ellipsis",
                 "eng", "equals", "fraction", "integral", "inverse", "left_paren",
                 "ln", "log", "m_plus", "minus", "multiply", "negate", "on",
                 "optn", "plus", "power", "right_paren", "s_to_d", "scientific",
                 "setup", "shift", "sin", "sqrt", "square", "sto", "tan",
                 "variable"}
        for cid, keys in inv.DERIVED_SEQUENCES.items():
            for k in keys:
                self.assertIn(k, known,
                              "case %s uses unknown key %r" % (cid, k))

    def test_derived_sequences_end_with_equals(self):
        for cid, keys in inv.DERIVED_SEQUENCES.items():
            self.assertEqual(keys[-1], "equals",
                             "case %s must submit with equals" % cid)

    def test_derived_sequences_do_not_reuse_an_existing_one(self):
        # setdefault in the tool means a derived sequence never overrides the
        # battery's own. Assert the ids are disjoint so that stays true.
        battery = {k for k in self.doc["keypad_sequences"]
                   if not k.startswith("_")}
        self.assertEqual(battery & set(inv.DERIVED_SEQUENCES), set())

    def test_every_case_now_has_a_sequence_or_is_unresolved(self):
        battery = {k: v for k, v in self.doc["keypad_sequences"].items()
                   if not k.startswith("_")}
        battery.update(self.doc["keypad_sequences"].get(
            "_extra_not_in_source_46", {}))
        allids = set(str(c["id"]) for c in self.doc["cases"])
        covered = set(battery) | set(inv.DERIVED_SEQUENCES)
        # only the unresolved case may lack a sequence
        uncovered = allids - covered
        self.assertEqual(uncovered, {"35"},
                         "cases without a keypad sequence: %s" % sorted(uncovered))


class TestValidityRule(unittest.TestCase):
    """The validity rule is what separates a UI defect from a maths defect."""

    def _classify(self, intended, constructed, missing=None):
        if intended is None:
            return "case specification is unresolved"
        if missing:
            return "missing control"
        if constructed is None:
            return "getExpr() unavailable"
        if constructed != intended:
            return "mismatch"
        return "valid"

    def test_matching_expression_is_valid(self):
        self.assertEqual(self._classify("2+3", "2+3"), "valid")

    def test_mismatched_expression_is_not_valid(self):
        self.assertEqual(self._classify("((-2)^(2))", "-(2(())^(2))"), "mismatch")

    def test_unresolved_case_is_never_valid(self):
        self.assertEqual(self._classify(None, None),
                         "case specification is unresolved")


class TestInventoryArtefact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(INVENTORY):
            raise unittest.SkipTest(
                "no inventory yet; run audit/tools/build_keypad_inventory.py")
        with open(INVENTORY, encoding="utf-8") as f:
            cls.doc = json.load(f)

    def test_every_case_is_accounted_for(self):
        self.assertEqual(len(self.doc["rows"]), 46)
        self.assertEqual(self.doc["summary"]["cases"], 46)
        self.assertEqual(self.doc["summary"]["constructable"]
                         + self.doc["summary"]["not_constructable"], 46)

    def test_summary_matches_the_rows(self):
        valid = sum(1 for r in self.doc["rows"] if r["valid"])
        self.assertEqual(self.doc["summary"]["constructable"], valid)

    def test_every_invalid_row_states_a_reason(self):
        for r in self.doc["rows"]:
            if not r["valid"]:
                self.assertTrue(r["reason"],
                                "case %s invalid without a reason" % r["case_id"])

    def test_no_case_is_claimed_valid_without_an_observation(self):
        for r in self.doc["rows"]:
            if r["valid"]:
                self.assertIsNotNone(r["constructed_getExpr"])
                self.assertEqual(r["constructed_getExpr"],
                                 r["intended_internal_expr"])

    def test_inventory_records_the_keypad_key_set(self):
        self.assertGreater(self.doc["key_count"], 0)
        self.assertIn("equals", self.doc["keys_exposed_by_keypad"])

    def test_inventory_is_inventory_only_no_app_change(self):
        # The tool must not claim to have altered keypad behaviour.
        src = (AUDIT / "tools" / "build_keypad_inventory.py").read_text(
            encoding="utf-8")
        for forbidden in ("write_text", "open(frontend", "shutil.copy"):
            self.assertNotIn(forbidden, src,
                             "inventory tool must not write to the frontend")


if __name__ == "__main__":
    unittest.main()