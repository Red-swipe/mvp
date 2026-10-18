"""Cross-path expression comparator for Mentis ClassWiz.

Runs all 46 battery cases through all five collectors, canonicalises every
observation and emits:
  - results.json          raw observations, nothing discarded
  - divergence_matrix.md  readable matrix, cases x collectors
  - divergence_matrix.csv machine-readable matrix

Usage:  python audit/tools/run_comparator.py [--out DIR]
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

import collectors as C  # noqa: E402

CASES_PATH = os.path.join(REPO, "audit", "data", "cases.json")
PATHS = ["engine", "safe_eval", "node_bridge", "http", "browser_file"]
TOL = 1e-6

# Symbols the divisor-by-zero contract may legitimately use. Sourced from
# audit/docs/divzero_contract.md -- see that file for why the set is a set.
DIVZERO_STRINGS = {"To infinity and beyonddd", "Math ERROR", "System ERROR",
                   "DIV_ZERO", "Division ERROR"}


def load_cases():
    with open(CASES_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    return doc


def judge(case, obs):
    """Turn one collector observation into a verdict against the case.

    Order matters. An unresolved SPECIFICATION outranks whatever a collector
    saw, so an undecided row can never be reported as a measured defect or as a
    silently skipped case.
    """
    if case.get("internal_expr_source") == "unresolved" and case.get("expected") is None:
        return "unresolved", (case.get("note")
                              or "case specification is unresolved")

    if obs is None:
        return "unexecuted", "no observation from this collector"
    if obs["status"] == "collector_error":
        return "collector_error", obs.get("detail", "")
    # input_build outranks a generic unexecuted so a mis-built expression is
    # never reported as merely skipped.
    if obs["error_class"] == "input_build":
        return "input_construction_failure", obs.get("detail", "")
    if obs["status"] == "unexecuted":
        return "unexecuted", obs.get("detail", "")

    expect_err = case.get("expect_error")

    if expect_err:
        if obs["is_error"]:
            txt = (obs.get("error_text") or "").strip()
            if txt in DIVZERO_STRINGS or obs.get("numeric") is None:
                return "pass", "error raised as contracted: %r" % txt
            return "fail", "error raised but unexpected text %r" % txt
        return "fail", "expected an error, got %r" % (obs.get("observed"),)

    if case.get("expected") is None:
        return "unresolved", "case expectation is unresolved in cases.json"
    if obs["is_error"]:
        return "fail", "unexpected error %r" % (obs.get("error_text"),)
    if obs.get("numeric") is None:
        return "unparseable", "output %r did not canonicalise to a number" % (obs.get("observed"),)
    if abs(obs["numeric"] - float(case["expected"])) <= TOL:
        return "pass", ""
    return "fail", "expected %r got %r" % (case["expected"], obs["numeric"])


# The complete verdict vocabulary and its meaning. Kept as data, not prose, so
# the matrix legend, the failure report and the tests cannot drift apart.
VERDICT_LEGEND = {
    "pass": ("PASS", "observation matches the declared expectation"),
    "fail": ("FAIL", "a real observation contradicts the expectation"),
    "unresolved": ("UNRES", "the specification itself is undecided; not a defect"),
    "input_construction_failure": ("INPUT", "the keypad built a different expression, "
                                          "so the calculator was never asked the question"),
    "unexecuted": ("N/A", "no observation was produced"),
    "unparseable": ("PARSE", "a real observation that is neither a number nor an error"),
    "collector_error": ("COLL", "the collector itself failed; nothing was learned"),
}

# Verdicts that indicate a defect in the calculator rather than a gap in the
# audit or an open question.
DEFECT_VERDICTS = ("fail",)


def verdict_code(v):
    return VERDICT_LEGEND.get(v, (v or "-", ""))[0]


def write_failure_report(rows, out_dir):
    """Group every non-passing cell by verdict so a reader sees the causes."""
    lines = ["# Non-passing results, grouped by classification", "",
             "A FAIL is a measured defect. INPUT is a keypad/UI defect.",
             "UNRES is an open question, not a defect. COLL and N/A are gaps in",
             "the audit itself. PARSE means the output could not be canonicalised.",
             ""]
    grouped = {}
    for r in rows:
        for p in PATHS:
            v = r[p]["verdict"]
            if v == "pass":
                continue
            grouped.setdefault(v, []).append((r, p))

    if not grouped:
        lines.append("No non-passing results.")
    for v in sorted(grouped):
        code, meaning = VERDICT_LEGEND.get(v, (v, ""))
        lines.append("## %s (%s) - %d" % (code, v, len(grouped[v])))
        lines.append("")
        lines.append(meaning)
        lines.append("")
        for r, p in grouped[v]:
            lines.append("- case %d `%s` on `%s`: %s"
                         % (r["id"], r["ascii"], p, r[p]["why"] or "(no reason)"))
        lines.append("")
    path = os.path.join(out_dir, "failure_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def summarize(rows):
    """Count a run across all collectors.

    Definitions, so the numbers cannot silently drift:
      loaded     cases present in the table and therefore reported
      executed   a collector produced a real observation (numeric or error)
      unresolved the specification itself is unresolved
      skipped    no observation at all, or the keypad built the wrong input
      failed     a real observation that contradicts the expectation

    failed/executed/unresolved/skipped are per collector-case pair, so they sum
    to loaded * len(PATHS). This is asserted in the tests.
    """
    tally = {"loaded": len(rows), "executed": 0, "unresolved": 0,
             "skipped": 0, "failed": 0}
    for r in rows:
        for p in PATHS:
            v = r[p]["verdict"]
            if v == "pass":
                tally["executed"] += 1
            elif v == "unresolved":
                tally["unresolved"] += 1
            elif v == "fail":
                tally["executed"] += 1
                tally["failed"] += 1
            elif v == "unparseable":
                tally["executed"] += 1
            else:  # unexecuted, input_construction_failure, collector_error
                tally["skipped"] += 1
    return tally


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "audit", "evidence",
                                                  "phase-c-20261015"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    doc = load_cases()
    cases = doc["cases"]
    sequences = dict(doc["keypad_sequences"])
    sequences.update(doc["keypad_sequences"].get("_extra_not_in_source_46", {}))

    print("battery: %d cases from %s" % (len(cases), CASES_PATH))
    for c in cases:
        if c["internal_expr"] is None:
            print("  case %d: UNRESOLVED internal expression (%s)"
                  % (c["id"], c.get("internal_expr_source")))

    raw = {p: [] for p in PATHS}
    for name in PATHS:
        print("collector %-12s ..." % name, flush=True)
        fn = C.COLLECTORS[name]
        try:
            if name == "browser_file":
                res = fn(cases, sequences, {c["id"]: c for c in cases})
            else:
                res = fn(cases)
        except Exception as e:  # noqa: BLE001
            res = [{"id": c["id"], "input": c["internal_expr"], "observed": None,
                    "numeric": None, "is_error": False, "error_text": None,
                    "error_class": "collector_error", "status": "collector_error",
                    "path": name, "detail": "collector raised: %r" % (e,)}
                   for c in cases]
        raw[name] = res
        ok = sum(1 for r in res if r.get("status") == "pass")
        ce = sum(1 for r in res if r.get("status") == "collector_error")
        print("    %d observations, %d usable, %d collector errors"
              % (len(res), ok, ce))

    # ---- judge ----
    by_path = {p: {r["id"]: r for r in raw[p]} for p in PATHS}
    rows = []
    for c in cases:
        row = {"id": c["id"], "ascii": c["ascii"],
               "internal_expr": c["internal_expr"],
               "internal_expr_source": c["internal_expr_source"],
               "expected": c["expected"], "expect_error": c["expect_error"]}
        for p in PATHS:
            obs = by_path[p].get(c["id"])
            verdict, why = judge(c, obs)
            row[p] = {"verdict": verdict, "why": why,
                      "observed": None if obs is None else obs.get("observed"),
                      "numeric": None if obs is None else obs.get("numeric"),
                      "error_text": None if obs is None else obs.get("error_text"),
                      "error_class": None if obs is None else obs.get("error_class"),
                      "getExpr": (obs or {}).get("input") if p == "browser_file" else None,
                      "detail": None if obs is None else obs.get("detail"),
                      "evidence": None if obs is None else obs.get("evidence")}
        rows.append(row)

    with open(os.path.join(args.out, "comparator_results.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_from": CASES_PATH, "tolerance": TOL,
                   "paths": PATHS, "cases": rows, "raw": raw},
                  f, indent=2, ensure_ascii=False)

    # ---- matrix md ----
    def cell(v):
        return verdict_code(v)

    lines = ["# Divergence matrix", "",
             "PASS = matches the declared expectation. FAIL = contradicts it.",
             "UNRES = case expectation unresolved. INPUT = keypad built a different",
             "expression than the case declares, so nothing was evaluated.",
             "N/A = no observation. PARSE = output did not canonicalise.",
             "COLL = the collector itself failed (infrastructure, not calculator).", "",
             "| # | ascii | expected | " + " | ".join(PATHS) + " |",
             "|---|---|---|" + "---|" * len(PATHS)]
    for r in rows:
        exp = "error" if r["expect_error"] else r["expected"]
        lines.append("| %d | `%s` | %s | %s |"
                     % (r["id"], r["ascii"], exp,
                        " | ".join(cell(r[p]["verdict"]) for p in PATHS)))
    lines.append("")
    with open(os.path.join(args.out, "divergence_matrix.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    with open(os.path.join(args.out, "divergence_matrix.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "ascii", "internal_expr", "internal_expr_source",
                    "expected", "expect_error"] +
                   ["%s_verdict" % p for p in PATHS] +
                   ["%s_observed" % p for p in PATHS] +
                   ["%s_numeric" % p for p in PATHS] +
                   ["%s_error_text" % p for p in PATHS] +
                   ["%s_why" % p for p in PATHS])
        for r in rows:
            w.writerow([r["id"], r["ascii"], r["internal_expr"],
                        r["internal_expr_source"], r["expected"], r["expect_error"]] +
                       [r[p]["verdict"] for p in PATHS] +
                       [r[p]["observed"] for p in PATHS] +
                       [r[p]["numeric"] for p in PATHS] +
                       [r[p]["error_text"] for p in PATHS] +
                       [r[p]["why"] for p in PATHS])

    failure_path = write_failure_report(rows, args.out)

    # ---- summary ----
    print()
    overall = summarize(rows)
    print("cases loaded=%d executed=%d unresolved=%d skipped=%d failed=%d"
          % (overall["loaded"], overall["executed"], overall["unresolved"],
             overall["skipped"], overall["failed"]))
    print()
    for p in PATHS:
        tally = {}
        for r in rows:
            tally[r[p]["verdict"]] = tally.get(r[p]["verdict"], 0) + 1
        print("%-13s %s" % (p, "  ".join("%s=%d" % kv for kv in sorted(tally.items()))))
    print()
    print("written to %s" % args.out)
    print("failure report: %s" % failure_path)


if __name__ == "__main__":
    main()