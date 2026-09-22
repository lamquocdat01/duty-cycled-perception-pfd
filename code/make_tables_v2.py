"""make_tables_v2.py -- Topic 35 / V2.

Emits every LaTeX table of the case study and the comparison section straight
from the released CSVs, into 02_Manuscript/body/tab_*.tex.  No table is typed by
hand, for the same reason no number is (checklist C6), and each file is a
complete float with its own caption and label.

Tables produced:
    tab_validation.tex   measured vs modelled miss rate against K
    tab_far.tex          false alarms per hour
    tab_latency.tex      latency against the schedule bound
    tab_sensitivity.tex  every axis of protocol section 8
    tab_worksheet.tex    the end-to-end design worksheet (VIEC 2.4)
    tab_cmp_amlas.tex    a per-invocation requirement read as a PFD-like
    tab_cmp_sis.tex      IEC 61508-6 low-demand PFD_avg against this model
    tab_cmp_zf.tex       a zero-failure demonstration in frames and in events
"""
from __future__ import annotations

import csv
import math
import pathlib

import case_study_v2 as C
import model_v2 as M

EVAL = pathlib.Path(__file__).resolve().parents[1]
RESULTS = EVAL / "results"
BODY = EVAL.parent / "02_Manuscript" / "body"

# Approach distances for the worksheet.  ISO 13855 positions a safeguard from the
# approach speed of the human body; the standard's own speed constant is not
# quoted here because the standard could not be read (AUTHOR ACTION A-W1), so the
# reaction time is swept over a declared range instead of being computed from a
# number we cannot verify.
TREACT_GRID = [0.3, 0.5, 1.0, 2.0, 3.0]


def rows(name):
    p = RESULTS / name
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


def f(x, dp=4):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "---"
    if isinstance(x, str):
        return x.replace("_", r"\_")
    if abs(x) != 0 and (abs(x) < 1e-3 or abs(x) >= 1e5):
        m, e = f"{x:.2e}".split("e")
        return f"${m}\\times 10^{{{int(e)}}}$"
    s = f"{x:.{dp}f}"
    if "." in s:            # never strip the zero off an integer: f(70, 0) was "7"
        s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def table(path, caption, label, header, body_rows, colspec, note=None, small=True):
    L = ["\\begin{table}[t]", "\\centering",
         f"\\caption{{{caption}}}", f"\\label{{{label}}}"]
    if small:
        L.append("\\small")
    L += ["\\fittab{%", f"\\begin{{tabular}}{{@{{}}{colspec}@{{}}}}", "\\toprule",
          " & ".join(header) + " \\\\", "\\midrule"]
    L += [" & ".join(r) + " \\\\" for r in body_rows]
    L += ["\\bottomrule", "\\end{tabular}}"]
    if note:
        L.append(f"\n\\vspace{{2pt}}\n{{\\footnotesize {note}}}")
    L.append("\\end{table}")
    (BODY / path).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("  wrote", path)


def n_req(eps, delta=0.05):
    return math.ceil(math.log(delta) / math.log(1.0 - eps))


