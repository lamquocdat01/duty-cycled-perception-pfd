"""make_v20_v21_table.py -- Topic 35 / V2.1.

Two tables the protocol makes mandatory, both about what the corpus change did:

  tab_v20_v21.tex      the eight headline quantities, V2.0 beside V2.1
  tab_v20_bysequence.tex  the V2.0 event count per MOT17Det sequence, with the
                       camera attribute and the measured camera motion, so that
                       "109 of 135 events came from moving cameras" is a table a
                       reader can check rather than a claim.

V2.0 is read from results_v2_0/, which is the untouched backup of the run that
included the moving cameras.  Nothing is recomputed from it.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
from collections import Counter

EVAL = pathlib.Path(__file__).resolve().parents[1]
R20 = EVAL / "results_v2_0"
R21 = EVAL / "results"
BODY = EVAL.parent / "02_Manuscript" / "body"

MOVING = {"MOT17-05", "MOT17-10", "MOT17-11", "MOT17-13"}


def rows(root, name):
    p = root / name
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k, v in list(r.items()):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    pass
            out.append(r)
    return out


def jload(root, name):
    p = root / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def f(x, dp=4):
    if x is None:
        return "---"
    if isinstance(x, str):
        return x
    if isinstance(x, float) and not math.isfinite(x):
        return "---"
    s = f"{x:.{dp}f}"
    if "." in s:            # never strip the zero off an integer: f(70, 0) was "7"
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def headline(root, T_ref=1.0):
    ev = rows(root, "events_v2.csv")
    br = [r for r in rows(root, "bridge_v2.csv") if r["corpus"] == "pooled"]
    pb = {r["corpus"]: r for r in rows(root, "p_beta_v2.csv")}
    bl = [r for r in rows(root, "beta_lag_curve_v2.csv")
          if r["corpus"] == "pooled" and r["lag"] == 1]
    am = [r for r in rows(root, "cmp_amlas_v2.csv")
          if r["corpus"] == "pooled" and abs(r["requirement_p"] - 0.95) < 1e-9
          and abs(r["T_seconds"] - T_ref) < 1e-9]
    ref = next((r for r in br if abs(r["T_seconds"] - T_ref) < 1e-9), None)
    inside = [r for r in br if 0 < r["M_K"] < 1e-1]
    kmax = max(inside, key=lambda r: r["T_seconds"]) if inside else None
    D = sorted(r["D_seconds"] for r in ev) if ev else []
    return {
        "n events (primary)": len(ev),
        "median event duration (s)": D[len(D) // 2] if D else None,
        "p-hat (pooled)": pb.get("pooled", {}).get("p_hat"),
        "beta-hat at lag 1": bl[0]["beta_hat"] if bl else None,
        f"structural floor M(K) at K = {T_ref:g} s": ref["M_K"] if ref else None,
        f"band at K = {T_ref:g} s": ref["band"] if ref else None,
        "largest K inside the SIL-1 band (s)": kmax["T_seconds"] if kmax else None,
        "staggered 1oo2 gain at that K": kmax["gain_staggered"] if kmax else None,
        "structural share of a 95 % requirement (%)":
            100.0 * am[0]["floor_share"] if am else None,
    }


def table(path, caption, label, header, body, colspec, note=None):
    L = ["\\begin{table}[t]", "\\centering", f"\\caption{{{caption}}}",
         f"\\label{{{label}}}", "\\small",
         "\\fittab{%", f"\\begin{{tabular}}{{@{{}}{colspec}@{{}}}}", "\\toprule",
         " & ".join(header) + " \\\\", "\\midrule"]
    L += [" & ".join(r) + " \\\\" for r in body]
    L += ["\\bottomrule", "\\end{tabular}}"]
    if note:
        L.append(f"\n\\vspace{{2pt}}\n{{\\footnotesize {note}}}")
    L.append("\\end{table}")
    (BODY / path).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("  wrote", path)


def main():
    BODY.mkdir(parents=True, exist_ok=True)
    a, b = headline(R20), headline(R21)
    body = []
    for k in a:
        va, vb = a[k], b.get(k)
        body.append([k.replace("%", "\\%"),
                     f(va, 3) if not isinstance(va, str) else va,
                     f(vb, 3) if not isinstance(vb, str) else vb])
    table("tab_v20_v21.tex",
          "What replacing the corpus did. V2.0 pooled MOT17Det with UR-Fall; "
          "81\\,\\% of its events came from sequences filmed with a moving "
          "camera, for which a zone fixed in image coordinates is not a danger "
          "zone. V2.1 is the static-camera CAVIAR sites. The model, the "
          "detector, its weights and every threshold are identical in the two "
          "columns.",
          "tab:v20v21",
          ["Quantity", "V2.0 (withdrawn)", "V2.1 (this paper)"],
          body, "lrr",
          note="The V2.0 column is reproduced from the untouched backup of that "
               "run and is not recomputed here.")

    ev20 = rows(R20, "events_v2.csv")
    cnt = Counter(r["video"] for r in ev20 if r["corpus"] == "MOT17Det")
    motion = {r["sequence"].split("/")[-1]: r["median_pct_diag"]
              for r in jload(R21, "camera_motion_v2_1.json") or []}
    body = []
    for v in sorted(cnt):
        body.append([v.replace("_", "\\_"),
                     "moving" if v in MOVING else "static",
                     f(motion.get(v), 3), str(cnt[v])])
    n_mov = sum(c for v, c in cnt.items() if v in MOVING)
    table("tab_v20_bysequence.tex",
          "The V2.0 run, by MOT17Det sequence: the camera attribute published "
          "in the benchmark, the camera motion measured here (median global "
          "frame-to-frame shift, \\% of the image diagonal at a stride of 5 "
          "frames), and the number of uncensored events each sequence "
          "contributed. The documentation and the measurement agree, and they "
          "separate by a factor of 27 with nothing in between.",
          "tab:v20seq",
          ["Sequence", "Benchmark", "Measured motion (\\%)", "Events in V2.0"],
          body, "llrr",
          note=f"{n_mov} of {sum(cnt.values())} MOT17Det events "
               f"({100.0 * n_mov / max(sum(cnt.values()), 1):.0f}\\,\\%) came "
               f"from the moving-camera sequences. Static threshold: 0.1\\,\\%.")
    # ---- the out-of-sample test, from the withdrawn run -------------------
    # V2.1 has a single admissible site, so there is no within-hazard corpus to
    # hold out.  The V2.0 run did have two, and its result -- that a
    # per-invocation detection probability does not transfer between scenes --
    # stands on its own and is cited in the body.
    X = rows(R20, "cross_corpus_v2.csv")
    if X:
        inside = sum(1 for r in X if str(r["inside_ci"]) == "True")
        table("tab_v20_xcorpus.tex",
              "Out-of-sample prediction in the withdrawn V2.0 run: $\\hat p$ and "
              "$\\hat\\beta$ fitted on one corpus, the miss rate predicted on the "
              "other. It fails, and the reason is visible rather than arguable --- "
              "$\\hat p$ differs by a factor of two between the two corpora, "
              "because a per-invocation detection probability is a property of a "
              "monitor in a scene and does not travel.",
              "tab:v20xcorpus",
              ["Fitted on", "Predicted on", "$K$ (s)", "$\\hat p$ used",
               "Measured", "95\\,\\% CI", "Predicted", "Inside CI"],
              [[f(r["fit_on"]), f(r["predict_on"]), f(r["T_seconds"], 3),
                f(r["p_fit"], 3), f(r["miss_measured"]),
                f"{f(r['miss_lo'])}--{f(r['miss_hi'])}", f(r["miss_predicted"]),
                "yes" if str(r["inside_ci"]) == "True" else "no"] for r in X],
              "llrrrrrl",
              note=f"{inside} of {len(X)} points fall inside the measured interval.")

    print("V20_V21_TABLES_DONE")


if __name__ == "__main__":
    main()
