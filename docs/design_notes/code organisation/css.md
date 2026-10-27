# CSS

Extracted verbatim from `frontend.html`.

- `<style>` block: source lines 8-1572 (the only `<style>` block in the file).
- Inline `style=""` attributes are inventoried at the end of this file; their host elements were left untouched in `html.md`.

## `<style>` block (lines 8-1572)

```css
  * { box-sizing: border-box; margin: 0; padding: 0; }

  @font-face {
    font-family: 'CASIO ClassWiz';
    src: url('/ClassWizFontSet/CASIOClassWizCW01.ttf') format('truetype'),
         url('/fonts/CASIOClassWizCW01.ttf') format('truetype'),
         url('ClassWizFontSet/CASIOClassWizCW01.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
  }

  @font-face {
    font-family: 'CASIO ClassWiz RS';
    src: url('/ClassWizFontSet/CASIO%20ClassWiz%20RS.ttf') format('truetype'),
         url('/fonts/CASIO%20ClassWiz%20RS.ttf') format('truetype'),
         url('ClassWizFontSet/CASIO%20ClassWiz%20RS.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
  }

  :root{
    --face:#2c2c2d;
    --face2:#242425;
    --rim:#b8b9b8;
    --rim-hi:#e4e5e3;
    --rim-lo:#777978;
    --key:#171719;
    --key2:#242426;
    --whitekey:#efefed;
    --blue:#2470e8;
    --yellow:#d8a527;
    --pink:#d7517f;
    --cyan:#4aa6d5;
    --lcd:#d5dfb8;
    --ink:#141614;
    --calc-contrast:.5;
  }

  body{
    min-height:100vh;
    display:flex;
    align-items:center;
    justify-content:center;
    background:#a7a7a7;
    font-family:Arial, Helvetica, sans-serif;
    padding:24px;
    user-select:none;
  }

  /* ── OUTER CALCULATOR SHELL ── */
  .shell{
    width:322px;
    padding:8px 9px 13px;
    border-radius:38px 38px 31px 31px;
    background:
      linear-gradient(90deg,var(--rim-lo) 0%,var(--rim-hi) 7%,#c7c8c6 17%,#a7a8a7 84%,#747675 100%);
    box-shadow:
      0 18px 42px rgba(0,0,0,.42),
      inset 0 1px 0 rgba(255,255,255,.8),
      inset 0 -2px 3px rgba(0,0,0,.35);
  }

  .calc{
    width:100%;
    border-radius:31px 31px 24px 24px;
    padding:17px 14px 15px;
    overflow:hidden;
    background:
      radial-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
      linear-gradient(180deg,#303031 0%,#29292a 55%,#262627 100%);
    background-size:4px 4px, auto;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,.05),
      inset 0 -1px 0 rgba(0,0,0,.55);
  }

  /* ── HEADER ── */
  .hdr{
    position:relative;
    height:65px;
    margin-bottom:4px;
  }
  .brand-casio{
    position:absolute;
    left:2px;
    top:2px;
    color:#fff;
    font-family:"Arial Black", Arial, sans-serif;
    font-size:22px;
    font-weight:900;
    letter-spacing:.1px;
  }
  .brand-cwiz{
    position:absolute;
    left:50%;
    top:29px;
    transform:translateX(-50%);
    color:#d95c7f;
    font-size:10px;
    font-weight:700;
    letter-spacing:3.2px;
    white-space:nowrap;
  }

  /* ── LCD + BLACK BEZEL ── */
  .lcd-bezel{
    background:#0e0f10;
    border-radius:13px;
    padding:12px 11px 11px;
    margin:0 1px 12px;
    box-shadow:
      inset 0 0 0 1px rgba(255,255,255,.03),
      0 2px 0 rgba(0,0,0,.4);
  }
  .lcd{
    position:relative;
    height:103px;
    border-radius:3px;
    border:1px solid #83877d;
    background:linear-gradient(180deg,#dce6c2 0%,#cedab0 100%);
    box-shadow:
      inset 0 2px 5px rgba(0,0,0,.17),
      inset 0 0 0 1px rgba(255,255,255,.35);
    color:var(--ink);
    padding:4px 6px;
    overflow:hidden;
    pointer-events:none;
    filter:contrast(calc(0.7 + var(--calc-contrast) * 0.6));
  }

  .small-font { font-size:0.75em; }

  /* SPLASH SCREEN */
  #lcdSplash{
    display:none;
    align-items:center;
    justify-content:center;
    height:100%;
    font-size:24px;
    font-weight:900;
    letter-spacing:2px;
    color:var(--ink);
  }

  /* MENU SCREEN */
  #lcdMenu{
    display:none;
    flex-direction:column;
    justify-content:space-between;
    height:100%;
  }
  .menu-icons{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:2px;
    height:56px;
  }
  .menu-icon{
    appearance:none;
    border:1px solid #353735;
    background:rgba(255,255,255,.15);
    font:700 9px/1 Arial, monospace;
    display:flex;
    align-items:center;
    justify-content:center;
    position:relative;
    color:var(--ink);
    cursor:pointer;
    padding:0 1px;
  }
  .menu-icon.selected{
    background:#141614;
    color:#dce6c2;
  }
  .menu-icon small{
    position:absolute;
    right:2px;
    bottom:1px;
    font-size:6px;
    font-family:Arial;
  }
  .menu-icon .mi-main{font-family:Arial; font-size:9px; font-weight:700; line-height:1.15; text-align:center;}
  .second-page{
    grid-template-columns:repeat(4,1fr);
  }
  .mode-page{display:none;}
  .mode-page.active{display:block;}
  .lcd-page-indicator{position:absolute;bottom:22px;left:50%;transform:translateX(-50%);font-size:9px;color:var(--ink);pointer-events:none;}

  .lcd-menu-top {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    height: 10px;
    padding: 0 3px;
    font-size: 9px;
    font-weight: 700;
    color: var(--ink);
    line-height: 1;
  }

  .lcd-menu-bottom{
    display:flex;
    justify-content:space-between;
    align-items:center;
    height:18px;
    font-size:14px;
    font-weight:700;
    line-height:1;
  }

  /* MATRIX SCREEN */
  #lcdMatrix{
    display:none;
    flex-direction:column;
    justify-content:space-between;
    height:100%;
    position:relative;
    color:var(--ink);
  }
  .matrix-menu-grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    grid-template-rows:1fr 1fr;
    gap:4px 8px;
    padding:4px 8px;
    font-size:13px;
    font-weight:700;
  }
  .matrix-dim-box{
    display:flex;
    flex-direction:column;
    justify-content:center;
    padding:2px 8px;
    gap:3px;
  }
  .matrix-dim-title{
    font-size:13px;
    font-weight:700;
  }
  .matrix-dim-line{
    display:flex;
    align-items:center;
    gap:6px;
    font-size:12px;
  }
  .matrix-dim-val{
    font-weight:700;
    font-size:13px;
  }
  .matrix-grid-container{
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    height:calc(100% - 14px);
  }
  .matrix-table{
    display:grid;
    gap:1px;
    background:#141614;
    border:1px solid #141614;
    margin:1px 2px;
  }
  .matrix-cell{
    background:#dce6c2;
    color:#141614;
    text-align:right;
    padding:0 2px;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .matrix-cell.active{
    background:#141614;
    color:#dce6c2;
    font-weight:bold;
  }
  .matrix-bottom-info{
    display:flex;
    justify-content:space-between;
    align-items:baseline;
    font-size:11px;
    line-height:1;
    font-weight:700;
    padding:0 3px 1px 3px;
  }

  /* VECTOR SCREEN */
  #lcdVector{
    display:none;
    flex-direction:column;
    justify-content:space-between;
    height:100%;
    position:relative;
    color:var(--ink);
  }
  .vector-menu-list{
    display:grid;
    grid-template-columns:1fr 1fr;
    grid-template-rows:1fr 1fr;
    gap:4px 8px;
    padding:4px 8px;
    font-size:13px;
    font-weight:700;
  }
  .vector-dim-box{
    display:flex;
    flex-direction:column;
    justify-content:center;
    padding:2px 8px;
    gap:3px;
  }
  .vector-dim-title{
    font-size:13px;
    font-weight:700;
  }
  .vector-dim-line{
    display:flex;
    align-items:center;
    gap:6px;
    font-size:12px;
  }
  .vector-dim-val{
    font-weight:700;
    font-size:13px;
  }
  .vector-grid-container{
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    height:calc(100% - 14px);
  }
  .vector-table{
    display:grid;
    gap:1px;
    background:#141614;
    border:1px solid #141614;
    margin:1px 2px;
  }
  .vector-cell{
    background:#dce6c2;
    color:#141614;
    text-align:right;
    padding:0 2px;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .vector-cell.active{
    background:#141614;
    color:#dce6c2;
    font-weight:bold;
  }
  .vector-bottom-info{
    display:flex;
    justify-content:space-between;
    align-items:baseline;
    font-size:11px;
    line-height:1;
    font-weight:700;
    padding:0 3px 1px 3px;
  }

  /* STATISTICS SCREEN */
  #lcdStatistics {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
  }
  /* DISTRIBUTION SCREEN */
  #lcdDistribution {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
    font-family: 'Courier New', Courier, monospace;
  }
  #lcdDistribution * { font-family: 'Courier New', Courier, monospace; }
  .dist-type-list { font-family: 'Courier New', Courier, monospace; font-size: 11px; line-height: 14px; padding: 2px 4px; }
  .dist-type-item { display: block; }
  .dist-type-item.selected { background: var(--lcd-fg, var(--ink)); color: var(--lcd-bg, #c5ccb8); }
  .dist-submenu { font-family: 'Courier New', Courier, monospace; font-size: 11px; padding: 4px; }
  .dist-field-list { font-family: 'Courier New', Courier, monospace; font-size: 11px; padding: 2px 4px; }
  .dist-field-row { display: flex; justify-content: space-between; line-height: 15px; }
  .dist-field-row.active { background: var(--lcd-fg, var(--ink)); color: var(--lcd-bg, #c5ccb8); }
  .dist-result-screen { font-family: 'Courier New', Courier, monospace; font-size: 12px; padding: 4px; }
  .dist-scroll-hint { font-size: 9px; text-align: right; padding-right: 4px; }
  .stat-type-list {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0px;
    margin-top: 2px;
    padding: 0 4px;
    font-size: 11px;
    font-weight: 700;
    width: 100%;
  }
  .stat-type-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .stat-type-item.selected {
    background: var(--ink);
    color: #dce6c2;
  }
  .stat-grid-container {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: calc(100% - 14px);
  }
  .stat-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 10px;
    margin: 1px 0;
  }
  .stat-table th {
    font-size: 9px;
    text-align: center;
    border-bottom: 1px solid var(--ink);
    padding: 0 2px;
  }
  .stat-table td {
    border: 1px solid var(--ink);
    padding: 0 2px;
    text-align: right;
    min-width: 36px;
    height: 13px;
    line-height: 13px;
    font-size: 9px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .stat-table td.active {
    background: var(--ink);
    color: #dce6c2;
    font-weight: bold;
  }
  .stat-row-num {
    font-size: 8px;
    color: var(--ink);
    opacity: 0.7;
    text-align: center !important;
    min-width: 16px !important;
    border: none !important;
  }
  .stat-bottom-info {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 11px;
    line-height: 1;
    font-weight: 700;
    padding: 0 3px 1px 3px;
  }
  .stat-scroll-hint {
    font-size: 9px;
    text-align: right;
    position: absolute;
    bottom: 2px;
    right: 4px;
  }

  /* SETUP SCREEN */
  #lcdSetup {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
  }
  .setup-menu-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 1px 4px;
    font-size: 11px;
    font-weight: 700;
  }
  .setup-menu-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 2px;
    height: 14px;
    line-height: 14px;
    cursor: pointer;
  }
  .setup-menu-item.selected {
    background: var(--ink);
    color: #dce6c2;
  }
  .setup-menu-item:hover {
    background: rgba(0, 0, 0, 0.08);
  }
  .setup-menu-item.selected:hover {
    background: var(--ink);
    color: #dce6c2;
  }
  .setup-main-menu-row {
    height: 18px;
    line-height: 18px;
    font-size: 13px;
  }
  .setup-prompt-box {
    display: flex;
    flex-direction: column;
    padding: 4px 6px;
    font-size: 11px;
    font-weight: 700;
  }
  .setup-prompt-title {
    font-size: 12px;
    margin-bottom: 4px;
  }
  .setup-prompt-hint {
    font-size: 9px;
    opacity: 0.8;
  }

  /* SPREADSHEET SCREEN */
  #lcdSpreadsheet {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
    font-family: 'Courier New', Courier, monospace;
  }
  #lcdSpreadsheet * { font-family: 'Courier New', Courier, monospace; }
  .sheet-grid-container {
    display: flex;
    flex-direction: column;
    height: calc(100% - 20px);
    overflow: hidden;
  }
  .sheet-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 8px;
  }
  .sheet-table th {
    font-size: 8px;
    text-align: center;
    border-bottom: 1px solid var(--ink);
    border-right: 1px solid var(--ink);
    padding: 0 1px;
    height: 9px;
    line-height: 9px;
    background: rgba(0,0,0,0.05);
  }
  .sheet-table td {
    border: 1px solid var(--ink);
    padding: 0 1px;
    text-align: right;
    height: 9px;
    line-height: 9px;
    font-size: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }
  .sheet-table th:first-child,
  .sheet-table td:first-child { width: 14px; }
  .sheet-table td.active {
    background: var(--ink);
    color: #dce6c2;
    font-weight: bold;
  }
  .sheet-row-header {
    font-size: 8px;
    font-weight: bold;
    text-align: center !important;
    min-width: 14px !important;
    background: rgba(0,0,0,0.05);
    border: 1px solid var(--ink);
  }
  .sheet-bottom-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    font-weight: 700;
    height: 18px;
    border-top: 1px solid var(--ink);
    padding: 0 4px;
  }

  /* RATIO SCREEN */
  #lcdRatio {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
  }
  .ratio-menu-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 6px 8px;
    font-size: 12px;
    font-weight: 700;
  }
  .ratio-input-view {
    display: flex;
    flex-direction: column;
    padding: 4px 6px;
    gap: 6px;
  }
  .ratio-formula-header {
    font-size: 12px;
    font-weight: 700;
  }
  .ratio-boxes-row {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 700;
  }
  .ratio-field-box {
    border: 1px solid var(--ink);
    padding: 1px 4px;
    min-width: 24px;
    height: 16px;
    line-height: 14px;
    text-align: center;
    background: #dce6c2;
  }
  .ratio-field-box.active {
    background: var(--ink);
    color: #dce6c2;
  }
  .ratio-result-line {
    font-size: 13px;
    font-weight: 700;
    text-align: right;
    padding-right: 8px;
  }

  /* TABLE SCREEN */
  #lcdTable { display:none; flex-direction:column; height:100%; position:relative; color:var(--ink); }
  .table-input-view { display:flex; flex-direction:column; gap:8px; padding:8px 7px; font-size:12px; font-weight:700; }
  .table-input-line { min-height:18px; white-space:nowrap; overflow:hidden; }
  .table-grid { display:grid; grid-template-columns:1fr 1.35fr; margin:2px 4px; border:1px solid var(--ink); gap:1px; background:var(--ink); font-size:10px; }
  .table-grid > div { background:#dce6c2; color:var(--ink); min-height:14px; line-height:14px; padding:0 3px; text-align:right; overflow:hidden; white-space:nowrap; }
  .table-grid > .table-head { text-align:center; font-weight:700; background:rgba(0,0,0,.08); }
  .table-grid > .table-selected { background:var(--ink); color:#dce6c2; font-weight:700; }
  .table-footer { display:flex; justify-content:space-between; padding:1px 5px; font-size:9px; }
  #lcdInequality { display:none; flex-direction:column; height:100%; position:relative; color:var(--ink); }
  .ineq-view { padding:5px 6px; font-size:11px; font-weight:700; }
  .ineq-title { font-size:12px; margin-bottom:5px; }
  .ineq-option { line-height:15px; padding:0 3px; }
  .ineq-option.selected { background:var(--ink); color:#dce6c2; }
  .ineq-template { border:1px solid var(--ink); padding:3px 4px; margin-bottom:5px; text-align:center; font-size:12px; }
  .ineq-coeff { display:flex; justify-content:space-between; line-height:17px; padding:0 5px; }
  .ineq-coeff.selected { background:var(--ink); color:#dce6c2; }
  .ineq-result { padding:7px 5px; font-size:11px; font-weight:700; }
  /* EQUATION / FUNCTION SCREEN */
  #lcdEquation { display:none; flex-direction:column; height:100%; position:relative; color:var(--ink); }
  .eq-view { padding:3px 4px; font-size:10px; font-weight:700; overflow:hidden; }
  .eq-title { font-size:11px; margin-bottom:3px; }
  .eq-option { line-height:14px; padding:0 3px; }
  .eq-option.selected { background:var(--ink); color:#dce6c2; }
  .eq-template { text-align:center; font-size:10px; line-height:13px; margin-bottom:2px; white-space:nowrap; }
  .eq-row { display:flex; align-items:center; gap:1px; line-height:14px; white-space:nowrap; }
  .eq-row-label { width:12px; }
  .eq-field { display:inline-block; min-width:18px; padding:0 2px; text-align:center; border:1px solid transparent; }
  .eq-field.active { background:var(--ink); color:#dce6c2; border-color:var(--ink); }
  .eq-op { margin:0 1px; }
  .eq-coeff-row { display:flex; justify-content:space-between; line-height:14px; padding:0 3px; }
  .eq-coeff-row.active { background:var(--ink); color:#dce6c2; }
  .eq-result { padding:5px 4px; font-size:11px; font-weight:700; line-height:16px; }
  .eq-solution { white-space:pre-line; }

  /* CONSTANTS SCREEN */
  #lcdConstants {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
  }

  /* CONVERSION SCREEN */
  #lcdConversion {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
  }

  /* RESET SCREEN */
  #lcdReset {
    display: none;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    position: relative;
    color: var(--ink);
  }
  .reset-confirm-box {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 4px;
    padding: 8px 4px;
    font-weight: 700;
  }
  .reset-title { font-size: 12px; }
  .reset-question { font-size: 11px; }
  .reset-choices {
    display: flex;
    justify-content: space-between;
    width: 80%;
    font-size: 11px;
    margin-top: 4px;
  }

  /* CALC SCREEN */
  #lcdCalc{
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    height:100%;
    position:relative;
  }

  /* STATUS BAR */
  .lcd-status-bar{
    display:flex;
    justify-content:space-between;
    align-items:center;
    height:12px;
    font-size:9px;
    font-weight:700;
    line-height:1;
    font-family: Arial, Helvetica, sans-serif;
  }
  .status-left, .status-right{
    display:flex;
    align-items:center;
    gap:4px;
  }
  .status-tag{
    display:none;
    border:1px solid currentColor;
    padding:0 2px;
    font-size:8px;
    line-height:9px;
    border-radius:1px;
    font-family: Arial, Helvetica, sans-serif;
  }
   .status-tag.active{display:inline-block;}
   .scroll-ind{
     font-size:8px;
     line-height:9px;
     margin-left:1px;
     font-family:Arial,Helvetica,sans-serif;
   }
  .status-indicator{
    font-size:9px;
    font-weight:bold;
  }

  .menu-overlay{
    position:absolute;
    inset:2px 4px 4px;
    z-index:20;
    padding:5px;
    background:#dce6c2;
    border:1px solid #353735;
    color:var(--ink);
    font-family:Arial, Helvetica, sans-serif;
    font-size:10px;
    pointer-events:auto;
  }
  .optn-section-label{font-weight:700; margin:2px 0 3px;}
  .optn-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:3px; margin-bottom:5px;}
  .optn-grid button{padding:3px 1px; border:1px solid #353735; background:rgba(255,255,255,.2); color:var(--ink); font:700 9px Arial, sans-serif;}
  .menu-overlay .menu-item{padding:2px 4px; font:700 11px/15px Arial, sans-serif; cursor:pointer;}
  .menu-overlay .menu-item:hover{background:var(--ink); color:#dce6c2;}

  /* EXPRESSION VIEWPORT */
  .lcd-expr-viewport{
    position:relative;
    width:100%;
    height:50px;
    overflow-x:hidden;
    overflow-y:hidden;
    white-space:nowrap;
    font-size:16px;
    line-height:1.2;
    padding-top:2px;
  }
  .lcd-expr-content{
    display:inline-flex;
    align-items:baseline;
    position:relative;
    font-family:monospace;
    font-size:16px;
    color:var(--ink);
  }

  /* RESULT LINE */
  .lcd-result-line{
    position:absolute;
    right:4px;
    bottom:2px;
    font-size:20px;
    font-weight:bold;
    line-height:1;
    font-family:monospace;
    text-align:right;
    white-space:nowrap;
    max-width:96%;
    overflow:hidden;
    color:var(--ink);
  }

  /* CURSOR */
  .lcd-cursor{
    display:inline-block;
    width:1.5px;
    height:15px;
    background-color:#141614;
    vertical-align:text-bottom;
    margin:0 0.5px;
    animation:lcdBlink 1s steps(1, start) infinite;
  }
  @keyframes lcdBlink {
    0%, 100% { opacity:1; }
    50% { opacity:0; }
  }

  /* EMPTY TEMPLATE SLOT */
  .slot-empty{
    display:inline-block;
    width:7px;
    height:10px;
    border:1px dashed #555;
    margin:0 1px;
    vertical-align:baseline;
  }

  /* FRACTION TEMPLATE */
  .math-fraction{
    display:inline-flex;
    flex-direction:column;
    align-items:center;
    vertical-align:middle;
    margin:0 2px;
    padding:0 1px;
    font-size:13px;
  }
  .math-numerator{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-width:8px;
    min-height:13px;
    padding:0 1px;
    line-height:1;
  }
  .math-fraction-bar{
    width:100%;
    height:1.2px;
    background-color:currentColor;
    margin:1px 0;
  }
  .math-denominator{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-width:8px;
    min-height:13px;
    padding:0 1px;
    line-height:1;
  }

  /* RADICAL TEMPLATE */
  .math-radical{
    display:inline-flex;
    align-items:flex-start;
    vertical-align:baseline;
    margin:0 1px;
  }
  .math-root-index{
    font-size:9px;
    line-height:1;
    margin-right:-2px;
    margin-top:-3px;
  }
  .math-radical-symbol{
    font-size:17px;
    line-height:1;
    margin-right:0;
    transform:translateY(1px);
  }
  .math-radicand{
    border-top:1.2px solid currentColor;
    display:inline-flex;
    align-items:center;
    padding:0 2px 0 1px;
    margin-top:2px;
    min-width:8px;
  }

  /* POWER TEMPLATE */
  .math-power{
    display:inline-flex;
    align-items:flex-start;
    vertical-align:baseline;
  }
  .math-power-base{
    display:inline-flex;
    align-items:baseline;
  }
  .math-power-exp{
    font-size:10px;
    line-height:1;
    margin-top:-6px;
    min-width:6px;
    padding:0 1px;
  }

  /* LOG BASE TEMPLATE */
  .math-log-base-template{
    display:inline-flex;
    align-items:baseline;
  }
  .math-log-sub{
    font-size:9px;
    line-height:1;
    margin-bottom:-4px;
    min-width:6px;
    padding:0 1px;
  }
  .math-log-arg{
    display:inline-flex;
    align-items:baseline;
    min-width:6px;
  }

  /* INTEGRAL TEMPLATE */
  .math-integral-template{
    display:inline-flex;
    align-items:center;
    vertical-align:middle;
    margin:0 2px;
  }
  .math-int-sym-col{
    display:inline-flex;
    flex-direction:column;
    align-items:center;
    margin-right:1px;
  }
  .math-int-upper{
    font-size:9px;
    line-height:1;
    min-height:9px;
    min-width:6px;
    padding:0 1px;
  }
  .math-int-sym{
    font-size:20px;
    line-height:15px;
  }
  .math-int-lower{
    font-size:9px;
    line-height:1;
    min-height:9px;
    min-width:6px;
    padding:0 1px;
  }
  .math-int-body{
    display:inline-flex;
    align-items:baseline;
    min-width:8px;
    margin:0 1px;
  }
  .math-int-dx{
    font-size:14px;
    line-height:1;
    margin-left:1px;
  }
  .top-row{
    display:grid;
    grid-template-columns:30px 30px 86px 30px 30px;
    align-items:end;
    justify-content:space-between;
    gap:6px;
    margin:0 1px 4px;
  }
  .bwc{
    width:30px;
    display:flex;
    flex-direction:column;
    align-items:center;
  }
  .lbl{
    width:100%;
    height:11px;
    text-align:center;
    white-space:nowrap;
    font-size:6px;
    line-height:10px;
    font-weight:700;
  }
  .ly{color:var(--yellow);}
  .lp{color:var(--pink);}
  .lc{color:var(--cyan);}
  .lg{color:#c8c8c8;}

  .bc{
    width:27px;height:27px;
    border:0;border-radius:50%;
    background:linear-gradient(180deg,#858587,#69696b);
    color:#fff;
    font-size:7px;
    font-weight:700;
    box-shadow:0 2px 0 #151516,0 3px 6px rgba(0,0,0,.25);
    cursor:pointer;
  }
  .bc:active{transform:translateY(1px);box-shadow:0 1px 0 #151516;}

  /* ── CLASSWIZ-STYLE D-PAD ──
     One continuous rounded control; no clip-paths, so the edges don't look chopped. */
  .dpo{
    width:86px;height:67px;
    display:flex;
    align-items:flex-end;
    justify-content:center;
  }
  .dpad{
    width:82px;
    height:62px;
    position:relative;
    filter:drop-shadow(0 2px 0 #111) drop-shadow(0 3px 3px rgba(0,0,0,.22));
  }
  .dpad-ring{
    position:absolute;
    inset:2px 0;
    border-radius:46% 46% 44% 44%;
    background:linear-gradient(180deg,#606063,#454548);
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,.09),
      inset 0 0 0 1px #1a1a1b;
  }
  .dp{
    position:absolute;
    z-index:2;
    border:0;
    padding:0;
    cursor:pointer;
    background:transparent;
    color:#d8d8d8;
    font-size:9px;
    line-height:1;
  }
  .dp:hover{background:rgba(255,255,255,.035);}
  .dp:active{transform:translateY(1px);}

  .dp-u{
    left:25px;top:2px;
    width:32px;height:22px;
    border-radius:16px 16px 5px 5px;
  }
  .dp-d{
    left:25px;bottom:2px;
    width:32px;height:22px;
    border-radius:5px 5px 16px 16px;
  }
  .dp-l{
    left:2px;top:20px;
    width:29px;height:23px;
    border-radius:16px 5px 5px 16px;
  }
  .dp-r{
    right:2px;top:20px;
    width:29px;height:23px;
    border-radius:5px 16px 16px 5px;
  }
  .dp-c{
    left:29px;top:21px;
    width:24px;height:21px;
    background:transparent;
    border:0;
    box-shadow:none;
  }

  /* Clean continuous ClassWiz D-pad: no center square and no X-shaped grooves. */
  .dpad::before,
  .dpad::after{
    content:none;
    display:none;
  }

  /* ── BUTTON GRID ── */
  .btns{display:flex;flex-direction:column;gap:3px;}
  .row{display:flex;gap:3px;align-items:flex-end;}
  .bw{
    min-width:0;
    flex:1;
    display:flex;
    flex-direction:column;
    align-items:center;
  }

  .b{
    width:100%;
    height:27px;
    border:0;
    border-radius:4px;
    background:linear-gradient(180deg,#222225,#121214);
    color:#fff;
    font-size:10px;
    font-weight:700;
    cursor:pointer;
    box-shadow:0 2px 0 #050506,0 3px 5px rgba(0,0,0,.25);
  }
  .b:active{transform:translateY(1px);box-shadow:0 1px 0 #050506;}
  /* ── LOWER KEYPAD ──
     Chunkier, squarer and brighter than the scientific keys, like the OG unit. */
  .numeric-row{
    gap:6px;
    margin-top:1px;
  }
  .numeric-row .bw{
    flex:1 1 0;
  }
  .numeric-row .lbl{
    height:10px;
    line-height:9px;
    font-size:5.6px;
  }
  .bn,
  .bop,
  .bdel,
  .bac{
    height:34px;
    border-radius:3px;
  }
  .bn{
    font-family:Arial, Helvetica, sans-serif;
    font-size:18px;
    font-weight:800;
    color:#121212;
    background:linear-gradient(180deg,#fbfbfa 0%,#ececea 68%,#dededb 100%);
    box-shadow:
      0 2px 0 #8e8e8b,
      0 3px 4px rgba(0,0,0,.28),
      inset 0 1px 0 rgba(255,255,255,.9);
  }
  .bop{
    font-family:Arial, Helvetica, sans-serif;
    font-size:17px;
    font-weight:500;
    color:#111;
    background:linear-gradient(180deg,#f5f5f4 0%,#e5e5e2 70%,#d7d7d4 100%);
    box-shadow:
      0 2px 0 #898986,
      0 3px 4px rgba(0,0,0,.28),
      inset 0 1px 0 rgba(255,255,255,.85);
  }
  .bdel,.bac{
    background:linear-gradient(180deg,#3d8df5 0%,#216edb 70%,#175ec7 100%);
    color:#fff;
    font-size:13px;
    font-weight:800;
    box-shadow:
      0 2px 0 #0b3e93,
      0 3px 4px rgba(0,0,0,.3),
      inset 0 1px 0 rgba(255,255,255,.2);
  }
  .numeric-row button:active{
    transform:translateY(1px);
  }
  .scientific-wide{
    font-size:11px !important;
    letter-spacing:-.2px;
  }

  .special-row{
    display:grid;
    grid-template-columns:1.26fr 1.26fr .45fr .88fr .88fr;
    gap:4px;
    align-items:end;
  }

  .small-note{
    font-size:5px;
    line-height:1;
    margin-top:1px;
  }
  .accent-y{color:var(--yellow);}
  .accent-p{color:var(--pink);}
  .accent-c{color:var(--cyan);}

  /* Calculator-style mathematical glyphs instead of text approximations */
  .math-key{
    font-family:"Times New Roman", Cambria, serif;
    font-weight:700;
    font-size:15px;
  }
  .frac-glyph{
    display:inline-grid;
    grid-template-rows:7px 1px 7px;
    width:15px;
    height:17px;
    vertical-align:middle;
    align-items:center;
    justify-items:center;
    line-height:1;
  }
  .frac-glyph .box{
    width:6px;height:5px;
    border:1px solid currentColor;
  }
  .frac-glyph .bar{
    width:15px;height:1px;
    background:currentColor;
  }
  .root-glyph{
    display:inline-flex;
    align-items:flex-start;
    height:17px;
    line-height:1;
  }
  .root-sign{
    font-family:"Times New Roman", Cambria, serif;
    font-size:19px;
    line-height:16px;
    transform:scaleX(.92);
    transform-origin:right center;
  }
  .root-box{
    width:11px;height:9px;
    border-top:1px solid currentColor;
    margin-top:2px;
    position:relative;
  }
  .root-box:after{
    content:"";
    position:absolute;
    width:6px;height:6px;
    border:1px solid currentColor;
    left:2px;top:3px;
  }


  .lcd-bottom{
    display:flex;
    justify-content:space-between;
    align-items:flex-end;
    margin-top:2px;
  }
  .lcd-mode-name{
    font-size:17px;
    line-height:1;
    white-space:nowrap;
  }
  .lcd-indicators{
    min-width:42px;
    text-align:right;
    font-size:8px;
    font-weight:700;
  }
  .lcd-cursor{
    display:inline-block;
    width:1px;
    height:17px;
    margin:0 1px;
    vertical-align:-2px;
    background:currentColor;
    animation:lcd-cursor-blink 1s steps(1,end) infinite;
  }
  @keyframes lcd-cursor-blink{50%{opacity:0;}}
  #shiftIndicator::after{content:"";}
  #alphaIndicator::after{content:"";}
  body.shift-on #shiftIndicator::after{content:"S"; margin-right:4px;}
  body.alpha-on #alphaIndicator::after{content:"A";}
  .legend-pair{
    display:flex;
    align-items:center;
    justify-content:center;
    gap:2px;
    width:100%;
  }
  .lbl .alpha-mark{color:var(--pink);}
  .lbl .base-mark{color:var(--cyan);}
  .lbl .shift-mark{color:var(--yellow);}


  /* ── More faithful fx-991EX key glyphs ── */
  .glyph{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    color:currentColor;
    line-height:1;
  }

  /* Integral template: upper box, integral, lower box, input box */
  .int-glyph{
    position:relative;
    width:23px;
    height:15px;
    font-family:"Times New Roman", Cambria, serif;
    transform:translateY(1px);
  }
  .int-glyph .int-sign{
    position:absolute;
    left:7px; top:0;
    font-size:18px;
    line-height:14px;
  }
  .int-glyph .ibox{
    position:absolute;
    width:4px; height:4px;
    border:1px solid currentColor;
  }
  .int-glyph .ibox.top{left:1px;top:0;}
  .int-glyph .ibox.bottom{left:1px;bottom:0;}
  .int-glyph .ibox.arg{right:0;top:5px;width:6px;height:5px;}

  /* Fraction template */
  .frac-glyph{
    display:inline-grid;
    grid-template-rows:6px 1px 6px;
    width:18px;
    height:15px;
    align-items:center;
    justify-items:center;
    line-height:1;
  }
  .frac-glyph .box{
    width:7px;
    height:5px;
    border:1px solid currentColor;
  }
  .frac-glyph .bar{
    width:17px;
    height:1px;
    background:currentColor;
  }

  /* Radical with an editable box under the vinculum */
  .root-glyph{
    position:relative;
    display:inline-block;
    width:22px;
    height:15px;
    transform:translateY(1px);
  }
  /* Draw the radical from lines instead of relying on a font glyph. */
  .root-glyph .root-hook{
    position:absolute;
    left:1px;
    top:7px;
    width:5px;
    height:6px;
    border-left:1.4px solid currentColor;
    border-bottom:1.4px solid currentColor;
    transform:skewX(-18deg) rotate(-7deg);
    transform-origin:left bottom;
  }
  .root-glyph .root-stem{
    position:absolute;
    left:5px;
    top:3px;
    width:7px;
    height:10px;
    border-left:1.4px solid currentColor;
    transform:rotate(24deg);
    transform-origin:left bottom;
  }
  .root-glyph .radicand{
    position:absolute;
    left:10px;
    top:2px;
    width:11px;
    height:10px;
    border-top:1.4px solid currentColor;
  }
  .root-glyph .radicand:after{
    content:"";
    position:absolute;
    left:2px;
    top:3px;
    width:6px;
    height:5px;
    border:1px solid currentColor;
  }

  /* x raised to an editable exponent box */
  .pow-glyph{
    position:relative;
    width:25px;
    height:17px;
    font-family:"Times New Roman", Cambria, serif;
    font-style:italic;
  }
  .pow-glyph .x{
    position:absolute;
    left:3px; bottom:0;
    font-size:17px;
  }
  .pow-glyph .expbox{
    position:absolute;
    right:2px; top:0;
    width:8px; height:7px;
    border:1px solid currentColor;
  }

  /* log with small editable base box, matching the physical key */
  .logbase-glyph{
    display:inline-flex;
    align-items:flex-end;
    font-family:Arial, sans-serif;
    font-weight:700;
    font-size:11px;
    height:15px;
  }
  .logbase-glyph .basebox{
    width:6px; height:6px;
    border:1px solid currentColor;
    margin-left:1px;
    margin-bottom:0;
  }

  /* mixed fraction icon above fraction key */
  .mixed-frac-legend{
    display:inline-flex;
    align-items:center;
    gap:1px;
    transform:scale(.86);
    transform-origin:center;
  }
  .mixed-frac-legend .whole{
    width:4px; height:5px; border:1px solid currentColor;
  }
  .mini-frac{
    display:inline-grid;
    grid-template-rows:4px 1px 4px;
    width:9px; height:9px;
    justify-items:center;
    align-items:center;
  }
  .mini-frac i{
    display:block;
    width:4px; height:3px; border:1px solid currentColor;
  }
  .mini-frac b{
    display:block;
    width:8px; height:1px; background:currentColor;
  }

  /* x-th-root legend above the power key */
  .xroot-legend{
    font-family:"Times New Roman", Cambria, serif;
    font-size:8px;
    white-space:nowrap;
  }

  /* ENG's two-way engineering-arrow legend */
  .eng-arrows{
    display:inline-flex;
    gap:1px;
    font-size:8px;
    font-weight:900;
  }
  .eng-arrows .left{color:#8d6fd4;}
  .eng-arrows .right{color:var(--yellow);}

  /* S↔D legend is a composite on the original */
  .sd-legend{
    display:inline-flex;
    align-items:center;
    gap:1px;
    font-size:5px;
    white-space:nowrap;
  }
  .sd-legend .shift-mark{font-size:5px;}
  .sd-legend .alpha-mark{font-size:6px;}

  .key.math-template{
    font-family:"Times New Roman", Cambria, serif;
    font-weight:700;
    overflow:hidden;
    display:flex;
    align-items:center;
    justify-content:center;
  }
  .b.math-template{
    overflow:hidden;
    display:flex;
    align-items:center;
    justify-content:center;
  }


  /* Top controls: all four round buttons share the D-pad centerline. */
  .top-controls{
    display:flex;
    flex-direction:row;
    align-items:center;
    justify-content:space-between;
    gap:4px;
  }
  .top-controls .bwc{
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    height:67px;
    gap:1px;
  }
  .top-controls .bwc .lbl{
    height:8px;
    min-height:8px;
    line-height:8px;
    margin:0 0 1px 0;
    padding:0;
  }
  .top-controls .bwc .bc{
    align-self:center;
    margin:0;
  }
  .top-controls .dpo,
  .top-controls .dpad{
    align-self:center;
  }

  /* subtle lower-body taper illusion */
  .bottom-pad{height:1px;}

  /* KaTeX scoped to LCD only — outer LCD keeps Casio ClassWiz TTF; KaTeX fonts apply inside child wrapper only */
  #lcdDisplay .katex-lcd-wrap { display: inline-block; max-width: 100%; overflow-x: auto; overflow-y: hidden; }
  #lcdDisplay .katex-lcd-wrap.katex-block { display: block; text-align: center; }
  #lcdDisplay .katex { color: inherit; background: transparent; font-size: 1.02em; white-space: nowrap; }
  #lcdDisplay .katex-display { margin: 0; padding: 0; }
  #lcdDisplay .katex-display > .katex { white-space: nowrap; }

```

