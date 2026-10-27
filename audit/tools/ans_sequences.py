"""Phase D D5: stateful Ans sequence coverage.

The 46-case battery is single-expression and cannot express Ans chaining, which
is case 35's whole problem. This collector runs a SEQUENCE of expressions
against one live calculator state and records the state after every step, so
"what happened to Ans?" becomes an observation rather than a guess.

No calculator semantics are changed. Nothing here asserts a contract: the
divide-by-zero sequences are deliberately left with an unresolved expectation,
because audit/docs/divzero_contract.md has no approved answer for whether Ans
is preserved, cleared or updated after an error.

Usage:
  python audit/tools/ans_sequences.py --out audit/evidence/phase-d-20261015
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
CHROMIUM = r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
FRONTEND = os.path.join(REPO, "frontend.html")

# Each sequence is a list of steps. A step is
#   {"expr": <internal template string>, "note": ...}      evaluate this
#   {"keys": [<data-key>...], "note": ...}                 drive the keypad
#   {"check_ans": True}                                    observe Ans only
#
# `expected_ans_after_error` is None wherever the contract is undecided. Those
# sequences report what was observed and are explicitly NOT scored.

SEQUENCES = [
    {
        "id": "ans_basic",
        "title": "harmless known sequence: 5, then Ans+2",
        "why": "establishes the baseline Ans behaviour that everything else "
               "is compared against",
        "contract": "approved_by_source",
        "steps": [
            {"keys": ["5", "equals"], "note": "compute 5"},
            {"keys": ["ans", "plus", "2", "equals"],
             "note": "Ans+2 -- 7 if Ans is still 5"},
        ],
        "expected_final": 7,
        "expected_ans": None,
    },
    {
        "id": "ans_chain",
        "title": "Ans chaining as battery case 35 intends",
        "why": "case 35 states '5+5 = then x2 =' expecting 20, but "
               "raw/context.md:239 records that a previous agent's case 35 "
               "never tested this at all",
        "contract": "contested_by_raw_context_239",
        "steps": [
            {"keys": ["5", "plus", "5", "equals"], "note": "compute 10"},
            {"keys": ["ans", "multiply", "2", "equals"],
             "note": "Ans should be 10, so 20"},
        ],
        "expected_final": None,
        "expected_ans": None,
        "note": "EXPECTATION UNRESOLVED. The arithmetic is unambiguous (10*2=20) "
                "but no keypad sequence in this repository is documented to "
                "produce it, and the battery row is contested. Observed "
                "behaviour is recorded without being scored.",
    },
    {
        "id": "divzero_then_ans",
        "title": "divide by zero, then use Ans",
        "why": "proves whether a failed calculation overwrites Ans. "
               "raw/september_handover.md:1403 states Ans must be preserved; "
               "audit/docs/divzero_contract.md records that this is undecided.",
        "contract": "BLOCKED_BY_GATE_B",
        "steps": [
            {"keys": ["1", "0", "equals"], "note": "compute 10"},
            {"keys": ["1", "divide", "0", "equals"],
             "note": "divide by zero"},
            {"check_ans": True, "note": "observe Ans"},
            {"keys": ["ans", "plus", "1", "equals"],
             "note": "Ans+1 -- 11 if Ans was preserved, something else if not"},
        ],
        "expected_final": None,
        "expected_ans": None,
        "note": "EXPECTATION UNRESOLVED by Gate B. Recorded as an observation.",
    },
    {
        "id": "usable_after_divzero",
        "title": "is the calculator still usable after a divide by zero",
        "why": "raw/context.md:351 requires that a non-maths failure show "
               "System ERROR, which implies recovery; whether the keypad still "
               "accepts input afterwards is unverified",
        "contract": "BLOCKED_BY_GATE_B",
        "steps": [
            {"keys": ["1", "divide", "0", "equals"], "note": "divide by zero"},
            {"keys": ["2", "plus", "2", "equals"],
             "note": "2+2 must work if the calculator recovered"},
        ],
        "expected_final": None,
        "expected_ans": None,
        "note": "EXPECTATION UNRESOLVED by Gate B, even though the arithmetic "
                "(2+2=4) is uncontroversial. The unresolved part is whether the "
                "next calculation SHOULD start clean after an error, which is "
                "precisely what the divzero_then_ans sequence shows the server "
                "failing to do. Recording the observation without scoring it.",
    },
]


def normalize(s):
    if s is None:
        return None
    s = (s.replace("\u2212", "-").replace("\u00d7", "*").replace("\u00f7", "/")
          .replace("\u00a0", " ").replace("\u200b", "").replace("\u221a", "sqrt"))
    s = " ".join(s.split())
    return s.split(" ")[-1] if s else None


def run_browser(out_dir):
    from playwright.sync_api import sync_playwright
    url = "file:///" + FRONTEND.replace("\\", "/")
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM)
        page = browser.new_page()
        console, pageerr = [], []
        page.on("console", lambda m: console.append("%s: %s" % (m.type, m.text))
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: pageerr.append(str(e)))
        page.goto(url, wait_until="load")

        for seq in SEQUENCES:
            page.evaluate(
                "() => { if (typeof hardResetExpr === 'function') hardResetExpr(); "
                "else if (typeof resetExpr === 'function') resetExpr(); }")
            page.evaluate("() => { if (typeof localAns !== 'undefined') localAns = '0'; }")
            page.wait_for_timeout(60)
            console.clear(); pageerr.clear()
            steps = []
            for step in seq["steps"]:
                if "keys" in step:
                    missing = []
                    for k in step["keys"]:
                        loc = page.locator('[data-key="%s"]' % k)
                        if loc.count() == 0:
                            missing.append(k)
                            continue
                        loc.click()
                elif "expr" in step:
                    # Submit through the real bridge, which is what the keypad's
                    # equals path ultimately calls.
                    page.evaluate(
                        "(e) => { try { localAns = String(localEvaluate(e)); } "
                        "catch (err) { localAns = '0'; window.__ansErr = "
                        "String(err && err.message || err); } }", step["expr"])
                    page.wait_for_timeout(250)
                page.wait_for_timeout(350)
                state = page.evaluate(
                    "() => (typeof appState !== 'undefined') "
                    "? {result: appState.result, error: appState.error, "
                    "  state: appState.state, localAns: (typeof localAns !== "
                    "'undefined') ? localAns : null} : null")
                lcd = " ".join((page.locator(".lcd").inner_text() or "").split())
                steps.append({
                    "note": step.get("note", ""),
                    "keys": step.get("keys"),
                    "expr": step.get("expr"),
                    "getExpr": page.evaluate(
                        "() => (typeof getExpr === 'function') ? getExpr() : null"),
                    "lcd": lcd,
                    "appState_result": None if not state else state.get("result"),
                    "appState_error": None if not state else state.get("error"),
                    "appState_state": None if not state else state.get("state"),
                    "localAns": None if not state else state.get("localAns"),
                    "keys_not_found": missing,
                })
            results.append({
                "id": seq["id"], "title": seq["title"], "why": seq["why"],
                "contract": seq["contract"],
                "note": seq.get("note"),
                "expected_final": seq["expected_final"],
                "expected_ans": seq["expected_ans"],
                "observed_final": steps[-1]["appState_result"] if steps else None,
                "observed_final_error": steps[-1]["appState_error"] if steps else None,
                "observed_ans": (steps[-1]["localAns"] if steps else None),
                "console_errors": list(console),
                "page_errors": list(pageerr),
                "steps": steps,
                "path": "browser_file",
            })
        browser.close()
    return results


def run_server(out_dir):
    """Run the same Ans sequences through the live server, so the Phase C claim
    that Ans handling DIVERGES between paths is tested rather than assumed.

    Every step is sent as individual keypresses and the server's own
    `expression` field is recorded after each one. That matters: the first
    version of this harness re-sent `equals` after each step, which silently
    re-evaluated the previous expression and produced a misleading "1.1".
    """
    sys.path.insert(0, os.path.join(REPO, "audit", "tools"))
    from collectors import ServerProcess

    results = []
    with ServerProcess() as srv:
        for seq in SEQUENCES:
            srv.post("/api/reset", {"target": "all"})
            steps = []
            for step in seq["steps"]:
                keys = step.get("keys")
                if keys is None:
                    steps.append({
                        "note": step.get("note", ""), "keys": None,
                        "expr": step.get("expr"), "http_status": None,
                        "expression": None, "display": None, "result": None,
                        "error": None, "state": None, "ans": None,
                        "observation_only": True,
                    })
                    continue
                # send each control in turn, recording the buffer after each
                last = None
                for k in keys:
                    last = srv.post("/api/key", {"key": k})
                st, body = last
                steps.append({
                    "note": step.get("note", ""), "keys": list(keys),
                    "expr": None,
                    "http_status": st,
                    "expression": body.get("expression"),
                    "display": body.get("display"),
                    "result": body.get("result"),
                    "error": body.get("error"),
                    "state": body.get("state"),
                    "ans": body.get("ans"),
                })
            real = [s for s in steps if not s.get("observation_only")]
            last = real[-1] if real else {}
            results.append({
                "id": seq["id"], "title": seq["title"], "why": seq["why"],
                "contract": seq["contract"],
                "note": seq.get("note"),
                "expected_final": seq["expected_final"],
                "expected_ans": seq["expected_ans"],
                "observed_final": last.get("result"),
                "observed_final_error": last.get("error"),
                "observed_ans": last.get("ans"),
                "steps": steps,
                "path": "http",
            })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPO, "audit", "evidence", "phase-d-20261015"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    results = run_browser(args.out)
    server_results = run_server(args.out)
    cross = {}
    for b, s in zip(results, server_results):
        cross[b["id"]] = {
            "contract": b["contract"],
            "browser_final": b["observed_final"],
            "browser_error": b["observed_final_error"],
            "browser_ans": b["observed_ans"],
            "server_final": s["observed_final"],
            "server_error": s["observed_final_error"],
            "server_ans": s["observed_ans"],
            "paths_agree": (str(b["observed_final"]) == str(s["observed_final"])),
            "ans_agrees": (str(b["observed_ans"]) == str(s["observed_ans"])),
        }
    path = os.path.join(args.out, "ans_sequences.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"chromium": CHROMIUM, "sequences": results,
                   "server_sequences": server_results,
                   "cross_path": cross}, f, indent=2, ensure_ascii=False)

    md = ["# Stateful Ans sequences", "",
          "Each step records the expression, getExpr(), LCD, appState and Ans.",
          "`contract` states whether the expectation is settled; sequences whose",
          "contract is blocked are reported as observations, NOT scored.", ""]
    for r in results:
        md.append("## %s - %s" % (r["id"], r["title"]))
        md.append("")
        md.append("contract: `%s`" % r["contract"])
        if r.get("note"):
            md.append("")
            md.append("> %s" % r["note"])
        md.append("")
        md.append("| # | step | getExpr | LCD | result | error | Ans |")
        md.append("|---|---|---|---|---|---|---|")
        for i, s in enumerate(r["steps"], 1):
            md.append("| %d | %s | `%s` | %s | %s | %s | %s |"
                      % (i, s["note"], s["getExpr"], s["lcd"],
                         s["appState_result"], s["appState_error"], s["localAns"]))
        md.append("")
        md.append("expected_final=%s  observed_final=%s  observed_ans=%s"
                  % (r["expected_final"], r["observed_final"], r["observed_ans"]))
        md.append("")
    md.append("## Cross-path comparison")
    md.append("")
    md.append("Tests the Phase C claim that Ans handling diverges between paths.")
    md.append("")
    md.append("| sequence | contract | browser final | server final | agree | "
              "browser Ans | server Ans | Ans agree |")
    md.append("|---|---|---|---|---|---|---|---|")
    for sid, c in cross.items():
        md.append("| %s | %s | %s | %s | %s | %s | %s | %s |"
                  % (sid, c["contract"], c["browser_final"], c["server_final"],
                     c["paths_agree"], c["browser_ans"], c["server_ans"],
                     c["ans_agrees"]))
    md.append("")
    md_path = os.path.join(args.out, "ans_sequences.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    for r in results:
        print("%-22s contract=%-32s observed_final=%s ans=%s"
              % (r["id"], r["contract"], r["observed_final"], r["observed_ans"]))
    print("written to %s and %s" % (path, md_path))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()