def main():
    BODY.mkdir(parents=True, exist_ok=True)

    # ---- validation ------------------------------------------------------
    R = [r for r in rows("miss_validation_v2.csv") if r["corpus"] == "pooled"]
    R.sort(key=lambda r: r["T_seconds"])
    # Protocol V2.1 section 7.1: the cluster count goes beside every interval,
    # and an interval built on fewer than ten clusters is labelled as indicative.
    cl = {r["corpus"]: r for r in rows("clusters_v2_1.csv")}
    nclus = cl.get("pooled", {}).get("n_clusters")
    weak = nclus is not None and float(nclus) < 10
    H = rows("het_validation_v2_2.csv")
    if H:
        SHORT = {"CAVIAR-LISBON": "corridor", "CAVIAR-INRIA": "lobby",
                 "pooled": "pooled"}
        body = []
        for site in ("CAVIAR-LISBON", "CAVIAR-INRIA"):
            for r in [x for x in H if x["corpus"] == site]:
                body.append([
                    SHORT.get(site, site), f(r["T_seconds"], 3),
                    f(r["n_events"], 0), f(r["miss_measured"], 3),
                    f"{f(r['miss_lo'], 3)}--{f(r['miss_hi'], 3)}",
                    f(r["hom_beta"], 3), f(r["hom_lovo"], 3),
                    f(r["het_lovo"], 3), f(r["het_lovo_beta"], 3),
                    f(r["structural_floor"], 3),
                    ("*" if str(r["near_tautology"]) == "True" else "")])
        table("tab_validation.tex",
              "Measured end-to-end miss rate against five predictions, per "
              "site. The measurement enumerates every schedule phase exactly. "
              "\\emph{Homogeneous} is Eq.~(1) with one frame-weighted "
              "$\\hat p$ and the fitted $\\hat\\beta$; \\emph{hom.\\ LOVO} is the "
              "same model refitted leave-one-video-out; \\emph{het.\\ LOVO} and "
              "\\emph{het.\\ Beta} are Eq.~(10) with the law of $p$ taken from "
              "the other videos of the same site, empirically and as a Beta "
              "fitted by moments. Only $p$ (or its law) and $\\beta$ are "
              "fitted; the miss rate is fitted to nothing. Rows marked * have "
              "at most two schedule phases, where the prediction is close to "
              "the definition of a miss and the comparison carries little "
              "information. Intervals are a cluster bootstrap over "
              f"{f(nclus, 0)} videos"
              + (", fewer than ten, so they are indicative only." if weak
                 else ".")
              + " The pooled rows, which mix the two sites by event with each "
                "predicted under its own law of $p$, are in the released CSV.",
              "tab:validation",
              ["Site", "$K$ (s)", "Ev.", "Measured", "95\\,\\% CI",
               "Homog.", "hom. LOVO", "het. LOVO", "het. Beta",
               "Floor $M(K)$", ""],
              body, "llrrrrrrrrl", small=True)
        # a narrow form for the two-column build: the informative periods and
        # the two predictors the argument rests on
        nbody = []
        for site in ("CAVIAR-LISBON", "CAVIAR-INRIA"):
            for r in [x for x in H if x["corpus"] == site
                      and str(x["near_tautology"]) != "True"]:
                nbody.append([
                    SHORT.get(site, site), f(r["T_seconds"], 3),
                    f(r["miss_measured"], 3),
                    f"{f(r['miss_lo'], 3)}--{f(r['miss_hi'], 3)}",
                    f(r["hom_beta"], 3), f(r["het_lovo"], 3),
                    f(r["structural_floor"], 3)])
        table("tab_validation_narrow.tex",
              "Measured end-to-end miss rate against the homogeneous model and "
              "against Eq.~(10) with the law of $p$ taken from the other videos "
              "of the same site, at the invocation periods where the phase "
              "enumeration carries information. The full grid, both sites "
              "pooled, the Beta form and the refitted homogeneous baseline are "
              "in the supplement and in the released CSV.",
              "tab:validation",
              ["Site", "$K$ (s)", "Measured", "95\\,\\% CI",
               "Homog.", "het. LOVO", "Floor"],
              nbody, "llrrrrr")

    else:
        table("tab_validation.tex",
              "Measured end-to-end miss rate against the model's prediction.",
              "tab:validation",
              ["$K$ (s)", "Events", "Measured", "95\\,\\% CI", "Clusters",
               "Model ($\\hat\\beta$)", "Model ($\\beta=0$)", "Floor $M(K)$"],
              [[f(r["T_seconds"], 3), f(r["n_events"], 0), f(r["miss_measured"]),
                f"{f(r['miss_lo'])}--{f(r['miss_hi'])}", f(nclus, 0),
                f(r["miss_model_beta"]), f(r["miss_model_beta0"]),
                f(r["structural_floor"])] for r in R],
              "lrrrrrrr")

    # ---- false alarms ----------------------------------------------------
    R = [r for r in rows("far_latency_v2.csv")
         if any(abs(r["T_seconds"] - t) < 1e-6 for t in (1 / 30, 0.2, 1.0, 5.0))]
    table("tab_far.tex",
          "False-alarm burden. The frame-level rate is the fraction of "
          "hazard-free frames on which the monitor fires; the per-hour figure "
          "converts it at the invocation period.",
          "tab:far",
          ["Corpus", "$K$ (s)", "Hazard-free frames", "Alarming frames",
           "Frame rate", "Alarms\\,/\\,h"],
          [[f(r["corpus"]), f(r["T_seconds"], 3), f(r["n_negative_frames"], 0),
            f(r["n_false_alarm_frames"], 0), f(r["fa_frame_rate"]),
            f(r["alarms_per_hour"], 1)] for r in R],
          "llrrrr")

    # ---- latency ---------------------------------------------------------
    R = [r for r in rows("latency_v2.csv") if r["corpus"] == "pooled"]
    R.sort(key=lambda r: r["T_seconds"])
    table("tab_latency.tex",
          "Delay from event onset to the first firing invocation, over all "
          "schedule phases, against the schedule's worst case $(K-1)/f$.",
          "tab:latency",
          ["$K$ (s)", "$n$", "Mean (s)", "Median (s)", "95th pct (s)",
           "Max (s)", "Bound $(K-1)/f$ (s)"],
          [[f(r["T_seconds"], 3), f(r["n"], 0), f(r["mean_s"], 3),
            f(r["median_s"], 3), f(r["q95_s"], 3), f(r["max_s"], 3),
            f(r["bound_s"], 3)] for r in R],
          "lrrrrrr")

    # ---- sensitivity -----------------------------------------------------
    R = rows("sensitivity_v2.csv")
    table("tab_sensitivity.tex",
          "Sensitivity. One axis of the frozen protocol is varied at a time; "
          "the primary setting is marked. Every axis is reported, including "
          "the ones that move the answer.",
          "tab:sensitivity",
          ["Axis", "Value", "$K$ (s)", "Events", "$\\hat p$", "$M(K)$",
           "Band", "Measured", "Model"],
          [[f(r["axis"]), f(r["value"]) + ("$^{\\star}$" if str(r["is_primary"]) == "True" else ""),
            f(r["T_seconds"], 2), f(r["n_events"], 0), f(r["p_hat"], 3),
            f(r["M_K"]), f(r["band"]), f(r["miss_measured"]), f(r["miss_model"])]
           for r in R],
          "llrrrrlrr",
          note="$^{\\star}$ primary setting of the frozen protocol.")

    # ---- worksheet -------------------------------------------------------
    ev = rows("events_v2.csv")
    pb = {r["corpus"]: r for r in rows("p_beta_v2.csv")}
    p_hat = float(pb.get("pooled", {}).get("p_hat", float("nan")))
    wrows = []
    for treact in TREACT_GRID:
        K = treact                       # one invocation per reaction window
        Ms, mm = [], []
        for e in ev:
            kf = max(1, int(round(K * e["fps"])))
            Ms.append(max(0.0, 1.0 - e["n_frames"] / kf))
            mm.append(float(M.p_miss_exact(e["n_frames"], kf, p_hat, 0.0)))
        MK = sum(Ms) / len(Ms) if Ms else float("nan")
        half = []
        for e in ev:
            kf = max(1, int(round(K * e["fps"])))
            half.append(max(0.0, 1.0 - e["n_frames"] / max(1.0, kf / 2.0)))
        MKh = sum(half) / len(half) if half else float("nan")
        pfd = sum(mm) / len(mm) if mm else float("nan")
        wrows.append([f(treact, 2), f(K, 2), f(MK), C.sil_band(MK), f(pfd),
                      C.sil_band(pfd), str(n_req(max(pfd, 1e-6))),
                      f(MKh), f(MKh / MK if MK > 0 else float("nan"), 3)])
    table("tab_worksheet.tex",
          "The end-to-end design worksheet. The required reaction time is "
          "\\emph{swept}, not imported: ISO~13855 positions a safeguard from "
          "the approach speed of the human body, and its speed constant is not "
          "quoted here because the standard could not be read directly. "
          "$n_{\\mathrm{req}}$ is counted in \\emph{events}, at "
          "$\\delta=0.05$.",
          "tab:worksheet",
          ["$\\Treact$ (s)", "$K$ (s)", "$M(K)$", "Band", "$\\PFDlike$",
           "Band", "$\\nreq$ (events)", "$M(K/2)$", "Gain"],
          wrows, "rrrlrlrrr",
          note="Gain is $M(K/2)/M(K)$, the improvement from a staggered "
               "$1$oo$2$: smaller is better.")

    # ---- comparison: an AMLAS-style requirement --------------------------
    R = [r for r in rows("cmp_amlas_v2.csv")
         if r["corpus"] == "pooled" and abs(r["requirement_p"] - 0.95) < 1e-9]
    R.sort(key=lambda r: r["T_seconds"])
    table("tab_cmp_amlas.tex",
          "A requirement of the form ``the detection rate shall be at least "
          "95\\,\\%'', stated per invocation, read as an event-level "
          "PFD-like quantity. The last column is the share of the result that "
          "the detector cannot influence.",
          "tab:cmpamlas",
          ["$K$ (s)", "$\\PFDlike$ at $p=0.95$", "Band", "Floor $M(K)$",
           "Floor share (\\%)"],
          [[f(r["T_seconds"], 3), f(r["pfd_like"]), f(r["band"]),
            f(r["structural_floor"]), f(100.0 * r["floor_share"], 1)] for r in R],
          "lrlrr")

    # ---- comparison: SIS -------------------------------------------------
    SIS_T = (1 / 30, 0.2, 1.0, 5.0)     # the full period grid is in the CSV
    R = [r for r in rows("cmp_sis_v2.csv") if abs(r["p"] - 0.99) < 1e-9
         and abs(r["tau_h"] - 8760.0) < 1e-9
         and any(abs(r["T_seconds"] - t) < 1e-6 for t in SIS_T)]
    R.sort(key=lambda r: (r["lambda_DU_per_h"], r["T_seconds"]))
    table("tab_cmp_sis.tex",
          "The IEC~61508-6 low-demand $\\PFDavg \\approx \\lamDU \\tau/2$ of a "
          "protection system against the sampling term of this paper, on "
          "matched parameters, at $\\tau = 8760$\\,h and $p=0.99$. "
          "$\\lamDU$ is swept, not imported; four invocation periods are shown "
          "and the whole grid is in the released CSV. The last column is the point: at "
          "$\\lamDU = 0$ the first column is zero and the third is not.",
          "tab:cmpsis",
          ["$\\lamDU$ (h$^{-1}$)", "$\\PFDavg$", "$K$ (s)", "Sampling term",
           "Ratio", "Sampling at $\\lamDU=0$"],
          [[f(r["lambda_DU_per_h"]), f(r["pfd_sis"], 6), f(r["T_seconds"], 3),
            f(r["pfd_sampling"]), f(r["ratio_sampling_over_sis"], 1),
            f(r["pfd_sampling_at_lambda_zero"])] for r in R],
          "rrrrrr")

    # ---- comparison: zero-failure ---------------------------------------
    R = [r for r in rows("cmp_zerofailure_v2.csv")
         if abs(r["delta"] - 0.05) < 1e-9 and abs(r["T_seconds"] - 1.0) < 1e-9]
    R.sort(key=lambda r: -r["eps"])
    table("tab_cmp_zf.tex",
          "A zero-failure demonstration counted in frames and counted in "
          "events, at $\\delta = 0.05$ and $K = 1$\\,s. A per-frame claim "
          "below the structural floor is not a stronger claim about the safety "
          "function; it is a claim about a different quantity.",
          "tab:cmpzf",
          ["$\\varepsilon$", "$\\nreq$", "Band if per frame",
           "Achievable per event", "Band per event", "Claim unreachable?"],
          [[f(r["eps"]), f(r["n_req"], 0), f(r["band_if_per_frame"]),
            f(r["achievable_per_event"]), f(r["band_per_event"]),
            "yes" if str(r["claim_is_unreachable_at_event_level"]) == "True" else "no"]
           for r in R],
          "rrlrll")

    # ---- Amendment 2': the detector audit and the GT-matched alarm --------
    R = rows("detector_quality_v2_1.csv")
    if R:
        agg = {}
        for r in R:
            a = agg.setdefault(r["corpus"], dict(n=0, rec=[], pre=[], cell=[],
                                                 clus=[], fp=0, inzone=0,
                                                 zones=set()))
            a["n"] += 1
            for key, field in (("rec", "recall"), ("pre", "precision"),
                               ("cell", "top_cell_share"),
                               ("clus", "top_cluster_share")):
                v = r.get(field)
                if isinstance(v, float) and math.isfinite(v):
                    a[key].append(v)
            if str(r.get("persistent_cluster")) == "True":
                a["persist"] = a.get("persist", 0) + 1
                z = str(r.get("top_cell_zone") or "")
                inzone = z not in ("", "none", "nan")
                if inzone:
                    a["persistinzone"] = a.get("persistinzone", 0) + 1
                if str(r.get("static_fp")) == "True":
                    a["fp"] += 1
                    if inzone:
                        a["inzone"] += 1
                        a["zones"].add(z)

        def rng(v, dp=3):
            return f"{f(min(v), dp)}--{f(max(v), dp)}" if v else "---"

        table("tab_detquality.tex",
              "Detector-quality audit, every corpus. Recall and precision are "
              "against the corpus's own annotation at "
              "$\\mathrm{IoU} \\ge 0.3$. \emph{Concentration} is the share of all "
              "detections falling in the 3$\times$3 neighbourhood of the "
              "most frequent cell of a "
              "38$\\times$28 grid over the image. A sequence counts as "
              "carrying a persistent detection cluster when that "
              "neighbourhood fires in more than half its frames. Such a "
              "cluster is a stationary \emph{false} positive only if it also "
              "fails to match an annotated person in most of its frames --- a "
              "person standing still produces one too --- and it matters most "
              "when it falls inside a danger zone, because there the frozen "
              "alarm rule credits it with detecting every event. UR Fall "
              "carries a per-frame posture label and no boxes, so recall, "
              "precision, the match test and zones are all undefined there.",
              "tab:detquality",
              ["Corpus", "Seq.", "Recall", "Precision", "Concentration",
               "Persistent cluster", "of those, false", "false and in a zone"],
              [[f(k), f(a["n"], 0), rng(a["rec"]), rng(a["pre"]),
                rng(a["clus"]),
                str(a.get("persist", 0)) + "/" + str(a["n"])
                + (" (" + str(a.get("persistinzone", 0)) + " in a zone)"
                   if a.get("persistinzone") else ""),
                ("---" if k == "URFD" else str(a["fp"])),
                ("---" if k == "URFD" else
                 str(a["inzone"]) + ((" (" + ", ".join(sorted(a["zones"])) + ")")
                                     if a["zones"] else ""))]
               for k, a in sorted(agg.items())],
              "lrllllll")

    R = rows("alarm_mode_v2_1.csv")
    if R:
        def g(v, dp=4):
            """Blank means the quantity is not defined for that corpus (UR Fall
            carries no box annotation), which the table says rather than
            leaving a hole."""
            if v is None or v == "":
                return "n/d"
            return f(v, dp)

        table("tab_alarmmode.tex",
              "The alarm rule, both ways. \\texttt{any\\_box} is the rule frozen "
              "before the run: any detected person box whose foot point lies in "
              "the zone. \\texttt{gt\\_matched} additionally requires the "
              "detection to match an annotated person at "
              "$\\mathrm{IoU} \\ge 0.3$, so that a stationary false positive "
              "inside a zone cannot raise every alarm. Each corpus appears at "
              "two invocation periods; \texttt{n/d} means the corpus carries "
              "no box annotation, so the matched rule is not defined for it.",
              "tab:alarmmode",
              ["Corpus", "$\\hat p$ any", "$\\hat p$ matched",
               "Miss any", "Miss matched", "Alarms/h any", "Alarms/h matched"],
              [[f(r["corpus"]) + " (" + str(T) + " s)",
                g(r.get("p_hat_any_box"), 3),
                g(r.get("p_hat_gt_matched"), 3),
                g(r.get("miss_" + lab + "_any_box"), 3),
                g(r.get("miss_" + lab + "_gt_matched"), 3),
                g(r.get("alarms_per_hour_" + lab + "_any_box"), 1),
                g(r.get("alarms_per_hour_" + lab + "_gt_matched"), 1)]
               for r in R if r["corpus"] != "pooled"
               for T, lab in ((0.5, "Thalf"), (1, "T1"))],
              "lrrrrrr")

    # ---- cross-corpus, out-of-sample -------------------------------------
    # Both CAVIAR sites are primary under Amendment 2', so this is populated
    # again; the withdrawn V2.0 run's version is in make_v20_v21_table.py.
    R = [r for r in rows("cross_corpus_v2.csv")
         if any(abs(r["T_seconds"] - t) < 1e-6 for t in (1 / 30, 0.2, 1.0, 5.0))]
    if R:
        table("tab_xcorpus.tex",
              "Out-of-sample prediction: $\\hat p$ and $\\hat\\beta$ fitted on one "
              "corpus, the miss rate predicted on the other. Nothing about the "
              "target corpus enters the prediction except its measured event "
              "durations. Four invocation periods are shown; the whole grid is "
              "in the released CSV.",
              "tab:xcorpus",
              ["Fitted on", "Predicted on", "$K$ (s)", "$\\hat p$ used",
               "Measured", "95\\,\\% CI", "Predicted", "Inside CI"],
              [[f(r["fit_on"]), f(r["predict_on"]), f(r["T_seconds"], 3),
                f(r["p_fit"], 3), f(r["miss_measured"]),
                f"{f(r['miss_lo'])}--{f(r['miss_hi'])}", f(r["miss_predicted"]),
                "yes" if str(r["inside_ci"]) == "True" else "no"] for r in R],
              "llrrrrrl")

    # ---- the UR Fall contrast case, measured against the model ------------
    R = rows("urfd_contrast_v2_1.csv")
    if R:
        table("tab_urfd_contrast.tex",
              "The contrasting hazard: a person lying on the floor, UR Fall "
              "Detection, on the include-censored axis. Every fall recording "
              "ends while the subject is still on the floor, so every fall "
              "event is right-censored; the model check is unaffected because "
              "both sides use the observed duration, while $F_D$-derived "
              "quantities are upper bounds.",
              "tab:urfdcontrast",
              ["Subset", "$K$ (s)", "Events", "Measured", "95\\,\\% CI",
               "Model ($\\hat\\beta$)", "Floor $M(K)$"],
              [[f(r["kind"]), f(r["T_seconds"], 3), f(r["n_events"], 0),
                f(r["miss_measured"]), f"{f(r['miss_lo'])}--{f(r['miss_hi'])}",
                f(r["miss_model_beta"]), f(r["structural_floor"])] for r in R],
              "lrrrrrr")

    write_validation_prose()
    write_abstract_numbers()
    print("TABLES_DONE")


