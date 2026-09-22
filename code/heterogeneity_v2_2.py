"""heterogeneity_v2_2.py -- dot 2c: the non-homogeneous-p layer.

Nothing about the corpus, the protocol, the detector or its cache changes here.
The frozen protocol hash is checked on entry exactly as the V2.1 driver checks
it, and the events this script reads are the events that driver produced.  What
is new is one modelling layer and the tests that layer has to pass:

    homogeneous   the V2.1 model: one detection probability for every event,
                  estimated frame-weighted, with the beta-factor correction
    plug-in       each event predicted with its OWN measured p_e.  This is not
                  a validation -- the quantity being predicted is a function of
                  the same alarms -- and is reported to size the effect only
    LOVO          leave-one-video-out: the law of p is taken from the OTHER
                  videos of the same site and used to predict the held-out
                  one.  This is the honest out-of-sample test
    LOVO-Beta     the same, with a two-parameter Beta fitted to the training
                  p_e by moments, which is what the design side can carry

A fair comparison has to give every predictor the same information, so the
homogeneous baseline is also refitted leave-one-video-out (hom-LOVO): it sees
the same training events and differs from LOVO only in throwing the dispersion
away.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict

import numpy as np

import case_study_v2 as C
import caviar_v2_1 as CV
import model_v2 as M
import run_case_study_v2_1 as R

RESULTS = C.RESULTS
BOOT_VIDEO = 400


def write_csv(path, rows, fields=None):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def build_channels_once():
    motion = json.loads((RESULTS / "camera_motion_v2_1.json").read_text(
        encoding="utf-8"))
    mot, urfd = C.load_mot17(), C.load_urfd()
    caviar_static, _ = R.static_gate(CV.load_caviar(motion), motion)
    return C.build_channels(mot, urfd, C.PRIMARY, caviar=caviar_static,
                            scope="primary")


def events_from(chans, setting):
    out = []
    for e, alarm in C._events_of(chans, setting, keep_censored=False):
        out.append(dict(corpus=e["corpus"], video=e["video"], zone=e["zone"],
                        n=int(e["n_frames"]), fps=float(e["fps"]),
                        D=float(e["D_seconds"]), alarm=alarm,
                        pe=float(alarm.mean())))
    return out


def dispersion_by_gap(chans):
    """Is the dispersion of p_e an artefact of the event convention?  Recompute
    it at every gap-merge tolerance the protocol sweeps (R2 attack V6)."""
    rows = []
    for g in C.SENS["gap_s"]:
        evs = events_from(chans, dict(C.PRIMARY, gap_s=g))
        for site in sorted({e["corpus"] for e in evs}):
            pe = np.array([e["pe"] for e in evs if e["corpus"] == site])
            a, b, mu, var = M.beta_moments(pe)
            rows.append(dict(gap_s=g, corpus=site, n_events=len(pe),
                             mean_pe=mu, sd_pe=float(np.sqrt(var)),
                             frac_zero=float((pe == 0).mean()),
                             beta_conc=(None if a is None else a + b)))
    return rows


def load_events():
    """The V2.1 primary events, with each event's alarm vector and p_e."""
    motion = json.loads((RESULTS / "camera_motion_v2_1.json").read_text(
        encoding="utf-8"))
    mot, urfd = C.load_mot17(), C.load_urfd()
    caviar_static, _ = R.static_gate(CV.load_caviar(motion), motion)
    chans = C.build_channels(mot, urfd, C.PRIMARY, caviar=caviar_static,
                             scope="primary")
    out = []
    for e, alarm in C._events_of(chans, C.PRIMARY, keep_censored=False):
        out.append(dict(corpus=e["corpus"], video=e["video"], zone=e["zone"],
                        n=int(e["n_frames"]), fps=float(e["fps"]),
                        D=float(e["D_seconds"]), alarm=alarm,
                        pe=float(alarm.mean())))
    return out


def k_frames(T, fps):
    return max(1, int(round(T * fps)))


def measured_mixed(evs, T):
    """Exact phase enumeration, allowing a mix of frame rates."""
    miss = tot = 0
    for e in evs:
        K = k_frames(T, e["fps"])
        a = e["alarm"]
        for phi in range(K):
            tot += 1
            if not a[phi::K].any():
                miss += 1
    return (miss / tot if tot else float("nan")), tot