## Inline `style=""` attributes (kept in place in `html.md`)

Listed in source order, verbatim. Nothing was rewritten, merged, or deduplicated.

| # | frontend.html line | declaration | host |
|---|-------------------|-------------|------|
| 1 | 1595 | ``style="display:none;"`` | HTML markup |
| 2 | 1596 | ``style="display:none;"`` | HTML markup |
| 3 | 1635 | ``style="display:none;"`` | HTML markup |
| 4 | 1636 | ``style="display:none;"`` | HTML markup |
| 5 | 1637 | ``style="display:none;"`` | HTML markup |
| 6 | 1638 | ``style="display:none;"`` | HTML markup |
| 7 | 1639 | ``style="display:none;"`` | HTML markup |
| 8 | 1646 | ``style="display:none; text-align:center;"`` | HTML markup |
| 9 | 1647 | ``style="font-weight:700; font-size:10px; margin-bottom:2px;"`` | HTML markup |
| 10 | 1648 | ``style="display:flex; justify-content:center;"`` | HTML markup |
| 11 | 1649 | ``style="font-size:8px; margin-top:2px; word-break:break-all;"`` | HTML markup |
| 12 | 1651 | ``style="display:none;"`` | HTML markup |
| 13 | 1656 | ``style="display:none;"`` | HTML markup |
| 14 | 1664 | ``style="display:none;"`` | HTML markup |
| 15 | 1669 | ``style="display:none;"`` | HTML markup |
| 16 | 1678 | ``style="display:none;"`` | HTML markup |
| 17 | 1701 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 18 | 1715 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 19 | 1729 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 20 | 1743 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 21 | 1756 | ``style="display:none;"`` | HTML markup |
| 22 | 1757 | ``style="display:none;"`` | HTML markup |
| 23 | 1760 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 24 | 1774 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 25 | 1788 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 26 | 1794 | ``style="flex:1;display:flex;flex-direction:column;justify-content:space-between;"`` | HTML markup |
| 27 | 1800 | ``style="flex:1;display:flex;flex-direction:column;"`` | HTML markup |
| 28 | 1804 | ``style="flex:1;display:flex;flex-direction:column;"`` | HTML markup |
| 29 | 1818 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 30 | 1832 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 31 | 1845 | ``style="flex:1; display:flex; flex-direction:column; justify-content:space-between;"`` | HTML markup |
| 32 | 1925 | ``style="display:block; overflow:visible;"`` | HTML markup |
| 33 | 2003 | ``style="font-size:14px;font-weight:600"`` | HTML markup |
| 34 | 5275 | ``style="font-size:9px;"`` | inside a JavaScript template literal |
| 35 | 5532 | ``style="margin-top:8px;"`` | inside a JavaScript template literal |
