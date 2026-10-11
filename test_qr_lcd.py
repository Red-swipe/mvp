"""Item 12 regression coverage: the QR code fits, is scaled correctly and decodes.

Defects this locks down, all measured on the real rendered DOM before the fix:

  QR-SIZE  the symbol was requested at a fixed 72x72. qrcodejs' canvas drawer
           divides by the module count, so modules landed on non-integer pixel
           boundaries (29 modules in 72px = 2.4828px each) and the symbol was
           anti-aliased rather than crisp.
  QR-QUIET the same drawer painted the matrix edge to edge with NO quiet zone.
           Measured ink bounding box was the full 72x72, i.e. a zero-module
           margin on all four sides. Re-encoding the identical payload that way
           does NOT decode at all (see test_old_style_rendering_does_not_decode).
  QR-CROP  the overlay only had 75px of content height while title + symbol +
           caption needed 101px, so `.lcd{overflow:hidden}` cropped the panel
           and the caption was never visible.
  QR-RECUR syncQrOverlay() re-entered showQRinLCD() while the host was still
           empty, recursing renderLCD() -> syncQrOverlay() -> showQRinLCD().
           Measured 1106 nested calls, with the resulting RangeError silently
           swallowed by syncQrOverlay's catch.
  QR-OFFLINE the library came from the cdnjs CDN, the calculator's only
           remaining network dependency, so the QR screen could not render at
           all in the offline portable build.

Static layer: the local script tag, the quiet-zone constant and the renderer
wiring. Browser layer: the real rendered DOM, driven through the real SHIFT+OPTN
key path over file://. Decoder layer: the actual screenshot pixels are decoded
with OpenCV and compared against the encoded payload.

Every test skips cleanly when Playwright/Chrome or OpenCV is unavailable; the
static tests always run.
"""
import pathlib
import re
import unittest

PROJECT = pathlib.Path(__file__).resolve().parent
FRONTEND_PATH = PROJECT / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")

PAYLOAD = "https://mentisai-delta.vercel.app/"

try:
    from playwright.sync_api import sync_playwright

    _pw = sync_playwright().start()
    _b = _pw.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _b.close()
    _pw.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False

try:
    import cv2
    import numpy  # noqa: F401  (cv2 pulls it in; imported for clarity)
    HAVE_DECODER = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_DECODER = False


# --------------------------------------------------------------------------
# Static / structural guarantees (always run)
# --------------------------------------------------------------------------
def strip_comments(src):
    out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    out = re.sub(r"(?m)^\s*//.*$", " ", out)
    return out


FRONTEND_NO_COMMENTS = strip_comments(FRONTEND)


class TestOfflineDependency(unittest.TestCase):
    """QR-OFFLINE: nothing may be fetched at runtime."""

    def test_no_remote_qr_library_reference_remains(self):
        self.assertNotIn("cdnjs.cloudflare.com/ajax/libs/qrcodejs", FRONTEND)
        self.assertNotIn("qrcode.min.js", FRONTEND)

    def test_qr_library_is_loaded_from_a_local_relative_path(self):
        tags = re.findall(r'<script[^>]*\bsrc=["\']([^"\']+)["\']', FRONTEND)
        self.assertIn("./qrcode/qrcode.js", tags,
                      "the QR library must be loaded locally, offline")

    def test_the_vendored_library_is_actually_present(self):
        lib = PROJECT / "qrcode" / "qrcode.js"
        self.assertTrue(lib.exists(), "qrcode/qrcode.js is missing")
        text = lib.read_text(encoding="utf-8", errors="replace")
        self.assertIn("Kazuhiko Arase", text, "upstream copyright header lost")
        self.assertIn("MIT license", text, "upstream licence header lost")
        self.assertIn("getModuleCount", text,
                      "the matrix access the renderer depends on is missing")

    def test_licence_and_attribution_are_preserved(self):
        notices = PROJECT / "qrcode" / "THIRD-PARTY-NOTICES.txt"
        self.assertTrue(notices.exists(),
                        "qrcode/THIRD-PARTY-NOTICES.txt is missing")
        text = notices.read_text(encoding="utf-8")
        self.assertIn("Kazuhiko Arase", text)
        self.assertIn("MIT", text)
        self.assertIn("qrcode-generator", text,
                      "the vendored package must be identified")

    def test_no_external_host_is_referenced_anywhere_in_the_document(self):
        remote = re.findall(r'(?:src|href)\s*=\s*["\']https?://[^"\']+["\']',
                            FRONTEND)
        self.assertEqual(remote, [], f"remote runtime resources: {remote}")


