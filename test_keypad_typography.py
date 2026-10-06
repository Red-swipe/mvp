"""Regression tests for the keypad typography: the CW01 keycap font removed
from the UI entirely, plain key faces, and plain-text SHIFT/ALPHA legends.

WHY: `CASIOClassWizCW01.ttf` is a bitmap-like keycap ARTWORK face. In it the
ASCII digits are circled keycap icons and the operators are circled/boxed
glyphs, so it cannot render readable text anywhere -- neither on the screen
(which was the original bug) nor on the keys (the follow-up bug). The UI must
therefore not reference it at all.

Covered:
  KEY-1  frontend.html contains ZERO references to CW01 / the ClassWiz face
  KEY-2  no @font-face rule survives
  KEY-3  every key face uses the plain text stack
  KEY-4  no element in the keypad resolves to the keycap font (COMPUTED style)
  KEY-5  no key renders a Private Use Area character (U+E000-U+F8FF)
  KEY-6  digits are plain digits and operators are real Unicode (× ÷ + −)
  KEY-7  SHIFT legends are orange, ALPHA legends are red
  KEY-8  superscript/subscript legends use <sup>/<sub>, not precomposed glyphs
  KEY-9  Cambria Math is only ever a fallback after a real text face

Browser tests skip cleanly when Playwright or Chrome is unavailable; the static
tests always run.
"""
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
FRONTEND = (PROJECT / "frontend.html").read_text(encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:                                     # pragma: no cover
    HAVE_PLAYWRIGHT = False

URL = (PROJECT / "frontend.html").as_uri()

KEYCAP_FACE = "CASIO ClassWiz"
TEXT_FACE = "Segoe UI"

# The genuine ClassWiz DISPLAY face (Wenti-D "ClassWiz CW Display" v3.009,
# SIL OFL 1.1, vendored at ClassWizFontSet/ClassWizCWDisplay-Regular.woff2).
# This is a real text face with 1287 glyphs and uniform tabular digits, unlike
# the CW01 keycap artwork above. It is now used for the SCREEN only.
LCD_DISPLAY_FACE = "CWDisplay"
LCD_DISPLAY_FILE = "ClassWizCWDisplay-Regular.woff2"

KEY_FACE_SELECTORS = [".b", ".bn", ".bop", ".bdel", ".bac", ".bc", ".lbl"]

# The keypad: the round top controls plus every key row.
KEYPAD_SELECTOR = ".top-controls, .row"

# Precomposed super/subscript characters that must become <sup>/<sub>.
PRECOMPOSED = {
    "\u00b2": "2", "\u00b3": "3", "\u207b": "-", "\u2079": "9",
    "\u02e3": "x", "\u1d62": "a",
}


def strip_comments(src):
    out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    out = re.sub(r"(?m)^\s*//.*$", " ", out)
    return out


CSS_NO_COMMENTS = strip_comments(FRONTEND)


def font_rules(css):
    out = []
    for m in re.finditer(r"([^{}@]+)\{([^{}]*)\}", css):
        selectors = m.group(1)
        if selectors.strip().lower().endswith("font-face"):
            continue
        body = m.group(2)
        if "font-family" not in body:
            continue
        fm = re.search(r"font-family\s*:\s*([^;}]+)", body)
        if fm:
            out.append((selectors.strip(), fm.group(1).strip()))
    return out


def selector_names(selectors):
    return {s.strip() for s in selectors.split(",")}


# --------------------------------------------------------------------------
# Source level
# --------------------------------------------------------------------------
class TestKeycapFontRemovedFromSource(unittest.TestCase):
    """KEY-1 / KEY-2 / KEY-3."""

    def test_no_reference_to_the_keycap_font_remains(self):
        self.assertNotIn("CW01", FRONTEND,
                         "frontend.html still references the CW01 keycap font")
        self.assertNotIn(KEYCAP_FACE, FRONTEND,
                         "frontend.html still declares/uses the keycap face")
        self.assertNotIn("Casio ClassWiz TTF", FRONTEND,
                         "a stale comment still claims the LCD uses that TTF")

    def test_only_the_display_face_is_declared(self):
        # The UI is no longer webfont-free: the genuine ClassWiz CW DISPLAY
        # face is declared so the screen can use it. Exactly one @font-face may
        # exist, it must be that face, and it must never be the keycap artwork.
        self.assertEqual(re.findall(r"@font-face", CSS_NO_COMMENTS), ["@font-face"],
                         "expected exactly one @font-face: the CW Display face")
        self.assertRegex(CSS_NO_COMMENTS,
                          rf'@font-face\s*\{{[^}}]*font-family\s*:\s*"{re.escape(LCD_DISPLAY_FACE)}"')
        self.assertIn(LCD_DISPLAY_FILE, CSS_NO_COMMENTS,
                      "the declared @font-face must point at the real asset")
        self.assertNotIn("CASIOClassWizCW01", CSS_NO_COMMENTS,
                         "the keycap artwork must never be a src")
        self.assertNotIn(KEYCAP_FACE, CSS_NO_COMMENTS,
                         "the keycap face must never be declared")

    def test_every_key_face_uses_the_plain_text_stack(self):
        seen = set()
        for selectors, stack in font_rules(CSS_NO_COMMENTS):
            for name in selector_names(selectors):
                if name in KEY_FACE_SELECTORS:
                    seen.add(name)
                    self.assertNotIn(KEYCAP_FACE, stack, f"{name}: {stack}")
                    self.assertIn(TEXT_FACE, stack, f"{name}: {stack}")
                    self.assertIn("Arial", stack, f"{name}: {stack}")
                    self.assertIn("sans-serif", stack, f"{name}: {stack}")
        for name in KEY_FACE_SELECTORS:
            self.assertIn(name, seen, f"{name} declares no font-family at all")

    def test_cambria_math_is_only_ever_a_fallback(self):
        # A math face named BEFORE a real text face would re-type the whole
        # legend instead of covering only the glyphs the text face lacks.
        for selectors, stack in font_rules(CSS_NO_COMMENTS):
            if "Cambria Math" not in stack:
                continue
            names = selector_names(selectors)
            text_named = [f for f in (TEXT_FACE, "Arial", "Helvetica")
                          if f in stack]
            self.assertTrue(text_named,
                            f"{selectors} names Cambria Math with no text face "
                            f"to fall back from: {stack}")
            first_math = stack.index("Cambria Math")
            for face in text_named:
                self.assertLess(stack.index(face), first_math,
                                f"{selectors} puts a math face before {face}: "
                                f"{stack}")
            del names


class TestLegendMarkup(unittest.TestCase):
    """KEY-8."""

    def _label_markup(self):
        return "\n".join(re.findall(r'<span class="lbl">.*?</span></span>',
                                    FRONTEND, re.S))

    def test_no_precomposed_super_or_subscript_characters_in_legends(self):
        markup = self._label_markup()
        self.assertTrue(markup, "no .lbl legend markup found")
        for ch in PRECOMPOSED:
            self.assertNotIn(ch, markup,
                             f"{ch!r} (U+{ord(ch):04X}) is a precomposed "
                             f"super/subscript glyph; use <sup>/<sub> so the "
                             f"legend is real text")

    def test_legends_use_sup_and_sub(self):
        markup = self._label_markup()
        self.assertIn("<sup>", markup, "no <sup> legend found")
        self.assertIn("<sub>", markup, "no <sub> legend found")

    def test_every_shift_and_alpha_legend_is_a_span(self):
        markup = self._label_markup()
        for cls in ("shift-mark", "alpha-mark"):
            self.assertIn(f'<span class="{cls}">', markup, cls)


# --------------------------------------------------------------------------
# Browser level
# --------------------------------------------------------------------------
def _chrome_available():
    if not HAVE_PLAYWRIGHT:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            b.close()
        return True
    except Exception:
        return False


CHROME_OK = _chrome_available()


@unittest.skipUnless(CHROME_OK, "Playwright + Chrome are required")
class KeypadBrowserCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 900, "height": 1600})
        cls.page.goto(URL)
        cls.page.wait_for_timeout(2500)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def keypad_fonts(self):
        return self.page.evaluate(
            """(pad) => Array.from(document.querySelectorAll(pad + ', ' + pad + ' *'))
                 .filter(e => (e.textContent || '').trim().length)
                 .map(e => ({ tag: e.tagName, cls: e.className,
                              font: getComputedStyle(e).fontFamily }))""",
            KEYPAD_SELECTOR)

    def keypad_texts(self):
        return self.page.evaluate(
            """() => Array.from(document.querySelectorAll('button.b'))
                 .map(b => ({ cls: b.className, text: b.textContent }))""")


