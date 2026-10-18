"""Phase D D3: keypad coverage inventory.

Drives the real `file://` keypad for every battery case and records, per case:

  case_id, intended internal expression, keypad sequence (or none),
  constructed getExpr(), whether it matches, why not when it does not, and an
  evidence reference.

This is INVENTORY ONLY. It never changes keypad behaviour, and it never
invents a successful observation: a case that cannot be constructed is
recorded as unconstructable with a reason.

Usage:
  python audit/tools/build_keypad_inventory.py --frontend frontend.html \
         --out audit/evidence/phase-d-20261015/keypad_inventory.json
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CHROMIUM = r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"

CASES_JSON = os.path.join(REPO, "audit", "data", "cases.json")

# Sequences for cases that had none in Phase C. Derived from the keys actually
# exposed by the keypad (51 unique data-key values) and read back from
# getExpr(), never assumed. A sequence that does not reproduce the intended
# expression is kept in the inventory as a FAILED attempt, with the observed
# getExpr() as evidence -- that is exactly the kind of finding this tool exists
# to surface.
DERIVED_SEQUENCES = {
    "17": ["sqrt", "1", "6", "equals"],
    "18": ["sqrt", "9", "plus", "1", "6", "equals"],
    "19": ["5", "shift", "optn", "dpad_center", "dpad_down", "equals"],
    "20": ["1", "0", "divide", "4", "equals"],
    "21": ["0", "decimal", "1", "plus", "0", "decimal", "2", "equals"],
    "22": ["1", "0", "0", "multiply", "1", "decimal", "0", "5", "square", "equals"],
    "23": ["left_paren", "3", "minus", "1", "right_paren", "divide",
           "left_paren", "9", "minus", "3", "right_paren", "equals"],
    "25": ["1", "divide", "2", "plus", "1", "divide", "3", "equals"],
    "26": ["3", "decimal", "5", "multiply", "2", "equals"],
    "27": ["9", "minus", "3", "multiply", "2", "plus", "1", "equals"],
    "28": ["sin", "3", "0", "equals"],
    "29": ["log", "1", "0", "0", "equals"],
    "30": ["2", "shift", "optn", "dpad_center", "dpad_down", "equals"],
    "32": ["9", "9", "9", "9", "9", "multiply", "9", "9", "9", "9", "9", "equals"],
    "33": ["7", "plus", "left_paren", "negate", "3", "right_paren",
           "left_paren", "negate", "2", "right_paren", "equals"],
    "34": ["2", "multiply", "left_paren", "3", "plus", "left_paren", "4",
           "minus", "1", "right_paren", "multiply", "2", "right_paren", "equals"],
}


def load_cases():
    with open(CASES_JSON, encoding="utf-8") as f:
        return json.load(f)["cases"]


def available_keys(page):
    return page.eval_on_selector_all(
        "[data-key]", "els => Array.from(new Set(els.map(e => e.dataset.key)))")


def probe(frontend, sequences, cases):
    """Drive each sequence once; return id -> observation."""
    from playwright.sync_api import sync_playwright

    url = "file:///" + frontend.replace("\\", "/")
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM)
        page = browser.new_page()
        page.goto(url, wait_until="load")
        keys_present = set(available_keys(page))
        for cid, keys in sequences.items():
            if keys is None:
                out[cid] = {"getExpr": None, "keys_not_found": None,
                            "lcd": None, "reason": "no keypad sequence defined"}
                continue
            missing = [k for k in keys if k not in keys_present]
            if missing:
                out[cid] = {"getExpr": None, "keys_not_found": missing,
                            "lcd": None,
                            "reason": "keypad exposes no control for: %s"
                                      % ",".join(missing)}
                continue
            page.evaluate(
                "() => { if (typeof hardResetExpr === 'function') hardResetExpr(); "
                "else if (typeof resetExpr === 'function') resetExpr(); }")
            page.wait_for_timeout(50)
            for k in keys:
                page.locator('[data-key="%s"]' % k).click()
            built = page.evaluate(
                "() => (typeof getExpr === 'function') ? getExpr() : null")
            page.wait_for_timeout(350)
            lcd = " ".join((page.locator(".lcd").inner_text() or "").split())
            out[cid] = {"getExpr": built, "keys_not_found": [], "lcd": lcd,
                        "reason": ""}
        browser.close()
    return out, sorted(keys_present)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frontend", default=os.path.join(REPO, "frontend.html"))
    ap.add_argument("--out", default=os.path.join(
        REPO, "audit", "evidence", "phase-d-20261015", "keypad_inventory.json"))
    args = ap.parse_args()

    cases = load_cases()
    seqs = {}
    with open(CASES_JSON, encoding="utf-8") as f:
        doc = json.load(f)
    for k, v in doc["keypad_sequences"].items():
        if not k.startswith("_"):
            seqs[k] = v
    for k, v in DERIVED_SEQUENCES.items():
        seqs.setdefault(k, v)

    print("driving %d keypad sequences" % len(seqs))
    observed, keys_present = probe(args.frontend, seqs, cases)

    rows = []
    for c in cases:
        cid = str(c["id"])
        intended = c["internal_expr"]
        o = observed.get(cid)
        entry = {
            "case_id": c["id"],
            "ascii": c["ascii"],
            "intended_internal_expr": intended,
            "keypad_sequence": seqs.get(cid),
            "sequence_origin": ("battery" if cid in doc["keypad_sequences"]
                                else ("derived_d3" if cid in DERIVED_SEQUENCES
                                      else None)),
            "constructed_getExpr": None if o is None else o["getExpr"],
            "keys_not_found": None if o is None else o["keys_not_found"],
            "lcd": None if o is None else o["lcd"],
            "valid": False,
            "reason": "",
            "evidence": "audit/evidence/phase-d-20261015/keypad_inventory.json",
        }
        if intended is None:
            entry["reason"] = "case specification is unresolved"
        elif o is None:
            entry["reason"] = "no sequence attempted"
        elif o["keys_not_found"]:
            entry["reason"] = o["reason"]
        elif o["getExpr"] is None:
            entry["reason"] = "getExpr() unavailable on the page"
        elif o["getExpr"] != intended:
            entry["reason"] = ("keypad constructed %r, intended %r"
                               % (o["getExpr"], intended))
        else:
            entry["valid"] = True
        rows.append(entry)

    payload = {
        "frontend": os.path.relpath(args.frontend, REPO).replace("\\", "/"),
        "chromium": CHROMIUM,
        "keys_exposed_by_keypad": keys_present,
        "key_count": len(keys_present),
        "summary": {
            "cases": len(rows),
            "constructable": sum(1 for r in rows if r["valid"]),
            "not_constructable": sum(1 for r in rows if not r["valid"]),
        },
        "rows": rows,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # human-readable companion
    md = ["# Keypad coverage inventory", "",
          "Keypad exposes %d unique controls." % len(keys_present), "",
          "constructable=%d  not_constructable=%d  total=%d"
          % (payload["summary"]["constructable"],
             payload["summary"]["not_constructable"], payload["summary"]["cases"]),
          "",
          "| # | intended | constructed | valid | reason |",
          "|---|---|---|---|---|"]
    for r in rows:
        md.append("| %d | `%s` | `%s` | %s | %s |"
                  % (r["case_id"], r["intended_internal_expr"] or "-",
                     r["constructed_getExpr"] if r["constructed_getExpr"] is not None else "-",
                     "yes" if r["valid"] else "no", r["reason"] or "-"))
    md_path = args.out.replace(".json", ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print("constructable=%d not_constructable=%d total=%d"
          % (payload["summary"]["constructable"],
             payload["summary"]["not_constructable"], payload["summary"]["cases"]))
    print("written to %s and %s" % (args.out, md_path))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()