class TestRendererWiring(unittest.TestCase):
    """QR-SIZE / QR-QUIET / QR-RECUR at the source level."""

    def test_quiet_zone_is_four_modules(self):
        self.assertIn("const QR_QUIET_MODULES = 4;", FRONTEND)

    def test_scale_is_computed_from_the_measured_box(self):
        fn = FRONTEND[FRONTEND.index("function qrModuleScale("):]
        fn = fn[: fn.index("function renderQrCode(")]
        self.assertIn("Math.floor", fn, "the module scale must be integral")
        self.assertIn("moduleCount + QR_QUIET_MODULES * 2", fn,
                      "the scale must account for the quiet zone on both sides")

    def test_scale_never_goes_below_one(self):
        # A viewport too small for a readable symbol must NOT be answered by
        # cropping the quiet zone.
        fn = FRONTEND[FRONTEND.index("function qrModuleScale("):]
        fn = fn[: fn.index("function renderQrCode(")]
        self.assertIn("Math.max(1,", fn)

    def test_quiet_zone_is_white_pixels_inside_the_canvas(self):
        fn = FRONTEND[FRONTEND.index("function renderQrCode("):]
        fn = fn[: fn.index("function showQRinLCD(")]
        self.assertIn("ctx.fillStyle = '#ffffff'", fn)
        self.assertIn("ctx.fillRect(0, 0, size, size)", fn)
        # every module is painted at the integer scale, offset by the quiet zone
        self.assertIn("(col + QR_QUIET_MODULES) * scale", fn)
        self.assertIn("(row + QR_QUIET_MODULES) * scale", fn)

    def test_overlay_does_not_recurse_back_into_showqr(self):
        seg = FRONTEND_NO_COMMENTS
        seg = seg[seg.index("function syncQrOverlay("):]
        seg = seg[: seg.index("async function backendKey(")]
        self.assertNotIn("showQRinLCD()", seg,
                         "syncQrOverlay must not call showQRinLCD back")

    def test_qr_overlay_is_a_flex_column_so_the_box_can_be_measured(self):
        css = FRONTEND_NO_COMMENTS
        rule = re.search(r"#qr-panel\{([^}]*)\}", css)
        self.assertIsNotNone(rule, "#qr-panel rule not found")
        self.assertIn("flex-direction:column", rule.group(1))
        self.assertIn("display:flex", rule.group(1))

    def test_overlay_is_shown_as_flex_not_block(self):
        # An inline display:block overrode the stylesheet, collapsing the QR box
        # to zero height and forcing a 1px module scale.
        seg = FRONTEND[FRONTEND.index("function syncQrOverlay("):]
        seg = seg[: seg.index("async function backendKey(")]
        self.assertIn("qr.style.display = 'flex'", seg)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class QrBrowserCase(unittest.TestCase):
    URL = FRONTEND_PATH.as_uri()

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        self.page = self._browser.new_page(viewport={"width": 1100, "height": 1400})
        self.page.set_default_timeout(15000)
        self.page.goto(self.URL, wait_until="domcontentloaded")
        self.page.wait_for_timeout(2500)

    def tearDown(self):
        self.page.close()

    def open_qr_screen(self):
        """The real key path: SHIFT + OPTN."""
        self.page.evaluate(
            """() => { const b=document.querySelector('[data-key="optn"]');
                 appState.shift = true; appState.alpha = false;
                 handleKey(b); appState.shift = false; renderLCD(); }""")
        self.page.wait_for_timeout(400)

    def measure(self):
        return self.page.evaluate(
            """() => {
              const box = (el) => el ? (({x,y,width,height,right,bottom}) =>
                    ({x:+x.toFixed(2), y:+y.toFixed(2), w:+width.toFixed(2),
                      h:+height.toFixed(2), right:+right.toFixed(2),
                      bottom:+bottom.toFixed(2)}))(el.getBoundingClientRect()) : null;
              const lcd = document.querySelector('.lcd');
              const panel = document.getElementById('qr-panel');
              const host = document.getElementById('lcdQrBox');
              const canvas = host ? host.querySelector('canvas') : null;
              const cs = panel ? getComputedStyle(panel) : null;
              const out = {
                lcd: box(lcd), panel: box(panel), host: box(host),
                canvas: canvas ? {px: canvas.width, styleW: canvas.style.width,
                                  styleH: canvas.style.height} : null,
                panelClippedV: panel ? panel.scrollHeight > panel.clientHeight + 0.5 : null,
                panelClippedH: panel ? panel.scrollWidth > panel.clientWidth + 0.5 : null,
                qrOpen: appState.qrOpen,
              };
              if (canvas) {
                const ctx = canvas.getContext('2d');
                const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
                const dark = (x, y) => d[(y * canvas.width + x) * 4] < 128;
                let minX = canvas.width, minY = canvas.height, maxX = -1, maxY = -1;
                for (let y = 0; y < canvas.height; y++)
                  for (let x = 0; x < canvas.width; x++)
                    if (dark(x, y)) { if (x<minX) minX=x; if (x>maxX) maxX=x;
                                       if (y<minY) minY=y; if (y>maxY) maxY=y; }
                out.ink = maxX < 0 ? null
                    : {x: minX, y: minY, w: maxX-minX+1, h: maxY-minY+1};
                out.quiet = maxX < 0 ? null
                    : {left: minX, top: minY,
                       right: canvas.width-1-maxX, bottom: canvas.height-1-maxY};
                // a finder pattern is 7 modules wide; the run gives the module size
                let run = 0;
                for (let x = minX; x <= maxX && dark(x, minY); x++) run++;
                out.finderRun = run;
                out.moduleFromFinder = run / 7;
              }
              return out;
            }""")


