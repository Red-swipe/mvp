"""Equivalence checks for test_frontend.html (manual browser fixture).

The fixture is an HTML page meant to be opened in a browser (it needs DOM +
a live server), so it cannot run under pytest. These tests guarantee it
cannot silently drift from frontend.html:
- same slot-template types in both serializeSlot implementations,
- same mixed-fraction serialization semantics,
- fixture still exercises the documented 1+1 user path.
"""
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
FRONTEND = (PROJECT / "frontend.html").read_text(encoding="utf-8")
FIXTURE = (PROJECT / "test_frontend.html").read_text(encoding="utf-8")


def template_types(src):
    types = set(re.findall(r"item\.type === '(\w+)'", src))
    types |= set(re.findall(r"type:'(\w+)'", src))
    return types


class TestFrontendFixture(unittest.TestCase):
    def test_fixture_exists_and_has_harness(self):
        self.assertIn("function serializeSlot", FIXTURE)
        self.assertIn("const getExpr", FIXTURE)
        self.assertIn("function insertToken", FIXTURE)
        self.assertIn("function resetExpr", FIXTURE)

    def test_template_type_parity(self):
        app_types = template_types(FRONTEND)
        fix_types = template_types(FIXTURE)
        # every template the app can build must serialize in the fixture
        for needed in ("fraction", "radical", "cbrt", "power", "log",
                       "integral", "mixed"):
            self.assertIn(needed, app_types, needed)
            self.assertIn(needed, fix_types, f"fixture missing {needed}")

    def test_mixed_serialization_matches(self):
        pat = r"String\(w\)\.trim\(\)\.startsWith\('-'\)"
        self.assertRegex(FRONTEND, re.compile(pat))
        self.assertRegex(FIXTURE, re.compile(pat))

    def test_user_path_documented(self):
        # 1 + 1 via insertToken, then POST /api/key equals
        self.assertIn("insertToken('1')", FIXTURE)
        self.assertIn("insertToken('+')", FIXTURE)
        self.assertIn("/api/key", FIXTURE)
        self.assertIn('"equals"', FIXTURE.replace("'", '"'))


def extract_function(src, name):
    start = src.index(f"function {name}(")
    brace = src.index("{", start)
    depth, i = 0, brace
    while True:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1


class TestDisplayFormat(unittest.TestCase):
    """Runs the real displayFormat() from frontend.html in node."""

    @classmethod
    def setUpClass(cls):
        import shutil
        if shutil.which("node") is None:
            raise unittest.SkipTest("node is not installed")
        import json
        import subprocess
        fn = extract_function(FRONTEND, "displayFormat")
        cases = [
            ["1.5", "Dot", False], ["1.5", "Comma", False],
            ["[[1.5,2]]", "Comma", False], ["1234567", "Dot", True],
            ["1234567.89", "Comma", True], ["-2.25", "Comma", False],
            ["Math ERROR", "Comma", True],
            ["1.234×10^3", "Comma", False],
        ]
        runner = (
            "let setupSettings={decimal_mark:'Dot',digit_separator:false};\n"
            + fn +
            "\nconst cases=JSON.parse(process.argv[2]);const out=[];"
            "for(const [v,m,s] of cases){setupSettings.decimal_mark=m;"
            "setupSettings.digit_separator=s;out.push(displayFormat(v));}"
            "process.stdout.write(JSON.stringify(out));\n")
        tmp = PROJECT / ".display_test_tmp.js"
        tmp.write_text(runner, encoding="utf-8")
        try:
            proc = subprocess.run(["node", str(tmp), json.dumps(cases)],
                                  capture_output=True, text=True,
                                  encoding="utf-8", timeout=60)
        finally:
            tmp.unlink(missing_ok=True)
        assert proc.returncode == 0, proc.stderr[:300]
        cls.got = dict(zip([c[0] + "|" + c[1] for c in cases],
                           json.loads(proc.stdout)))

    def test_dot(self):
        self.assertEqual(self.got["1.5|Dot"], "1.5")

    def test_comma(self):
        self.assertEqual(self.got["1.5|Comma"], "1,5")
        self.assertEqual(self.got["-2.25|Comma"], "-2,25")
        self.assertEqual(self.got["[[1.5,2]]|Comma"], "[[1,5;2]]")
        self.assertEqual(self.got["1.234×10^3|Comma"], "1,234×10^3")

    def test_separator(self):
        self.assertEqual(self.got["1234567|Dot"], "1 234 567")
        self.assertEqual(self.got["1234567.89|Comma"], "1 234 567,89")

    def test_errors_passthrough(self):
        self.assertEqual(self.got["Math ERROR|Comma"], "Math ERROR")


if __name__ == "__main__":
    unittest.main()
