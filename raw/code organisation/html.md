# HTML

Extracted verbatim from `frontend.html` (lines 1-8216).

- The single `<style>` block (source lines 8-1572) is in `css.md`.
- The single inline `<script>` block (source lines 2012-8213) is in `js.md`.
- The three external `<script src=...>` tags and the `<link rel="stylesheet">` tag are HTML elements and remain below.
- Inline `style=""` attributes and inline `onclick=""` handlers are left on their elements, exactly as in the original. Standalone inventories are in `css.md` and `js.md`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Casio fx-991EX ClassWiz - OG-style mockup</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<!-- [frontend.html lines 8-1572] <style>...</style> block extracted verbatim to css.md -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
</head>
<body>

<div class="shell">
  <div class="calc">

    <div class="hdr">
      <div class="brand-casio">MENTIS</div>
      <div class="brand-cwiz">CLASSWIZ</div>
    </div>

    <div class="lcd-bezel">
      <div class="lcd" id="lcdDisplay">
        <!-- SPLASH SCREEN -->
        <div id="lcdSplash">MENTIS</div>

        <!-- MENU SCREEN -->
        <div id="lcdMenu">
          <div class="lcd-menu-top">
            <span id="menuScrollIndLeft"  class="scroll-ind" style="display:none;">◀</span>
            <span id="menuScrollIndRight" class="scroll-ind" style="display:none;">▶</span>
          </div>
          <div class="mode-page mode-page-1 active">
            <div class="menu-icons">
              <button class="menu-icon selected" data-mode="Calculate"><span class="mi-main">×÷<br>+−</span><small>1</small></button>
              <button class="menu-icon" data-mode="Complex"><span class="mi-main">a+bi</span><small>2</small></button>
              <button class="menu-icon" data-mode="Base-N"><span class="mi-main">2 8<br>10 16</span><small>3</small></button>
              <button class="menu-icon" data-mode="Matrix"><span class="mi-main">[■]</span><small>4</small></button>
              <button class="menu-icon" data-mode="Vector"><span class="mi-main">↗</span><small>5</small></button>
              <button class="menu-icon" data-mode="Statistics"><span class="mi-main">▥</span><small>6</small></button>
              <button class="menu-icon" data-mode="Distribution"><span class="mi-main">⌒</span><small>7</small></button>
              <button class="menu-icon" data-mode="Spreadsheet"><span class="mi-main">▦</span><small>8</small></button>
            </div>
          </div>
          <div class="mode-page mode-page-2">
            <div class="menu-icons second-page">
              <button class="menu-icon" data-mode="Table"><span class="mi-main">x y</span><small>9</small></button>
              <button class="menu-icon" data-mode="Equation/Func"><span class="mi-main">=ƒ</span><small>10</small></button>
              <button class="menu-icon" data-mode="Inequality"><span class="mi-main">≶</span><small>11</small></button>
              <button class="menu-icon" data-mode="Ratio"><span class="mi-main">a:b</span><small>12</small></button>
            </div>
          </div>
           <div class="lcd-menu-bottom">
              <span id="lcdMenuLabel">1:Calculate</span>
            </div>
        </div>

        <!-- CALCULATION SCREEN -->
        <div id="lcdCalc">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="indShift" class="status-tag">S</span>
              <span id="indAlpha" class="status-tag">A</span>
              <span id="indMemory" class="status-tag">M</span>
              <span id="indMode" class="status-tag"></span>
              <span id="indAngle" class="status-indicator">D</span>
              <span id="indMath" class="status-indicator">Math</span>
            </div>