class TestKeypadRendered(KeypadBrowserCase):
    def test_no_keypad_element_resolves_to_the_keycap_font(self):
        rows = self.keypad_fonts()
        self.assertTrue(rows, "no keypad text elements found")
        bad = [r for r in rows if KEYCAP_FACE in r["font"]]
        self.assertEqual(bad, [],
                         "these keypad elements still compute the keycap "
                         f"face: {bad[:5]}")

    def test_no_key_uses_a_private_use_character(self):
        rows = self.keypad_texts()
        self.assertTrue(rows, "no keys found")
        bad = []
        for row in rows:
            for ch in row["text"]:
                if 0xE000 <= ord(ch) <= 0xF8FF:
                    bad.append((row["cls"], row["text"], f"U+{ord(ch):04X}"))
        self.assertEqual(bad, [],
                         "these keys render Private Use Area characters, which "
                         f"only a symbol font can draw: {bad}")

    def test_digits_are_plain_digits(self):
        digits = [r["text"] for r in self.keypad_texts() if "bn" in r["cls"]]
        self.assertTrue(digits, "no numeric keys found")
        for want in "0123456789":
            self.assertIn(want, digits,
                          f"no plain {want!r} key found; got {sorted(digits)}")
        for text in digits:
            self.assertTrue(re.fullmatch(r"[0-9.]", text),
                            f"a numeric key renders more than one character: {text!r}")

    def test_operators_use_real_unicode_characters(self):
        found = {r["text"] for r in self.keypad_texts() if "bop" in r["cls"]}
        self.assertTrue(found, "no operator keys found")
        for want in ("×", "÷", "+", "−"):
            self.assertIn(want, found,
                          f"operator {want!r} missing from the keys; got {sorted(found)}")
        for text in found:
            # `Ans` is an answer-recall key that reuses the .bop styling.
            self.assertIn(text, ("×", "÷", "+", "−", "=", "×10x", "Ans"),
                          f"unexpected operator key text: {text!r}")

    def test_every_alpha_legend_including_the_base_marks_is_red(self):
        # DEC / HEX / BIN / OCT are ALPHA labels (they carry data-alpha), so
        # they must be red like every other ALPHA legend -- not a third colour.
        colours = self.page.evaluate(
            """() => {
                 const pick = (sel) => {
                   const el = document.querySelector(sel);
                   return el ? getComputedStyle(el).color : null;
                 };
                 return { alpha: pick('.lbl .alpha-mark'),
                          base: pick('.lbl .base-mark'),
                          shift: pick('.lbl .shift-mark') };
               }""")
        self.assertIsNotNone(colours["alpha"], "no .lbl .alpha-mark legend found")
        self.assertIsNotNone(colours["base"], "no .lbl .base-mark legend found")
        self.assertIsNotNone(colours["shift"], "no .lbl .shift-mark legend found")
        self.assertEqual(colours["base"], colours["alpha"],
                         "the DEC/HEX/BIN/OCT legends are ALPHA labels, so they "
                         f"must use the ALPHA colour, not {colours['base']}")
        self.assertNotEqual(colours["shift"], colours["alpha"],
                            "SHIFT and ALPHA legends must be distinguishable")
        self.assertTrue(re.search(r'<span class="base-mark">[^<]*</span>\s*</span>\s*'
                                  r'<button[^>]*data-alpha', FRONTEND),
                        "every base-mark legend must sit above a data-alpha key")

    def test_every_shift_legend_is_orange(self):
        # The ENG legend is a SHIFT label too (data-shift="ENG_LEFT"); it used a
        # purple/yellow pair, which broke the orange-SHIFT / red-ALPHA code.
        colours = self.page.evaluate(
            """() => Array.from(document.querySelectorAll('.lbl .eng-arrows *'))
                 .map(e => getComputedStyle(e).color)""")
        self.assertTrue(colours, "no .eng-arrows legend found")
        shift_colour = self.page.evaluate(
            "() => getComputedStyle(document.querySelector('.lbl .shift-mark')).color")
        for colour in colours:
            self.assertEqual(colour, shift_colour,
                             f"the ENG shift legend is {colour}, not the SHIFT "
                             f"colour {shift_colour}")

    def test_shift_legends_are_orange_and_alpha_legends_are_red(self):
        colors = self.page.evaluate(
            """() => {
                 const s = document.querySelector('.lbl .shift-mark');
                 const a = document.querySelector('.lbl .alpha-mark');
                 return { shift: s ? getComputedStyle(s).color : null,
                          alpha: a ? getComputedStyle(a).color : null };
               }""")
        self.assertIsNotNone(colors["shift"], "no .shift-mark legend found")
        self.assertIsNotNone(colors["alpha"], "no .alpha-mark legend found")

        def rgb(c):
            return [int(x) for x in re.findall(r"\d+", c)[:3]]

        shift, alpha = rgb(colors["shift"]), rgb(colors["alpha"])
        r, g, b = shift
        self.assertGreater(r, 150, f"SHIFT legend is not a warm colour: {colors['shift']}")
        self.assertGreater(r, g + 40,
                           f"SHIFT legend is not orange (r must dominate g): "
                           f"{colors['shift']}")
        self.assertGreater(r, b + 40,
                           f"SHIFT legend is not orange (r must dominate b): "
                           f"{colors['shift']}")
        r, g, b = alpha
        self.assertGreater(r, 150, f"ALPHA legend is not a strong red: {colors['alpha']}")
        self.assertGreater(r, g + 60,
                           f"ALPHA legend is not red (r must dominate g): "
                           f"{colors['alpha']}")
        self.assertGreater(r, b + 60,
                           f"ALPHA legend is not red (r must dominate b): "
                           f"{colors['alpha']}")

    def test_legends_render_their_sup_and_sub_parts(self):
        # A <sup>/<sub> legend must actually be laid out as a raised/lowered
        # part, not as one flat run of characters.
        info = self.page.evaluate(
            """() => {
                 const sup = document.querySelector('.lbl sup');
                 const sub = document.querySelector('.lbl sub');
                 const host = sup ? sup.parentElement : null;
                 return {
                   supTag: sup ? sup.tagName : null,
                   subTag: sub ? sub.tagName : null,
                   supSize: sup ? parseFloat(getComputedStyle(sup).fontSize) : null,
                   hostSize: host ? parseFloat(getComputedStyle(host).fontSize) : null,
                   supText: sup ? sup.textContent : null,
                   subText: sub ? sub.textContent : null,
                 };
               }""")
        self.assertEqual(info["supTag"], "SUP", info)
        self.assertEqual(info["subTag"], "SUB", info)
        self.assertLess(info["supSize"], info["hostSize"],
                        "a <sup> legend must be smaller than its host")
        self.assertTrue(info["supText"], "the <sup> legend is empty")


if __name__ == "__main__":
    unittest.main()