def write_abstract_numbers():
    """The two sentences of the abstract that carry numbers, generated.

    The design number required by the prompt is the largest invocation period
    whose structural floor still fits inside the SIL-1 PFD-like band, plus the
    improvement a staggered 1oo2 buys at that period."""
    B = [r for r in rows("bridge_v2.csv") if r["corpus"] == "pooled"]
    V = [r for r in rows("miss_validation_v2.csv") if r["corpus"] == "pooled"]
    B.sort(key=lambda r: r["T_seconds"])
    inside = [r for r in B if r["M_K"] < 1e-1]
    kmax = max(inside, key=lambda r: r["T_seconds"]) if inside else None
    ok = sum(1 for r in V if r["miss_lo"] <= r["miss_model_beta"] <= r["miss_hi"])
    ref = min(B, key=lambda r: abs(r["T_seconds"] - 1.0)) if B else None

    # Kept deliberately terse: the abstract limit is 200 words and this is
    # the only part of it that is generated, so it must not eat the budget.
    # Since dot 2c the sentence reports the heterogeneous model out of sample,
    # because that is the model the paper puts forward.
    H = rows("het_validation_v2_2.csv")
    parts = []
    if H:
        sites = [c for c in {r["corpus"] for r in H} if c != "pooled"]
        inf = [r for r in H if r["corpus"] in sites
               and str(r["near_tautology"]) != "True"]
        per = len(inf) // max(1, len(sites))
        lov = sum(1 for r in inf if str(r["inside_lovo"]) == "True")
        hom = sum(1 for r in inf if str(r["inside_hom"]) == "True")
        parts.append(
            f"Out of sample it falls inside the measured "
            f"95\\,\\% interval at {lov} of {len(inf)} informative cells, "
            f"against {hom} for one mean probability.")
    if ref:
        band = ref["band"].replace("SIL 1", "SIL~1")
        t = (f"At one second the structural floor is {f(ref['M_K'], 3)}, "
             f"{band}, whatever the detector does")
        if ref.get("gain_staggered") and math.isfinite(ref["gain_staggered"]):
            t += (f"; a staggered second channel multiplies it by "
                  f"{f(ref['gain_staggered'], 2)}")
        parts.append(t + ".")
    if kmax:
        parts.append(f"The longest period that stays inside that band is "
                     f"{f(kmax['T_seconds'], 3)}" + chr(92) + ",s.")
    txt = ("% GENERATED by make_tables_v2.py -- do not edit by hand.\n"
           + " ".join(parts) + "\n")
    (BODY / "abstract_numbers.tex").write_text(txt, encoding="utf-8")
    print("  wrote abstract_numbers.tex")