class TestQrFitsTheLcd(QrBrowserCase):
    """QR-SIZE / QR-CROP on the real screen."""

    def test_the_qr_screen_renders_a_canvas(self):
        self.open_qr_screen()
        m = self.measure()
        self.assertTrue(m["qrOpen"])
        self.assertIsNotNone(m["canvas"], "no canvas was rendered")

    def test_the_qr_fits_inside_the_lcd_viewport(self):
        self.open_qr_screen()
        m = self.measure()
        c = m["canvas"]
        size = float(c["styleW"].replace("px", ""))
        self.assertGreaterEqual(m["lcd"]["w"], size,
                                "the QR is wider than the LCD")
        self.assertGreaterEqual(m["lcd"]["h"], size,
                                "the QR is taller than the LCD")
        # and it sits inside the LCD border box on every side
        self.assertGreaterEqual(m["host"]["x"], m["lcd"]["x"] - 0.5)
        self.assertGreaterEqual(m["host"]["y"], m["lcd"]["y"] - 0.5)
        self.assertLessEqual(m["host"]["bottom"], m["lcd"]["bottom"] + 0.5)

    def test_the_canvas_is_square_and_matches_its_css_size(self):
        self.open_qr_screen()
        m = self.measure()
        c = m["canvas"]
        self.assertEqual(c["px"], c["px"])
        self.assertEqual(float(c["styleW"].replace("px", "")),
                         float(c["styleH"].replace("px", "")))
        self.assertEqual(c["px"], int(float(c["styleW"].replace("px", ""))))

    def test_the_overlay_is_not_clipped(self):
        self.open_qr_screen()
        m = self.measure()
        self.assertFalse(m["panelClippedV"],
                         "the QR overlay overflows the LCD vertically and is cropped")
        self.assertFalse(m["panelClippedH"],
                         "the QR overlay overflows the LCD horizontally")

    def test_the_screen_is_centred(self):
        self.open_qr_screen()
        m = self.measure()
        canvas_left = m["host"]["x"] + (m["host"]["w"] - float(
            m["canvas"]["styleW"].replace("px", ""))) / 2
        lcd_centre = (m["lcd"]["x"] + m["lcd"]["right"]) / 2
        canvas_centre = canvas_left + float(
            m["canvas"]["styleW"].replace("px", "")) / 2
        self.assertAlmostEqual(canvas_centre, lcd_centre, delta=1.5,
                               msg="the QR is not horizontally centred")


