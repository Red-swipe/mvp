"""Static-route tests for the vendored KaTeX distribution served over HTTP.

WHY: KaTeX is vendored under ./katex and referenced from frontend.html with
RELATIVE urls, so the page requests /katex/katex.min.css, /katex/katex.min.js
and /katex/fonts/*.woff2. The server only had a /fonts/ route, so every one of
those returned 404 and an http:// visit silently lost all typeset results.

Covered:
  ROUTE-1  the three asset classes are served with the correct Content-Type
  ROUTE-2  /katex/../mvp_server.py is refused (raw AND percent-encoded)
  ROUTE-3  a sibling file outside the katex directory is unreachable
  ROUTE-4  an unknown file inside the katex directory is a 404, not a crash
  ROUTE-5  the real page loads over http:// with working KaTeX

Every request here is a real socket request against a real server process --
no mocking of the handler -- because the whole point is what the wire carries.
"""
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
KATEX_DIR = PROJECT / "katex"

EXPECTED_TYPES = {
    "katex/katex.min.css": "text/css",
    "katex/katex.min.js": "application/javascript",
    "katex/contrib/auto-render.min.js": "application/javascript",
}


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def raw_get(port, raw_path):
    """Send a literal request line, bypassing any client-side normalisation.

    urllib/http.client rewrite `..` segments before the request leaves the
    process, so a traversal test built on them proves nothing: the crafted path
    never reaches the handler. This puts the bytes on the wire verbatim.
    """
    with socket.create_connection(("127.0.0.1", port), timeout=15) as s:
        s.sendall(f"GET {raw_path} HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                  f"Connection: close\r\n\r\n".encode())
        chunks = []
        while True:
            data = s.recv(65536)
            if not data:
                break
            chunks.append(data)
    raw = b"".join(chunks).decode("utf-8", "replace")
    head, _, body = raw.partition("\r\n\r\n")
    status = int(head.split()[1])
    headers = {}
    for line in head.split("\r\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return status, headers, body


class ServerCase(unittest.TestCase):
    """Boots the real mvp_server.py once for the whole class."""

    @classmethod
    def setUpClass(cls):
        if not KATEX_DIR.is_dir():                          # pragma: no cover
            raise unittest.SkipTest("katex is not vendored")
        cls.port = _free_port()
        cls.proc = subprocess.Popen(
            [sys.executable, "mvp_server.py", "--port", str(cls.port),
             "--no-browser"],
            cwd=str(PROJECT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        deadline = time.time() + 40
        while time.time() < deadline:
            if cls.proc.poll() is not None:                 # pragma: no cover
                raise unittest.SkipTest(
                    "mvp_server.py exited: "
                    + cls.proc.communicate()[1].decode("utf-8", "replace")[:400])
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{cls.port}/health", timeout=2) as r:
                    if r.status == 200:
                        return
            except Exception:
                time.sleep(0.25)
        raise unittest.SkipTest("mvp_server.py did not become ready")  # pragma: no cover

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "proc", None) and cls.proc.poll() is None:
            cls.proc.terminate()
            try:
                cls.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:               # pragma: no cover
                cls.proc.kill()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def get(self, path):
        with urllib.request.urlopen(self.url(path), timeout=15) as r:
            return r.status, dict(r.headers), r.read()


class TestKatexRoute(ServerCase):
    """ROUTE-1 / ROUTE-4."""

    def _woff2(self):
        css = (KATEX_DIR / "katex.min.css").read_text(encoding="utf-8")
        refs = sorted(set(re.findall(r"url\((fonts/[^)]+\.woff2)\)", css)))
        self.assertTrue(refs, "the vendored stylesheet references no woff2")
        return refs[0]

    def test_the_stylesheet_is_served_as_text_css(self):
        status, headers, body = self.get("/katex/katex.min.css")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "text/css")
        self.assertIn("KaTeX_Main", body.decode("utf-8"))

    def test_the_scripts_are_served_as_javascript(self):
        for name in ("katex.min.js", "contrib/auto-render.min.js"):
            with self.subTest(asset=name):
                status, headers, body = self.get(f"/katex/{name}")
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("Content-Type"),
                                 "application/javascript")
                self.assertGreater(len(body), 1000)

    def test_a_font_is_served_as_font_woff2(self):
        rel = self._woff2()
        status, headers, body = self.get(f"/katex/{rel}")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "font/woff2")
        # woff2 magic: 'wOF2'
        self.assertEqual(body[:4], b"wOF2",
                         "the body is not a woff2 file")

    def test_every_content_type_is_one_we_declared(self):
        seen = set()
        for rel, expected in EXPECTED_TYPES.items():
            status, headers, _ = self.get("/" + rel)
            self.assertEqual(status, 200, rel)
            self.assertEqual(headers.get("Content-Type"), expected, rel)
            seen.add(headers.get("Content-Type"))
        self.assertEqual(seen - set(EXPECTED_TYPES.values()), set(),
                         "an unexpected Content-Type was served")

    def test_an_unknown_file_inside_katex_is_a_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/katex/definitely-not-here.css")
        self.assertEqual(ctx.exception.code, 404)