<div class="status-right">
                <span id="indBase" class="status-tag" style="display:none;"></span>
                <span id="calcScrollIndUp"    class="scroll-ind" style="display:none;">▲</span>
                <span id="calcScrollIndDown"  class="scroll-ind" style="display:none;">▼</span>
                <span id="calcScrollIndLeft"  class="scroll-ind" style="display:none;">◀</span>
                <span id="calcScrollIndRight" class="scroll-ind" style="display:none;">▶</span>
              </div>
          </div>
          <div class="lcd-expr-viewport" id="lcdExprViewport">
            <div class="lcd-expr-content" id="lcdExprContent"></div>
          </div>
          <div class="lcd-result-line" id="lcdResultLine"></div>
          <div id="qr-panel" class="menu-overlay" style="display:none; text-align:center;">
            <div style="font-weight:700; font-size:10px; margin-bottom:2px;">Mentis QR</div>
            <div id="lcdQrBox" style="display:flex; justify-content:center;"></div>
            <div style="font-size:8px; margin-top:2px; word-break:break-all;">https://mentisai-delta.vercel.app/</div>
          </div>
          <div id="optn-panel" class="menu-overlay" style="display:none;">
            <div id="optn-main-menu">
              <div class="menu-item" onclick="optnSelectCategory(1)">1&nbsp;&nbsp;Hyperbolic</div>
              <div class="menu-item" onclick="optnSelectCategory(2)">2&nbsp;&nbsp;Angle Unit</div>
            </div>
            <div id="optn-hyp-menu" style="display:none;">
              <div class="menu-item" onclick="insertOptn('sinh(')">1&nbsp;&nbsp;sinh</div>
              <div class="menu-item" onclick="insertOptn('cosh(')">2&nbsp;&nbsp;cosh</div>
              <div class="menu-item" onclick="insertOptn('tanh(')">3&nbsp;&nbsp;tanh</div>
              <div class="menu-item" onclick="insertOptn('asinh(')">4&nbsp;&nbsp;sinh⁻¹</div>
              <div class="menu-item" onclick="insertOptn('acosh(')">5&nbsp;&nbsp;cosh⁻¹</div>
              <div class="menu-item" onclick="insertOptn('atanh(')">6&nbsp;&nbsp;tanh⁻¹</div>
            </div>
            <div id="optn-angle-menu" style="display:none;">
              <div class="menu-item" onclick="insertOptn('°')">1&nbsp;&nbsp;°&nbsp;&nbsp;Degree</div>
              <div class="menu-item" onclick="insertOptn('r')">2&nbsp;&nbsp;r&nbsp;&nbsp;Radian</div>
              <div class="menu-item" onclick="insertOptn('g')">3&nbsp;&nbsp;g&nbsp;&nbsp;Gradian</div>
            </div>
            <div id="optn-mat-menu" style="display:none;">
              <div class="menu-item" onclick="insertOptn('MatA')">1&nbsp;&nbsp;MatA</div>
              <div class="menu-item" onclick="insertOptn('MatB')">2&nbsp;&nbsp;MatB</div>
              <div class="menu-item" onclick="insertOptn('MatC')">3&nbsp;&nbsp;MatC</div>
              <div class="menu-item" onclick="insertOptn('MatD')">4&nbsp;&nbsp;MatD</div>
              <div class="menu-item" onclick="insertOptn('Det(')">5&nbsp;&nbsp;Determinant</div>
              <div class="menu-item" onclick="insertOptn('Trn(')">6&nbsp;&nbsp;Transpose</div>
              <div class="menu-item" onclick="insertOptn('Identity(')">7&nbsp;&nbsp;Identity</div>
            </div>
            <div id="optn-vct-menu" style="display:none;">
              <div class="menu-item" onclick="insertOptn('VctA')">1&nbsp;&nbsp;VctA</div>
              <div class="menu-item" onclick="insertOptn('VctB')">2&nbsp;&nbsp;VctB</div>
              <div class="menu-item" onclick="insertOptn('VctC')">3&nbsp;&nbsp;VctC</div>
              <div class="menu-item" onclick="insertOptn('VctD')">4&nbsp;&nbsp;VctD</div>
              <div class="menu-item" onclick="insertOptn('Dot(')">5&nbsp;&nbsp;Dot Product</div>
              <div class="menu-item" onclick="insertOptn('Angle(')">6&nbsp;&nbsp;Angle</div>
              <div class="menu-item" onclick="insertOptn('UnitV(')">7&nbsp;&nbsp;Unit Vector</div>
            </div>
          </div>
        </div>

        <!-- MATRIX SCREEN -->
        <div id="lcdMatrix">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="matIndShift" class="status-tag">S</span>
              <span id="matIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">MAT</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdMatrixBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- VECTOR SCREEN -->
        <div id="lcdVector">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="vctIndShift" class="status-tag">S</span>
              <span id="vctIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">VCT</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdVectorBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- STATISTICS SCREEN -->
        <div id="lcdStatistics">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="statIndShift" class="status-tag">S</span>
              <span id="statIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">STAT</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdStatisticsBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- DISTRIBUTION SCREEN -->
        <div id="lcdDistribution">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="distIndShift" class="status-tag">S</span>
              <span id="distIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">DIST</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdDistributionBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- SETUP SCREEN -->
        <div id="lcdSetup">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="setupIndShift" class="status-tag">S</span>
              <span id="setupIndAlpha" class="status-tag">A</span>
              <span id="setupIndAngle" class="status-indicator">D</span>
              <span id="setupIndMath" class="status-indicator">Math</span>
            </div>