def predict(evs, T, train_pe, mode):
    """Event-weighted prediction over evs, integrating p over train_pe."""
    vals = []
    ab = None
    if mode == "beta":
        a, b, mu, _v = M.beta_moments(train_pe)
        ab = (a, b, mu)
    for e in evs:
        K = k_frames(T, e["fps"])
        if mode == "het":
            vals.append(float(M.p_miss_het_empirical(e["n"], K, train_pe)[0]))
        elif mode == "hom":
            vals.append(float(M.p_miss_exact(e["n"], K,
                                             float(np.mean(train_pe)))))
        elif mode == "beta":
            a, b, mu = ab
            if a is None:
                vals.append(float(M.p_miss_exact(e["n"], K, mu)))
            else:
                vals.append(float(M.p_miss_het_beta(e["n"], K, a, b)))
        elif mode == "plugin":
            vals.append(float(M.p_miss_exact(e["n"], K, e["pe"])))
        else:
            raise ValueError(mode)
    return float(np.mean(vals)) if vals else float("nan")


def lovo_prediction(evs, all_evs, T, mode):
    """Each event predicted from the p_e of the OTHER videos of its own site."""
    by_site = defaultdict(list)
    for e in evs:
        by_site[e["corpus"]].append(e)
    num = den = 0.0
    for site, sev in by_site.items():
        pool = [x for x in all_evs if x["corpus"] == site]
        by_video = defaultdict(list)
        for e in sev:
            by_video[e["video"]].append(e)
        for v, ve in by_video.items():
            train = np.array([x["pe"] for x in pool if x["video"] != v])
            if not len(train):
                continue
            num += len(ve) * predict(ve, T, train, mode)
            den += len(ve)
    return (num / den) if den else float("nan")


def het_by_site(evs, all_evs, T):
    """Plug the whole site's law of p into its own events, mixing sites by
    event count -- the pooled row the audit asks for."""
    num = den = 0.0
    for site in sorted({e["corpus"] for e in evs}):
        sel = [e for e in evs if e["corpus"] == site]
        train = np.array([x["pe"] for x in all_evs if x["corpus"] == site])
        num += len(sel) * predict(sel, T, train, "het")
        den += len(sel)
    return (num / den) if den else float("nan")