class TestQrQuietZoneAndScale(QrBrowserCase):
    """QR-QUIET / integer module scaling."""

    def test_quiet_zone_is_at_least_four_modules_on_every_side(self):
        self.open_qr_screen()
        m = self.measure()
        scale = m["moduleFromFinder"]
        self.assertGreaterEqual(scale, 1)
        for side in ("left", "top", "right", "bottom"):
            with self.subTest(side=side):
                self.assertGreaterEqual(m["quiet"][side] / scale, 4.0,
                                        f"quiet zone too small on the {side}")

    def test_module_scaling_is_integer(self):
        self.open_qr_screen()
        m = self.measure()
        scale = m["moduleFromFinder"]
        self.assertEqual(scale, round(scale),
                         f"module size {scale} is fractional")

    def test_matrix_dimensions_and_module_count_are_consistent(self):
        self.open_qr_screen()
        m = self.measure()
        scale = m["moduleFromFinder"]
        n = m["ink"]["w"] / scale
        self.assertEqual(n, round(n), "the matrix width is not a whole module count")
        self.assertEqual(m["ink"]["w"], m["ink"]["h"],
                         "the symbol is not square")
        # size == (N + 2*quiet) * scale
        quiet = 4
        self.assertEqual(m["canvas"]["px"], (n + 2 * quiet) * scale)
        # and the quiet zone is exactly 4 modules
        self.assertEqual(m["quiet"]["left"], quiet * scale)

    def test_the_symbol_is_not_drawn_edge_to_edge(self):
        # The pre-fix drawing had ink touching all four canvas edges.
        self.open_qr_screen()
        m = self.measure()
        for side, value in (("left", m["quiet"]["left"]), ("top", m["quiet"]["top"]),
                            ("right", m["quiet"]["right"]),
                            ("bottom", m["quiet"]["bottom"])):
            self.assertGreater(value, 0,
                               f"the symbol touches the {side} edge: no quiet zone")


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestQrRecursion(QrBrowserCase):
    """QR-RECUR."""

    def test_opening_the_screen_calls_showqr_only_once(self):
        calls = self.page.evaluate(
            """() => {
              const orig = window.showQRinLCD;
              let n = 0;
              window.showQRinLCD = function (...a) { n++; return orig.apply(this, a); };
              const b = document.querySelector('[data-key="optn"]');
              appState.shift = true; appState.alpha = false;
              handleKey(b); appState.shift = false; renderLCD();
              window.showQRinLCD = orig;
              return n;
            }""")
        self.assertEqual(calls, 1,
                         "showQRinLCD re-entered itself (renderLCD/syncQrOverlay cycle)")

    def test_opening_the_screen_raises_no_errors(self):
        errs = []
        self.page.on("pageerror", lambda e: errs.append(str(e)))
        self.open_qr_screen()
        self.assertEqual(errs, [])


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestQrOffline(QrBrowserCase):
    """QR-OFFLINE, with every http(s) request hard-blocked."""

    def test_the_qr_renders_with_all_network_requests_blocked(self):
        blocked = []
        self.page.route("http://**/*", lambda route, req: (blocked.append(req.url), route.abort()))
        self.page.route("https://**/*", lambda route, req: (blocked.append(req.url), route.abort()))
        self.open_qr_screen()
        m = self.measure()
        self.assertIsNotNone(m["canvas"],
                             "no QR was rendered while offline")
        self.assertEqual(blocked, [],
                         f"the page attempted network requests: {blocked}")

    def test_only_local_scripts_are_present(self):
        srcs = self.page.evaluate(
            "() => Array.from(document.querySelectorAll('script[src]'))"
            ".map(s => s.getAttribute('src'))")
        for src in srcs:
            self.assertFalse(src.startswith("http"),
                             f"remote script still referenced: {src}")


@unittest.skipUnless(HAVE_BROWSER and HAVE_DECODER,
                     "Playwright + Chrome + OpenCV are required")
