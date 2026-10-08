"""Item 8 regression coverage: key labels must match the real SHIFT/ALPHA
mappings defined in raw/buttons.md, and the keys must actually perform them.

raw/buttons.md is authoritative:
    * *10^x        -> shift: pi,  alpha: e
    - ANS          -> shift: %

Defect this locks down: the printed legend above a key (.lbl .shift-mark /
.lbl .alpha-mark) disagreed with the button's data-shift/data-alpha attributes.
The ALPHA `e` overlay was printed on the ANS key (which has no ALPHA mapping) and
the SHIFT `%` overlay was missing entirely, while the *10^x key carried no ALPHA
overlay at all.

Static layer: every printed overlay matches its data-* attribute.
Browser layer: the real rendered legend AND the real insertion behaviour, driven
through handleKey. Loads frontend.html over file:// -- no server.
"""
import pathlib
import re
import unittest

FRONTEND_PATH = pathlib.Path(__file__).resolve().parent / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright

    _pw = sync_playwright().start()
    _b = _pw.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _b.close()
    _pw.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False


def _key_blocks():
    """[(key, data_shift, data_alpha, printed_shift, printed_alpha, label)]."""
    out = []
    for block in re.findall(r'<div class="bw">(.*?)</div>', FRONTEND, re.S):
        mk = re.search(r'data-key="([^"]+)"', block)
        if not mk:
            continue
        grab = lambda pat: (re.search(pat, block, re.S).group(1).strip()
                            if re.search(pat, block, re.S) else None)
        ml = re.search(r'<button[^>]*>(.*?)</button>', block, re.S)
        out.append((
            mk.group(1),
            grab(r'data-shift="([^"]+)"'),
            grab(r'data-alpha="([^"]+)"'),
            grab(r'<span class="shift-mark">(.*?)</span>'),
            grab(r'<span class="alpha-mark">(.*?)</span>'),
            re.sub(r"<[^>]+>", "", ml.group(1)).strip() if ml else "",
        ))
    return out


BLOCKS = {b[0]: b for b in _key_blocks()}