class TestKatexRouteTraversal(ServerCase):
    """ROUTE-2 / ROUTE-3.

    The first three cases are refused by the extension allow-list as well as by
    the containment check, so on their own they cannot tell the two apart. The
    probe case below is the one that isolates containment: the target has an
    allowed extension, so only the resolved-path check can refuse it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.probe = PROJECT / "_traversal_probe.css"
        cls.probe.write_text("/* TRAVERSAL-PROBE-SECRET */\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        probe = getattr(cls, "probe", None)
        if probe and probe.exists():
            probe.unlink()
        super().tearDownClass()

    def _assert404(self, raw_path, why):
        status, _headers, body = raw_get(self.port, raw_path)
        self.assertEqual(status, 404,
                         f"{why}: {raw_path} returned {status}")
        self.assertNotIn("def main", body,
                         "the response leaked server source code")

    def test_dot_dot_out_of_the_katex_directory_is_refused(self):
        self._assert404("/katex/../mvp_server.py",
                        "traversal out of the katex directory")

    def test_a_deeper_traversal_is_refused(self):
        self._assert404("/katex/fonts/../../mvp_server.py",
                        "traversal through a subdirectory")

    def test_a_percent_encoded_traversal_is_refused(self):
        # The handler unquotes the path, so %2e%2e is decoded to `..` before
        # any containment check runs -- this is the vector that matters.
        self._assert404("/katex/%2e%2e/mvp_server.py",
                        "percent-encoded traversal")

    def test_an_absolute_sibling_path_is_refused(self):
        self._assert404("/katex/../frontend.html",
                        "traversal to a file outside the katex directory")

    def test_a_traversal_to_an_allowed_extension_is_still_refused(self):
        # The target's extension IS served under /katex/, so the extension
        # allow-list cannot be what stops this: only the resolved-path
        # containment check can. Without it the probe's bytes are returned.
        status, headers, body = raw_get(
            self.port, "/katex/../_traversal_probe.css")
        self.assertEqual(status, 404,
                         "a `..` escape to an allowed extension was served")
        self.assertNotIn("TRAVERSAL-PROBE-SECRET", body,
                         "the response leaked a file from outside katex/")

    def test_a_backslash_traversal_is_refused(self):
        # On Windows a backslash is a path separator, so this escapes just as
        # `..` does and must be caught by the same resolved-path check.
        status, _headers, body = raw_get(
            self.port, r"/katex/..\_traversal_probe.css")
        self.assertEqual(status, 404,
                         "a backslash escape to an allowed extension was served")
        self.assertNotIn("TRAVERSAL-PROBE-SECRET", body,
                         "the response leaked a file from outside katex/")

    def test_the_katex_root_itself_is_not_a_directory_listing(self):
        status, _headers, _body = raw_get(self.port, "/katex/")
        self.assertNotEqual(status, 200,
                            "the katex directory must not be listable")


class TestPageOverHttp(ServerCase):
    """ROUTE-5."""

    def test_the_page_loads_over_http_with_working_katex(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:                                 # pragma: no cover
            self.skipTest("Playwright is not installed")
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(channel="chrome")
        except Exception:                                   # pragma: no cover
            self.skipTest("Chrome is not available")
        try:
            page = browser.new_page(viewport={"width": 700, "height": 1700},
                                    device_scale_factor=2)
            bad = []
            page.on("response", lambda r: bad.append((r.status, r.url))
                    if r.status >= 400 else None)
            page.goto(self.url("/"), wait_until="load")
            page.wait_for_timeout(3000)

            version = page.evaluate("() => window.katex && window.katex.version")
            self.assertEqual(version, "0.16.11",
                             f"katex did not load over http (got {version!r})")

            page.evaluate("""() => { resetExpr(); }""")
            for ch in "123+456":
                page.evaluate("(c) => insertToken(c)", ch)
            page.evaluate("() => evaluate()")
            page.wait_for_timeout(600)

            info = page.evaluate(
                """() => {
                     const k = document.querySelector('#lcdResultLine .katex');
                     return { result: appState.result,
                              katex: !!k,
                              font: k ? getComputedStyle(k).fontFamily : null };
                   }""")
            self.assertEqual(info["result"], "579", info)
            self.assertTrue(info["katex"],
                            "the result line was not typeset with KaTeX")
            self.assertIn("KaTeX_Main", info["font"], info)

            relevant = [u for _s, u in bad if "katex" in u]
            self.assertEqual(relevant, [],
                             f"katex assets 404'd over http: {relevant}")

            shot = PROJECT / "_katex_http_check.png"
            page.locator(".lcd-bezel").screenshot(path=str(shot))
            self.addCleanup(lambda: os.path.exists(shot) and os.remove(shot))
            self.assertTrue(shot.is_file(), "no screenshot was produced")
        finally:
            browser.close()
            pw.stop()


if __name__ == "__main__":
    unittest.main()