class TestQrDecoding(QrBrowserCase):
    """The rendered pixels must actually decode."""

    def decode_screenshot(self, locator):
        path = PROJECT / ".codex_test_tmp" / "item12_test_qr.png"
        path.parent.mkdir(exist_ok=True)
        locator.screenshot(path=str(path))
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        self.assertIsNotNone(img, "screenshot could not be read")
        data, pts, _ = cv2.QRCodeDetector().detectAndDecode(img)
        return data, img

    def test_the_rendered_lcd_qr_decodes_to_the_encoded_payload(self):
        self.open_qr_screen()
        # Capture the WHOLE LCD, not just the canvas: the LCD applies a CSS
        # contrast() filter and a background gradient to whatever is inside it,
        # so only the full-screen capture proves the on-screen result decodes.
        data, img = self.decode_screenshot(self.page.locator(".lcd"))
        self.assertEqual(data, PAYLOAD,
                         f"decoded {data!r} from the rendered LCD ({img.shape})")

    def test_the_qr_box_alone_decodes_at_its_actual_size(self):
        self.open_qr_screen()
        data, img = self.decode_screenshot(self.page.locator("#lcdQrBox"))
        self.assertEqual(data, PAYLOAD,
                         f"decoded {data!r} at {img.shape[1]}x{img.shape[0]} px")

    def test_the_qr_decodes_at_device_pixel_ratio_2(self):
        self.page.close()
        self.page = self._browser.new_page(viewport={"width": 1100, "height": 1400},
                                           device_scale_factor=2)
        self.page.goto(self.URL, wait_until="domcontentloaded")
        self.page.wait_for_timeout(2500)
        self.open_qr_screen()
        data, img = self.decode_screenshot(self.page.locator(".lcd"))
        self.assertEqual(data, PAYLOAD,
                         f"decoded {data!r} at devicePixelRatio 2 ({img.shape})")

    def test_the_pre_fix_rendering_does_not_decode(self):
        # Reproduces exactly what qrcodejs did: width/moduleCount fractional
        # module size and no quiet zone. Same payload, same 72px request.
        self.page.evaluate(
            """(text) => {
              const qr = qrcode(3, 'M');
              qr.addData(text); qr.make();
              const n = qr.getModuleCount();
              const nw = 72 / n, nh = 72 / n;
              const c = document.createElement('canvas');
              c.width = 72; c.height = 72; c.id = 'oldq';
              const ctx = c.getContext('2d');
              for (let r = 0; r < n; r++) for (let col = 0; col < n; col++) {
                ctx.fillStyle = qr.isDark(r, col) ? '#000' : '#fff';
                ctx.fillRect(col * nw, r * nh, nw, nh);
              }
              document.body.appendChild(c);
            }""", PAYLOAD)
        data, img = self.decode_screenshot(self.page.locator("#oldq"))
        self.assertNotEqual(data, PAYLOAD,
                            "the old fractional/no-quiet-zone rendering unexpectedly "
                            "decoded; the defect this file guards is gone")


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestQrPayloads(QrBrowserCase):
    """The production renderer across payload lengths."""

    def render_payload(self, text, avail_w, avail_h):
        return self.page.evaluate(
            """([text, w, h]) => {
                 const host = document.createElement('div');
                 host.id = 'probe-qr-host';
                 host.style.cssText = 'position:absolute;left:0;top:0;';
                 document.body.appendChild(host);
                 const m = renderQrCode(host, text, w, h);
                 const c = host.querySelector('canvas');
                 return { metrics: m, px: c ? c.width : null };
               }""", [text, avail_w, avail_h])

    def test_a_short_payload_renders_and_fits(self):
        m = self.render_payload("A", 232, 76)
        self.assertIsNotNone(m["metrics"])
        self.assertGreaterEqual(m["metrics"]["size"], 1)
        self.assertLessEqual(m["px"], 76)
        self.page.evaluate("() => document.getElementById('probe-qr-host').remove()")

    def test_the_normal_payload_renders_at_the_expected_scale(self):
        m = self.render_payload(PAYLOAD, 232, 76)
        self.assertEqual(m["metrics"]["moduleCount"], 29)
        self.assertEqual(m["metrics"]["scale"], 2)
        self.assertEqual(m["metrics"]["size"], (29 + 8) * 2)
        self.assertEqual(m["metrics"]["quietPx"], 8)
        self.page.evaluate("() => document.getElementById('probe-qr-host').remove()")

    def test_a_larger_version_still_honours_the_quiet_zone_and_integer_scale(self):
        # 77 bytes needs a 37-module matrix, which the LCD cannot fit at scale 2.
        # The contract is that it drops to scale 1 and NEVER crops the quiet zone.
        long_text = PAYLOAD + "?ref=qr&model=fx-991EX-classwiz-emulator-v1"
        m = self.render_payload(long_text, 232, 76)
        metrics = m["metrics"]
        self.assertGreater(metrics["moduleCount"], 29, "payload did not grow the matrix")
        self.assertEqual(metrics["scale"], round(metrics["scale"]))
        self.assertGreaterEqual(metrics["quietPx"], 4)
        self.assertEqual(metrics["size"],
                         (metrics["moduleCount"] + 8) * metrics["scale"])
        self.page.evaluate("() => document.getElementById('probe-qr-host').remove()")

    def test_an_unrenderable_viewport_falls_back_to_scale_one(self):
        # Requirement: report the constraint rather than crop the quiet zone.
        m = self.render_payload(PAYLOAD, 5, 5)
        self.assertEqual(m["metrics"]["scale"], 1)
        self.assertEqual(m["metrics"]["quietPx"], 4)
        self.page.evaluate("() => document.getElementById('probe-qr-host').remove()")

    def test_a_missing_library_falls_back_to_text_rather_than_a_broken_symbol(self):
        out = self.page.evaluate(
            """() => {
                 const saved = window.qrcode;
                 window.qrcode = undefined;
                 const host = document.createElement('div');
                 document.body.appendChild(host);
                 const m = renderQrCode(host, 'payload', 232, 76);
                 const text = host.textContent;
                 host.remove();
                 window.qrcode = saved;
                 return { m, text };
               }""")
        self.assertIsNone(out["m"])
        self.assertEqual(out["text"], "payload")


if __name__ == "__main__":
    unittest.main()