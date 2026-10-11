"""Declarative Issue 7 coverage guards for the real calculator key matrix.

The live browser audit drives the rendered ``button[data-key]`` elements.  This
test keeps the discovered surface from silently shrinking and checks that the
same DOM metadata is present for every supported modifier.  Behavioural
regressions remain in the focused state-machine and setup tests.
"""
import re
import unittest
from pathlib import Path


FRONTEND = (Path(__file__).resolve().parent / "frontend.html").read_text(
    encoding="utf-8"
)


def physical_keys():
    return re.findall(r'<button\b[^>]*\bdata-key="([^"]+)"[^>]*>', FRONTEND)


def button_attributes():
    tags = re.findall(r"<button\b[^>]*>", FRONTEND)
    return [
        {
            "key": re.search(r'\bdata-key="([^"]+)"', tag).group(1),
            "shift": (re.search(r'\bdata-shift="([^"]+)"', tag) or [None, None])[1],
            "alpha": (re.search(r'\bdata-alpha="([^"]+)"', tag) or [None, None])[1],
        }
        for tag in tags
        if re.search(r'\bdata-key="([^"]+)"', tag)
    ]


class TestFunctionalMatrixCoverage(unittest.TestCase):
    def test_physical_key_and_modifier_surface(self):
        buttons = button_attributes()
        self.assertEqual(len(buttons), 51)
        self.assertEqual(len({button["key"] for button in buttons}), 51)
        self.assertEqual(sum(bool(button["shift"]) for button in buttons), 37)
        self.assertEqual(sum(bool(button["alpha"]) for button in buttons), 20)

        for button in buttons:
            self.assertIn(f'data-key="{button["key"]}"', FRONTEND)
            if button["shift"]:
                self.assertIn(button["shift"], FRONTEND)
            if button["alpha"]:
                self.assertIn(button["alpha"], FRONTEND)

    def test_menu_and_setup_registries_are_exhaustive(self):
        self.assertEqual(len(re.findall(r'data-mode="[^"]+"', FRONTEND)), 12)
        setup = FRONTEND[FRONTEND.index("const SETUP_MENU"):]
        setup = setup[:setup.index("let setupSettings")]
        self.assertEqual(len(re.findall(r'\{ id:', setup)), 14)
        self.assertIn("function handleSetupKey(key)", FRONTEND)

    def test_matrix_routing_is_present(self):
        self.assertIn("document.querySelectorAll('[data-key]')", FRONTEND)
        self.assertIn("function handleKey(btn)", FRONTEND)
        self.assertIn("if (appState.mode === 'Base-N' && (isShift || isAlpha))", FRONTEND)
        self.assertIn("function handleSetupKey(key)", FRONTEND)


if __name__ == "__main__":
    unittest.main()