def write_validation_prose():
    """body/05b_case_numbers.tex -- the paragraph that says how the comparison
    came out.  Generated, including every directional word, because a partial
    corpus once made a directional sentence true and the full corpus made it
    false (V1, CP-L1).  If the model stops predicting the measurement, this
    paragraph says so by itself."""
    R = [r for r in rows("miss_validation_v2.csv") if r["corpus"] == "pooled"]
    R.sort(key=lambda r: r["T_seconds"])
    inside = [r for r in R if r["miss_lo"] <= r["miss_model_beta"] <= r["miss_hi"]]
    n, k = len(R), len(inside)
    worst = max(R, key=lambda r: abs(r["miss_model_beta"] - r["miss_measured"]))
    rel = [abs(r["miss_model_beta"] - r["miss_measured"]) / r["miss_measured"]
           for r in R if r["miss_measured"] > 0]
    med_rel = sorted(rel)[len(rel) // 2] if rel else float("nan")
    b0_better = sum(1 for r in R
                    if abs(r["miss_model_beta0"] - r["miss_measured"])
                    < abs(r["miss_model_beta"] - r["miss_measured"]))

    verdict = ("the model reproduces the measurement across the whole grid"
               if k == n else
               f"the model reproduces the measurement at {k} of the {n} "
               f"invocation periods tested" if k >= n / 2 else
               f"the model reproduces the measurement at only {k} of the {n} "
               f"invocation periods tested")
    direction = ("over-predicts" if worst["miss_model_beta"] > worst["miss_measured"]
                 else "under-predicts")
    # Which way does the beta-factor correction move the prediction, and does it
    # help?  Both answers are emitted, because the interesting case is the one
    # where a plausible correction makes the fit worse.
    over = sum(1 for r in R if r["miss_model_beta"] > r["miss_measured"])
    if b0_better > n - b0_better:
        beta_line = (
            f"The $\\beta$-factor correction is \\emph{{not}} an improvement here: "
            f"the independence model ($\\beta=0$) is closer to the measurement at "
            f"{b0_better} of the {n} periods, and the fitted correction sits above "
            f"the measured value at {over} of them. Section~\\ref{{sec:limitations}} "
            f"says why a two-point mixture over-states the effect of a dependence "
            f"that decays with lag.")
    elif b0_better:
        beta_line = (f"The $\\beta$-factor correction improves the fit at "
                     f"{n - b0_better} of the {n} periods and does not at "
                     f"{b0_better}.")
    else:
        beta_line = ("The $\\beta$-factor correction improves the fit at every "
                     "period tested.")

    txt = f"""% GENERATED by make_tables_v2.py -- do not edit by hand.
% Every directional word below is emitted from the data, not typed.
Across the {n} invocation periods tested, the homogeneous prediction falls inside the
measured 95\\,\\% interval at {k} of them: {verdict}. The median relative
departure between prediction and measurement is {100.0 * med_rel:.1f}\\,\\%, and
the largest single departure is at an invocation period of
{worst['T_seconds']:.3g}\\,s, where the model {direction} the measured miss rate
({f(worst['miss_model_beta'])} against {f(worst['miss_measured'])}).
{beta_line}
Table~\\ref{{tab:validation}} gives the whole grid.
"""
    txt += per_site_sentence()
    txt += het_sentences()
    (BODY / "05b_case_numbers.tex").write_text(txt, encoding="utf-8")
    print("  wrote 05b_case_numbers.tex")


def het_sentences():
    """The dot-2c paragraph: how the heterogeneous layer does against the
    homogeneous one, out of sample, with every count emitted from the CSV."""
    R = rows("het_validation_v2_2.csv")
    if not R:
        return ""
    NAME = {"CAVIAR-LISBON": "the corridor", "CAVIAR-INRIA": "the lobby",
            "pooled": "the two sites pooled by event"}
    out = []
    for site in ("CAVIAR-LISBON", "CAVIAR-INRIA"):
        sub = [r for r in R if r["corpus"] == site]
        if not sub:
            continue
        inf = [r for r in sub if str(r["near_tautology"]) != "True"]
        hom = sum(1 for r in inf if str(r["inside_hom"]) == "True")
        lov = sum(1 for r in inf if str(r["inside_lovo"]) == "True")
        bet = sum(1 for r in inf if str(r["inside_lovo_beta"]) == "True")
        under = sum(1 for r in inf
                    if str(r["inside_hom"]) != "True"
                    and r["hom_beta"] < r["miss_measured"])
        bad = len(inf) - hom
        out.append(
            f"On {NAME.get(site, site)}, over the {len(inf)} invocation periods "
            f"at which the phase enumeration has more than two phases, the "
            f"homogeneous model is inside the measured interval at {hom} and "
            f"the heterogeneous one, fitted on other videos, at {lov} "
            f"({bet} for its Beta form)."
            + (f" At the {bad} period{'s' if bad > 1 else ''} the homogeneous "
               f"model misses, it under-predicts the miss rate at "
               f"{under if under != bad else 'every one'}."
               if bad else " "))
    jen = all(str(r["jensen_ok"]) == "True" for r in R)
    out.append(
        "The predicted inequality holds in every cell computed: the "
        "heterogeneous prediction is at or above the homogeneous one "
        f"{'everywhere' if jen else 'in most cells'}, so the homogeneous number "
        "is the optimistic one." if jen else
        "The predicted inequality fails in at least one cell, which is "
        "reported in the released table rather than smoothed over.")
    return " ".join(out) + chr(10)


def per_site_sentence():
    BS = chr(92)
    """One generated sentence reporting the model check per site, which
    protocol section 11 (Amendment 2 prime) requires: a pooled row over sites
    with very different detection probabilities mixes two regimes."""
    V = rows("miss_validation_v2.csv")
    P = {r["corpus"]: r for r in rows("p_beta_v2.csv")}
    sites = sorted({r["corpus"] for r in V if r["corpus"] != "pooled"})
    bits = []
    for c in sites:
        sub = [r for r in V if r["corpus"] == c]
        if not sub:
            continue
        k = sum(1 for r in sub
                if r["miss_lo"] <= r["miss_model_beta"] <= r["miss_hi"])
        ph = P.get(c, {}).get("p_hat")
        name = {"CAVIAR-LISBON": "the corridor", "CAVIAR-INRIA": "the lobby",
                "MOT17Det-static": "the MOT17Det stratum", "URFD": "UR Fall"}.get(
                    c, c.replace("_", " "))
        ph_s = "$" + BS + "hat p = " + f(ph, 3) + "$"
        bits.append(f"{k} of {len(sub)} on {name} ({ph_s})")
    if len(bits) < 2:
        return ""
    return ("Per site, the prediction falls inside the measured interval at "
            + "; ".join(bits) + ". The pooled row therefore mixes a "
            "detector-bound regime with a schedule-bound one, and is reported "
            "for completeness rather than as the headline; the per-site rows "
            "of Table~" + chr(92) + "ref{tab:validation} are the comparison to "
            "read." + chr(10))


if __name__ == "__main__":
    main()