class TestKeyLegendConsistency(unittest.TestCase):
    def test_scientific_key_matches_buttons_md(self):
        key, ds, da, ps, pa, label = BLOCKS["scientific"]
        self.assertEqual(ds, "pi")          # raw/buttons.md: shift + *10^x -> pi
        self.assertEqual(da, "e")           # raw/buttons.md: alpha + *10^x -> e
        self.assertEqual(ps, "\u03c0")      # SHIFT overlay is actually printed
        self.assertEqual(pa, "e")           # ALPHA overlay is actually printed
        self.assertIn("\u00d710", label)    # the real multiplication sign

    def test_ans_key_matches_buttons_md(self):
        key, ds, da, ps, pa, label = BLOCKS["ans"]
        self.assertEqual(ds, "percent")     # raw/buttons.md: shift + ANS -> %
        self.assertIsNone(da)               # ANS has no ALPHA mapping at all
        self.assertEqual(ps, "%")           # SHIFT overlay is actually printed
        self.assertIsNone(pa)               # no stray ALPHA overlay on this key
        self.assertTrue(label.startswith("Ans"))

    def test_the_alpha_e_overlay_belongs_only_to_the_scientific_key(self):
        owners = [key for key, _, _, _, pa, _ in _key_blocks() if pa == "e"]
        self.assertEqual(owners, ["scientific"])

    def test_item8_keys_print_exactly_the_overlays_they_own(self):
        # Scoped to the two keys Item 8 covers. Several OTHER keys still have
        # printed-overlay/attribute mismatches (fraction, square, power, log,
        # ln, eng, right_paren); most are BASE-N mode overlays, and they are
        # deliberately left untouched by this item.
        for name in ("scientific", "ans"):
            with self.subTest(key=name):
                key, ds, da, ps, pa, _ = BLOCKS[name]
                self.assertEqual(ds is not None, ps is not None)
                self.assertEqual(da is not None, pa is not None)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestKeyBehaviour(unittest.TestCase):
    URL = FRONTEND_PATH.as_uri()

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 1000, "height": 1300})
        cls.page.set_default_timeout(10000)
        cls.page.goto(cls.URL, wait_until="domcontentloaded")
        cls.page.wait_for_timeout(2500)
        cls.page.evaluate("() => { appState.poweredOn = true; appState.splash = false; renderLCD(); }")
        cls.page.wait_for_timeout(300)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def _clear(self):
        self.page.evaluate(
            "() => { resetExpr(); appState.shift = false; appState.alpha = false; renderLCD(); }")
        self.page.wait_for_timeout(150)

    def _press(self, key, shift=False, alpha=False, mode="Calculate"):
        return self.page.evaluate(
            """(o) => {
                 appState.mode = o.mode;
                 appState.shift = o.shift; appState.alpha = o.alpha;
                 handleKey({ dataset: { key: o.key }, classList: { toggle: () => {} },
                             hasAttribute: () => false, getAttribute: () => null });
                 renderLCD();
                 return { expr: getExpr(), shift: appState.shift, alpha: appState.alpha };
               }""",
            {"key": key, "shift": shift, "alpha": alpha, "mode": mode})

    def test_rendered_legends(self):
        lg = self.page.evaluate(
            """() => { const out = {};
                 document.querySelectorAll('[data-key]').forEach(b => {
                   const w = b.closest('.bw'); if (!w) return;
                   const s = w.querySelector('.shift-mark'), a = w.querySelector('.alpha-mark');
                   out[b.dataset.key] = { sm: s ? s.textContent.trim() : null,
                                          am: a ? a.textContent.trim() : null,
                                          ds: b.dataset.shift || null,
                                          da: b.dataset.alpha || null }; });
                 return out; }""")
        self.assertEqual(lg["scientific"]["sm"], "\u03c0")
        self.assertEqual(lg["scientific"]["am"], "e")
        self.assertEqual(lg["ans"]["sm"], "%")
        self.assertIsNone(lg["ans"]["am"])
        self.assertIsNone(lg["ans"]["da"])

    def test_scientific_key_mappings(self):
        self._clear()
        r = self._press("scientific")
        # getExpr() serialises the display token x10^ with an ASCII `*`.
        self.assertTrue("\u00d710^" in r["expr"] or "*10^" in r["expr"], r["expr"])
        self._clear()
        r = self._press("scientific", shift=True)
        self.assertIn("pi", r["expr"].lower(), r["expr"])
        self._clear()
        r = self._press("scientific", alpha=True)
        self.assertIn("e", r["expr"], r["expr"])

    def test_ans_key_mappings(self):
        self._clear()
        self.assertIn("Ans", self._press("ans")["expr"])
        self._clear()
        self.assertIn("%", self._press("ans", shift=True)["expr"])

    def test_shift_is_one_shot_after_use(self):
        self._clear()
        r = self._press("scientific", shift=True)
        self.assertFalse(r["shift"], "SHIFT should clear once its key has fired")
        self._clear()
        self.assertIn("Ans", self._press("ans")["expr"])  # no leak into the next key

    def test_base_n_keeps_the_item2_inert_behaviour(self):
        for shift, alpha, name in ((False, False, "normal"), (True, False, "SHIFT"),
                                   (False, True, "ALPHA")):
            with self.subTest(modifier=name):
                self._clear()
                r = self._press("scientific", shift=shift, alpha=alpha, mode="Base-N")
                self.assertEqual(r["expr"].strip(), "",
                                 "scientific key must stay inert in BASE-N")

    def test_other_overlays_untouched(self):
        lg = self.page.evaluate(
            """() => { const out = {};
                 document.querySelectorAll('[data-key]').forEach(b => {
                   const w = b.closest('.bw'); if (!w) return;
                   const s = w.querySelector('.shift-mark');
                   out[b.dataset.key] = s ? s.textContent.trim() : null; });
                 return out; }""")
        self.assertTrue(lg["log"].startswith("10"), lg["log"])
        self.assertTrue(lg["ln"].startswith("e"), lg["ln"])
        self.assertEqual(lg["equals"], "\u2248")


if __name__ == "__main__":
    unittest.main()