def main():
    freeze = C.check_protocol()
    print("protocol V2.1 still frozen at", freeze["sha256"][:16],
          "-- dot 2c changes no corpus, protocol or cache", flush=True)
    rng = np.random.default_rng(C.SEED)
    evs = load_events()
    sites = sorted({e["corpus"] for e in evs})
    print(f"{len(evs)} events, {len(sites)} sites, "
          f"{len({(e['corpus'], e['video']) for e in evs})} videos", flush=True)

    # ---- the heterogeneity itself, reported before any model is fitted
    pe_rows = []
    for site in ["pooled"] + sites:
        pe = np.array([e["pe"] for e in evs
                       if site == "pooled" or e["corpus"] == site])
        a, b, mu, var = M.beta_moments(pe)
        pe_rows.append(dict(
            corpus=site, n_events=len(pe), mean_pe=mu, var_pe=var,
            sd_pe=float(np.sqrt(var)), frac_zero=float((pe == 0).mean()),
            frac_one=float((pe == 1).mean()),
            q05=float(np.percentile(pe, 5)), median=float(np.median(pe)),
            q95=float(np.percentile(pe, 95)),
            beta_a=a, beta_b=b, beta_conc=(None if a is None else a + b)))
    write_csv(RESULTS / "pe_distribution_v2_2.csv", pe_rows)
    # is that dispersion an artefact of where one event is said to end?
    gap_rows = dispersion_by_gap(build_channels_once())
    write_csv(RESULTS / "pe_by_gap_v2_2.csv", gap_rows)
    for site in sorted({r["corpus"] for r in gap_rows}):
        sub = [r for r in gap_rows if r["corpus"] == site]
        tag = site.replace("CAVIAR-", "").replace("-", "").lower()
        N0 = (min(r["frac_zero"] for r in sub), max(r["frac_zero"] for r in sub))
        print(f"  gap sweep {site:14s} share of p_e = 0 over "
              f"g in {C.SENS['gap_s']}: {N0[0]:.3f}-{N0[1]:.3f}; "
              f"n_events {min(r['n_events'] for r in sub)}-"
              f"{max(r['n_events'] for r in sub)}", flush=True)
    for r in pe_rows:
        print(f"  p_e {r['corpus']:14s} mean {r['mean_pe']:.3f} "
              f"sd {r['sd_pe']:.3f} zero {100 * r['frac_zero']:.0f}% "
              f"one {100 * r['frac_one']:.0f}%", flush=True)

    # ---- measured against five predictors, on the frozen period grid
    V = {(r["corpus"], float(r["T_seconds"])): r
         for r in csv.DictReader(open(RESULTS / "miss_validation_v2.csv",
                                      encoding="utf-8"))}
    rows = []
    for T in C.T_GRID:
        for site in ["pooled"] + sites:
            sel = [e for e in evs if site == "pooled" or e["corpus"] == site]
            if not sel:
                continue
            meas, tot = measured_mixed(sel, T)
            ref = V.get((site, T))
            if ref is None:
                raise SystemExit(f"no V2.1 row for {site} at K = {T}")
            if abs(float(ref["miss_measured"]) - meas) > 1e-9:
                raise SystemExit(
                    f"measured miss disagrees with the V2.1 run at {site} "
                    f"K={T}: {meas} vs {ref['miss_measured']}")
            lo, hi = float(ref["miss_lo"]), float(ref["miss_hi"])
            plugin = predict(sel, T, None, "plugin")
            het_all = het_by_site(sel, evs, T)
            lovo = lovo_prediction(sel, evs, T, "het")
            lovo_beta = lovo_prediction(sel, evs, T, "beta")
            lovo_hom = lovo_prediction(sel, evs, T, "hom")
            Ks = sorted({k_frames(T, e["fps"]) for e in sel})
            rows.append(dict(
                T_seconds=T, corpus=site, n_events=len(sel), n_phases=tot,
                K_frames=Ks[0] if len(Ks) == 1 else min(Ks),
                miss_measured=meas, miss_lo=lo, miss_hi=hi,
                hom_beta=float(ref["miss_model_beta"]),
                hom_beta0=float(ref["miss_model_beta0"]),
                structural_floor=float(ref["structural_floor"]),
                het_plugin=plugin, het_all=het_all,
                het_lovo=lovo, het_lovo_beta=lovo_beta, hom_lovo=lovo_hom,
                inside_hom=bool(lo <= float(ref["miss_model_beta"]) <= hi),
                inside_hom_lovo=bool(lo <= lovo_hom <= hi),
                inside_plugin=bool(lo <= plugin <= hi),
                inside_lovo=bool(lo <= lovo <= hi),
                inside_lovo_beta=bool(lo <= lovo_beta <= hi),
                jensen_ok=bool(lovo >= lovo_hom - 1e-12),
                near_tautology=bool(min(Ks) <= 2)))
    write_csv(RESULTS / "het_validation_v2_2.csv", rows)

    N = {}
    for site in ["pooled"] + sites:
        sub = [r for r in rows if r["corpus"] == site]
        tag = site.replace("CAVIAR-", "").replace("-", "").lower()
        n = len(sub)
        for key, lab in (("inside_hom", "hom"), ("inside_hom_lovo", "homlovo"),
                         ("inside_plugin", "plugin"), ("inside_lovo", "lovo"),
                         ("inside_lovo_beta", "lovobeta")):
            N[f"inside_{lab}_{tag}"] = sum(1 for r in sub if r[key])
        N[f"n_periods_{tag}"] = n
        sub2 = [r for r in sub if not r["near_tautology"]]
        N[f"n_periods_informative_{tag}"] = len(sub2)
        for key, lab in (("inside_hom", "hom"), ("inside_lovo", "lovo"),
                         ("inside_lovo_beta", "lovobeta")):
            N[f"inside_informative_{lab}_{tag}"] = sum(
                1 for r in sub2 if r[key])
        N[f"jensen_holds_{tag}"] = all(r["jensen_ok"] for r in sub)
        r1 = next((r for r in sub if abs(r["T_seconds"] - 1.0) < 1e-9), None)
        if r1:
            for k in ("miss_measured", "miss_lo", "miss_hi", "hom_beta",
                      "het_lovo", "het_lovo_beta", "hom_lovo", "het_plugin"):
                N[f"{k}_T1p0_{tag}"] = r1[k]
        src = next(x for x in pe_rows if x["corpus"] == site)
        N[f"pe_mean_{tag}"] = src["mean_pe"]
        N[f"pe_sd_{tag}"] = src["sd_pe"]
        N[f"pe_frac_zero_{tag}"] = src["frac_zero"]
        N[f"pe_beta_conc_{tag}"] = src["beta_conc"]
        print(f"  {site:14s} inside CI: homogeneous "
              f"{N[f'inside_hom_{tag}']}/{n}, hom-LOVO "
              f"{N[f'inside_homlovo_{tag}']}/{n}, LOVO "
              f"{N[f'inside_lovo_{tag}']}/{n}, LOVO-Beta "
              f"{N[f'inside_lovobeta_{tag}']}/{n}, plug-in "
              f"{N[f'inside_plugin_{tag}']}/{n}", flush=True)

    # ---- per-video leave-one-video-out, bootstrapped over the video's events
    vrows = []
    for site in sites:
        sev = [e for e in evs if e["corpus"] == site]
        for v in sorted({e["video"] for e in sev}):
            ve = [e for e in sev if e["video"] == v]
            train = np.array([x["pe"] for x in sev if x["video"] != v])
            if not len(train):
                continue
            for T in (0.5, 1.0):
                meas, _tot = measured_mixed(ve, T)
                pred = predict(ve, T, train, "het")
                hom = predict(ve, T, train, "hom")
                idx = np.arange(len(ve))
                bs = [measured_mixed([ve[i] for i in rng.choice(idx, len(idx))],
                                     T)[0] for _ in range(BOOT_VIDEO)]
                lo = float(np.percentile(bs, 2.5))
                hi = float(np.percentile(bs, 97.5))
                vrows.append(dict(
                    corpus=site, video=v, T_seconds=T, n_events=len(ve),
                    miss_measured=meas, boot_lo=lo, boot_hi=hi,
                    het_lovo=pred, hom_lovo=hom,
                    inside_lovo=bool(lo <= pred <= hi),
                    inside_hom=bool(lo <= hom <= hi),
                    abs_err_lovo=abs(pred - meas),
                    abs_err_hom=abs(hom - meas)))
    write_csv(RESULTS / "lovo_v2_2.csv", vrows)
    for T in (0.5, 1.0):
        sub = [r for r in vrows if abs(r["T_seconds"] - T) < 1e-9]
        t = str(T).replace(".", "p")
        N[f"lovo_videos_T{t}"] = len(sub)
        N[f"lovo_inside_T{t}"] = sum(1 for r in sub if r["inside_lovo"])
        N[f"lovo_inside_hom_T{t}"] = sum(1 for r in sub if r["inside_hom"])
        N[f"lovo_medabs_T{t}"] = float(np.median(
            [r["abs_err_lovo"] for r in sub]))
        N[f"lovo_medabs_hom_T{t}"] = float(np.median(
            [r["abs_err_hom"] for r in sub]))
        print(f"  per-video LOVO at K = {T} s: {N[f'lovo_inside_T{t}']}/"
              f"{len(sub)} inside the video's own interval (homogeneous "
              f"{N[f'lovo_inside_hom_T{t}']}/{len(sub)}); median |error| "
              f"{N[f'lovo_medabs_T{t}']:.3f} against "
              f"{N[f'lovo_medabs_hom_T{t}']:.3f}", flush=True)

    # ---- Monte-Carlo check of the added layer
    worst, cells = 0.0, 0
    for site in sites:
        pe = np.array([e["pe"] for e in evs if e["corpus"] == site])
        for T in (0.2, 1.0, 3.0):
            for e in [x for x in evs if x["corpus"] == site][:40]:
                K = k_frames(T, e["fps"])
                an = float(M.p_miss_het_empirical(e["n"], K, pe)[0])
                ps = rng.choice(pe, 200000)
                m = np.floor(e["n"] / K)
                phi = e["n"] / K - m
                k = m + (rng.random(200000) < phi)
                sim = float(np.mean(np.where(k <= 0, 1.0, (1.0 - ps) ** k)))
                worst = max(worst, abs(an - sim))
                cells += 1
    N["het_mc_cells"] = cells
    N["het_mc_max_abs_err"] = worst
    print(f"  mixture MC check: {cells} cells, "
          f"max |analytic - MC| = {worst:.5f}", flush=True)

    for site in sorted({r["corpus"] for r in gap_rows}):
        sub = [r for r in gap_rows if r["corpus"] == site]
        tag = site.replace("CAVIAR-", "").replace("-", "").lower()
        N[f"gap_frac_zero_min_{tag}"] = min(r["frac_zero"] for r in sub)
        N[f"gap_frac_zero_max_{tag}"] = max(r["frac_zero"] for r in sub)
        N[f"gap_sd_min_{tag}"] = min(r["sd_pe"] for r in sub)
        N[f"gap_sd_max_{tag}"] = max(r["sd_pe"] for r in sub)
        N[f"gap_nevents_min_{tag}"] = min(r["n_events"] for r in sub)
        N[f"gap_nevents_max_{tag}"] = max(r["n_events"] for r in sub)
    N["gap_grid"] = C.SENS["gap_s"]

    N["protocol_sha256"] = freeze["sha256"]
    N["n_events_het"] = len(evs)
    N["boot_video_reps"] = BOOT_VIDEO
    json.dump(N, open(RESULTS / "numbers_v2_2.json", "w"), indent=1, default=str)
    print("wrote numbers_v2_2.json with", len(N), "keys")
    print("HETEROGENEITY_V2_2_DONE")


if __name__ == "__main__":
    main()
