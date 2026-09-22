"""comparison_v2.py -- Topic 35 / V2, VIEC 3.

Three quantitative comparisons against recent work, on the *measured* event
durations of the case study.  Replaces the V1 five-column "only we have all the
dots" table, which was self-assertion rather than comparison.

(a) An AMLAS-style requirement stated per frame / per invocation
    ("the detection rate shall be at least 95%") converted to a PFD-like number
    per invocation period K, so that one can read off which band that same 95%
    lands in.
(b) The IEC 61508-6 low-demand PFD_avg of a safety instrumented system,
    lambda_DU * tau / 2, against this model on matched parameters.  lambda_DU
    and tau are SWEPT over a declared grid -- no point estimate is imported
    from anywhere -- and the difference is by construction the sampling term.
(c) A black-box zero-failure demonstration counted in frames against the same
    demonstration counted in events.

Reads  ../results/events_v2.csv
Writes ../results/cmp_amlas_v2.csv, cmp_sis_v2.csv, cmp_zerofailure_v2.csv,
       ../results/comparison_numbers_v2.json
"""
from __future__ import annotations

import csv
import json
import math
import pathlib

import numpy as np

import case_study_v2 as C
import model_v2 as M

RESULTS = C.RESULTS
T_GRID = C.T_GRID
# swept grids, declared here and in the manuscript; nothing is imported
P_GRID = [0.90, 0.95, 0.97, 0.99, 0.995, 0.999]
LAMBDA_DU = [1e-7, 1e-6, 1e-5]          # per hour
TAU = [4380.0, 8760.0]                  # hours between proof tests
EPS_GRID = [0.2, 0.1, 0.05, 0.02, 0.01, 1e-3, 1e-4]
DELTA_GRID = [0.10, 0.05, 0.01]