<div class="status-right">
                <span id="setupScrollIndUp"    class="scroll-ind" style="display:none;">▲</span>
                <span id="setupScrollIndDown"  class="scroll-ind" style="display:none;">▼</span>
              </div>
          </div>
          <div id="lcdSetupBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- SPREADSHEET SCREEN -->
        <div id="lcdSpreadsheet">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="sheetIndShift" class="status-tag">S</span>
              <span id="sheetIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">SHEET</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdSpreadsheetBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- RATIO SCREEN -->
        <div id="lcdRatio">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="ratioIndShift" class="status-tag">S</span>
              <span id="ratioIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">RATIO</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdRatioBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- TABLE SCREEN -->
        <div id="lcdTable">
          <div class="lcd-status-bar"><div class="status-left"><span id="tableIndShift" class="status-tag">S</span><span id="tableIndAlpha" class="status-tag">A</span><span class="status-tag active">TABLE</span><span class="status-indicator">D</span><span class="status-indicator">Math</span></div></div>
          <div id="lcdTableBody" style="flex:1;display:flex;flex-direction:column;justify-content:space-between;"></div>
        </div>

        <!-- INEQUALITY SCREEN -->
        <div id="lcdInequality">
          <div class="lcd-status-bar"><div class="status-left"><span id="ineqIndShift" class="status-tag">S</span><span id="ineqIndAlpha" class="status-tag">A</span><span class="status-tag active">INEQ</span><span class="status-indicator">D</span><span class="status-indicator">Math</span></div></div>
          <div id="lcdInequalityBody" style="flex:1;display:flex;flex-direction:column;"></div>
        </div>
        <div id="lcdEquation">
          <div class="lcd-status-bar"><div class="status-left"><span id="eqIndShift" class="status-tag">S</span><span id="eqIndAlpha" class="status-tag">A</span><span class="status-tag active">EQN</span><span class="status-indicator">D</span><span class="status-indicator">Math</span></div></div>
          <div id="lcdEquationBody" style="flex:1;display:flex;flex-direction:column;"></div>
        </div>

        <!-- CONSTANTS SCREEN -->
        <div id="lcdConstants">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="constIndShift" class="status-tag">S</span>
              <span id="constIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">CONST</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdConstantsBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- CONVERSION SCREEN -->
        <div id="lcdConversion">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="convIndShift" class="status-tag">S</span>
              <span id="convIndAlpha" class="status-tag">A</span>
              <span class="status-tag active">CONV</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdConversionBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>

        <!-- RESET SCREEN -->
        <div id="lcdReset">
          <div class="lcd-status-bar">
            <div class="status-left">
              <span id="resetIndShift" class="status-tag">S</span>
              <span id="resetIndAlpha" class="status-tag">A</span>
              <span class="status-indicator">D</span>
              <span class="status-indicator">Math</span>
            </div>
          </div>
          <div id="lcdResetBody" style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"></div>
        </div>
      </div>
    </div>

    <div class="top-row top-controls">
      <div class="bwc">
        <span class="lbl ly">SHIFT</span>
        <button class="bc" data-key="shift"></button>
      </div>
      <div class="bwc">
        <span class="lbl lp">ALPHA</span>
        <button class="bc" data-key="alpha"></button>
      </div>

      <div class="dpo">
        <div class="dpad">
          <div class="dpad-ring"></div>
          <button class="dp dp-u" data-key="dpad_up">▲</button>
          <button class="dp dp-l" data-key="dpad_left">◀</button>
          <button class="dp dp-c" data-key="dpad_center" aria-label="D-pad center"></button>
          <button class="dp dp-r" data-key="dpad_right">▶</button>
          <button class="dp dp-d" data-key="dpad_down">▼</button>
        </div>
      </div>

      <div class="bwc">
        <span class="lbl"><span class="lg">MENU</span> <span class="shift-mark">SETUP</span></span>
        <button class="bc" data-shift="SETUP" data-key="setup"></button>
      </div>
      <div class="bwc">
        <span class="lbl lg">ON</span>
        <button class="bc" data-key="on"></button>
      </div>
    </div>

    <div class="btns">

      <div class="special-row">
        <div class="bw">
          <span class="lbl"><span class="shift-mark">QR</span></span>
          <button class="b" data-shift="QR" data-key="optn">OPTN</button>
        </div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark">SOLVE</span><span class="alpha-mark">=</span></span>
          <button class="b" data-shift="SOLVE" data-alpha="=" data-key="calc">CALC</button>
        </div>
        <div></div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark">Σ</span><span class="alpha-mark">:</span></span>
          <button class="b math-template" data-shift="d/dx" data-alpha=":" data-key="integral" aria-label="integral">
            <span class="glyph int-glyph">
              <span class="ibox top"></span><span class="int-sign">∫</span>
              <span class="ibox bottom"></span><span class="ibox arg"></span>
            </span>
          </button>
        </div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark">d/dx</span></span>
          <button class="b variable" data-shift="Sigma" data-key="variable">x</button>
        </div>
      </div>

      <!-- This row is SIX keys on the reference calculator:
           fraction / sqrt / square / power / log-base / ln -->
      <div class="row">
        <div class="bw">
          <span class="lbl">
            <span class="shift-mark mixed-frac-legend">
              <span class="whole"></span><span class="mini-frac"><i></i><b></b><i></i></span>
            </span>
          </span>
          <button class="b math-template" data-shift="mixed_fraction" data-key="fraction" aria-label="fraction">
            <span class="glyph frac-glyph"><span class="box"></span><span class="bar"></span><span class="box"></span></span>
          </button>
        </div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark">∛</span></span>
          <button class="b math-template" data-shift="cuberoot" data-key="sqrt" aria-label="square root">
            <svg viewBox="0 0 28 18" width="28" height="18" aria-hidden="true"
                 style="display:block; overflow:visible;">
              <path d="M2 10 L5 10 L7.5 15 L11 3.5 L25.5 3.5"
                    fill="none" stroke="currentColor" stroke-width="1.6"
                    stroke-linecap="round" stroke-linejoin="round"/>
              <rect x="13.2" y="6.1" width="7" height="5.7"
                    fill="none" stroke="currentColor" stroke-width="1.0"/>
            </svg>
          </button>
        </div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark">x³</span> <span class="base-mark">DEC</span></span>
          <button class="b" data-shift="cube" data-alpha="DEC" data-key="square">x²</button>
        </div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark xroot-legend">ˣ√□</span> <span class="base-mark">HEX</span></span>
          <button class="b math-template" data-shift="xroot" data-alpha="HEX" data-key="power" aria-label="power template">
            <span class="glyph pow-glyph"><span class="x">x</span><span class="expbox"></span></span>
          </button>
        </div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark">10ˣ</span> <span class="base-mark">BIN</span></span>
          <button class="b" data-shift="10^x" data-alpha="BIN" data-key="log">
            <span class="logbase-glyph">log<span class="basebox"></span></span>
          </button>
        </div>
        <div class="bw">
          <span class="lbl"><span class="shift-mark">eˣ</span> <span class="base-mark">OCT</span></span>
          <button class="b" data-shift="e^x" data-alpha="OCT" data-key="ln">ln</button>
        </div>
      </div>

      <!-- Magenta ALPHA variables A-F belong across this six-key row. -->
      <div class="row">
        <div class="bw"><span class="lbl"><span class="shift-mark">logₐ</span> <span class="alpha-mark">A</span></span><button class="b" data-shift="log_base" data-alpha="A" data-key="negate">(-)</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">FACT</span> <span class="alpha-mark">B</span></span><button class="b" data-shift="FACT" data-alpha="B" data-key="ellipsis">°′″</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">x!</span> <span class="alpha-mark">C</span></span><button class="b" data-shift="factorial" data-alpha="C" data-key="inverse">x⁻¹</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">sin⁻¹</span> <span class="alpha-mark">D</span></span><button class="b" data-shift="asin" data-alpha="D" data-key="sin">sin</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">cos⁻¹</span> <span class="alpha-mark">E</span></span><button class="b" data-shift="acos" data-alpha="E" data-key="cos">cos</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">tan⁻¹</span> <span class="alpha-mark">F</span></span><button class="b" data-shift="atan" data-alpha="F" data-key="tan">tan</button></div>
      </div>

      <div class="row">
        <div class="bw"><span class="lbl"><span class="shift-mark">RECALL</span></span><button class="b" data-shift="RECALL" data-key="sto">STO</button></div>
        <div class="bw"><span class="lbl"><span class="eng-arrows"><span class="left">←</span><span class="right">→</span></span></span><button class="b" data-shift="ENG_LEFT" data-alpha="i" data-key="eng">ENG</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">Abs</span></span><button class="b" data-shift="Abs" data-key="left_paren">(</button></div>
        <div class="bw"><span class="lbl"><span class="alpha-mark">x</span></span><button class="b" data-shift="comma" data-alpha="x" data-key="right_paren">)</button></div>
        <div class="bw"><span class="lbl"><span class="sd-legend"><span class="shift-mark">a b/c↔d/c</span><span class="alpha-mark">y</span></span></span><button class="b" data-shift="fraction_toggle" data-alpha="y" data-key="s_to_d">S⇔D</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">M−</span> <span class="alpha-mark">M</span></span><button class="b" data-shift="M-" data-alpha="M" data-key="m_plus">M+</button></div>
      </div>

      <div class="row numeric-row">
        <div class="bw"><span class="lbl"><span class="shift-mark">CONST</span></span><button class="b bn" data-shift="CONST" data-key="7">7</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">CONV</span></span><button class="b bn" data-shift="CONV" data-key="8">8</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">RESET</span></span><button class="b bn" data-shift="RESET" data-key="9">9</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">INS</span> <span class="alpha-mark">UNDO</span></span><button class="b bdel" data-shift="INS" data-alpha="UNDO" data-key="del">DEL</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">OFF</span></span><button class="b bac" data-shift="OFF" data-key="ac">AC</button></div>
      </div>

      <div class="row numeric-row">
        <div class="bw"><span class="lbl">&nbsp;</span><button class="b bn" data-key="4">4</button></div>
        <div class="bw"><span class="lbl">&nbsp;</span><button class="b bn" data-key="5">5</button></div>
        <div class="bw"><span class="lbl">&nbsp;</span><button class="b bn" data-key="6">6</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">nPr</span></span><button class="b bop" data-shift="nPr" data-key="multiply">×</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">nCr</span></span><button class="b bop" data-shift="nCr" data-key="divide">÷</button></div>
      </div>

      <div class="row numeric-row">
        <div class="bw"><span class="lbl">&nbsp;</span><button class="b bn" data-key="1">1</button></div>
        <div class="bw"><span class="lbl">&nbsp;</span><button class="b bn" data-key="2">2</button></div>
        <div class="bw"><span class="lbl">&nbsp;</span><button class="b bn" data-key="3">3</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">Pol</span></span><button class="b bop" data-shift="Pol" data-key="plus">+</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">Rec</span></span><button class="b bop" data-shift="Rec" data-key="minus">−</button></div>
      </div>

      <div class="row numeric-row">
        <div class="bw"><span class="lbl"><span class="shift-mark">Rnd</span></span><button class="b bn" data-shift="Rnd" data-key="0">0</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">Ran#</span> <span class="alpha-mark">RanInt</span></span><button class="b bn" data-shift="Ran#" data-alpha="RanInt" data-key="decimal">.</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">π</span></span><button class="b bop scientific-wide" data-shift="pi" data-alpha="e" data-key="scientific">×10ˣ</button></div>
        <div class="bw"><span class="lbl"><span class="alpha-mark">e</span></span><button class="b bop" style="font-size:14px;font-weight:600" data-shift="percent" data-key="ans">Ans</button></div>
        <div class="bw"><span class="lbl"><span class="shift-mark">≈</span></span><button class="b bop" data-shift="approx" data-key="equals">=</button></div>
      </div>

      <div class="bottom-pad"></div>
    </div>
  </div>
</div>

<!-- [frontend.html lines 2012-8213] <script>...</script> block extracted verbatim to js.md -->

</body>
</html>

```