def load_events():
    rows = []
    with open(RESULTS / "events_v2.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["n_frames"] = int(r["n_frames"])
            r["fps"] = float(r["fps"])
            r["D_seconds"] = float(r["D_seconds"])
            rows.append(r)
    return rows


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def n_req(eps, delta):
    return math.ceil(math.log(delta) / math.log(1.0 - eps))


def event_miss(events, T, p, beta=0.0):
    vals = []
    for e in events:
        K = max(1, int(round(T * e["fps"])))
        vals.append(float(M.p_miss_exact(e["n_frames"], K, p, beta)))
    return float(np.mean(vals)) if vals else float("nan")


def measured_concentration():
    """The event-to-event dispersion of p, as measured, expressed as the Beta
    concentration a + b of the schedule-bound site.  Read from the released
    CSV so that nothing here is typed by hand; None if it is not available."""
    f = RESULTS / "pe_distribution_v2_2.csv"
    if not f.exists():
        return None, None
    best = None
    with open(f, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["corpus"] == "pooled" or not r.get("beta_conc"):
                continue
            try:
                conc, mu = float(r["beta_conc"]), float(r["mean_pe"])
            except ValueError:
                continue
            # the site whose monitor is schedule-bound rather than
            # detector-bound is the one a designer reasons about
            if best is None or mu > best[1]:
                best = (conc, mu, r["corpus"])
    return (best[0], best[2]) if best else (None, None)


def event_miss_disp(events, T, mu, conc):
    """Event-level miss when the requirement fixes only the MEAN detection
    probability mu and the event-to-event dispersion is Beta with
    concentration conc.  conc None means homogeneous (no dispersion)."""
    if conc is None:
        return event_miss(events, T, mu)
    a, b = M.beta_with_mean(mu, conc)
    vals = []
    for e in events:
        K = max(1, int(round(T * e["fps"])))
        vals.append(float(M.p_miss_het_beta(e["n_frames"], K, a, b)))
    return float(np.mean(vals)) if vals else float("nan")


def main():
    events = load_events()
    N = {}
    global CONC
    CONC, CONC_SITE = measured_concentration()
    N["dispersion_concentration"] = CONC
    N["dispersion_site"] = CONC_SITE
    print(f"design-side dispersion: Beta concentration {CONC} "
          f"(measured on {CONC_SITE})", flush=True)

    # ---- (a) an AMLAS-style per-invocation requirement, read as a PFD-like -----
    rows = []
    for p in P_GRID:
        for T in T_GRID:
            for corpus in ["pooled"] + sorted({e["corpus"] for e in events}):
                sel = [e for e in events
                       if corpus == "pooled" or e["corpus"] == corpus]
                if not sel:
                    continue
                m = event_miss(sel, T, p)
                floor = event_miss(sel, T, 1.0)
                mh = event_miss_disp(sel, T, p, CONC)
                rows.append(dict(requirement_p=p, T_seconds=T, corpus=corpus,
                                 n_events=len(sel), pfd_like=m,
                                 band=C.sil_band(m), structural_floor=floor,
                                 floor_share=(floor / m) if m > 0 else float("nan"),
                                 pfd_like_dispersed=mh,
                                 band_dispersed=C.sil_band(mh),
                                 dispersion_penalty=(mh / m) if m > 0 else float("nan"),
                                 beta_concentration=CONC))
    write_csv(RESULTS / "cmp_amlas_v2.csv", rows)
    for T in (0.5, 1.0):
        r = next((x for x in rows if x["requirement_p"] == 0.95
                  and x["T_seconds"] == T and x["corpus"] == "pooled"), None)
        if r:
            t = str(T).replace(".", "p")
            N[f"amlas95_pfd_T{t}"] = r["pfd_like"]
            N[f"amlas95_band_T{t}"] = r["band"]
            N[f"amlas95_floorshare_T{t}"] = r["floor_share"]

    # ---- (b) SIS low-demand PFD_avg against this model ------------------------
    rows = []
    for lam in LAMBDA_DU:
        for tau in TAU:
            pfd_sis = lam * tau / 2.0
            for T in T_GRID:
                for p in (0.95, 0.99):
                    m = event_miss(events, T, p)
                    rows.append(dict(
                        lambda_DU_per_h=lam, tau_h=tau, T_seconds=T, p=p,
                        pfd_sis=pfd_sis, band_sis=C.sil_band(pfd_sis),
                        pfd_sampling=m, band_sampling=C.sil_band(m),
                        pfd_combined=1.0 - (1.0 - pfd_sis) * (1.0 - m),
                        ratio_sampling_over_sis=(m / pfd_sis) if pfd_sis > 0 else float("inf"),
                        pfd_sis_at_lambda_zero=0.0,
                        pfd_sampling_at_lambda_zero=m))
    write_csv(RESULTS / "cmp_sis_v2.csv", rows)
    r = next((x for x in rows if x["lambda_DU_per_h"] == 1e-6 and x["tau_h"] == 8760.0
              and x["T_seconds"] == 1.0 and x["p"] == 0.99), None)
    if r:
        N["sis_pfd_ref"] = r["pfd_sis"]
        N["sis_band_ref"] = r["band_sis"]
        N["sampling_pfd_ref"] = r["pfd_sampling"]
        N["sampling_band_ref"] = r["band_sampling"]
        N["sampling_over_sis_ref"] = r["ratio_sampling_over_sis"]

    # ---- (c) zero-failure demonstration: frames against events ---------------
    rows = []
    for eps in EPS_GRID:
        for delta in DELTA_GRID:
            n = n_req(eps, delta)
            for T in (0.5, 1.0):
                floor = event_miss(events, T, 1.0)
                # Total observation time, if the n demonstration cases are frames
                # rather than events: n frames at the median frame rate.
                fps = float(np.median([e["fps"] for e in events])) if events else 30.0
                med_D = float(np.median([e["D_seconds"] for e in events])) if events else 1.0
                rows.append(dict(
                    eps=eps, delta=delta, n_req=n, T_seconds=T,
                    claim_if_per_frame=eps,
                    band_if_per_frame=C.sil_band(eps),
                    achievable_per_event=max(eps, floor),
                    band_per_event=C.sil_band(max(eps, floor)),
                    structural_floor=floor,
                    claim_is_unreachable_at_event_level=bool(eps < floor),
                    demonstration_hours_frames=n / fps / 3600.0,
                    demonstration_hours_events=n * med_D / 3600.0))
    write_csv(RESULTS / "cmp_zerofailure_v2.csv", rows)
    r = next((x for x in rows if x["eps"] == 0.01 and x["delta"] == 0.05
              and x["T_seconds"] == 1.0), None)
    if r:
        N["zf_nreq_eps1e2_delta05"] = r["n_req"]
        N["zf_band_per_frame"] = r["band_if_per_frame"]
        N["zf_band_per_event"] = r["band_per_event"]
        N["zf_unreachable"] = r["claim_is_unreachable_at_event_level"]
        N["zf_hours_frames"] = r["demonstration_hours_frames"]
        N["zf_hours_events"] = r["demonstration_hours_events"]

    # ---- (d) what the dispersion does to the design quantities ---------------
    rows = []
    for p in (0.95, 0.99, 0.999):
        for T in T_GRID:
            for conc, lab in ((None, "homogeneous"), (CONC, "measured")):
                single = event_miss_disp(events, T, p, conc)
                if conc is None:
                    stag = event_miss(events, T * 0.5, p)
                    indep = float(np.mean([
                        float(M.p_miss_exact(e["n_frames"],
                                             max(1, int(round(T * e["fps"]))),
                                             p)) ** 2 for e in events]))
                else:
                    a, b = M.beta_with_mean(p, conc)
                    stag = float(np.mean([
                        float(M.p_miss_het_beta(e["n_frames"],
                                                max(1, int(round(T * e["fps"]))) / 2.0,
                                                a, b)) for e in events]))
                    indep = float(np.mean([
                        float(M.p_miss_1oo2_independent_het(
                            e["n_frames"], max(1, int(round(T * e["fps"]))),
                            np.random.default_rng(M.SEED).beta(a, b, 4000))[0])
                        for e in events]))
                rows.append(dict(
                    requirement_p=p, T_seconds=T, dispersion=lab,
                    beta_concentration=conc, single=single,
                    band_single=C.sil_band(single),
                    staggered_1oo2=stag, independent_1oo2=indep,
                    gain_staggered=(stag / single) if single > 0 else float("nan"),
                    gain_independent=(indep / single) if single > 0 else float("nan")))
    write_csv(RESULTS / "cmp_dispersion_v2_2.csv", rows)
    for p in (0.99,):
        for lab in ("homogeneous", "measured"):
            ok = [r for r in rows if r["requirement_p"] == p
                  and r["dispersion"] == lab
                  and r["band_single"] in ("SIL 1", "SIL 2", "SIL 3", "SIL 4")]
            kmax = max((r["T_seconds"] for r in ok), default=None)
            tag = "hom" if lab == "homogeneous" else "disp"
            N[f"kmax_sil1_{tag}_p99"] = kmax
            ref = next((r for r in rows if r["requirement_p"] == p
                        and r["dispersion"] == lab
                        and abs(r["T_seconds"] - 1.0) < 1e-9), None)
            if ref:
                N[f"pfd_T1_{tag}_p99"] = ref["single"]
                N[f"band_T1_{tag}_p99"] = ref["band_single"]
                N[f"gain_staggered_T1_{tag}_p99"] = ref["gain_staggered"]
                N[f"gain_independent_T1_{tag}_p99"] = ref["gain_independent"]
            sh = min(r["T_seconds"] for r in rows)
            r0 = next((r for r in rows if r["requirement_p"] == p
                       and r["dispersion"] == lab
                       and abs(r["T_seconds"] - sh) < 1e-12), None)
            if r0:
                N[f"pfd_shortest_{tag}_p99"] = r0["single"]
                N[f"band_shortest_{tag}_p99"] = r0["band_single"]
                N["shortest_T_seconds"] = sh
            print(f"  p = {p}, {lab:12s}: longest K inside a SIL band "
                  f"{kmax} s; at K = 1 s PFD-like "
                  f"{(ref or {}).get('single')}", flush=True)

    hom = N.get("pfd_shortest_hom_p99")
    dis = N.get("pfd_shortest_disp_p99")
    if hom and dis:
        N["dispersion_penalty_shortest_p99"] = dis / hom
    hom1 = N.get("pfd_T1_hom_p99")
    dis1 = N.get("pfd_T1_disp_p99")
    if hom1 and dis1:
        N["dispersion_penalty_T1_p99"] = dis1 / hom1

    N["p_grid"] = P_GRID
    N["lambda_DU_grid"] = LAMBDA_DU
    N["tau_grid"] = TAU
    json.dump(N, open(RESULTS / "comparison_numbers_v2.json", "w"), indent=1, default=str)
    print("comparison tables written;", len(N), "numbers")
    print("COMPARISON_DONE")


if __name__ == "__main__":
    main()
